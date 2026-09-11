"""Capa de persistencia: conexión a SQLite y esquema de la base de datos.

Aquí NO hay lógica de negocio, solo el "cómo" se guardan los datos. La app es
local-first: un único fichero SQLite en el equipo del usuario.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

# Fichero de datos por defecto: ~/.kcn/kcn.db (oculto, en el home del usuario).
DEFAULT_DB_PATH = Path.home() / ".kcn" / "kcn.db"

# Esquema. Se ejecuta con "IF NOT EXISTS", así que es seguro llamarlo siempre.
SCHEMA = """
-- Perfil del usuario: una sola fila (CHECK id = 1 lo garantiza).
CREATE TABLE IF NOT EXISTS profile (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    weight_kg      REAL    NOT NULL,
    height_cm      REAL    NOT NULL,
    age            INTEGER NOT NULL,
    sex            TEXT    NOT NULL,
    activity       TEXT    NOT NULL,
    goal           TEXT    NOT NULL,
    protein_per_kg REAL    NOT NULL,
    fat_per_kg     REAL    NOT NULL,
    weekly_rate_kg REAL    NOT NULL,
    meal_count     INTEGER NOT NULL
);

-- Biblioteca de alimentos: tus alimentos propios y los cacheados de Open Food Facts.
CREATE TABLE IF NOT EXISTS foods (
    id                INTEGER PRIMARY KEY,
    name              TEXT NOT NULL,
    brand             TEXT,
    barcode           TEXT UNIQUE,
    source            TEXT NOT NULL,
    kcal_per_100g     REAL NOT NULL,
    protein_per_100g  REAL NOT NULL,
    carbs_per_100g    REAL NOT NULL,
    fat_per_100g      REAL NOT NULL,
    default_serving_g REAL
);

CREATE INDEX IF NOT EXISTS idx_foods_name ON foods(name);

-- Registros de comida: qué has comido, cuánto, en qué comida y qué día.
CREATE TABLE IF NOT EXISTS food_entries (
    id         INTEGER PRIMARY KEY,
    food_id    INTEGER NOT NULL REFERENCES foods(id) ON DELETE CASCADE,
    grams      REAL    NOT NULL,
    meal_index INTEGER NOT NULL DEFAULT 0,
    on_date    TEXT    NOT NULL,   -- fecha ISO 'YYYY-MM-DD' (para el total del día)
    at_ts      TEXT    NOT NULL    -- instante ISO completo (para ordenar por hora)
);

CREATE INDEX IF NOT EXISTS idx_entries_date ON food_entries(on_date);


-- Entrenos: kcal quemadas que amplían el margen del día.
CREATE TABLE IF NOT EXISTS workouts (
    id           INTEGER PRIMARY KEY,
    description  TEXT    NOT NULL,
    calories     INTEGER NOT NULL,
    duration_min INTEGER,
    on_date      TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_workouts_date ON workouts(on_date);


-- Historial de medidas corporales (báscula). Todos los campos opcionales.
CREATE TABLE IF NOT EXISTS body_measurements (
    id             INTEGER PRIMARY KEY,
    on_date        TEXT NOT NULL,
    weight_kg      REAL,
    body_fat_pct   REAL,
    water_pct      REAL,
    muscle_mass_kg REAL,
    bone_mass_kg   REAL,
    visceral_fat   REAL,
    metabolic_age  INTEGER,
    note           TEXT
);

CREATE INDEX IF NOT EXISTS idx_measurements_date ON body_measurements(on_date);


-- Registros de agua bebida.
CREATE TABLE IF NOT EXISTS water_entries (
    id      INTEGER PRIMARY KEY,
    ml      INTEGER NOT NULL,
    on_date TEXT    NOT NULL,
    at_ts   TEXT    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_water_date ON water_entries(on_date);


-- Recetas / platos compuestos.
CREATE TABLE IF NOT EXISTS recipes (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL,
    servings INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS recipe_items (
    id        INTEGER PRIMARY KEY,
    recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
    food_id   INTEGER NOT NULL REFERENCES foods(id),
    grams     REAL    NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_recipe_items_recipe ON recipe_items(recipe_id);


-- Ajustes de la app (clave/valor en JSON), p. ej. los recordatorios.
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


def get_connection(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Abre la base de datos (creando la carpeta si hace falta) y la configura.

    Usa ':memory:' como ruta para una base de datos en memoria (ideal en tests).
    """
    if db_path != ":memory:":
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        db_path = str(path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row          # acceder a columnas por nombre: row["name"]
    conn.execute("PRAGMA foreign_keys = ON")  # respetar las claves foráneas
    return conn

def _migrate(conn: sqlite3.Connection) -> None:
    """Migraciones ligeras para bases de datos ya existentes."""
    cols = [r["name"] for r in conn.execute("PRAGMA table_info(foods)")]
    if "favorite" not in cols:
        conn.execute("ALTER TABLE foods ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")

    pcols = [r["name"] for r in conn.execute("PRAGMA table_info(profile)")]
    if "carb_cycle_pct" not in pcols:
        conn.execute("ALTER TABLE profile ADD COLUMN carb_cycle_pct REAL NOT NULL DEFAULT 0")

    cols = [r["name"] for r in conn.execute("PRAGMA table_info(foods)")]
    if "favorite" not in cols:
        conn.execute("ALTER TABLE foods ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
    if "role" not in cols:
        conn.execute("ALTER TABLE foods ADD COLUMN role TEXT")
    if "meal_tags" not in cols:
        conn.execute("ALTER TABLE foods ADD COLUMN meal_tags TEXT")

    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    """Crea las tablas e índices si no existen."""
    conn.executescript(SCHEMA)
    conn.commit()
    _migrate(conn)


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Atajo: abre la conexión y se asegura de que el esquema existe."""
    conn = get_connection(db_path)
    init_db(conn)
    return conn



