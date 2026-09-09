"""Tests de la capa de datos (repositorio) con base de datos en memoria."""

from datetime import date, datetime

import pytest

from kcn.core.models import (
    ActivityLevel, Food, FoodEntry, FoodSource, Goal, Sex, UserProfile,
)
from kcn.data import repository as repo
from kcn.data.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def avocado() -> Food:
    return Food("Aguacate", kcal_per_100g=160, protein_per_100g=2,
                carbs_per_100g=9, fat_per_100g=15, default_serving_g=200)


# --- Perfil ------------------------------------------------------------------

def test_profile_roundtrip(conn):
    p = UserProfile(weight_kg=78, height_cm=173, age=25, sex=Sex.MALE,
                    activity=ActivityLevel.VERY_ACTIVE, goal=Goal.LOSE)
    repo.save_profile(conn, p)
    got = repo.get_profile(conn)
    assert got.weight_kg == 78
    assert got.sex is Sex.MALE                       # enum reconstruido por nombre
    assert got.activity is ActivityLevel.VERY_ACTIVE
    assert got.goal is Goal.LOSE


def test_get_profile_none_when_empty(conn):
    assert repo.get_profile(conn) is None


def test_profile_upsert_keeps_single_row(conn):
    repo.save_profile(conn, UserProfile(weight_kg=78, height_cm=173, age=25, sex=Sex.MALE))
    repo.save_profile(conn, UserProfile(weight_kg=80, height_cm=173, age=25, sex=Sex.MALE))
    assert repo.get_profile(conn).weight_kg == 80
    count = conn.execute("SELECT COUNT(*) AS n FROM profile").fetchone()["n"]
    assert count == 1


# --- Alimentos ---------------------------------------------------------------

def test_add_food_assigns_id(conn):
    f = repo.add_food(conn, avocado())
    assert f.id is not None
    assert repo.get_food(conn, f.id).name == "Aguacate"


def test_get_food_by_barcode(conn):
    f = Food("Atún en lata", kcal_per_100g=116, protein_per_100g=26,
             carbs_per_100g=0, fat_per_100g=1, source=FoodSource.OPEN_FOOD_FACTS,
             barcode="8410000000000")
    repo.add_food(conn, f)
    assert repo.get_food_by_barcode(conn, "8410000000000").name == "Atún en lata"
    assert repo.get_food_by_barcode(conn, "0000") is None


def test_upsert_by_barcode_deduplicates(conn):
    f1 = Food("Yogur", kcal_per_100g=60, protein_per_100g=4, carbs_per_100g=5,
              fat_per_100g=3, source=FoodSource.OPEN_FOOD_FACTS, barcode="123")
    f2 = Food("Yogur natural", kcal_per_100g=61, protein_per_100g=4,
              carbs_per_100g=5, fat_per_100g=3,
              source=FoodSource.OPEN_FOOD_FACTS, barcode="123")
    a = repo.upsert_food_by_barcode(conn, f1)
    b = repo.upsert_food_by_barcode(conn, f2)
    assert a.id == b.id                               # mismo producto, no duplicado
    assert repo.get_food(conn, a.id).name == "Yogur natural"  # se actualizó
    n = conn.execute("SELECT COUNT(*) AS n FROM foods").fetchone()["n"]
    assert n == 1


def test_search_is_case_insensitive(conn):
    repo.add_food(conn, avocado())
    assert [f.name for f in repo.search_foods(conn, "agua")] == ["Aguacate"]
    assert [f.name for f in repo.search_foods(conn, "AGUA")] == ["Aguacate"]
    assert repo.search_foods(conn, "pizza") == []


# --- Registros y contador diario ---------------------------------------------

def test_add_entry_persists_new_food(conn):
    entry = repo.add_entry(conn, FoodEntry(food=avocado(), grams=200))
    assert entry.id is not None
    assert entry.food.id is not None                 # el alimento se guardó solo


def test_day_totals_sums_entries(conn):
    repo.add_entry(conn, FoodEntry(food=avocado(), grams=200))  # 320 kcal
    repo.add_entry(conn, FoodEntry(food=avocado(), grams=100))  # 160 kcal
    total = repo.day_totals(conn, date.today())
    assert total.kcal == 480
    assert total.fat_g == 45                          # 30 + 15


def test_entries_ordered_by_meal(conn):
    repo.add_entry(conn, FoodEntry(food=avocado(), grams=50, meal_index=4))  # cena
    repo.add_entry(conn, FoodEntry(food=avocado(), grams=50, meal_index=0))  # desayuno
    meals = [e.meal_index for e in repo.get_entries_for_date(conn, date.today())]
    assert meals == [0, 4]


def test_totals_isolated_by_date(conn):
    old = FoodEntry(food=avocado(), grams=200, at=datetime(2020, 1, 1, 8, 0))
    repo.add_entry(conn, old)
    assert repo.day_totals(conn, date.today()).kcal == 0
    assert repo.day_totals(conn, date(2020, 1, 1)).kcal == 320


def test_delete_food_cascades_entries(conn):
    entry = repo.add_entry(conn, FoodEntry(food=avocado(), grams=200))
    repo.delete_food(conn, entry.food.id)
    assert repo.get_entries_for_date(conn, date.today()) == []  # FK ON DELETE CASCADE


def test_delete_entry(conn):
    entry = repo.add_entry(conn, FoodEntry(food=avocado(), grams=200))
    repo.delete_entry(conn, entry.id)
    assert repo.day_totals(conn, date.today()).kcal == 0