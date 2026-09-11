"""Tests de roles e inferencia de alimentos."""

import pytest

from kcn.core.calculations import infer_role
from kcn.core.models import Food, FoodRole, MealType
from kcn.data import repository as repo
from kcn.data.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def test_infer_role_by_macros():
    assert infer_role(Food("Pollo", 165, 31, 0, 4)) is FoodRole.PROTEIN
    assert infer_role(Food("Arroz", 130, 2.7, 28, 0.3)) is FoodRole.CARB
    assert infer_role(Food("Aceite", 900, 0, 0, 100)) is FoodRole.FAT
    assert infer_role(Food("Agua", 0, 0, 0, 0)) is FoodRole.OTHER


def test_food_role_defaults(conn):
    f = repo.add_food(conn, Food("X", 100, 5, 10, 3))
    got = repo.get_food(conn, f.id)
    assert got.role is FoodRole.OTHER
    assert got.meal_tags == []


def test_persist_role_and_tags(conn):
    f = Food("Avena", 380, 13, 60, 7, role=FoodRole.CARB,
             meal_tags=[MealType.BREAKFAST])
    saved = repo.add_food(conn, f)
    got = repo.get_food(conn, saved.id)
    assert got.role is FoodRole.CARB
    assert got.meal_tags == [MealType.BREAKFAST]


def test_set_food_role(conn):
    f = repo.add_food(conn, Food("Pechuga", 165, 31, 0, 4))
    repo.set_food_role(conn, f.id, role=FoodRole.PROTEIN,
                       meal_tags=[MealType.MAIN])
    got = repo.get_food(conn, f.id)
    assert got.role is FoodRole.PROTEIN
    assert got.meal_tags == [MealType.MAIN]