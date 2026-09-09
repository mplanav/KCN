"""Motor de recomendación (puro): rellena objetivos de macros con tu biblioteca.

Estrategia greedy y explicable: prioriza proteína, luego carbohidratos, luego
grasa. En cada paso elige el alimento más denso en ese macro y calcula los
gramos para cubrir el hueco sin pasarse de calorías.
"""

from __future__ import annotations

from dataclasses import dataclass

from kcn.core.calculations import (
    day_targets,
    default_meal_names,
    default_meal_weights,
    split_into_meals,
)
from kcn.core.models import DayType, Food, MacroTargets, UserProfile
from kcn.core.summary import DaySummary


@dataclass
class Suggestion:
    """Una sugerencia: comer estos gramos de este alimento."""

    food: Food
    grams: float

    @property
    def macros(self) -> MacroTargets:
        return self.food.macros_for(self.grams)


_DENSITY = {"protein": "protein_per_100g", "carbs": "carbs_per_100g", "fat": "fat_per_100g"}


def _density(food: Food, macro: str) -> float:
    return getattr(food, _DENSITY[macro])


def _gap(target: MacroTargets, macro: str) -> float:
    return {"protein": target.protein_g, "carbs": target.carbs_g, "fat": target.fat_g}[macro]


def _best_source(candidates: list[Food], macro: str, used: set) -> Food | None:
    """El alimento más denso en `macro` que aún no se haya usado."""
    best, best_d = None, 0.0
    for f in candidates:
        if id(f) in used:
            continue
        d = _density(f, macro)
        if d > best_d:
            best, best_d = f, d
    return best if best_d > 0 else None


def suggest_to_fill(candidates: list[Food], target: MacroTargets, max_items: int = 3,
                    round_to: int = 5, min_grams: int = 10, max_grams: int = 500) -> list[Suggestion]:
    """Sugiere alimentos para acercarse a `target` (proteína → carbos → grasa)."""
    remaining = MacroTargets(max(target.kcal, 0), max(target.protein_g, 0),
                             max(target.carbs_g, 0), max(target.fat_g, 0))
    suggestions: list[Suggestion] = []
    used: set = set()

    for macro in ("protein", "carbs", "fat"):
        if len(suggestions) >= max_items:
            break
        gap = _gap(remaining, macro)
        if gap <= 0:
            continue
        food = _best_source(candidates, macro, used)
        if food is None:
            continue

        grams = gap / (_density(food, macro) / 100.0)
        if food.kcal_per_100g > 0 and remaining.kcal > 0:      # no pasarse de kcal
            grams = min(grams, remaining.kcal / (food.kcal_per_100g / 100.0))
        grams = min(grams, max_grams)
        grams = round(grams / round_to) * round_to
        if grams < min_grams:
            continue

        s = Suggestion(food=food, grams=float(grams))
        suggestions.append(s)
        used.add(id(food))
        m = s.macros
        remaining = MacroTargets(remaining.kcal - m.kcal, remaining.protein_g - m.protein_g,
                                 remaining.carbs_g - m.carbs_g, remaining.fat_g - m.fat_g)
    return suggestions


def plan_day(profile: UserProfile, day_type: DayType, candidates: list[Food],
             max_items_per_meal: int = 3) -> list[tuple[str, list[Suggestion]]]:
    """'Plan de comida para hoy': sugerencias para cada comida del día."""
    target = day_targets(profile, day_type)
    meals = split_into_meals(target,
                             weights=default_meal_weights(profile.meal_count),
                             names=default_meal_names(profile.meal_count))
    return [(mt.name, suggest_to_fill(candidates, mt.targets, max_items=max_items_per_meal))
            for mt in meals]


def suggest_next_meal(summary: DaySummary, candidates: list[Food],
                      meal_index: int | None = None,
                      max_items: int = 3) -> tuple:
    """'Idea siguiente comida': mira lo que falta en la próxima comida y sugiere.

    Si no se indica `meal_index`, elige la primera comida aún sin registrar.
    Devuelve (comida, lista_de_sugerencias).
    """
    if meal_index is not None:
        meal = summary.meals[meal_index]
    else:
        meal = next((m for m in summary.meals if m.consumed.kcal == 0), summary.meals[-1])

    gap = meal.target.remaining(meal.consumed)
    return meal, suggest_to_fill(candidates, gap, max_items=max_items)