"""Employee data models."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EmployeeAttribute(BaseModel):
    """Employee skill or attribute."""

    name: str
    level: int = Field(default=1, ge=1, le=5)


class EmployeeInfo(BaseModel):
    """Individual employee information."""

    index: int = Field(description="Zero-based row index in the schedule")
    name: str
    required_holidays: int = Field(ge=0, description="Contract-specified holiday count")
    preferred_days_off: list[int] = Field(
        default_factory=list, description="1-indexed day numbers marked as preferred off"
    )
    attributes: list[EmployeeAttribute] = Field(default_factory=list)
