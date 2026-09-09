"""Tests del ajuste automático por progreso."""

from datetime import date, timedelta

from kcn.core.models import Goal, Sex, UserProfile
from kcn.core.progress import suggest_adjustment

BASE = date(2026, 1, 1)


def lose(rate=0.5):
    return UserProfile(weight_kg=80, height_cm=180, age=30, sex=Sex.MALE,
                       goal=Goal.LOSE, weekly_rate_kg=rate)


def maintain():
    return UserProfile(weight_kg=80, height_cm=180, age=30, sex=Sex.MALE,
                       goal=Goal.MAINTAIN)


def series(weekly_change, start=80.0, weeks=4):
    return [(BASE + timedelta(days=7 * i), start + weekly_change * i) for i in range(weeks + 1)]


def test_not_enough_data():
    s = suggest_adjustment(lose(), [(BASE, 80.0), (BASE + timedelta(days=5), 79.9)], 2500)
    assert s.enough_data is False
    assert s.suggested_kcal is None


def test_on_track():
    s = suggest_adjustment(lose(0.5), series(-0.5), 2500)
    assert s.enough_data and s.on_track
    assert s.suggested_kcal_delta == 0


def test_losing_too_slow_reduces_calories():
    s = suggest_adjustment(lose(0.5), series(-0.2), 2500)   # baja 0.2/sem, objetivo 0.5
    assert s.suggested_kcal_delta == -330                    # (-0.5 - -0.2)*7700/7
    assert s.suggested_kcal == 2500 - 330


def test_gaining_when_should_maintain():
    s = suggest_adjustment(maintain(), series(+0.3), 2800)
    assert s.suggested_kcal_delta == -330


def test_delta_is_clamped():
    s = suggest_adjustment(lose(2.0), series(0.0), 2500)     # objetivo -2/sem, real 0
    assert s.suggested_kcal_delta == -500                    # recortado al máximo