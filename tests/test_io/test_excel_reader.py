"""Tests for Excel reader."""

from __future__ import annotations

import numpy as np
import pytest

from ga_shift.models.schedule import ShiftInput


class TestReadShiftInput:
    def test_loads_correct_dimensions(self, sample_shift_input: ShiftInput):
        assert sample_shift_input.num_employees == 10
        assert sample_shift_input.num_days == 31

    def test_employee_names(self, sample_shift_input: ShiftInput):
        assert len(sample_shift_input.employee_names) == 10
        assert all(isinstance(n, str) for n in sample_shift_input.employee_names)

    def test_required_workers(self, sample_shift_input: ShiftInput):
        rw = sample_shift_input.required_workers
        assert len(rw) == 31
        assert all(rw > 0)

    def test_base_schedule_shape(self, sample_shift_input: ShiftInput):
        assert sample_shift_input.base_schedule.shape == (10, 31)

    def test_base_schedule_values(self, sample_shift_input: ShiftInput):
        unique = np.unique(sample_shift_input.base_schedule)
        # Only 0 (work) and 2 (preferred off) in base schedule
        assert all(v in (0, 2) for v in unique)

    def test_employees_list(self, sample_shift_input: ShiftInput):
        assert len(sample_shift_input.employees) == 10
        for emp in sample_shift_input.employees:
            assert emp.required_holidays > 0
            assert emp.name

    def test_preferred_days_off(self, sample_shift_input: ShiftInput):
        # At least some employees should have preferred days off
        has_preferred = any(len(e.preferred_days_off) > 0 for e in sample_shift_input.employees)
        assert has_preferred
