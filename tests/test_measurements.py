"""Tests del historial de medidas corporales y del IMC."""

from datetime import date

import pytest

from kcn.core.calculations import bmi, bmi_category
from kcn.core.models import BodyMeasurement
from kcn.data import repository as repo
from kcn.data.db import connect


@pytest.fixture
def conn():
    c = connect(":memory:")
    yield c
    c.close()


def test_add_partial_measurement(conn):
    m = repo.add_measurement(conn, BodyMeasurement(weight_kg=78.0, body_fat_pct=14.5))
    assert m.id is not None
    got = repo.latest_measurement(conn)
    assert got.weight_kg == 78.0
    assert got.body_fat_pct == 14.5
    assert got.muscle_mass_kg is None            # campos no rellenados quedan None


def test_latest_is_most_recent_by_date(conn):
    repo.add_measurement(conn, BodyMeasurement(weight_kg=80, on=date(2026, 1, 1)))
    repo.add_measurement(conn, BodyMeasurement(weight_kg=78, on=date(2026, 6, 1)))
    assert repo.latest_measurement(conn).weight_kg == 78


def test_weight_series_ascending_and_filters_nulls(conn):
    repo.add_measurement(conn, BodyMeasurement(body_fat_pct=15, on=date(2026, 1, 1)))  # sin peso
    repo.add_measurement(conn, BodyMeasurement(weight_kg=79, on=date(2026, 2, 1)))
    repo.add_measurement(conn, BodyMeasurement(weight_kg=78, on=date(2026, 3, 1)))
    series = repo.weight_series(conn)
    assert [w for _, w in series] == [79, 78]     # solo pesos, en orden ascendente


def test_delete_measurement(conn):
    m = repo.add_measurement(conn, BodyMeasurement(weight_kg=78))
    repo.delete_measurement(conn, m.id)
    assert repo.latest_measurement(conn) is None


def test_bmi_and_category():
    value = bmi(78, 173)
    assert value == pytest.approx(26.06, abs=0.05)
    assert bmi_category(value) == "Sobrepeso"      # el IMC no ve tu músculo (ver caveat)
    assert bmi_category(22) == "Normopeso"
    assert bmi_category(17) == "Bajo peso"
    assert bmi_category(31) == "Obesidad"