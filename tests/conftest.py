"""Common test fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from ga_shift.io.excel_reader import read_shift_input
from ga_shift.io.template_generator import generate_kimachiya_template
from ga_shift.models.constraint import ConstraintSet
from ga_shift.models.employee import EmployeeInfo, EmployeeType, Section
from ga_shift.models.ga_config import GAConfig
from ga_shift.models.schedule import ScheduleContext, ShiftInput


@pytest.fixture
def sample_shift_input() -> ShiftInput:
    """Load sample shift input from the test Excel file.

    Always generates a kimachiya template to ensure compatibility
    with the current column layout.
    """
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
        tmppath = f.name
    generate_kimachiya_template(tmppath, 2026, 3)
    si = read_shift_input(tmppath)
    Path(tmppath).unlink()
    return si


@pytest.fixture
def small_shift_input() -> ShiftInput:
    """Create a minimal ShiftInput for fast unit tests."""
    num_employees = 3
    num_days = 7

    base_schedule = np.zeros((num_employees, num_days), dtype=int)
    # Employee 0 has a preferred off on day 3
    base_schedule[0, 2] = 2

    employees = [
        EmployeeInfo(
            index=0, name="Alice", required_holidays=2,
            preferred_days_off=[3],
            employee_type=EmployeeType.FULL_TIME,
            section=Section.PREP,
            available_vacation_days=5,
        ),
        EmployeeInfo(
            index=1, name="Bob", required_holidays=2,
            preferred_days_off=[],
            employee_type=EmployeeType.FULL_TIME,
            section=Section.LUNCH,
            available_vacation_days=5,
        ),
        EmployeeInfo(
            index=2, name="Charlie", required_holidays=2,
            preferred_days_off=[],
            employee_type=EmployeeType.PART_TIME,
            section=Section.PREP_LUNCH,
            available_vacation_days=3,
        ),
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
def kimachiya_shift_input() -> ShiftInput:
    """Create a kimachiya-specific ShiftInput for unit tests.

    5 employees, 14 days (2 weeks), with unavailable days and sections.
    """
    num_employees = 5
    num_days = 14

    base_schedule = np.zeros((num_employees, num_days), dtype=int)

    # 島村 (index=3): Wednesday unavailable → days 4, 11 (1-indexed, 0-indexed: 3, 10)
    base_schedule[3, 3] = 3  # Wed of week 1
    base_schedule[3, 10] = 3  # Wed of week 2

    employees = [
        EmployeeInfo(
            index=0, name="川崎聡",
            required_holidays=4,
            preferred_days_off=[],
            employee_type=EmployeeType.FULL_TIME,
            section=Section.PREP,
            available_vacation_days=10,
        ),
        EmployeeInfo(
            index=1, name="斎藤駿児",
            required_holidays=4,
            preferred_days_off=[],
            employee_type=EmployeeType.FULL_TIME,
            section=Section.PREP_LUNCH,
            available_vacation_days=10,
        ),
        EmployeeInfo(
            index=2, name="平田園美",
            required_holidays=4,
            preferred_days_off=[],
            employee_type=EmployeeType.PART_TIME,
            section=Section.PREP,
            available_vacation_days=5,
        ),
        EmployeeInfo(
            index=3, name="島村誠",
            required_holidays=4,
            preferred_days_off=[],
            employee_type=EmployeeType.FULL_TIME,
            section=Section.LUNCH,
            available_vacation_days=10,
            unavailable_days=[4, 11],  # 1-indexed
        ),
        EmployeeInfo(
            index=4, name="橋本由紀",
            required_holidays=4,
            preferred_days_off=[],
            employee_type=EmployeeType.PART_TIME,
            section=Section.LUNCH,
            available_vacation_days=5,
        ),
    ]

    return ShiftInput(
        num_employees=num_employees,
        num_days=num_days,
        employee_names=[e.name for e in employees],
        employees=employees,
        required_workers=np.full(num_days, 3, dtype=int),
        base_schedule=base_schedule,
        weekdays=[0, 1, 2, 3, 4, 5, 6, 0, 1, 2, 3, 4, 5, 6],  # Mon-Sun x2
        required_kitchen_workers=np.full(num_days, 3, dtype=int),
    )


@pytest.fixture
def default_constraint_set() -> ConstraintSet:
    return ConstraintSet.default_set()


@pytest.fixture
def kimachi_constraint_set() -> ConstraintSet:
    return ConstraintSet.kimachi_default()


@pytest.fixture
def fast_ga_config() -> GAConfig:
    """Fast GA config for tests."""
    return GAConfig(
        initial_population=20,
        elite_count=5,
        generation_count=3,
    )
