"""Servicio de progreso: usa el historial de peso de la base de datos."""

from __future__ import annotations

import sqlite3

from kcn.core import progress as core_progress
from kcn.core.calculations import goal_kcal
from kcn.core.models import UserProfile
from kcn.data import repository as repo


def adjustment(conn: sqlite3.Connection, profile: UserProfile,
               window_days: int = 28) -> core_progress.AdjustmentSuggestion:
    series = repo.weight_series(conn)
    return core_progress.suggest_adjustment(
        profile, series, goal_kcal(profile), window_days=window_days)