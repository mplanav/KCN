"""Tests del módulo de entrenos."""

from datetime import date

import pytest

from kcn.data.db import connect
from kcn.fitness import repo as frepo
from kcn.fitness.models import Exercise, ExerciseSet, WorkoutSession


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def press_session():
    return WorkoutSession(
        name="Push", calories=350,
        sets=[ExerciseSet(Exercise("Press banca"), weight_kg=80, reps=8),
              ExerciseSet(Exercise("Press banca"), weight_kg=80, reps=6)])


def test_add_and_read_session(conn):
    s = frepo.add_session(conn, press_session())
    assert s.id is not None
    got = frepo.get_sessions_for_date(conn, date.today())
    assert len(got) == 1
    assert got[0].name == "Push"
    assert len(got[0].sets) == 2
    assert got[0].volume == 80 * 8 + 80 * 6


def test_get_or_create_dedupes_exercise(conn):
    a = frepo.get_or_create_exercise(conn, "Sentadilla")
    b = frepo.get_or_create_exercise(conn, "sentadilla")   # case-insensitive
    assert a.id == b.id


def test_session_calories_sum(conn):
    frepo.add_session(conn, WorkoutSession(name="A", calories=300))
    frepo.add_session(conn, WorkoutSession(name="B", calories=150))
    assert frepo.session_calories_for_date(conn, date.today()) == 450


def test_delete_session_cascades_sets(conn):
    s = frepo.add_session(conn, press_session())
    frepo.delete_session(conn, s.id)
    assert frepo.get_sessions_for_date(conn, date.today()) == []
    n = conn.execute("SELECT COUNT(*) AS n FROM workout_sets").fetchone()["n"]
    assert n == 0


def test_best_series(conn):
    frepo.add_session(conn, WorkoutSession(
        name="d1", on=date(2026, 1, 1),
        sets=[ExerciseSet(Exercise("Peso muerto"), weight_kg=100, reps=5)]))
    ex = frepo.get_or_create_exercise(conn, "Peso muerto")
    series = frepo.exercise_best_series(conn, ex.id)
    assert series == [(date(2026, 1, 1), 100)]
