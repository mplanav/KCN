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


def init_db(conn: sqlite3.Connection) -> None:
    """Crea las tablas e índices si no existen."""
    conn.executescript(SCHEMA)
    conn.commit()


def connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    """Atajo: abre la conexión y se asegura de que el esquema existe."""
    conn = get_connection(db_path)
    init_db(conn)
    return conn