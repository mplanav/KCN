"""Núcleo de dominio de KCN (Python puro, sin UI ni base de datos).

Reexporta lo principal para poder hacer `from kcn.core import macro_targets`.
"""

from kcn.core.models import (
    ActivityLevel,
    Goal,
    MacroTargets,
    MealTarget,
    Sex,
    UserProfile,
)
from kcn.core.calculations import (
    KCAL_PER_G_CARB,
    KCAL_PER_G_FAT,
    KCAL_PER_G_PROTEIN,
    bmr_mifflin_st_jeor,
    default_meal_names,
    default_meal_weights,
    goal_kcal,
    macro_targets,
    split_into_meals,
    tdee,
)

__all__ = [
    "ActivityLevel", "Goal", "MacroTargets", "MealTarget", "Sex", "UserProfile",
    "KCAL_PER_G_CARB", "KCAL_PER_G_FAT", "KCAL_PER_G_PROTEIN",
    "bmr_mifflin_st_jeor", "default_meal_names", "default_meal_weights",
    "goal_kcal", "macro_targets", "split_into_meals", "tdee",
]