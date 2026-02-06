"""Base classes for the constraint template system."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from ga_shift.models.constraint import ParameterDef
from ga_shift.models.schedule import ScheduleContext


class PenaltyResult:
    """Result of a penalty function evaluation."""

    __slots__ = ("penalty", "details")

    def __init__(self, penalty: float = 0.0, details: str = "") -> None:
        self.penalty = penalty
        self.details = details


# Type alias for compiled penalty functions
PenaltyFunction = Callable[[ScheduleContext], PenaltyResult]


class ConstraintTemplate(ABC):
    """Abstract base class for constraint templates.

    Each template defines:
    - A unique ID and display name
    - Configurable parameters with defaults
    - A compile() method that produces a PenaltyFunction
    """

    @property
    @abstractmethod
    def template_id(self) -> str:
        """Unique identifier for this constraint template."""

    @property
    @abstractmethod
    def name_ja(self) -> str:
        """Japanese display name."""

    @property
    @abstractmethod
    def category(self) -> str:
        """Category: employee, day, pattern, fairness."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Description of what this constraint does."""

    @property
    @abstractmethod
    def parameters(self) -> list[ParameterDef]:
        """Parameter definitions for UI rendering."""

    @abstractmethod
    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        """Compile this template with given parameters into a penalty function."""


@dataclass
class CompiledConstraint:
    """A constraint template compiled with specific parameters."""

    template_id: str
    name_ja: str
    penalty_fn: PenaltyFunction
    parameters: dict[str, Any]
