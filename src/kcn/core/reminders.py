"""Lógica de recordatorios (pura): dado el momento y el estado del día, decide
qué recordatorios tocan. La ENTREGA (notificación en el móvil) es otra capa.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from kcn.core.models import ReminderSettings
from kcn.core.summary import DaySummary


class ReminderKind(str, Enum):
    MEAL = "meal"
    WEIGHT = "weight"
    WATER = "water"


@dataclass
class Reminder:
    kind: ReminderKind
    message: str
    meal_index: int | None = None


# Horas límite por defecto para "ya deberías haber registrado esta comida".
_DEFAULT_DEADLINES = {
    3: ["10:00", "15:00", "22:00"],
    4: ["10:00", "15:00", "18:00", "22:00"],
    5: ["10:00", "12:30", "15:30", "18:30", "22:00"],
    6: ["09:30", "11:30", "15:00", "18:00", "21:00", "23:00"],
}


def _deadlines(settings: ReminderSettings, meal_count: int) -> list[str]:
    if settings.meal_times and len(settings.meal_times) == meal_count:
        return settings.meal_times
    return _DEFAULT_DEADLINES.get(meal_count, ["23:59"] * meal_count)


def _hhmm(s: str) -> tuple[int, int]:
    h, m = s.split(":")
    return int(h), int(m)


def due_reminders(now: datetime, settings: ReminderSettings, summary: DaySummary,
                  days_since_weight: int | None) -> list[Reminder]:
    """Lista de recordatorios que tocan en este momento."""
    out: list[Reminder] = []

    # Comidas no registradas cuya hora límite ya ha pasado.
    if settings.meals_enabled:
        deadlines = _deadlines(settings, len(summary.meals))
        for i, meal in enumerate(summary.meals):
            if meal.consumed.kcal > 0:
                continue
            if (now.hour, now.minute) >= _hhmm(deadlines[i]):
                out.append(Reminder(ReminderKind.MEAL,
                                    f"Aún no has registrado {meal.name.lower()}.", i))

    # Peso: si nunca o hace demasiados días.
    if settings.weight_enabled:
        if days_since_weight is None or days_since_weight >= settings.weight_every_days:
            out.append(Reminder(ReminderKind.WEIGHT, "Toca registrar tu peso."))

    # Agua: dentro de la franja horaria y por detrás de lo esperado.
    if settings.water_enabled and summary.water_goal_ml > 0:
        if settings.water_start_hour <= now.hour < settings.water_end_hour:
            window = settings.water_end_hour - settings.water_start_hour
            frac = (now.hour - settings.water_start_hour) / window if window > 0 else 1.0
            frac = min(max(frac, 0.0), 1.0)
            expected = summary.water_goal_ml * frac
            if summary.water_ml < expected and summary.water_remaining_ml > 0:
                out.append(Reminder(ReminderKind.WATER, "Vas por detrás con el agua, ¡hidrátate!"))

    return out