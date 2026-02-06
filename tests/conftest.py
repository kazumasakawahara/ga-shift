"""Common test fixtures."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ga_shift.io.excel_reader import read_shift_input
from ga_shift.models.constraint import ConstraintSet
from ga_shift.models.employee import EmployeeInfo
from ga_shift.models.ga_config import GAConfig
from ga_shift.models.schedule import ScheduleContext, ShiftInput


@pytest.fixture
def sample_shift_input() -> ShiftInput:
    """Load sample shift input from the test Excel file."""
    project_root = Path(__file__).parent.parent
    filepath = project_root / "shift_input.xlsx"
    if not filepath.exists():
        pytest.skip("shift_input.xlsx not found")
    return read_shift_input(filepath)


@pytest.fixture
def small_shift_input() -> ShiftInput:
    """Create a minimal ShiftInput for fast unit tests."""
    num_employees = 3
    num_days = 7

    base_schedule = np.zeros((num_employees, num_days), dtype=int)
    # Employee 0 has a preferred off on day 3
    base_schedule[0, 2] = 2

    employees = [
        EmployeeInfo(index=0, name="Alice", required_holidays=2, preferred_days_off=[3]),
        EmployeeInfo(index=1, name="Bob", required_holidays=2, preferred_days_off=[]),
        EmployeeInfo(index=2, name="Charlie", required_holidays=2, preferred_days_off=[]),
    ]

    return ShiftInput(
        num_employees=num_employees,
        num_days=num_days,
        employee_names=["Alice", "Bob", "Charlie"],
        employees=employees,
        required_workers=np.array([2, 2, 2, 2, 2, 2, 2]),
        base_schedule=base_schedule,
        weekdays=[0, 1, 2, 3, 4, 5, 6],  # Mon-Sun
    )


@pytest.fixture
def default_constraint_set() -> ConstraintSet:
    return ConstraintSet.default_set()


@pytest.fixture
def fast_ga_config() -> GAConfig:
    """Fast GA config for tests."""
    return GAConfig(
        initial_population=20,
        elite_count=5,
        generation_count=3,
    )
