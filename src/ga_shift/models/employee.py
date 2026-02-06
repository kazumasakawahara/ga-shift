"""Employee data models."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class EmployeeType(str, Enum):
    """Employment type."""

    FULL_TIME = "正規"
    PART_TIME = "パート"


class Section(str, Enum):
    """Work section assignment."""

    PREP = "仕込み"
    LUNCH = "ランチ"
    PREP_LUNCH = "仕込み・ランチ"
    HALL = "ホール"


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
    employee_type: EmployeeType = Field(
        default=EmployeeType.FULL_TIME, description="Employment type"
    )
    section: Section | None = Field(default=None, description="Work section")
    available_vacation_days: int = Field(
        default=0, ge=0, description="Available paid leave days for the month"
    )
    unavailable_days: list[int] = Field(
        default_factory=list,
        description="1-indexed day numbers marked as unavailable (code 3 / ×)",
    )
