"""Tests del resumen del día (pieza pura + servicio)."""

from datetime import date

import pytest

from kcn.core.models import (
    ActivityLevel, DayType, Food, FoodEntry, Sex, UserProfile, WaterEntry, Workout,
)
from kcn.core.summary import build_day_summary
from kcn.data import repository as repo
from kcn.data.db import connect
from kcn.services import day as day_service


def marc() -> UserProfile:
    return UserProfile(weight_kg=78, height_cm=173, age=25, sex=Sex.MALE,
                       activity=ActivityLevel.VERY_ACTIVE)


def foodA() -> Food:
    return Food("A", 100, 10, 10, 5)   # 100 g -> 100 kcal, 10 P, 10 C, 5 G


# --- Pieza pura --------------------------------------------------------------

def test_summary_consumed_and_meals():
    entries = [FoodEntry(foodA(), 100, meal_index=0),
               FoodEntry(foodA(), 200, meal_index=2)]
    s = build_day_summary(marc(), DayType.REST, entries)
    assert s.consumed.kcal == 300                 # 100 + 200
    assert len(s.meals) == 5
    assert s.meals[0].consumed.kcal == 100
    assert s.meals[2].consumed.kcal == 200
    assert s.meals[1].consumed.kcal == 0


def test_exercise_adds_calorie_budget():
    s = build_day_summary(marc(), DayType.REST, [], exercise_kcal=300)
    assert s.calorie_budget == s.target.kcal + 300
    assert s.remaining.kcal == s.target.kcal + 300     # no has comido nada


def test_water_fields():
    s = build_day_summary(marc(), DayType.REST, [], water_ml=1000)
    assert s.water_ml == 1000
    assert s.water_goal_ml == 2500                 # hombre (EFSA)
    assert s.water_remaining_ml == 1500


# --- Servicio (con base de datos) --------------------------------------------

@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def test_service_builds_from_db(conn):
    repo.add_entry(conn, FoodEntry(food=foodA(), grams=100, meal_index=0))
    repo.add_workout(conn, Workout("Gym", 300))
    repo.add_water(conn, WaterEntry(ml=500))
    s = day_service.get_day_summary(conn, marc())
    assert s.consumed.kcal == 100
    assert s.exercise_kcal == 300
    assert s.water_ml == 500
    assert s.day_type == DayType.TRAINING          # hay entreno -> día de entreno


def test_service_rest_day_when_no_workout(conn):
    repo.add_entry(conn, FoodEntry(food=foodA(), grams=100, meal_index=0))
    s = day_service.get_day_summary(conn, marc())
    assert s.day_type == DayType.REST