"""Adherencia y rachas (lógica pura sobre resúmenes de día)."""

from __future__ import annotations

from kcn.core.summary import DaySummary


def is_on_target(summary: DaySummary, kcal_tolerance: float = 0.10,
                 protein_min_ratio: float = 0.9) -> bool:
    budget = summary.calorie_budget
    if summary.consumed.kcal <= 0 or budget <= 0:
        return False
    within_kcal = abs(summary.consumed.kcal - budget) <= kcal_tolerance * budget
    protein_ok = summary.consumed.protein_g >= protein_min_ratio * summary.target.protein_g
    return within_kcal and protein_ok


def adherence_rate(summaries: list[DaySummary], **kw) -> float:
    if not summaries:
        return 0.0
    hits = sum(1 for s in summaries if is_on_target(s, **kw))
    return hits / len(summaries)


def current_streak(summaries: list[DaySummary], **kw) -> int:
    streak = 0
    for s in summaries:
        if is_on_target(s, **kw):
            streak += 1
        else:
            break
    return streak
