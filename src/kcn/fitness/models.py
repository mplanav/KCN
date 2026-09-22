"""Modelos del módulo de entrenos."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date


@dataclass
class Exercise:
    name: str
    category: str = "strength"
    muscle_group: str | None = None
    id: int | None = None


@dataclass
class ExerciseSet:
    exercise: Exercise
    weight_kg: float | None = None
    reps: int | None = None
    id: int | None = None

    @property
    def volume(self) -> float:
        return (self.weight_kg or 0.0) * (self.reps or 0)


@dataclass
class WorkoutSession:
    name: str = ""
    on: date = None
    calories: int | None = None
    duration_min: int | None = None
    note: str | None = None
    sets: list[ExerciseSet] = field(default_factory=list)
    id: int | None = None

    def __post_init__(self) -> None:
        if self.on is None:
            self.on = date.today()

    @property
    def volume(self) -> float:
        return sum(s.volume for s in self.sets)
