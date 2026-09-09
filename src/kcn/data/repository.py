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
    BodyMeasurement,
    Food,
    FoodEntry,
    FoodSource,
    Goal,
    MacroTargets,
    Recipe, 
    RecipeItem,
    Sex,
    UserProfile,
    WaterEntry,
    Workout,
)


# --- Perfil ------------------------------------------------------------------

def save_profile(conn: sqlite3.Connection, profile: UserProfile) -> None:
    """Guarda (o actualiza) el perfil único del usuario."""
    conn.execute(
        """
        INSERT INTO profile (id, weight_kg, height_cm, age, sex, activity, goal,
                             protein_per_kg, fat_per_kg, weekly_rate_kg, meal_count,
                             carb_cycle_pct)
        VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            weight_kg=excluded.weight_kg, height_cm=excluded.height_cm,
            age=excluded.age, sex=excluded.sex, activity=excluded.activity,
            goal=excluded.goal, protein_per_kg=excluded.protein_per_kg,
            fat_per_kg=excluded.fat_per_kg, weekly_rate_kg=excluded.weekly_rate_kg,
            meal_count=excluded.meal_count, carb_cycle_pct=excluded.carb_cycle_pct
        """,
        (profile.weight_kg, profile.height_cm, profile.age,
         profile.sex.name, profile.activity.name, profile.goal.name,
         profile.protein_per_kg, profile.fat_per_kg,
         profile.weekly_rate_kg, profile.meal_count, profile.carb_cycle_pct),
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
        meal_count=row["meal_count"], carb_cycle_pct=row["carb_cycle_pct"],
    )


# --- Alimentos ---------------------------------------------------------------

def _row_to_food(row: sqlite3.Row) -> Food:
    return Food(
        id=row["id"], name=row["name"], brand=row["brand"], barcode=row["barcode"],
        source=FoodSource(row["source"]),
        kcal_per_100g=row["kcal_per_100g"], protein_per_100g=row["protein_per_100g"],
        carbs_per_100g=row["carbs_per_100g"], fat_per_100g=row["fat_per_100g"],
        default_serving_g=row["default_serving_g"],
        favorite=bool(row["favorite"]),
    )


def add_food(conn: sqlite3.Connection, food: Food) -> Food:
    """Inserta un alimento nuevo y le asigna el id generado."""
    cur = conn.execute(
        """
        INSERT INTO foods (name, brand, barcode, source, kcal_per_100g,
                           protein_per_100g, carbs_per_100g, fat_per_100g,
                           default_serving_g, favorite)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (food.name, food.brand, food.barcode, food.source.value,
         food.kcal_per_100g, food.protein_per_100g, food.carbs_per_100g,
         food.fat_per_100g, food.default_serving_g, int(food.favorite)),
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
            f.fat_per_100g, f.default_serving_g, f.favorite
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
            default_serving_g=r["default_serving_g"], favorite=bool(r["favorite"]),
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

# --- Edición y accesos rápidos ----------------------------------------------

def update_entry(conn: sqlite3.Connection, entry_id: int,
                 grams: float | None = None, meal_index: int | None = None) -> None:
    """Edita un registro existente (cantidad y/o comida)."""
    if grams is not None:
        if grams <= 0:
            raise ValueError("grams debe ser > 0")
        conn.execute("UPDATE food_entries SET grams = ? WHERE id = ?", (grams, entry_id))
    if meal_index is not None:
        conn.execute("UPDATE food_entries SET meal_index = ? WHERE id = ?",
                     (meal_index, entry_id))
    conn.commit()


def set_favorite(conn: sqlite3.Connection, food_id: int, favorite: bool = True) -> None:
    conn.execute("UPDATE foods SET favorite = ? WHERE id = ?", (int(favorite), food_id))
    conn.commit()


def list_favorites(conn: sqlite3.Connection) -> list[Food]:
    rows = conn.execute("SELECT * FROM foods WHERE favorite = 1 ORDER BY name").fetchall()
    return [_row_to_food(r) for r in rows]


def recent_foods(conn: sqlite3.Connection, limit: int = 10) -> list[Food]:
    """Alimentos usados más recientemente (para registro rápido)."""
    rows = conn.execute(
        """
        SELECT f.*, MAX(e.at_ts) AS last_used
        FROM foods f JOIN food_entries e ON e.food_id = f.id
        GROUP BY f.id ORDER BY last_used DESC LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [_row_to_food(r) for r in rows]


def frequent_foods(conn: sqlite3.Connection, limit: int = 10) -> list[Food]:
    """Alimentos más usados (por número de registros)."""
    rows = conn.execute(
        """
        SELECT f.*, COUNT(e.id) AS uses
        FROM foods f JOIN food_entries e ON e.food_id = f.id
        GROUP BY f.id ORDER BY uses DESC, f.name LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [_row_to_food(r) for r in rows]

# --- Entrenos ----------------------------------------------------------------

def add_workout(conn: sqlite3.Connection, workout: Workout) -> Workout:
    cur = conn.execute(
        "INSERT INTO workouts (description, calories, duration_min, on_date) "
        "VALUES (?, ?, ?, ?)",
        (workout.description, workout.calories, workout.duration_min,
         workout.on.isoformat()),
    )
    conn.commit()
    workout.id = cur.lastrowid
    return workout


def get_workouts_for_date(conn: sqlite3.Connection, on: date) -> list[Workout]:
    rows = conn.execute(
        "SELECT * FROM workouts WHERE on_date = ? ORDER BY id",
        (on.isoformat(),),
    ).fetchall()
    return [
        Workout(id=r["id"], description=r["description"], calories=r["calories"],
                duration_min=r["duration_min"], on=date.fromisoformat(r["on_date"]))
        for r in rows
    ]


def delete_workout(conn: sqlite3.Connection, workout_id: int) -> None:
    conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    conn.commit()


def day_workout_calories(conn: sqlite3.Connection, on: date) -> int:
    """kcal totales quemadas en entrenos ese día (0 si no hay)."""
    row = conn.execute(
        "SELECT COALESCE(SUM(calories), 0) AS c FROM workouts WHERE on_date = ?",
        (on.isoformat(),),
    ).fetchone()
    return int(row["c"])

# --- Medidas corporales ------------------------------------------------------

def _row_to_measurement(r: sqlite3.Row) -> BodyMeasurement:
    return BodyMeasurement(
        id=r["id"], on=date.fromisoformat(r["on_date"]),
        weight_kg=r["weight_kg"], body_fat_pct=r["body_fat_pct"],
        water_pct=r["water_pct"], muscle_mass_kg=r["muscle_mass_kg"],
        bone_mass_kg=r["bone_mass_kg"], visceral_fat=r["visceral_fat"],
        metabolic_age=r["metabolic_age"], note=r["note"],
    )


def add_measurement(conn: sqlite3.Connection, m: BodyMeasurement) -> BodyMeasurement:
    cur = conn.execute(
        """
        INSERT INTO body_measurements (on_date, weight_kg, body_fat_pct, water_pct,
            muscle_mass_kg, bone_mass_kg, visceral_fat, metabolic_age, note)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (m.on.isoformat(), m.weight_kg, m.body_fat_pct, m.water_pct,
         m.muscle_mass_kg, m.bone_mass_kg, m.visceral_fat, m.metabolic_age, m.note),
    )
    conn.commit()
    m.id = cur.lastrowid
    return m


def get_measurements(conn: sqlite3.Connection, limit: int | None = None) -> list[BodyMeasurement]:
    """Historial completo, de más reciente a más antiguo."""
    q = "SELECT * FROM body_measurements ORDER BY on_date DESC, id DESC"
    rows = (conn.execute(q + " LIMIT ?", (limit,)) if limit else conn.execute(q)).fetchall()
    return [_row_to_measurement(r) for r in rows]


def latest_measurement(conn: sqlite3.Connection) -> BodyMeasurement | None:
    rows = get_measurements(conn, limit=1)
    return rows[0] if rows else None


def weight_series(conn: sqlite3.Connection) -> list[tuple[date, float]]:
    """Serie de peso (fecha, kg) en orden ascendente, para gráficas y ajuste automático."""
    rows = conn.execute(
        "SELECT on_date, weight_kg FROM body_measurements "
        "WHERE weight_kg IS NOT NULL ORDER BY on_date ASC, id ASC"
    ).fetchall()
    return [(date.fromisoformat(r["on_date"]), r["weight_kg"]) for r in rows]


def delete_measurement(conn: sqlite3.Connection, measurement_id: int) -> None:
    conn.execute("DELETE FROM body_measurements WHERE id = ?", (measurement_id,))
    conn.commit()

# --- Agua --------------------------------------------------------------------

def add_water(conn: sqlite3.Connection, entry: WaterEntry) -> WaterEntry:
    cur = conn.execute(
        "INSERT INTO water_entries (ml, on_date, at_ts) VALUES (?, ?, ?)",
        (entry.ml, entry.on.isoformat(), entry.at.isoformat()),
    )
    conn.commit()
    entry.id = cur.lastrowid
    return entry


def get_water_for_date(conn: sqlite3.Connection, on: date) -> list[WaterEntry]:
    rows = conn.execute(
        "SELECT * FROM water_entries WHERE on_date = ? ORDER BY at_ts",
        (on.isoformat(),),
    ).fetchall()
    return [
        WaterEntry(id=r["id"], ml=r["ml"], on=date.fromisoformat(r["on_date"]),
                   at=datetime.fromisoformat(r["at_ts"]))
        for r in rows
    ]


def day_water_ml(conn: sqlite3.Connection, on: date) -> int:
    """Total de ml bebidos ese día (0 si no hay)."""
    row = conn.execute(
        "SELECT COALESCE(SUM(ml), 0) AS ml FROM water_entries WHERE on_date = ?",
        (on.isoformat(),),
    ).fetchone()
    return int(row["ml"])


def delete_water(conn: sqlite3.Connection, water_id: int) -> None:
    conn.execute("DELETE FROM water_entries WHERE id = ?", (water_id,))
    conn.commit()

# --- Recetas -----------------------------------------------------------------

def add_recipe(conn: sqlite3.Connection, recipe: Recipe) -> Recipe:
    """Guarda una receta y sus ingredientes (guardando alimentos nuevos si hace falta)."""
    cur = conn.execute("INSERT INTO recipes (name, servings) VALUES (?, ?)",
                       (recipe.name, recipe.servings))
    recipe.id = cur.lastrowid
    for item in recipe.items:
        if item.food.id is None:
            item.food = add_food(conn, item.food)
        conn.execute("INSERT INTO recipe_items (recipe_id, food_id, grams) VALUES (?, ?, ?)",
                     (recipe.id, item.food.id, item.grams))
    conn.commit()
    return recipe


def get_recipe(conn: sqlite3.Connection, recipe_id: int) -> Recipe | None:
    row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        return None
    item_rows = conn.execute(
        """
        SELECT ri.grams, f.*
        FROM recipe_items ri JOIN foods f ON f.id = ri.food_id
        WHERE ri.recipe_id = ? ORDER BY ri.id
        """,
        (recipe_id,),
    ).fetchall()
    items = [RecipeItem(food=_row_to_food(r), grams=r["grams"]) for r in item_rows]
    return Recipe(id=row["id"], name=row["name"], servings=row["servings"], items=items)


def list_recipes(conn: sqlite3.Connection) -> list[Recipe]:
    ids = [r["id"] for r in conn.execute("SELECT id FROM recipes ORDER BY name")]
    return [get_recipe(conn, rid) for rid in ids]


def delete_recipe(conn: sqlite3.Connection, recipe_id: int) -> None:
    conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    conn.commit()


def log_recipe(conn: sqlite3.Connection, recipe_id: int, meal_index: int = 0,
               servings: float = 1) -> list[FoodEntry]:
    """Registra una receta como comidas del día (una entrada por ingrediente).

    `servings` = cuántas raciones te comes ahora. Escala los ingredientes
    respecto a las raciones totales de la receta.
    """
    recipe = get_recipe(conn, recipe_id)
    if recipe is None:
        raise ValueError("receta no encontrada")
    factor = servings / recipe.servings
    entries = []
    for item in recipe.items:
        entry = FoodEntry(food=item.food, grams=item.grams * factor, meal_index=meal_index)
        entries.append(add_entry(conn, entry))
    return entries