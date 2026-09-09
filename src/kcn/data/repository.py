"""Repositorio: guarda y lee los modelos del dominio en SQLite.

Traduce entre las filas de la base de datos y los objetos del `core`
(UserProfile, Food, FoodEntry). El resto de la app nunca escribe SQL: llama a
estas funciones.
"""

from __future__ import annotations

import sqlite3
from datetime import date, datetime

from kcn.core.models import (
    ActivityLevel,
    Food,
    FoodEntry,
    FoodSource,
    Goal,
    MacroTargets,
    Sex,
    UserProfile,
)


# --- Perfil ------------------------------------------------------------------

def save_profile(conn: sqlite3.Connection, profile: UserProfile) -> None:
    """Guarda (o actualiza) el perfil único del usuario."""
    conn.execute(
        """
        INSERT INTO profile (id, weight_kg, height_cm, age, sex, activity, goal,
                             protein_per_kg, fat_per_kg, weekly_rate_kg, meal_count)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            weight_kg=excluded.weight_kg, height_cm=excluded.height_cm,
            age=excluded.age, sex=excluded.sex, activity=excluded.activity,
            goal=excluded.goal, protein_per_kg=excluded.protein_per_kg,
            fat_per_kg=excluded.fat_per_kg, weekly_rate_kg=excluded.weekly_rate_kg,
            meal_count=excluded.meal_count
        """,
        (
            profile.weight_kg, profile.height_cm, profile.age,
            profile.sex.name, profile.activity.name, profile.goal.name,
            profile.protein_per_kg, profile.fat_per_kg,
            profile.weekly_rate_kg, profile.meal_count,
        ),
    )
    conn.commit()


def get_profile(conn: sqlite3.Connection) -> UserProfile | None:
    """Devuelve el perfil, o None si aún no se ha creado."""
    row = conn.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    if row is None:
        return None
    return UserProfile(
        weight_kg=row["weight_kg"], height_cm=row["height_cm"], age=row["age"],
        sex=Sex[row["sex"]], activity=ActivityLevel[row["activity"]],
        goal=Goal[row["goal"]], protein_per_kg=row["protein_per_kg"],
        fat_per_kg=row["fat_per_kg"], weekly_rate_kg=row["weekly_rate_kg"],
        meal_count=row["meal_count"],
    )


# --- Alimentos ---------------------------------------------------------------

def _row_to_food(row: sqlite3.Row) -> Food:
    return Food(
        id=row["id"], name=row["name"], brand=row["brand"], barcode=row["barcode"],
        source=FoodSource(row["source"]),
        kcal_per_100g=row["kcal_per_100g"], protein_per_100g=row["protein_per_100g"],
        carbs_per_100g=row["carbs_per_100g"], fat_per_100g=row["fat_per_100g"],
        default_serving_g=row["default_serving_g"],
    )


def add_food(conn: sqlite3.Connection, food: Food) -> Food:
    """Inserta un alimento nuevo y le asigna el id generado."""
    cur = conn.execute(
        """
        INSERT INTO foods (name, brand, barcode, source, kcal_per_100g,
                           protein_per_100g, carbs_per_100g, fat_per_100g,
                           default_serving_g)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (food.name, food.brand, food.barcode, food.source.value,
         food.kcal_per_100g, food.protein_per_100g, food.carbs_per_100g,
         food.fat_per_100g, food.default_serving_g),
    )
    conn.commit()
    food.id = cur.lastrowid
    return food


def upsert_food_by_barcode(conn: sqlite3.Connection, food: Food) -> Food:
    """Si ya existe un alimento con ese código de barras, lo actualiza; si no, lo crea.

    Útil para cachear productos de Open Food Facts sin duplicarlos.
    """
    if food.barcode:
        existing = get_food_by_barcode(conn, food.barcode)
        if existing:
            conn.execute(
                """
                UPDATE foods SET name=?, brand=?, source=?, kcal_per_100g=?,
                    protein_per_100g=?, carbs_per_100g=?, fat_per_100g=?,
                    default_serving_g=? WHERE id=?
                """,
                (food.name, food.brand, food.source.value, food.kcal_per_100g,
                 food.protein_per_100g, food.carbs_per_100g, food.fat_per_100g,
                 food.default_serving_g, existing.id),
            )
            conn.commit()
            food.id = existing.id
            return food
    return add_food(conn, food)


def get_food(conn: sqlite3.Connection, food_id: int) -> Food | None:
    row = conn.execute("SELECT * FROM foods WHERE id = ?", (food_id,)).fetchone()
    return _row_to_food(row) if row else None


def get_food_by_barcode(conn: sqlite3.Connection, barcode: str) -> Food | None:
    row = conn.execute("SELECT * FROM foods WHERE barcode = ?", (barcode,)).fetchone()
    return _row_to_food(row) if row else None


def search_foods(conn: sqlite3.Connection, query: str, limit: int = 20) -> list[Food]:
    """Busca alimentos por nombre (parcial, sin distinguir mayúsculas)."""
    rows = conn.execute(
        "SELECT * FROM foods WHERE name LIKE ? ORDER BY name LIMIT ?",
        (f"%{query}%", limit),
    ).fetchall()
    return [_row_to_food(r) for r in rows]


def delete_food(conn: sqlite3.Connection, food_id: int) -> None:
    conn.execute("DELETE FROM foods WHERE id = ?", (food_id,))
    conn.commit()


# --- Registros de comida -----------------------------------------------------

def add_entry(conn: sqlite3.Connection, entry: FoodEntry) -> FoodEntry:
    """Registra un alimento consumido. Si el alimento aún no está guardado, lo guarda."""
    if entry.food.id is None:
        entry.food = add_food(conn, entry.food)
    cur = conn.execute(
        """
        INSERT INTO food_entries (food_id, grams, meal_index, on_date, at_ts)
        VALUES (?, ?, ?, ?, ?)
        """,
        (entry.food.id, entry.grams, entry.meal_index,
         entry.on.isoformat(), entry.at.isoformat()),
    )
    conn.commit()
    entry.id = cur.lastrowid
    return entry


def get_entries_for_date(conn: sqlite3.Connection, on: date) -> list[FoodEntry]:
    """Todos los registros de un día, ordenados por comida y hora."""
    rows = conn.execute(
        """
        SELECT
            e.id AS entry_id, e.grams, e.meal_index, e.on_date, e.at_ts,
            f.id AS food_id, f.name, f.brand, f.barcode, f.source,
            f.kcal_per_100g, f.protein_per_100g, f.carbs_per_100g,
            f.fat_per_100g, f.default_serving_g
        FROM food_entries e
        JOIN foods f ON f.id = e.food_id
        WHERE e.on_date = ?
        ORDER BY e.meal_index, e.at_ts
        """,
        (on.isoformat(),),
    ).fetchall()

    entries: list[FoodEntry] = []
    for r in rows:
        food = Food(
            id=r["food_id"], name=r["name"], brand=r["brand"], barcode=r["barcode"],
            source=FoodSource(r["source"]),
            kcal_per_100g=r["kcal_per_100g"], protein_per_100g=r["protein_per_100g"],
            carbs_per_100g=r["carbs_per_100g"], fat_per_100g=r["fat_per_100g"],
            default_serving_g=r["default_serving_g"],
        )
        entries.append(FoodEntry(
            id=r["entry_id"], food=food, grams=r["grams"],
            meal_index=r["meal_index"],
            on=date.fromisoformat(r["on_date"]),
            at=datetime.fromisoformat(r["at_ts"]),
        ))
    return entries


def delete_entry(conn: sqlite3.Connection, entry_id: int) -> None:
    conn.execute("DELETE FROM food_entries WHERE id = ?", (entry_id,))
    conn.commit()


def day_totals(conn: sqlite3.Connection, on: date) -> MacroTargets:
    """Suma de macros consumidos en un día (el contador diario)."""
    total = MacroTargets(0, 0, 0, 0)
    for entry in get_entries_for_date(conn, on):
        total = total + entry.macros
    return total