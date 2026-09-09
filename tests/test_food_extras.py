"""Tests de edición de registros y accesos rápidos (favoritos/recientes/frecuentes)."""

from datetime import date, datetime

import pytest

from kcn.core.models import Food, FoodEntry
from kcn.data import repository as repo
from kcn.data.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def avocado() -> Food:
    return Food("Aguacate", 160, 2, 9, 15)


def test_update_entry_grams(conn):
    e = repo.add_entry(conn, FoodEntry(food=avocado(), grams=100))  # 160 kcal
    repo.update_entry(conn, e.id, grams=200)
    assert repo.day_totals(conn, date.today()).kcal == 320


def test_update_entry_invalid_grams(conn):
    e = repo.add_entry(conn, FoodEntry(food=avocado(), grams=100))
    with pytest.raises(ValueError):
        repo.update_entry(conn, e.id, grams=0)


def test_favorite_toggle(conn):
    f = repo.add_food(conn, avocado())
    repo.set_favorite(conn, f.id, True)
    favs = repo.list_favorites(conn)
    assert len(favs) == 1
    assert favs[0].name == "Aguacate"
    assert favs[0].favorite is True


def test_recent_foods_order(conn):
    a = repo.add_food(conn, Food("Avena", 380, 13, 60, 7))
    b = repo.add_food(conn, Food("Pollo", 165, 31, 0, 4))
    repo.add_entry(conn, FoodEntry(food=a, grams=50, at=datetime(2026, 1, 1, 8, 0)))
    repo.add_entry(conn, FoodEntry(food=b, grams=100, at=datetime(2026, 1, 2, 8, 0)))
    names = [f.name for f in repo.recent_foods(conn)]
    assert names[0] == "Pollo"          # el más reciente primero


def test_frequent_foods_order(conn):
    a = repo.add_food(conn, Food("Avena", 380, 13, 60, 7))
    b = repo.add_food(conn, Food("Pollo", 165, 31, 0, 4))
    repo.add_entry(conn, FoodEntry(food=a, grams=50))
    repo.add_entry(conn, FoodEntry(food=a, grams=50))
    repo.add_entry(conn, FoodEntry(food=b, grams=100))
    names = [f.name for f in repo.frequent_foods(conn)]
    assert names[0] == "Avena"          # usado 2 veces