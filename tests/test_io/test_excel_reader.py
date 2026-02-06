"""Tests for Excel reader."""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest

from ga_shift.io.excel_reader import read_shift_input
from ga_shift.io.template_generator import generate_kimachiya_template
from ga_shift.models.employee import EmployeeType, Section
from ga_shift.models.schedule import ShiftInput


class TestReadShiftInput:
    def test_loads_correct_dimensions(self, sample_shift_input: ShiftInput):
        assert sample_shift_input.num_employees >= 1
        assert sample_shift_input.num_days >= 1

    def test_employee_names(self, sample_shift_input: ShiftInput):
        assert len(sample_shift_input.employee_names) == sample_shift_input.num_employees
        assert all(isinstance(n, str) for n in sample_shift_input.employee_names)

    def test_required_workers(self, sample_shift_input: ShiftInput):
        rw = sample_shift_input.required_workers
        assert len(rw) == sample_shift_input.num_days
        assert all(rw > 0)

    def test_base_schedule_shape(self, sample_shift_input: ShiftInput):
        expected = (sample_shift_input.num_employees, sample_shift_input.num_days)
        assert sample_shift_input.base_schedule.shape == expected

    def test_base_schedule_values(self, sample_shift_input: ShiftInput):
        unique = np.unique(sample_shift_input.base_schedule)
        # Valid values: 0 (work), 2 (preferred off), 3 (unavailable)
        assert all(v in (0, 2, 3) for v in unique)

    def test_employees_list(self, sample_shift_input: ShiftInput):
        assert len(sample_shift_input.employees) == sample_shift_input.num_employees
        for emp in sample_shift_input.employees:
            assert emp.required_holidays > 0
            assert emp.name


class TestKimachiyaRoundTrip:
    """Tests for kimachiya-specific Excel round-trip."""

    @pytest.fixture
    def kimachiya_excel(self):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            filepath = f.name
        generate_kimachiya_template(filepath, 2026, 3)
        yield filepath
        Path(filepath).unlink(missing_ok=True)

    def test_kimachiya_dimensions(self, kimachiya_excel):
        si = read_shift_input(kimachiya_excel)
        assert si.num_employees == 5
        assert si.num_days == 31

    def test_kimachiya_names(self, kimachiya_excel):
        si = read_shift_input(kimachiya_excel)
        expected = ["川崎聡", "斎藤駿児", "平田園美", "島村誠", "橋本由紀"]
        assert si.employee_names == expected

    def test_kimachiya_employee_types(self, kimachiya_excel):
        si = read_shift_input(kimachiya_excel)
        assert si.employees[0].employee_type == EmployeeType.FULL_TIME
        assert si.employees[2].employee_type == EmployeeType.PART_TIME
        assert si.employees[4].employee_type == EmployeeType.PART_TIME

    def test_kimachiya_sections(self, kimachiya_excel):
        si = read_shift_input(kimachiya_excel)
        assert si.employees[0].section == Section.PREP
        assert si.employees[1].section == Section.PREP_LUNCH
        assert si.employees[3].section == Section.LUNCH

    def test_kimachiya_vacation_days(self, kimachiya_excel):
        si = read_shift_input(kimachiya_excel)
        assert si.employees[0].available_vacation_days == 10
        assert si.employees[2].available_vacation_days == 5

    def test_kimachiya_unavailable_days(self, kimachiya_excel):
        si = read_shift_input(kimachiya_excel)
        shimamura = si.employees[3]
        # 2026年3月の水曜日: 4, 11, 18, 25
        assert len(shimamura.unavailable_days) == 4
        assert all(d in shimamura.unavailable_days for d in [4, 11, 18, 25])

    def test_kimachiya_unavailable_code3(self, kimachiya_excel):
        si = read_shift_input(kimachiya_excel)
        base = si.base_schedule
        for emp in si.employees:
            for d in emp.unavailable_days:
                assert base[emp.index, d - 1] == 3

    def test_kimachiya_kitchen_required(self, kimachiya_excel):
        si = read_shift_input(kimachiya_excel)
        assert si.required_kitchen_workers is not None
        assert all(si.required_kitchen_workers == 3)
