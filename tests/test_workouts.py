"""Tests del registro de entrenos."""

from datetime import date

import pytest

from kcn.core.models import Workout
from kcn.data import repository as repo
from kcn.data.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def test_add_and_get_workout(conn):
    w = repo.add_workout(conn, Workout("Natación 30 min", calories=300, duration_min=30))
    assert w.id is not None
    got = repo.get_workouts_for_date(conn, date.today())
    assert len(got) == 1
    assert got[0].description == "Natación 30 min"
    assert got[0].calories == 300


def test_day_workout_calories_sums(conn):
    repo.add_workout(conn, Workout("Gym", 250))
    repo.add_workout(conn, Workout("Calistenia", 150))
    assert repo.day_workout_calories(conn, date.today()) == 400


def test_workouts_isolated_by_date(conn):
    repo.add_workout(conn, Workout("Hyrox", 600, on=date(2020, 1, 1)))
    assert repo.day_workout_calories(conn, date.today()) == 0
    assert repo.day_workout_calories(conn, date(2020, 1, 1)) == 600


def test_delete_workout(conn):
    w = repo.add_workout(conn, Workout("Aquagym", 200))
    repo.delete_workout(conn, w.id)
    assert repo.day_workout_calories(conn, date.today()) == 0


def test_negative_calories_raises():
    with pytest.raises(ValueError):
        Workout("x", calories=-5)