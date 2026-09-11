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
    infer_role,
    split_into_meals,
)
from kcn.core.models import DayType, Food, FoodRole, MacroTargets, MealType, UserProfile
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

# --- Coherencia: roles, encaje por comida y plantillas -----------------------

def effective_role(food: Food) -> FoodRole:
    """Rol del alimento: el asignado, o uno inferido por macros si es OTHER."""
    return food.role if food.role is not FoodRole.OTHER else infer_role(food)


def fits_meal(food: Food, meal_type: MealType) -> bool:
    """Un alimento sin etiquetas vale para cualquier comida; con etiquetas, solo las suyas."""
    return (not food.meal_tags) or (meal_type in food.meal_tags)


def meal_type_for_name(name: str) -> MealType:
    """Traduce el nombre de la comida a su tipo (para elegir plantilla)."""
    n = name.lower()
    if "desayuno" in n:
        return MealType.BREAKFAST
    if any(k in n for k in ("media mañana", "merienda", "recena", "snack")):
        return MealType.SNACK
    return MealType.MAIN


# Plantillas: orden de huecos (rol, macro guía). "portion" = ración fija (verdura/fruta).
_TEMPLATES: dict[MealType, list[tuple[FoodRole, str]]] = {
    MealType.BREAKFAST: [(FoodRole.CARB, "carbs"), (FoodRole.PROTEIN, "protein"),
                         (FoodRole.FRUIT, "portion"), (FoodRole.FAT, "fat")],
    MealType.MAIN:      [(FoodRole.PROTEIN, "protein"), (FoodRole.CARB, "carbs"),
                         (FoodRole.VEGETABLE, "portion"), (FoodRole.FAT, "fat")],
    MealType.SNACK:     [(FoodRole.PROTEIN, "protein"), (FoodRole.FRUIT, "portion")],
}


def _best_of_role(candidates: list[Food], role: FoodRole, macro: str, used: set) -> Food | None:
    matches = [f for f in candidates if id(f) not in used and effective_role(f) is role]
    if not matches:
        return None
    if macro == "portion":
        return matches[0]
    best, best_d = None, 0.0
    for f in matches:
        d = _density(f, macro)
        if d > best_d:
            best, best_d = f, d
    return best


def coherent_meal(candidates: list[Food], meal_type: MealType, meal_target: MacroTargets,
                  max_items: int = 4, round_to: int = 5, min_grams: int = 10) -> list[Suggestion]:
    """Arma una comida coherente rellenando los huecos de la plantilla del tipo de comida."""
    pool = [f for f in candidates if fits_meal(f, meal_type)]
    remaining = MacroTargets(max(meal_target.kcal, 0), max(meal_target.protein_g, 0),
                             max(meal_target.carbs_g, 0), max(meal_target.fat_g, 0))
    picks: list[Suggestion] = []
    used: set = set()

    for role, macro in _TEMPLATES.get(meal_type, _TEMPLATES[MealType.MAIN]):
        if len(picks) >= max_items:
            break
        food = _best_of_role(pool, role, macro, used)
        if food is None:
            continue

        if macro == "portion":                       # verdura/fruta: ración fija
            grams = round((food.default_serving_g or 100) / round_to) * round_to
        else:
            gap = _gap(remaining, macro)
            if gap <= 0:
                continue
            dens = _density(food, macro)
            if dens <= 0:
                continue
            grams = gap / (dens / 100.0)
            if food.kcal_per_100g > 0 and remaining.kcal > 0:
                grams = min(grams, remaining.kcal / (food.kcal_per_100g / 100.0))
            grams = round(grams / round_to) * round_to
            if grams < min_grams:
                continue

        s = Suggestion(food=food, grams=float(grams))
        picks.append(s)
        used.add(id(food))
        m = s.macros
        remaining = MacroTargets(remaining.kcal - m.kcal, remaining.protein_g - m.protein_g,
                                 remaining.carbs_g - m.carbs_g, remaining.fat_g - m.fat_g)
    return picks


def plan_day_coherent(profile: UserProfile, day_type: DayType, candidates: list[Food],
                      max_items_per_meal: int = 4) -> list[tuple[str, list[Suggestion]]]:
    """'Plan de comida para hoy' coherente: una plantilla adecuada por cada comida."""
    target = day_targets(profile, day_type)
    meals = split_into_meals(target,
                             weights=default_meal_weights(profile.meal_count),
                             names=default_meal_names(profile.meal_count))
    return [(mt.name, coherent_meal(candidates, meal_type_for_name(mt.name), mt.targets,
                                    max_items=max_items_per_meal))
            for mt in meals]