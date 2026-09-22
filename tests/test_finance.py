"""Tests del módulo de finanzas."""

from datetime import date

import pytest

from kcn.data.db import connect
from kcn.finance import repo as frepo
from kcn.finance.models import Expense


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def test_income_roundtrip(conn):
    frepo.set_income(conn, 1800)
    assert frepo.get_income(conn) == 1800
    frepo.set_income(conn, 2000)
    assert frepo.get_income(conn) == 2000


def test_expenses_and_month_totals(conn):
    cat = frepo.add_category(conn, "Comida", 300)
    frepo.add_expense(conn, Expense(amount=20, category_id=cat.id, on=date(2026, 3, 5)))
    frepo.add_expense(conn, Expense(amount=15, category_id=cat.id, on=date(2026, 3, 9)))
    frepo.add_expense(conn, Expense(amount=99, on=date(2026, 4, 1)))   # otro mes
    assert frepo.month_spent(conn, 2026, 3) == 35
    assert frepo.spent_by_category(conn, 2026, 3)[cat.id] == 35
    assert len(frepo.expenses_for_month(conn, 2026, 3)) == 2


def test_delete_category_nulls_expense(conn):
    cat = frepo.add_category(conn, "Ocio", 100)
    frepo.add_expense(conn, Expense(amount=10, category_id=cat.id, on=date(2026, 3, 1)))
    frepo.delete_category(conn, cat.id)
    assert frepo.spent_by_category(conn, 2026, 3) == {None: 10}


def test_savings_goal(conn):
    g = frepo.add_goal(conn, "Viaje", 1000)
    frepo.add_to_goal(conn, g.id, 200)
    frepo.add_to_goal(conn, g.id, 50)
    assert frepo.list_goals(conn)[0].saved == 250
