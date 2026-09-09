"""Tests del recomendador."""

import pytest

from kcn.core.models import (
    ActivityLevel, DayType, Food, FoodEntry, MacroTargets, Sex, UserProfile,
)
from kcn.core.recommender import suggest_to_fill, plan_day, suggest_next_meal
from kcn.core.summary import build_day_summary
from kcn.data import repository as repo
from kcn.data.db import connect
from kcn.services import recommender as rec_service


def chicken(): return Food("Pollo", 165, 31, 0, 4)      # proteína
def rice():    return Food("Arroz", 130, 2.7, 28, 0.3)   # carbos
def oil():     return Food("Aceite", 900, 0, 0, 100)     # grasa


def marc():
    return UserProfile(weight_kg=78, height_cm=173, age=25, sex=Sex.MALE,
                       activity=ActivityLevel.VERY_ACTIVE)


# --- Motor puro --------------------------------------------------------------

def test_fill_prioritizes_protein():
    sugg = suggest_to_fill([chicken(), rice(), oil()], MacroTargets(580, 40, 60, 20))
    names = [s.food.name for s in sugg]
    assert "Pollo" in names
    assert all(s.grams > 0 for s in sugg)
    total_protein = sum(s.macros.protein_g for s in sugg)
    assert total_protein >= 30            # cubre buena parte de la proteína


def test_fill_empty_candidates():
    assert suggest_to_fill([], MacroTargets(500, 40, 50, 15)) == []


def test_fill_zero_target():
    assert suggest_to_fill([chicken()], MacroTargets(0, 0, 0, 0)) == []


def test_plan_day_has_one_entry_per_meal():
    plan = plan_day(marc(), DayType.REST, [chicken(), rice(), oil()])
    assert len(plan) == 5                 # 5 comidas
    assert all(isinstance(name, str) for name, _ in plan)


def test_next_meal_picks_first_empty():
    s = build_day_summary(marc(), DayType.REST, [])   # nada comido aún
    meal, sugg = suggest_next_meal(s, [chicken(), rice(), oil()])
    assert meal.index == 0                # primera comida
    assert len(sugg) >= 1


# --- Servicio ----------------------------------------------------------------

@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def test_service_plan_today(conn):
    for f in (chicken(), rice(), oil()):
        repo.add_food(conn, f)
    plan = rec_service.plan_today(conn, marc())
    assert len(plan) == 5


def test_service_next_meal_idea(conn):
    for f in (chicken(), rice(), oil()):
        repo.add_food(conn, f)
    meal, sugg = rec_service.next_meal_idea(conn, marc())
    assert meal is not None