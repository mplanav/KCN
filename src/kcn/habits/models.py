"""Modelos del módulo de hábitos."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Habit:
    name: str
    active: bool = True
    id: int | None = None
