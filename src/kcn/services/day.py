"""Servicio de día: arma el resumen leyendo de la base de datos."""

from __future__ import annotations

import sqlite3
from datetime import date

from kcn.core.models import DayType, UserProfile
from kcn.core.summary import DaySummary, build_day_summary
from kcn.data import repository as repo


def get_day_summary(conn: sqlite3.Connection, profile: UserProfile,
                    on: date | None = None,
                    day_type: DayType | None = None) -> DaySummary:
    """Resumen del día `on`. Si no se indica el tipo de día, se deduce:
    día de entreno si hay algún entreno registrado, si no, descanso.
    """
    on = on or date.today()
    entries = repo.get_entries_for_date(conn, on)
    exercise_kcal = repo.day_workout_calories(conn, on)
    water_ml = repo.day_water_ml(conn, on)

    if day_type is None:
        day_type = DayType.TRAINING if exercise_kcal > 0 else DayType.REST

    return build_day_summary(profile, day_type, entries,
                             exercise_kcal=exercise_kcal, water_ml=water_ml, on=on)