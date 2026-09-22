"""Acceso a datos del módulo de hábitos (crea sus tablas al vuelo)."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from kcn.habits.models import Habit

_SCHEMA = """
CREATE TABLE IF NOT EXISTS habits (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL,
    active  INTEGER NOT NULL DEFAULT 1,
    created TEXT
);
CREATE TABLE IF NOT EXISTS habit_logs (
    id       INTEGER PRIMARY KEY,
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    on_date  TEXT NOT NULL,
    UNIQUE(habit_id, on_date)
);
CREATE INDEX IF NOT EXISTS idx_habitlogs_date ON habit_logs(on_date);
"""


def _ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def add_habit(conn, name: str) -> Habit:
    _ensure(conn)
    cur = conn.execute("INSERT INTO habits (name, active, created) VALUES (?, 1, ?)",
                       (name, date.today().isoformat()))
    conn.commit()
    return Habit(id=cur.lastrowid, name=name, active=True)


def list_habits(conn, active_only: bool = True) -> list[Habit]:
    _ensure(conn)
    q = "SELECT * FROM habits" + (" WHERE active = 1" if active_only else "") + " ORDER BY id"
    return [Habit(id=r["id"], name=r["name"], active=bool(r["active"]))
            for r in conn.execute(q).fetchall()]


def delete_habit(conn, habit_id: int) -> None:
    _ensure(conn)
    conn.execute("DELETE FROM habits WHERE id = ?", (habit_id,))
    conn.commit()


def set_done(conn, habit_id: int, on: date, done: bool) -> None:
    _ensure(conn)
    if done:
        conn.execute("INSERT OR IGNORE INTO habit_logs (habit_id, on_date) VALUES (?, ?)",
                     (habit_id, on.isoformat()))
    else:
        conn.execute("DELETE FROM habit_logs WHERE habit_id = ? AND on_date = ?",
                     (habit_id, on.isoformat()))
    conn.commit()


def done_ids_for_date(conn, on: date) -> set[int]:
    _ensure(conn)
    rows = conn.execute("SELECT habit_id FROM habit_logs WHERE on_date = ?", (on.isoformat(),)).fetchall()
    return {r["habit_id"] for r in rows}


def streak(conn, habit_id: int, today: date) -> int:
    _ensure(conn)
    rows = conn.execute("SELECT on_date FROM habit_logs WHERE habit_id = ?", (habit_id,)).fetchall()
    done = {date.fromisoformat(r["on_date"]) for r in rows}
    n, d = 0, today
    while d in done:
        n += 1
        d -= timedelta(days=1)
    return n
