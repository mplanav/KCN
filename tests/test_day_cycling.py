"""Tests del ciclado de carbohidratos por tipo de día."""

from kcn.core.calculations import day_targets, macro_targets
from kcn.core.models import ActivityLevel, DayType, Sex, UserProfile


def profile(pct=0.0):
    return UserProfile(weight_kg=80, height_cm=180, age=30, sex=Sex.MALE,
                       activity=ActivityLevel.MODERATE, carb_cycle_pct=pct)


def test_no_cycling_by_default():
    p = profile(0.0)
    base = macro_targets(p)
    assert day_targets(p, DayType.TRAINING) == base
    assert day_targets(p, DayType.REST) == base


def test_training_day_more_carbs_rest_day_fewer():
    p = profile(0.2)
    base = macro_targets(p)
    train = day_targets(p, DayType.TRAINING)
    rest = day_targets(p, DayType.REST)
    assert train.carbs_g > base.carbs_g > rest.carbs_g
    assert train.kcal > base.kcal > rest.kcal


def test_protein_and_fat_unchanged():
    p = profile(0.2)
    base = macro_targets(p)
    for dt in (DayType.TRAINING, DayType.REST):
        t = day_targets(p, dt)
        assert t.protein_g == base.protein_g
        assert t.fat_g == base.fat_g       # solo se mueven los carbos


def test_shift_is_symmetric_in_carbs():
    p = profile(0.2)
    base = macro_targets(p)
    train = day_targets(p, DayType.TRAINING)
    rest = day_targets(p, DayType.REST)
    up = train.carbs_g - base.carbs_g
    down = base.carbs_g - rest.carbs_g
    assert abs(up - down) <= 1             # simétrico (salvo redondeo)


def test_rest_carbs_never_negative():
    p = profile(5.0)                        # % absurdo
    assert day_targets(p, DayType.REST).carbs_g >= 0