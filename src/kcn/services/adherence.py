"""Servicio de adherencia: construye los resúmenes de los últimos días."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from kcn.core import adherence as core_adh
from kcn.core.models import UserProfile
from kcn.core.summary import DaySummary
from kcn.services import day as day_service


def recent_summaries(conn: sqlite3.Connection, profile: UserProfile,
                     days: int = 7, end: date | None = None) -> list[DaySummary]:
    end = end or date.today()
    return [day_service.get_day_summary(conn, profile, on=end - timedelta(days=i))
            for i in range(days)]


def adherence_rate(conn: sqlite3.Connection, profile: UserProfile,
                   days: int = 30, end: date | None = None) -> float:
    return core_adh.adherence_rate(recent_summaries(conn, profile, days=days, end=end))


def current_streak(conn: sqlite3.Connection, profile: UserProfile,
                   max_lookback: int = 90, end: date | None = None) -> int:
    return core_adh.current_streak(
        recent_summaries(conn, profile, days=max_lookback, end=end))
