"""Constraint configuration models."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ParameterType(str, Enum):
    """Types of constraint parameters."""

    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    SELECT = "select"


class ParameterDef(BaseModel):
    """Definition of a constraint parameter for UI rendering."""

    name: str
    display_name: str
    param_type: ParameterType
    default: Any
    min_value: float | None = None
    max_value: float | None = None
    options: list[str] | None = None
    description: str = ""


class ConstraintConfig(BaseModel):
    """A single constraint configuration with user-specified parameters."""

    template_id: str
    enabled: bool = True
    parameters: dict[str, Any] = Field(default_factory=dict)


class ConstraintSet(BaseModel):
    """A collection of constraint configurations."""

    name: str = "default"
    constraints: list[ConstraintConfig] = Field(default_factory=list)

    @classmethod
    def default_set(cls) -> ConstraintSet:
        """Create the default constraint set matching ga_shift_v2.py behavior."""
        return cls(
            name="default",
            constraints=[
                ConstraintConfig(
                    template_id="avoid_long_consecutive_work",
                    parameters={"threshold": 5, "penalty_weight": 1.0},
                ),
                ConstraintConfig(
                    template_id="no_isolated_holidays",
                    parameters={"penalty_weight": 10.0},
                ),
                ConstraintConfig(
                    template_id="required_workers_match",
                    parameters={"penalty_per_diff": 4.0},
                ),
            ],
        )

    @classmethod
    def kimachi_default(cls) -> ConstraintSet:
        """Create the kimachiya cafe default constraint set."""
        return cls(
            name="kimachiya",
            constraints=[
                # Hard constraints
                ConstraintConfig(
                    template_id="unavailable_day_hard",
                    parameters={"penalty_per_violation": 1000.0},
                ),
                # Kitchen staffing (most important)
                ConstraintConfig(
                    template_id="kitchen_min_workers",
                    parameters={"min_workers": 3, "penalty_per_missing": 50.0},
                ),
                # Substitute constraint: Saito covers for Shimamura
                ConstraintConfig(
                    template_id="substitute_constraint",
                    parameters={
                        "primary_name": "島村誠",
                        "substitute_name": "斎藤駿児",
                        "penalty_weight": 40.0,
                    },
                ),
                # Vacation days limit
                ConstraintConfig(
                    template_id="vacation_days_limit",
                    parameters={"penalty_per_excess": 20.0},
                ),
                # Pattern constraints
                ConstraintConfig(
                    template_id="avoid_long_consecutive_work",
                    parameters={"threshold": 5, "penalty_weight": 2.0},
                ),
                ConstraintConfig(
                    template_id="no_isolated_holidays",
                    parameters={"penalty_weight": 5.0},
                ),
                ConstraintConfig(
                    template_id="no_isolated_workdays",
                    parameters={"penalty_weight": 5.0},
                ),
                # Employee constraints
                ConstraintConfig(
                    template_id="max_consecutive_work",
                    parameters={"max_days": 6, "penalty_per_violation": 30.0},
                ),
                ConstraintConfig(
                    template_id="min_days_off_per_week",
                    parameters={"min_days_off": 1, "penalty_per_violation": 20.0},
                ),
                # Fairness
                ConstraintConfig(
                    template_id="equal_weekend_distribution",
                    parameters={"max_diff": 2, "penalty_per_diff": 5.0},
                ),
            ],
        )
