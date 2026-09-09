"""Modelos de dominio de KCN.

Son estructuras de datos puras (dataclasses / enums). No saben nada de la base
de datos ni de la interfaz: solo describen "qué" es un perfil, unos objetivos, etc.
Esto hace que la lógica sea fácil de testear y de reutilizar desde cualquier UI.
"""

from __future__ import annotations

from dataclasses import dataclass
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