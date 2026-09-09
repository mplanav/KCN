"""Tests de recetas / platos compuestos."""

from datetime import date

import pytest

from kcn.core.models import Food, Recipe, RecipeItem
from kcn.data import repository as repo
from kcn.data.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def sample_recipe() -> Recipe:
    a = Food("A", 100, 10, 10, 5)     # 100 g -> 100 kcal, 10 P, 10 C, 5 G
    b = Food("B", 200, 0, 50, 0)      #  50 g -> 100 kcal,  0 P, 25 C, 0 G
    return Recipe(name="Plato", servings=2,
                  items=[RecipeItem(a, 100), RecipeItem(b, 50)])


def test_recipe_totals_and_per_serving():
    r = sample_recipe()
    t = r.total_macros()
    assert (t.kcal, t.protein_g, t.carbs_g, t.fat_g) == (200, 10, 35, 5)
    ps = r.per_serving()
    assert (ps.kcal, ps.protein_g, ps.carbs_g, ps.fat_g) == (100, 5, 18, 2)


def test_add_and_get_recipe(conn):
    r = repo.add_recipe(conn, sample_recipe())
    got = repo.get_recipe(conn, r.id)
    assert got.name == "Plato"
    assert got.servings == 2
    assert [i.food.name for i in got.items] == ["A", "B"]
    assert [i.grams for i in got.items] == [100, 50]


def test_log_recipe_adds_entries(conn):
    r = repo.add_recipe(conn, sample_recipe())
    repo.log_recipe(conn, r.id, meal_index=0, servings=2)   # las 2 raciones enteras
    total = repo.day_totals(conn, date.today())
    assert (total.kcal, total.protein_g, total.carbs_g, total.fat_g) == (200, 10, 35, 5)


def test_delete_recipe_cascades_items(conn):
    r = repo.add_recipe(conn, sample_recipe())
    repo.delete_recipe(conn, r.id)
    assert repo.get_recipe(conn, r.id) is None
    n = conn.execute("SELECT COUNT(*) AS n FROM recipe_items").fetchone()["n"]
    assert n == 0