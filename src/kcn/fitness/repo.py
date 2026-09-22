"""Acceso a datos del módulo de entrenos (crea sus tablas al vuelo)."""

from __future__ import annotations

import sqlite3
from datetime import date

from kcn.fitness.models import Exercise, ExerciseSet, WorkoutSession

_SCHEMA = """
CREATE TABLE IF NOT EXISTS exercises (
    id           INTEGER PRIMARY KEY,
    name         TEXT NOT NULL,
    category     TEXT NOT NULL DEFAULT 'strength',
    muscle_group TEXT
);
CREATE TABLE IF NOT EXISTS workout_sessions (
    id           INTEGER PRIMARY KEY,
    on_date      TEXT NOT NULL,
    name         TEXT,
    calories     INTEGER,
    duration_min INTEGER,
    note         TEXT
);
CREATE TABLE IF NOT EXISTS workout_sets (
    id          INTEGER PRIMARY KEY,
    session_id  INTEGER NOT NULL REFERENCES workout_sessions(id) ON DELETE CASCADE,
    exercise_id INTEGER NOT NULL REFERENCES exercises(id),
    weight_kg   REAL,
    reps        INTEGER,
    position    INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_wsessions_date ON workout_sessions(on_date);
CREATE INDEX IF NOT EXISTS idx_wsets_session ON workout_sets(session_id);
CREATE INDEX IF NOT EXISTS idx_exercises_name ON exercises(name);
"""


def _ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


# --- Ejercicios --------------------------------------------------------------

def _row_to_exercise(r) -> Exercise:
    return Exercise(id=r["id"], name=r["name"], category=r["category"],
                    muscle_group=r["muscle_group"])


def add_exercise(conn, ex: Exercise) -> Exercise:
    _ensure(conn)
    cur = conn.execute("INSERT INTO exercises (name, category, muscle_group) VALUES (?, ?, ?)",
                       (ex.name, ex.category, ex.muscle_group))
    conn.commit()
    ex.id = cur.lastrowid
    return ex


def search_exercises(conn, query: str = "", limit: int = 30) -> list[Exercise]:
    _ensure(conn)
    rows = conn.execute("SELECT * FROM exercises WHERE name LIKE ? ORDER BY name LIMIT ?",
                        (f"%{query}%", limit)).fetchall()
    return [_row_to_exercise(r) for r in rows]


def get_or_create_exercise(conn, name: str, category: str = "strength",
                           muscle_group: str | None = None) -> Exercise:
    _ensure(conn)
    r = conn.execute("SELECT * FROM exercises WHERE name = ? COLLATE NOCASE", (name,)).fetchone()
    if r:
        return _row_to_exercise(r)
    return add_exercise(conn, Exercise(name=name, category=category, muscle_group=muscle_group))


# --- Sesiones ----------------------------------------------------------------

def _row_to_session(conn, r) -> WorkoutSession:
    set_rows = conn.execute(
        """SELECT ws.id AS set_id, ws.weight_kg, ws.reps, ws.exercise_id,
                  e.name AS ex_name, e.category AS ex_cat, e.muscle_group AS ex_mg
           FROM workout_sets ws JOIN exercises e ON e.id = ws.exercise_id
           WHERE ws.session_id = ? ORDER BY ws.position""", (r["id"],)).fetchall()
    sets = [ExerciseSet(
        exercise=Exercise(id=sr["exercise_id"], name=sr["ex_name"],
                          category=sr["ex_cat"], muscle_group=sr["ex_mg"]),
        weight_kg=sr["weight_kg"], reps=sr["reps"], id=sr["set_id"]) for sr in set_rows]
    return WorkoutSession(id=r["id"], on=date.fromisoformat(r["on_date"]), name=r["name"],
                          calories=r["calories"], duration_min=r["duration_min"],
                          note=r["note"], sets=sets)


def add_session(conn, session: WorkoutSession) -> WorkoutSession:
    _ensure(conn)
    cur = conn.execute(
        "INSERT INTO workout_sessions (on_date, name, calories, duration_min, note) "
        "VALUES (?, ?, ?, ?, ?)",
        (session.on.isoformat(), session.name, session.calories,
         session.duration_min, session.note))
    session.id = cur.lastrowid
    for i, s in enumerate(session.sets):
        if s.exercise.id is None:
            s.exercise = get_or_create_exercise(conn, s.exercise.name, s.exercise.category,
                                                s.exercise.muscle_group)
        conn.execute(
            "INSERT INTO workout_sets (session_id, exercise_id, weight_kg, reps, position) "
            "VALUES (?, ?, ?, ?, ?)",
            (session.id, s.exercise.id, s.weight_kg, s.reps, i))
    conn.commit()
    return session


def get_sessions_for_date(conn, on: date) -> list[WorkoutSession]:
    _ensure(conn)
    rows = conn.execute("SELECT * FROM workout_sessions WHERE on_date = ? ORDER BY id",
                        (on.isoformat(),)).fetchall()
    return [_row_to_session(conn, r) for r in rows]


def delete_session(conn, session_id: int) -> None:
    _ensure(conn)
    conn.execute("DELETE FROM workout_sessions WHERE id = ?", (session_id,))
    conn.commit()


def session_calories_for_date(conn, on: date) -> int:
    _ensure(conn)
    row = conn.execute("SELECT COALESCE(SUM(calories), 0) AS c FROM workout_sessions WHERE on_date = ?",
                       (on.isoformat(),)).fetchone()
    return int(row["c"])


def exercise_best_series(conn, exercise_id: int) -> list[tuple[date, float]]:
    """Mejor peso levantado por día de un ejercicio (para progreso/PRs)."""
    _ensure(conn)
    rows = conn.execute(
        """SELECT s.on_date AS d, MAX(ws.weight_kg) AS w
           FROM workout_sets ws JOIN workout_sessions s ON s.id = ws.session_id
           WHERE ws.exercise_id = ? AND ws.weight_kg IS NOT NULL
           GROUP BY s.on_date ORDER BY s.on_date""", (exercise_id,)).fetchall()
    return [(date.fromisoformat(r["d"]), r["w"]) for r in rows]