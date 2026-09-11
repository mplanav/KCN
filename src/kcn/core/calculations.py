"""Cálculos nutricionales del núcleo.

Todos los valores están contrastados con fuentes oficiales; ver FUENTES.md.

Pipeline:
    UserProfile
      -> BMR (Mifflin-St Jeor)
      -> TDEE (BMR * PAL de FAO/WHO)
      -> kcal objetivo (TDEE +/- ajuste por objetivo, con suelo de seguridad)
      -> macros (proteína y grasa por kg; grasa nunca < 20% AMDR; carbos = resto)
      -> reparto por comidas
"""

from __future__ import annotations

from kcn.core.models import DayType, FoodRole, Goal, MacroTargets, MealTarget, Sex, UserProfile

# Factores de Atwater: energía por gramo de macronutriente (kcal). [FUENTES.md #5]
KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_CARB = 4
KCAL_PER_G_FAT = 9

# Regla de Wishnofsky (aproximación): 1 kg de grasa corporal ≈ 7700 kcal. [#6]
KCAL_PER_KG_BODYWEIGHT = 7700.0

# AMDR (Institute of Medicine): rangos de distribución de macros. [#4]
AMDR_FAT_MIN_PCT = 0.20   # grasa: 20-35% de la energía
AMDR_FAT_MAX_PCT = 0.35
AMDR_CARB_MIN_PCT = 0.45  # carbohidratos: 45-65% de la energía
AMDR_CARB_MAX_PCT = 0.65

# Suelo de seguridad para déficits (heurística; el suelo real es el BMR). [#7]
MIN_KCAL_FLOOR = {Sex.MALE: 1500, Sex.FEMALE: 1200}


def bmr_mifflin_st_jeor(profile: UserProfile) -> float:
    """Tasa metabólica basal (kcal/día), ecuación de Mifflin-St Jeor. [#1]

    Hombres: 10*peso + 6.25*altura - 5*edad + 5
    Mujeres: 10*peso + 6.25*altura - 5*edad - 161
    """
    base = 10 * profile.weight_kg + 6.25 * profile.height_cm - 5 * profile.age
    return base + 5 if profile.sex is Sex.MALE else base - 161


def tdee(profile: UserProfile) -> float:
    """Gasto energético total diario = BMR * PAL (factor de actividad FAO). [#2]"""
    return bmr_mifflin_st_jeor(profile) * float(profile.activity)


def _daily_kcal_adjustment(profile: UserProfile) -> float:
    """Ajuste diario de kcal (negativo para perder, positivo para ganar). [#6]"""
    if profile.goal is Goal.MAINTAIN:
        return 0.0
    daily = profile.weekly_rate_kg * KCAL_PER_KG_BODYWEIGHT / 7.0
    return -daily if profile.goal is Goal.LOSE else daily


def goal_kcal(profile: UserProfile) -> int:
    """kcal objetivo diarias, con el ajuste por objetivo y el suelo de seguridad."""
    raw = tdee(profile) + _daily_kcal_adjustment(profile)
    if profile.goal is Goal.LOSE:
        floor = max(bmr_mifflin_st_jeor(profile), MIN_KCAL_FLOOR[profile.sex])
        raw = max(raw, floor)
    return round(raw)


def macro_targets(profile: UserProfile) -> MacroTargets:
    """Reparte las kcal objetivo en macros.

    Estrategia (avalada por ISSN y AMDR):
      1. Proteína fija por kg de peso — protege masa muscular. [#3]
      2. Grasa fija por kg, pero nunca por debajo del 20% de la energía. [#4]
      3. Carbohidratos = kcal restantes.
    Caso límite: si proteína + grasa superan las kcal (déficit agresivo), se
    recorta la grasa respetando la proteína.
    """
    kcal = goal_kcal(profile)

    protein_g = round(profile.protein_per_kg * profile.weight_kg)
    protein_kcal = protein_g * KCAL_PER_G_PROTEIN

    # Grasa: la mayor entre "por kg" y el suelo del AMDR (20% de la energía).
    fat_by_kg = profile.fat_per_kg * profile.weight_kg
    fat_floor = AMDR_FAT_MIN_PCT * kcal / KCAL_PER_G_FAT
    fat_g = round(max(fat_by_kg, fat_floor))
    fat_kcal = fat_g * KCAL_PER_G_FAT

    if protein_kcal + fat_kcal > kcal:
        fat_g = max((kcal - protein_kcal) // KCAL_PER_G_FAT, 0)
        fat_kcal = fat_g * KCAL_PER_G_FAT

    remaining_kcal = max(kcal - protein_kcal - fat_kcal, 0)
    carbs_g = round(remaining_kcal / KCAL_PER_G_CARB)

    return MacroTargets(kcal=kcal, protein_g=int(protein_g),
                        carbs_g=int(carbs_g), fat_g=int(fat_g))


# --- Reparto por comidas -----------------------------------------------------

_DEFAULT_WEIGHTS: dict[int, list[float]] = {
    1: [1.0],
    2: [0.5, 0.5],
    3: [0.30, 0.40, 0.30],
    4: [0.25, 0.35, 0.15, 0.25],
    5: [0.25, 0.10, 0.30, 0.10, 0.25],
    6: [0.20, 0.10, 0.25, 0.10, 0.25, 0.10],
}

_DEFAULT_NAMES: dict[int, list[str]] = {
    1: ["Comida"],
    2: ["Comida", "Cena"],
    3: ["Desayuno", "Comida", "Cena"],
    4: ["Desayuno", "Comida", "Merienda", "Cena"],
    5: ["Desayuno", "Media mañana", "Comida", "Merienda", "Cena"],
    6: ["Desayuno", "Media mañana", "Comida", "Merienda", "Cena", "Recena"],
}


def default_meal_weights(meal_count: int) -> list[float]:
    """Pesos por defecto para repartir el día en `meal_count` comidas."""
    if meal_count in _DEFAULT_WEIGHTS:
        return list(_DEFAULT_WEIGHTS[meal_count])
    return [1.0 / meal_count] * meal_count


def default_meal_names(meal_count: int) -> list[str]:
    """Nombres por defecto de las comidas."""
    if meal_count in _DEFAULT_NAMES:
        return list(_DEFAULT_NAMES[meal_count])
    return [f"Comida {i + 1}" for i in range(meal_count)]


def split_into_meals(
    targets: MacroTargets,
    weights: list[float] | None = None,
    names: list[str] | None = None,
) -> list[MealTarget]:
    """Reparte unos objetivos diarios entre varias comidas.

    La última comida se calcula como el resto exacto para que la suma cuadre
    con el total (sin descuadres por redondeo).
    """
    if weights is None:
        weights = default_meal_weights(len(names) if names else 5)
    n = len(weights)
    if names is None:
        names = default_meal_names(n)
    if len(names) != n:
        raise ValueError("names y weights deben tener la misma longitud")

    total_w = sum(weights)
    if total_w <= 0:
        raise ValueError("La suma de pesos debe ser > 0")
    weights = [w / total_w for w in weights]

    meals: list[MealTarget] = []
    acc = MacroTargets(0, 0, 0, 0)
    for i, (name, w) in enumerate(zip(names, weights)):
        if i < n - 1:
            m = MacroTargets(
                kcal=round(targets.kcal * w),
                protein_g=round(targets.protein_g * w),
                carbs_g=round(targets.carbs_g * w),
                fat_g=round(targets.fat_g * w),
            )
            acc = acc + m
        else:
            m = targets.remaining(acc)
        meals.append(MealTarget(name=name, weight=w, targets=m))
    return meals

# --- IMC (Índice de Masa Corporal), clasificación OMS [#9] -------------------

def bmi(weight_kg: float, height_cm: float) -> float:
    """Índice de Masa Corporal = peso(kg) / altura(m)²."""
    h = height_cm / 100.0
    return weight_kg / (h * h)


def bmi_category(value: float) -> str:
    """Clasificación de la OMS. Ojo: el IMC no distingue músculo de grasa."""
    if value < 18.5:
        return "Bajo peso"
    if value < 25:
        return "Normopeso"
    if value < 30:
        return "Sobrepeso"
    return "Obesidad"

# --- Agua: ingesta adecuada de agua total (EFSA) [#10] -----------------------

WATER_AI_ML = {Sex.MALE: 2500, Sex.FEMALE: 2000}


def default_water_goal_ml(profile: UserProfile) -> int:
    """Objetivo diario de agua (ml) por defecto, según la EFSA.

    Es una referencia; entrenando fuerte o con calor conviene beber más para
    reponer el sudor. El usuario podrá ajustarlo.
    """
    return WATER_AI_ML[profile.sex]

# --- Objetivos por tipo de día (ciclado de carbohidratos) [#11] --------------

def day_targets(profile: UserProfile, day_type: DayType) -> MacroTargets:
    """Objetivos ajustados al tipo de día.

    El desplazamiento va SOLO a los carbohidratos; proteína y grasa se mantienen.
    Si el ciclado está desactivado (carb_cycle_pct = 0), devuelve el objetivo base.
    """
    base = macro_targets(profile)
    if profile.carb_cycle_pct <= 0:
        return base

    shift_kcal = round(profile.carb_cycle_pct * base.kcal)
    if day_type is DayType.REST:
        shift_kcal = -shift_kcal

    carbs_g = max(base.carbs_g + round(shift_kcal / KCAL_PER_G_CARB), 0)
    kcal = base.protein_g * KCAL_PER_G_PROTEIN + carbs_g * KCAL_PER_G_CARB \
        + base.fat_g * KCAL_PER_G_FAT

    return MacroTargets(kcal=kcal, protein_g=base.protein_g,
                        carbs_g=carbs_g, fat_g=base.fat_g)

def infer_role(food) -> FoodRole:
    """Rol aproximado según qué macro aporta más energía. No distingue verdura/fruta."""
    p = food.protein_per_100g * KCAL_PER_G_PROTEIN
    c = food.carbs_per_100g * KCAL_PER_G_CARB
    f = food.fat_per_100g * KCAL_PER_G_FAT
    top = max(p, c, f)
    if top <= 0:
        return FoodRole.OTHER
    if top == p:
        return FoodRole.PROTEIN
    if top == c:
        return FoodRole.CARB
    return FoodRole.FAT