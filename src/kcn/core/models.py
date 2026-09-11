"""Modelos de dominio de KCN.

Son estructuras de datos puras (dataclasses / enums). No saben nada de la base
de datos ni de la interfaz: solo describen "qué" es un perfil, unos objetivos, etc.
Esto hace que la lógica sea fácil de testear y de reutilizar desde cualquier UI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum


class Sex(str, Enum):
    """Sexo biológico. Necesario para la fórmula de Mifflin-St Jeor."""

    MALE = "male"
    FEMALE = "female"


class ActivityLevel(float, Enum):
    """Nivel de actividad física — factores PAL de FAO/WHO/UNU (2004).

    El valor del enum ES el PAL (Physical Activity Level): el multiplicador que
    se aplica al BMR para obtener el gasto total diario (TDEE = PAL * BMR).
    Bandas oficiales FAO: sedentario/ligero 1,40-1,69; activo/moderado
    1,70-1,99; vigoroso 2,00-2,40. Ver FUENTES.md.
    """

    SEDENTARY = 1.40      # Oficina, poco o ningún ejercicio
    LIGHT = 1.55          # Ejercicio ligero 1-3 días/semana
    MODERATE = 1.70       # Ejercicio moderado 3-5 días/semana
    ACTIVE = 1.85         # Ejercicio intenso 6-7 días/semana
    VERY_ACTIVE = 2.10    # Muy intenso: 2 sesiones/día o trabajo físico

    @property
    def label(self) -> str:
        return {
            ActivityLevel.SEDENTARY: "Sedentario (1,40)",
            ActivityLevel.LIGHT: "Ligero (1,55)",
            ActivityLevel.MODERATE: "Moderado (1,70)",
            ActivityLevel.ACTIVE: "Activo (1,85)",
            ActivityLevel.VERY_ACTIVE: "Muy activo (2,10)",
        }[self]


class Goal(str, Enum):
    """Objetivo respecto al peso corporal."""

    LOSE = "lose"          # Déficit calórico
    MAINTAIN = "maintain"  # Mantenimiento
    GAIN = "gain"          # Superávit calórico

    @property
    def label(self) -> str:
        return {
            Goal.LOSE: "Perder grasa",
            Goal.MAINTAIN: "Mantener",
            Goal.GAIN: "Ganar músculo",
        }[self]

class DayType(str, Enum):
    """Tipo de día para el ciclado de carbohidratos."""

    TRAINING = "training"
    REST = "rest"


@dataclass
class UserProfile:
    """Perfil del usuario. De aquí salen TODOS los objetivos calculados.

    Campos con valores por defecto sensatos y editables:
      - protein_per_kg / fat_per_kg: gramos por kg de peso corporal.
      - weekly_rate_kg: ritmo objetivo de cambio de peso (kg/semana). Se usa
        con `goal` para el déficit/superávit. En MAINTAIN se ignora.
      - meal_count: nº de comidas al día para repartir los objetivos.
    """

    weight_kg: float
    height_cm: float
    age: int
    sex: Sex
    activity: ActivityLevel = ActivityLevel.MODERATE
    goal: Goal = Goal.MAINTAIN

    protein_per_kg: float = 1.8
    fat_per_kg: float = 0.9
    weekly_rate_kg: float = 0.5
    meal_count: int = 5
    weekly_rate_kg: float = 0.5
    meal_count: int = 5
    carb_cycle_pct: float = 0.0   # 0 = sin ciclado; p. ej. 0.15 = ±15% en carbos

    def __post_init__(self) -> None:
        # Validación básica: mejor fallar pronto que calcular con datos absurdos.
        if self.weight_kg <= 0:
            raise ValueError("weight_kg debe ser > 0")
        if self.height_cm <= 0:
            raise ValueError("height_cm debe ser > 0")
        if self.age <= 0:
            raise ValueError("age debe ser > 0")
        if self.meal_count < 1:
            raise ValueError("meal_count debe ser >= 1")
        if self.protein_per_kg < 0 or self.fat_per_kg < 0:
            raise ValueError("protein_per_kg y fat_per_kg deben ser >= 0")
        if self.carb_cycle_pct < 0:
            raise ValueError("carb_cycle_pct debe ser >= 0")


@dataclass
class MacroTargets:
    """Objetivos nutricionales. Sirve tanto para el día completo como por comida."""

    kcal: int
    protein_g: int
    carbs_g: int
    fat_g: int

    def __add__(self, other: "MacroTargets") -> "MacroTargets":
        """Permite sumar objetivos con el operador +."""
        return MacroTargets(
            kcal=self.kcal + other.kcal,
            protein_g=self.protein_g + other.protein_g,
            carbs_g=self.carbs_g + other.carbs_g,
            fat_g=self.fat_g + other.fat_g,
        )

    def remaining(self, consumed: "MacroTargets") -> "MacroTargets":
        """Lo que falta respecto a este objetivo (puede ser negativo si te pasas)."""
        return MacroTargets(
            kcal=self.kcal - consumed.kcal,
            protein_g=self.protein_g - consumed.protein_g,
            carbs_g=self.carbs_g - consumed.carbs_g,
            fat_g=self.fat_g - consumed.fat_g,
        )


@dataclass
class MealTarget:
    """Objetivo asignado a una comida concreta del día."""

    name: str          # "Desayuno", "Comida"...
    weight: float      # Fracción del total diario (0-1)
    targets: MacroTargets

class FoodSource(str, Enum):
    """Origen de un alimento."""

    CUSTOM = "custom"        # Creado por ti (p. ej. el aguacate del mercado)
    OPEN_FOOD_FACTS = "off"  # Importado de Open Food Facts (barcode/búsqueda)


@dataclass
class Food:
    """Alimento con su información nutricional por 100 g.

    Guardamos siempre "por 100 g" (como en las etiquetas y en Open Food Facts)
    y calculamos los macros de cada cantidad concreta con `macros_for`.
    """

    name: str
    kcal_per_100g: float
    protein_per_100g: float
    carbs_per_100g: float
    fat_per_100g: float
    source: FoodSource = FoodSource.CUSTOM
    brand: str | None = None
    barcode: str | None = None
    default_serving_g: float | None = None  # ración típica (p. ej. 1 aguacate ≈ 200 g)
    favorite: bool = False
    id: int | None = None                    # lo asigna la base de datos

    def macros_for(self, grams: float) -> MacroTargets:
        """Macros para una cantidad dada en gramos."""
        factor = grams / 100.0
        return MacroTargets(
            kcal=round(self.kcal_per_100g * factor),
            protein_g=round(self.protein_per_100g * factor),
            carbs_g=round(self.carbs_per_100g * factor),
            fat_g=round(self.fat_per_100g * factor),
        )


@dataclass
class FoodEntry:
    """Un alimento consumido, en una comida concreta y una fecha concreta."""

    food: Food
    grams: float
    meal_index: int = 0                      # 0 = primera comida del día
    on: date = None                          # se rellena en __post_init__
    at: datetime = None                      # momento exacto del registro
    id: int | None = None

    def __post_init__(self) -> None:
        if self.at is None:
            self.at = datetime.now()
        if self.on is None:
            self.on = self.at.date()
        if self.grams <= 0:
            raise ValueError("grams debe ser > 0")

    @property
    def macros(self) -> MacroTargets:
        """Macros de este registro (según los gramos consumidos)."""
        return self.food.macros_for(self.grams)

@dataclass
class Workout:
    """Entreno registrado de forma general (sin sincronización con salud).

    El usuario describe el entreno ('Natación 30 min', 'Hyrox', 'Calistenia') y
    le asocia una estimación de kcal, que ampliarán su margen del día.
    """

    description: str
    calories: int
    duration_min: int | None = None
    on: date = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.on is None:
            self.on = date.today()
        if self.calories < 0:
            raise ValueError("calories debe ser >= 0")

@dataclass
class BodyMeasurement:
    """Medidas corporales en una fecha concreta.

    Todos los campos salvo la fecha son OPCIONALES: el usuario rellena lo que le
    dé su báscula (o lo que quiera seguir). Diseñado para ampliarse con más
    campos en el futuro sin romper nada.
    """

    on: date = None
    weight_kg: float | None = None
    body_fat_pct: float | None = None       # % de grasa corporal
    water_pct: float | None = None          # % de agua / hidratación
    muscle_mass_kg: float | None = None     # masa muscular
    bone_mass_kg: float | None = None       # masa ósea
    visceral_fat: float | None = None       # índice de grasa visceral
    metabolic_age: int | None = None        # edad metabólica
    note: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.on is None:
            self.on = date.today()

@dataclass
class WaterEntry:
    """Un registro de agua bebida (p. ej. un vaso de 250 ml)."""

    ml: int
    on: date = None
    at: datetime = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.at is None:
            self.at = datetime.now()
        if self.on is None:
            self.on = self.at.date()
        if self.ml <= 0:
            raise ValueError("ml debe ser > 0")
@dataclass
class RecipeItem:
    """Un ingrediente de una receta: un alimento y su cantidad."""

    food: Food
    grams: float

    def __post_init__(self) -> None:
        if self.grams <= 0:
            raise ValueError("grams debe ser > 0")


@dataclass
class Recipe:
    """Un plato compuesto por varios alimentos (p. ej. tu batido post-entreno).

    `servings` = para cuántas raciones es el total de la receta.
    """

    name: str
    items: list[RecipeItem] = field(default_factory=list)
    servings: int = 1
    id: int | None = None

    def __post_init__(self) -> None:
        if self.servings < 1:
            raise ValueError("servings debe ser >= 1")

    def total_macros(self) -> MacroTargets:
        """Macros de la receta completa."""
        total = MacroTargets(0, 0, 0, 0)
        for item in self.items:
            total = total + item.food.macros_for(item.grams)
        return total

    def per_serving(self) -> MacroTargets:
        """Macros por ración."""
        t = self.total_macros()
        s = self.servings
        return MacroTargets(round(t.kcal / s), round(t.protein_g / s),
                            round(t.carbs_g / s), round(t.fat_g / s))


@dataclass
class ReminderSettings:
    """Preferencias de recordatorios (todo configurable por el usuario)."""

    meals_enabled: bool = True
    meal_times: list[str] = field(default_factory=list)   # "HH:MM" por comida; vacío = por defecto
    weight_enabled: bool = True
    weight_every_days: int = 5
    water_enabled: bool = True
    water_interval_hours: int = 2
    water_start_hour: int = 10
    water_end_hour: int = 22