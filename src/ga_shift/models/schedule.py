"""Schedule-related data models."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from ga_shift.models.employee import EmployeeInfo


class ShiftInput(BaseModel):
    """Input data parsed from Excel file."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    num_employees: int
    num_days: int
    employee_names: list[str]
    employees: list[EmployeeInfo]
    required_workers: NDArray[np.int_] = Field(
        description="Required workers per day, shape=(num_days,)"
    )
    base_schedule: NDArray[np.int_] = Field(
        description="Base schedule matrix, shape=(num_employees, num_days). 0=work, 2=preferred off"
    )
    day_labels: list[str] = Field(
        default_factory=list, description="Day labels (e.g. '1(月)')"
    )
    weekdays: list[int] = Field(
        default_factory=list, description="Weekday indices (0=Mon..6=Sun) for each day"
    )


class ScheduleContext(BaseModel):
    """Context for constraint evaluation.

    Provides a unified view of a schedule for penalty functions.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    schedule: NDArray[np.int_] = Field(
        description="Schedule matrix, shape=(num_employees, num_days). 0=work, 1=holiday, 2=preferred off"
    )
    shift_input: ShiftInput
    employee_index: int | None = Field(
        default=None, description="If set, evaluate only this employee"
    )
    day_index: int | None = Field(
        default=None, description="If set, evaluate only this day"
    )

    @property
    def num_employees(self) -> int:
        return self.shift_input.num_employees

    @property
    def num_days(self) -> int:
        return self.shift_input.num_days

    @property
    def binary_schedule(self) -> NDArray[np.int_]:
        """Schedule where 2 (preferred off) is treated as 1 (holiday)."""
        return np.where(self.schedule == 2, 1, self.schedule)

    @property
    def work_schedule(self) -> NDArray[np.int_]:
        """Binary work schedule: 1=work, 0=off."""
        return 1 - self.binary_schedule


class ShiftResult(BaseModel):
    """Result of GA optimization."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    best_schedule: NDArray[np.int_] = Field(
        description="Best schedule found, shape=(num_employees, num_days)"
    )
    best_score: float
    score_history: list[float] = Field(default_factory=list)
    generation_count: int = 0
