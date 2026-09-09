"""Tests del núcleo de cálculo nutricional.

Incluyen tests que fijan las constantes oficiales (ver FUENTES.md): si alguien
las modifica sin justificación, el test lo detecta.
"""

import pytest

from kcn.core import (
    ActivityLevel,
    Goal,
    Sex,
    UserProfile,
    bmr_mifflin_st_jeor,
    goal_kcal,
    macro_targets,
    split_into_meals,
    tdee,
)
from kcn.core.calculations import (
    KCAL_PER_G_CARB,
    KCAL_PER_G_FAT,
    KCAL_PER_G_PROTEIN,
    default_meal_names,
)


def make(**kw) -> UserProfile:
    base = dict(weight_kg=80, height_cm=180, age=30, sex=Sex.MALE)
    base.update(kw)
    return UserProfile(**base)


# --- Constantes oficiales (blindaje de FUENTES.md) ---------------------------

def test_atwater_factors():
    assert (KCAL_PER_G_PROTEIN, KCAL_PER_G_CARB, KCAL_PER_G_FAT) == (4, 4, 9)


def test_activity_factors_match_fao_pal():
    # Bandas FAO/WHO: sed/ligero 1.40-1.69, activo 1.70-1.99, vigoroso 2.00-2.40
    assert ActivityLevel.SEDENTARY == pytest.approx(1.40)
    assert ActivityLevel.LIGHT == pytest.approx(1.55)
    assert ActivityLevel.MODERATE == pytest.approx(1.70)
    assert ActivityLevel.ACTIVE == pytest.approx(1.85)
    assert ActivityLevel.VERY_ACTIVE == pytest.approx(2.10)


# --- BMR ---------------------------------------------------------------------

def test_bmr_male_exact():
    assert bmr_mifflin_st_jeor(make()) == pytest.approx(1780.0)


def test_bmr_female_exact():
    assert bmr_mifflin_st_jeor(make(sex=Sex.FEMALE)) == pytest.approx(1614.0)


# --- TDEE / kcal objetivo ----------------------------------------------------

def test_tdee_applies_pal():
    p = make(activity=ActivityLevel.VERY_ACTIVE)
    assert tdee(p) == pytest.approx(bmr_mifflin_st_jeor(p) * 2.10)


def test_maintain_equals_tdee_rounded():
    p = make(goal=Goal.MAINTAIN)
    assert goal_kcal(p) == round(tdee(p))


def test_lose_subtracts_550_for_half_kg():
    p = make(goal=Goal.LOSE, weekly_rate_kg=0.5)
    assert goal_kcal(p) == round(tdee(p) - 550)


def test_gain_adds_surplus():
    p = make(goal=Goal.GAIN, weekly_rate_kg=0.25)
    assert goal_kcal(p) == round(tdee(p) + 0.25 * 7700 / 7)


def test_deficit_never_below_floor():
    p = make(weight_kg=50, height_cm=160, age=25, goal=Goal.LOSE, weekly_rate_kg=2.0)
    assert goal_kcal(p) >= round(bmr_mifflin_st_jeor(p))


# --- Macros ------------------------------------------------------------------

def test_macros_protein_and_fat_by_bodyweight():
    m = macro_targets(make())
    assert m.protein_g == round(1.8 * 80)  # 144
    assert m.fat_g == round(0.9 * 80)      # 72 (por encima del suelo AMDR aquí)


def test_fat_floor_respects_amdr_20pct():
    # Grasa por kg muy baja: debe activarse el suelo del 20% del AMDR.
    m = macro_targets(make(fat_per_kg=0.3))
    assert m.fat_g > round(0.3 * 80)               # el suelo ha subido la grasa
    assert m.fat_g * KCAL_PER_G_FAT >= 0.195 * m.kcal  # ~20% (tolerancia de redondeo)


def test_macros_kcal_sum_matches_target():
    m = macro_targets(make())
    computed = (m.protein_g * KCAL_PER_G_PROTEIN
                + m.carbs_g * KCAL_PER_G_CARB
                + m.fat_g * KCAL_PER_G_FAT)
    assert abs(computed - m.kcal) <= 5


def test_carbs_never_negative_on_aggressive_cut():
    p = make(weight_kg=120, height_cm=170, age=40, goal=Goal.LOSE,
             weekly_rate_kg=1.0, protein_per_kg=2.2, fat_per_kg=1.0)
    m = macro_targets(p)
    assert m.carbs_g >= 0
    assert m.protein_g > 0


# --- Reparto por comidas -----------------------------------------------------

def test_split_sums_exactly_to_daily_target():
    m = macro_targets(make())
    meals = split_into_meals(m)
    assert len(meals) == 5
    assert sum(x.targets.kcal for x in meals) == m.kcal
    assert sum(x.targets.protein_g for x in meals) == m.protein_g
    assert sum(x.targets.carbs_g for x in meals) == m.carbs_g
    assert sum(x.targets.fat_g for x in meals) == m.fat_g


def test_split_uses_default_names():
    meals = split_into_meals(macro_targets(make()))
    assert [x.name for x in meals] == default_meal_names(5)


def test_split_custom_weights_normalize():
    m = macro_targets(make())
    meals = split_into_meals(m, weights=[2, 1, 1], names=["A", "B", "C"])
    assert len(meals) == 3
    assert sum(x.targets.kcal for x in meals) == m.kcal
    assert meals[0].targets.kcal > meals[1].targets.kcal


# --- Validación --------------------------------------------------------------

@pytest.mark.parametrize("bad", [
    dict(weight_kg=0), dict(height_cm=-1), dict(age=0),
    dict(meal_count=0), dict(protein_per_kg=-1),
])
def test_invalid_profile_raises(bad):
    with pytest.raises(ValueError):
        make(**bad)


# --- Perfil real de Marc -----------------------------------------------------

def test_marc_profile_is_plausible():
    marc = UserProfile(weight_kg=78, height_cm=173, age=25, sex=Sex.MALE,
                       activity=ActivityLevel.VERY_ACTIVE, goal=Goal.MAINTAIN)
    assert 3400 <= goal_kcal(marc) <= 3900
    assert macro_targets(marc).protein_g == round(1.8 * 78)  # 140