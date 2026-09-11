"""Tests del recomendador coherente (roles + plantillas + encaje por comida)."""

from kcn.core.models import (
    ActivityLevel, DayType, Food, FoodRole, MacroTargets, MealType, Sex, UserProfile,
)
from kcn.core.recommender import (
    coherent_meal, effective_role, fits_meal, meal_type_for_name, plan_day_coherent,
)


def marc():
    return UserProfile(weight_kg=78, height_cm=173, age=25, sex=Sex.MALE,
                       activity=ActivityLevel.VERY_ACTIVE)


def library():
    return [
        Food("Pollo", 165, 31, 0, 4, role=FoodRole.PROTEIN, meal_tags=[MealType.MAIN]),
        Food("Arroz", 130, 2.7, 28, 0.3, role=FoodRole.CARB),
        Food("Avena", 380, 13, 60, 7, role=FoodRole.CARB, meal_tags=[MealType.BREAKFAST]),
        Food("Yogur", 60, 10, 4, 0, role=FoodRole.PROTEIN, meal_tags=[MealType.BREAKFAST]),
        Food("Aceite", 900, 0, 0, 100, role=FoodRole.FAT),
    ]


def test_meal_type_for_name():
    assert meal_type_for_name("Desayuno") is MealType.BREAKFAST
    assert meal_type_for_name("Media mañana") is MealType.SNACK
    assert meal_type_for_name("Merienda") is MealType.SNACK
    assert meal_type_for_name("Comida") is MealType.MAIN
    assert meal_type_for_name("Cena") is MealType.MAIN


def test_effective_role_infers_when_other():
    assert effective_role(Food("X", 100, 30, 0, 0)) is FoodRole.PROTEIN     # inferido
    assert effective_role(Food("Y", 20, 1, 3, 0, role=FoodRole.VEGETABLE)) is FoodRole.VEGETABLE


def test_fits_meal():
    chicken = Food("Pollo", 165, 31, 0, 4, meal_tags=[MealType.MAIN])
    rice = Food("Arroz", 130, 2.7, 28, 0.3)
    assert fits_meal(rice, MealType.MAIN) is True          # sin etiquetas: vale para todo
    assert fits_meal(chicken, MealType.MAIN) is True
    assert fits_meal(chicken, MealType.BREAKFAST) is False  # etiquetado solo comida/cena


def test_main_meal_is_coherent():
    picks = [p.food.name for p in coherent_meal(library(), MealType.MAIN,
                                                MacroTargets(700, 45, 60, 20))]
    assert "Pollo" in picks          # proteína
    assert "Arroz" in picks          # carbo (sin etiqueta, vale)
    assert "Avena" not in picks      # avena es solo desayuno
    assert "Yogur" not in picks      # yogur es solo desayuno


def test_breakfast_excludes_lunch_only_foods():
    picks = [p.food.name for p in coherent_meal(library(), MealType.BREAKFAST,
                                                MacroTargets(500, 30, 60, 15))]
    assert "Pollo" not in picks      # el pollo NO aparece en el desayuno
    assert "Avena" in picks          # carbo de desayuno
    assert "Yogur" in picks          # proteína de desayuno


def test_plan_day_coherent_breakfast_has_no_chicken():
    plan = dict(plan_day_coherent(marc(), DayType.REST, library()))
    assert len(plan) == 5
    assert "Pollo" not in [s.food.name for s in plan["Desayuno"]]