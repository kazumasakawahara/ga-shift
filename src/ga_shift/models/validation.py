"""Validation result models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ViolationSeverity(str, Enum):
    """Severity levels for constraint violations."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Violation(BaseModel):
    """A single constraint violation."""

    constraint_id: str
    message: str
    severity: ViolationSeverity = ViolationSeverity.WARNING
    employee_index: int | None = None
    day_index: int | None = None
    penalty: float = 0.0


class ConstraintScore(BaseModel):
    """Score breakdown for a single constraint."""

    constraint_id: str
    constraint_name: str
    penalty: float
    violations: list[Violation] = Field(default_factory=list)


class ValidationReport(BaseModel):
    """Complete validation report for a schedule."""

    total_penalty: float = 0.0
    constraint_scores: list[ConstraintScore] = Field(default_factory=list)
    violations: list[Violation] = Field(default_factory=list)

    @property
    def is_compliant(self) -> bool:
        """True if no error-level violations exist."""
        return not any(v.severity == ViolationSeverity.ERROR for v in self.violations)

    @property
    def error_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        return sum(1 for v in self.violations if v.severity == ViolationSeverity.WARNING)
