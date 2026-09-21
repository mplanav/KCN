"""Servicio de recordatorios: reúne el estado del día y pregunta qué toca."""

from __future__ import annotations

import sqlite3
from datetime import datetime

from kcn.core import reminders as core_rem
from kcn.core.models import UserProfile
from kcn.data import repository as repo
from kcn.services import day as day_service


def due_now(conn: sqlite3.Connection, profile: UserProfile,
            now: datetime | None = None) -> list[core_rem.Reminder]:
    now = now or datetime.now()
    summary = day_service.get_day_summary(conn, profile, on=now.date())
    settings = repo.get_reminder_settings(conn)
    series = repo.weight_series(conn)
    days_since_weight = (now.date() - series[-1][0]).days if series else None
    return core_rem.due_reminders(now, settings, summary, days_since_weight)
