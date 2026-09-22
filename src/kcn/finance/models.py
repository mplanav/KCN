"""Modelos del módulo de finanzas."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class Category:
    name: str
    monthly_limit: float = 0.0
    id: int | None = None


@dataclass
class Expense:
    amount: float
    on: date = None
    category_id: int | None = None
    note: str | None = None
    id: int | None = None

    def __post_init__(self) -> None:
        if self.on is None:
            self.on = date.today()


@dataclass
class SavingsGoal:
    name: str
    target: float = 0.0
    saved: float = 0.0
    id: int | None = None
