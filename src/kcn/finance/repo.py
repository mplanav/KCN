"""Acceso a datos del módulo de finanzas (crea sus tablas al vuelo)."""

from __future__ import annotations

import sqlite3
from datetime import date

from kcn.finance.models import Category, Expense, SavingsGoal

_SCHEMA = """
CREATE TABLE IF NOT EXISTS finance_settings (
    id             INTEGER PRIMARY KEY CHECK (id = 1),
    monthly_income REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS budget_categories (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    monthly_limit REAL NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS expenses (
    id          INTEGER PRIMARY KEY,
    on_date     TEXT NOT NULL,
    amount      REAL NOT NULL,
    category_id INTEGER REFERENCES budget_categories(id) ON DELETE SET NULL,
    note        TEXT
);
CREATE TABLE IF NOT EXISTS savings_goals (
    id     INTEGER PRIMARY KEY,
    name   TEXT NOT NULL,
    target REAL NOT NULL DEFAULT 0,
    saved  REAL NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_expenses_date ON expenses(on_date);
"""


def _ensure(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    conn.commit()


def _month_prefix(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}"


# --- Nómina ------------------------------------------------------------------

def set_income(conn, amount: float) -> None:
    _ensure(conn)
    conn.execute(
        "INSERT INTO finance_settings (id, monthly_income) VALUES (1, ?) "
        "ON CONFLICT(id) DO UPDATE SET monthly_income = excluded.monthly_income", (amount,))
    conn.commit()


def get_income(conn) -> float:
    _ensure(conn)
    r = conn.execute("SELECT monthly_income FROM finance_settings WHERE id = 1").fetchone()
    return float(r["monthly_income"]) if r else 0.0


# --- Categorías --------------------------------------------------------------

def add_category(conn, name: str, monthly_limit: float = 0.0) -> Category:
    _ensure(conn)
    cur = conn.execute("INSERT INTO budget_categories (name, monthly_limit) VALUES (?, ?)",
                       (name, monthly_limit))
    conn.commit()
    return Category(id=cur.lastrowid, name=name, monthly_limit=monthly_limit)


def list_categories(conn) -> list[Category]:
    _ensure(conn)
    return [Category(id=r["id"], name=r["name"], monthly_limit=r["monthly_limit"])
            for r in conn.execute("SELECT * FROM budget_categories ORDER BY name").fetchall()]


def delete_category(conn, category_id: int) -> None:
    _ensure(conn)
    conn.execute("DELETE FROM budget_categories WHERE id = ?", (category_id,))
    conn.commit()


# --- Gastos ------------------------------------------------------------------

def add_expense(conn, expense: Expense) -> Expense:
    _ensure(conn)
    cur = conn.execute(
        "INSERT INTO expenses (on_date, amount, category_id, note) VALUES (?, ?, ?, ?)",
        (expense.on.isoformat(), expense.amount, expense.category_id, expense.note))
    conn.commit()
    expense.id = cur.lastrowid
    return expense


def expenses_for_month(conn, year: int, month: int) -> list[Expense]:
    _ensure(conn)
    rows = conn.execute(
        "SELECT * FROM expenses WHERE on_date LIKE ? ORDER BY on_date DESC, id DESC",
        (_month_prefix(year, month) + "%",)).fetchall()
    return [Expense(id=r["id"], on=date.fromisoformat(r["on_date"]), amount=r["amount"],
                    category_id=r["category_id"], note=r["note"]) for r in rows]


def delete_expense(conn, expense_id: int) -> None:
    _ensure(conn)
    conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
    conn.commit()


def month_spent(conn, year: int, month: int) -> float:
    _ensure(conn)
    r = conn.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM expenses WHERE on_date LIKE ?",
                     (_month_prefix(year, month) + "%",)).fetchone()
    return float(r["s"])


def spent_by_category(conn, year: int, month: int) -> dict:
    _ensure(conn)
    rows = conn.execute(
        "SELECT category_id, COALESCE(SUM(amount), 0) AS s FROM expenses "
        "WHERE on_date LIKE ? GROUP BY category_id", (_month_prefix(year, month) + "%",)).fetchall()
    return {r["category_id"]: float(r["s"]) for r in rows}


# --- Metas de ahorro ---------------------------------------------------------

def add_goal(conn, name: str, target: float) -> SavingsGoal:
    _ensure(conn)
    cur = conn.execute("INSERT INTO savings_goals (name, target, saved) VALUES (?, ?, 0)",
                       (name, target))
    conn.commit()
    return SavingsGoal(id=cur.lastrowid, name=name, target=target, saved=0.0)


def list_goals(conn) -> list[SavingsGoal]:
    _ensure(conn)
    return [SavingsGoal(id=r["id"], name=r["name"], target=r["target"], saved=r["saved"])
            for r in conn.execute("SELECT * FROM savings_goals ORDER BY id").fetchall()]


def add_to_goal(conn, goal_id: int, amount: float) -> None:
    _ensure(conn)
    conn.execute("UPDATE savings_goals SET saved = saved + ? WHERE id = ?", (amount, goal_id))
    conn.commit()


def delete_goal(conn, goal_id: int) -> None:
    _ensure(conn)
    conn.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,))
    conn.commit()
