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
