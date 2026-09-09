"""Tests del registro de agua."""

from datetime import date, datetime

import pytest

from kcn.core.calculations import default_water_goal_ml
from kcn.core.models import Sex, UserProfile, WaterEntry
from kcn.data import repository as repo
from kcn.data.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def test_add_and_sum_water(conn):
    repo.add_water(conn, WaterEntry(ml=250))
    repo.add_water(conn, WaterEntry(ml=500))
    assert repo.day_water_ml(conn, date.today()) == 750


def test_water_isolated_by_date(conn):
    repo.add_water(conn, WaterEntry(ml=1000, at=datetime(2020, 1, 1, 9, 0)))
    assert repo.day_water_ml(conn, date.today()) == 0
    assert repo.day_water_ml(conn, date(2020, 1, 1)) == 1000


def test_delete_water(conn):
    w = repo.add_water(conn, WaterEntry(ml=250))
    repo.delete_water(conn, w.id)
    assert repo.day_water_ml(conn, date.today()) == 0


def test_negative_water_raises():
    with pytest.raises(ValueError):
        WaterEntry(ml=0)


def test_default_water_goal_by_sex():
    male = UserProfile(weight_kg=78, height_cm=173, age=25, sex=Sex.MALE)
    female = UserProfile(weight_kg=60, height_cm=165, age=25, sex=Sex.FEMALE)
    assert default_water_goal_ml(male) == 2500
    assert default_water_goal_ml(female) == 2000