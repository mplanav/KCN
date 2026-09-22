"""Tests del módulo de hábitos."""

from datetime import date, timedelta

import pytest

from kcn.data.db import connect
from kcn.habits import repo as hrepo


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def test_add_and_list(conn):
    hrepo.add_habit(conn, "Estirar")
    habits = hrepo.list_habits(conn)
    assert len(habits) == 1 and habits[0].name == "Estirar"


def test_toggle_done(conn):
    h = hrepo.add_habit(conn, "Leer")
    today = date.today()
    hrepo.set_done(conn, h.id, today, True)
    assert h.id in hrepo.done_ids_for_date(conn, today)
    hrepo.set_done(conn, h.id, today, False)
    assert h.id not in hrepo.done_ids_for_date(conn, today)


def test_streak(conn):
    h = hrepo.add_habit(conn, "Agua")
    today = date.today()
    for i in range(3):
        hrepo.set_done(conn, h.id, today - timedelta(days=i), True)
    assert hrepo.streak(conn, h.id, today) == 3


def test_delete_cascades_logs(conn):
    h = hrepo.add_habit(conn, "X")
    hrepo.set_done(conn, h.id, date.today(), True)
    hrepo.delete_habit(conn, h.id)
    assert hrepo.list_habits(conn) == []
    n = conn.execute("SELECT COUNT(*) AS n FROM habit_logs").fetchone()["n"]
    assert n == 0
