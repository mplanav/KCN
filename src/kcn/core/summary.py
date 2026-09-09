"""Resumen del día: junta objetivo, comido, ejercicio y agua.

`build_day_summary` es una función PURA (no toca la base de datos): recibe los
datos ya cargados y devuelve el resumen. Así es fácil de testear.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_cls

from kcn.core.calculations import (
    day_targets,
    default_meal_names,
    default_meal_weights,
    default_water_goal_ml,
    split_into_meals,
)
from kcn.core.models import DayType, FoodEntry, MacroTargets, UserProfile


@dataclass
class MealSummary:
    """Estado de una comida concreta del día."""

    index: int
    name: str
    target: MacroTargets
    consumed: MacroTargets
    entries: list[FoodEntry] = field(default_factory=list)

    @property
    def remaining(self) -> MacroTargets:
        return self.target.remaining(self.consumed)


@dataclass
class DaySummary:
    """Foto completa del día."""

    on: date_cls
    day_type: DayType
    target: MacroTargets       # objetivo de macros del día (según tipo de día)
    consumed: MacroTargets     # lo comido hasta ahora
    exercise_kcal: int
    water_ml: int
    water_goal_ml: int
    meals: list[MealSummary] = field(default_factory=list)

    @property
    def calorie_budget(self) -> int:
        """kcal disponibles = objetivo + lo quemado en ejercicio."""
        return self.target.kcal + self.exercise_kcal

    @property
    def remaining(self) -> MacroTargets:
        """Lo que te queda. Las kcal incluyen el margen del ejercicio."""
        return MacroTargets(
            kcal=self.calorie_budget - self.consumed.kcal,
            protein_g=self.target.protein_g - self.consumed.protein_g,
            carbs_g=self.target.carbs_g - self.consumed.carbs_g,
            fat_g=self.target.fat_g - self.consumed.fat_g,
        )

    @property
    def water_remaining_ml(self) -> int:
        return self.water_goal_ml - self.water_ml


def _sum_macros(entries: list[FoodEntry]) -> MacroTargets:
    total = MacroTargets(0, 0, 0, 0)
    for e in entries:
        total = total + e.macros
    return total


def build_day_summary(
    profile: UserProfile,
    day_type: DayType,
    entries: list[FoodEntry],
    exercise_kcal: int = 0,
    water_ml: int = 0,
    on: date_cls | None = None,
) -> DaySummary:
    on = on or date_cls.today()
    target = day_targets(profile, day_type)

    names = default_meal_names(profile.meal_count)
    weights = default_meal_weights(profile.meal_count)
    meal_targets = split_into_meals(target, weights=weights, names=names)

    meals: list[MealSummary] = []
    for i, mt in enumerate(meal_targets):
        m_entries = [e for e in entries if e.meal_index == i]
        meals.append(MealSummary(index=i, name=mt.name, target=mt.targets,
                                 consumed=_sum_macros(m_entries), entries=m_entries))

    return DaySummary(
        on=on, day_type=day_type, target=target,
        consumed=_sum_macros(entries), exercise_kcal=exercise_kcal,
        water_ml=water_ml, water_goal_ml=default_water_goal_ml(profile),
        meals=meals,
    )