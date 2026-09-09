"""Tests del parser de Open Food Facts (con datos de ejemplo, sin red)."""

import pytest

from kcn.core.models import FoodSource
from kcn.services.openfoodfacts import _parse_product

NUTELLA = {
    "code": "3017620422003",
    "product_name": "Nutella",
    "brands": "Nutella,Ferrero",
    "nutriments": {
        "energy-kcal_100g": 539,
        "proteins_100g": 6.3,
        "carbohydrates_100g": 57.5,
        "fat_100g": 30.9,
    },
    "serving_quantity": "15",
}


def test_parse_full_product():
    f = _parse_product(NUTELLA)
    assert f.name == "Nutella"
    assert f.brand == "Nutella"                 # solo la primera marca
    assert f.barcode == "3017620422003"
    assert f.source is FoodSource.OPEN_FOOD_FACTS
    assert f.kcal_per_100g == 539.0
    assert f.protein_per_100g == 6.3
    assert f.carbs_per_100g == 57.5
    assert f.fat_per_100g == 30.9
    assert f.default_serving_g == 15.0


def test_parse_converts_kj_when_no_kcal():
    p = {"code": "1", "product_name": "X",
         "nutriments": {"energy_100g": 2255}}      # solo kJ
    f = _parse_product(p)
    assert f.kcal_per_100g == pytest.approx(539.0, abs=0.5)  # 2255 / 4.184


def test_parse_missing_name_returns_none():
    assert _parse_product({"code": "1", "nutriments": {"energy-kcal_100g": 100}}) is None


def test_parse_missing_energy_returns_none():
    assert _parse_product({"code": "1", "product_name": "X",
                           "nutriments": {"proteins_100g": 5}}) is None


def test_parse_code_cast_to_str():
    f = _parse_product({"code": 12345, "product_name": "X",
                        "nutriments": {"energy-kcal_100g": 100}})
    assert f.barcode == "12345"


def test_parse_missing_macros_default_to_zero():
    f = _parse_product({"code": "1", "product_name": "X",
                        "nutriments": {"energy-kcal_100g": 100}})
    assert (f.protein_per_100g, f.carbs_per_100g, f.fat_per_100g) == (0.0, 0.0, 0.0)