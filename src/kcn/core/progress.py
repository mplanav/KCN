"""Ajuste automático por progreso: compara el ritmo real de peso con el objetivo.

Usa regresión lineal sobre el historial de peso (más robusta que 'último menos
primero' frente a las fluctuaciones diarias) y sugiere un ajuste de kcal usando
la equivalencia 7700 kcal ≈ 1 kg (FUENTES #6).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from kcn.core.calculations import KCAL_PER_KG_BODYWEIGHT
from kcn.core.models import Goal, UserProfile


@dataclass
class WeightTrend:
    weekly_change_kg: float
    span_days: int
    n_points: int


def _slope_per_day(points: list[tuple[date, float]]) -> float:
    """Pendiente (kg/día) por mínimos cuadrados."""
    xs = [(d - points[0][0]).days for d, _ in points]
    ys = [w for _, w in points]
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    den = sum((x - mx) ** 2 for x in xs)
    if den == 0:
        return 0.0
    num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return num / den


def weight_trend(series: list[tuple[date, float]], window_days: int = 28) -> WeightTrend | None:
    """Tendencia de peso en la ventana reciente (kg/semana)."""
    if len(series) < 2:
        return None
    end = series[-1][0]
    window = [(d, w) for d, w in series if (end - d).days <= window_days]
    if len(window) < 2:
        return None
    span = (window[-1][0] - window[0][0]).days
    if span <= 0:
        return None
    return WeightTrend(weekly_change_kg=_slope_per_day(window) * 7,
                       span_days=span, n_points=len(window))


def expected_weekly_change_kg(profile: UserProfile) -> float:
    if profile.goal is Goal.MAINTAIN:
        return 0.0
    return -profile.weekly_rate_kg if profile.goal is Goal.LOSE else profile.weekly_rate_kg


@dataclass
class AdjustmentSuggestion:
    enough_data: bool
    on_track: bool
    expected_weekly_change_kg: float
    actual_weekly_change_kg: float | None
    suggested_kcal_delta: int
    suggested_kcal: int | None
    reason: str


def suggest_adjustment(profile: UserProfile, series: list[tuple[date, float]],
                       current_kcal: int, window_days: int = 28,
                       min_span_days: int = 14, tolerance_kg: float = 0.1,
                       max_delta: int = 500) -> AdjustmentSuggestion:
    """Sugiere un ajuste de kcal según el progreso real de peso."""
    expected = expected_weekly_change_kg(profile)
    trend = weight_trend(series, window_days)

    if trend is None or trend.span_days < min_span_days:
        return AdjustmentSuggestion(
            enough_data=False, on_track=False, expected_weekly_change_kg=expected,
            actual_weekly_change_kg=None, suggested_kcal_delta=0, suggested_kcal=None,
            reason="Necesito al menos ~2 semanas de registros de peso para ajustar con criterio.")

    actual = trend.weekly_change_kg
    diff = expected - actual

    if abs(diff) < tolerance_kg:
        return AdjustmentSuggestion(
            enough_data=True, on_track=True, expected_weekly_change_kg=expected,
            actual_weekly_change_kg=actual, suggested_kcal_delta=0,
            suggested_kcal=current_kcal,
            reason="Vas en línea con tu objetivo; no hace falta cambiar nada.")

    delta = round(diff * KCAL_PER_KG_BODYWEIGHT / 7)
    delta = max(-max_delta, min(max_delta, delta))
    verb = "bajar" if delta < 0 else "subir"
    reason = (f"Tu ritmo real es {actual:+.2f} kg/sem y el objetivo {expected:+.2f} kg/sem. "
              f"Se sugiere {verb} unas {abs(delta)} kcal/día.")
    return AdjustmentSuggestion(
        enough_data=True, on_track=False, expected_weekly_change_kg=expected,
        actual_weekly_change_kg=actual, suggested_kcal_delta=delta,
        suggested_kcal=current_kcal + delta, reason=reason)