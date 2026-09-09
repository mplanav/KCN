"""Servicio de recomendación: usa tu biblioteca de alimentos desde la base de datos."""

from __future__ import annotations

import sqlite3
from datetime import date

from kcn.core import recommender as core_rec
from kcn.core.models import DayType, UserProfile
from kcn.data import repository as repo
from kcn.services import day as day_service


def _candidates(conn: sqlite3.Connection, limit: int = 200):
    """Tu biblioteca de alimentos (todos los guardados)."""
    return repo.search_foods(conn, "", limit=limit)


def plan_today(conn: sqlite3.Connection, profile: UserProfile,
               day_type: DayType | None = None, on: date | None = None):
    on = on or date.today()
    if day_type is None:
        day_type = (DayType.TRAINING if repo.day_workout_calories(conn, on) > 0
                    else DayType.REST)
    return core_rec.plan_day(profile, day_type, _candidates(conn))


def next_meal_idea(conn: sqlite3.Connection, profile: UserProfile,
                   on: date | None = None, meal_index: int | None = None):
    summary = day_service.get_day_summary(conn, profile, on=on)
    return core_rec.suggest_next_meal(summary, _candidates(conn), meal_index=meal_index)