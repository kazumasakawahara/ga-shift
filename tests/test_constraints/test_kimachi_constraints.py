"""Tests for kimachiya-specific constraints."""

from __future__ import annotations

import numpy as np
import pytest

from ga_shift.constraints.kimachi_constraints import (
    ClosedDayConstraint,
    KitchenMinWorkers,
    SubstituteConstraint,
    UnavailableDayHard,
    VacationDaysLimit,
)
from ga_shift.models.schedule import ScheduleContext, ShiftInput


class TestKitchenMinWorkers:
    def test_no_penalty_when_enough_workers(self, kimachiya_shift_input: ShiftInput):
        """All 5 employees working → 5 kitchen workers (>= 3) → no penalty."""
        schedule = np.zeros((5, 14), dtype=int)
        # Set unavailable days
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = KitchenMinWorkers()
        fn = template.compile({"min_workers": 3, "penalty_per_missing": 50.0})
        result = fn(ctx)
        assert result.penalty == 0.0

    def test_penalty_when_too_few_workers(self, kimachiya_shift_input: ShiftInput):
        """Only 2 kitchen workers on a day → penalty."""
        schedule = np.zeros((5, 14), dtype=int)
        schedule[3, 3] = 3  # unavailable
        schedule[3, 10] = 3

        # Day 0: 3 people off → only 2 working
        schedule[0, 0] = 1  # Kawasaki off
        schedule[1, 0] = 1  # Saito off
        schedule[2, 0] = 1  # Hirata off
        # Only Shimamura (LUNCH) and Hashimoto (LUNCH) working → 2 kitchen workers

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = KitchenMinWorkers()
        fn = template.compile({"min_workers": 3, "penalty_per_missing": 50.0})
        result = fn(ctx)
        assert result.penalty > 0

    def test_code3_counts_as_absent(self, kimachiya_shift_input: ShiftInput):
        """Code 3 (unavailable) should count as absent for kitchen count."""
        schedule = np.zeros((5, 14), dtype=int)
        schedule[3, 3] = 3  # Shimamura unavailable on Wed
        schedule[3, 10] = 3

        # Day 3 (Wed): Shimamura unavailable + 2 others off → only 2 kitchen workers
        schedule[0, 3] = 1  # Kawasaki off
        schedule[2, 3] = 1  # Hirata off

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = KitchenMinWorkers()
        fn = template.compile({"min_workers": 3, "penalty_per_missing": 50.0})
        result = fn(ctx)
        # Day 3: Shimamura absent (code 3), Kawasaki off, Hirata off
        # Only Saito and Hashimoto → 2 kitchen workers → penalty for 1 missing
        assert result.penalty == 50.0


class TestSubstituteConstraint:
    def test_no_penalty_when_substitute_works(self, kimachiya_shift_input: ShiftInput):
        """When Shimamura is absent, Saito is working → no penalty."""
        schedule = np.zeros((5, 14), dtype=int)
        schedule[3, 3] = 3  # Shimamura unavailable Wed
        schedule[3, 10] = 3
        # Saito (index=1) is working on both days (default=0)

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = SubstituteConstraint()
        fn = template.compile({
            "primary_name": "島村誠",
            "substitute_name": "斎藤駿児",
            "penalty_weight": 40.0,
        })
        result = fn(ctx)
        assert result.penalty == 0.0

    def test_penalty_when_both_absent(self, kimachiya_shift_input: ShiftInput):
        """When both Shimamura and Saito are absent → penalty."""
        schedule = np.zeros((5, 14), dtype=int)
        schedule[3, 3] = 3  # Shimamura unavailable Wed
        schedule[3, 10] = 3
        schedule[1, 3] = 1  # Saito also off on Wed

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = SubstituteConstraint()
        fn = template.compile({
            "primary_name": "島村誠",
            "substitute_name": "斎藤駿児",
            "penalty_weight": 40.0,
        })
        result = fn(ctx)
        assert result.penalty == 40.0  # One day violation

    def test_multiple_violations(self, kimachiya_shift_input: ShiftInput):
        """Both absent on multiple days."""
        schedule = np.zeros((5, 14), dtype=int)
        schedule[3, 3] = 3  # Shimamura unavailable Wed week 1
        schedule[3, 10] = 3  # Shimamura unavailable Wed week 2
        schedule[1, 3] = 1  # Saito off Wed week 1
        schedule[1, 10] = 1  # Saito off Wed week 2

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = SubstituteConstraint()
        fn = template.compile({
            "primary_name": "島村誠",
            "substitute_name": "斎藤駿児",
            "penalty_weight": 40.0,
        })
        result = fn(ctx)
        assert result.penalty == 80.0  # Two violations


class TestVacationDaysLimit:
    def test_no_penalty_within_limit(self, kimachiya_shift_input: ShiftInput):
        """Preferred days within limit → no penalty."""
        # kimachiya_shift_input has no preferred_days_off
        schedule = np.zeros((5, 14), dtype=int)
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = VacationDaysLimit()
        fn = template.compile({"penalty_per_excess": 20.0})
        result = fn(ctx)
        assert result.penalty == 0.0

    def test_penalty_when_over_limit(self, kimachiya_shift_input: ShiftInput):
        """More preferred days than available → penalty."""
        # Modify employee to have excess preferred days
        si = kimachiya_shift_input
        # Hashimoto (index=4) has 5 vacation days
        # Give her 7 preferred days off
        si.employees[4].preferred_days_off = [1, 2, 3, 5, 6, 7, 8]

        schedule = np.zeros((5, 14), dtype=int)
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        ctx = ScheduleContext(schedule=schedule, shift_input=si)
        template = VacationDaysLimit()
        fn = template.compile({"penalty_per_excess": 20.0})
        result = fn(ctx)
        # 7 preferred - 5 available = 2 excess → 2 * 20 = 40
        assert result.penalty == 40.0


class TestUnavailableDayHard:
    def test_no_penalty_when_respected(self, kimachiya_shift_input: ShiftInput):
        """Unavailable days kept as code 3 → no penalty."""
        schedule = np.zeros((5, 14), dtype=int)
        schedule[3, 3] = 3  # Shimamura Wed
        schedule[3, 10] = 3

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = UnavailableDayHard()
        fn = template.compile({"penalty_per_violation": 1000.0})
        result = fn(ctx)
        assert result.penalty == 0.0

    def test_extreme_penalty_when_violated(self, kimachiya_shift_input: ShiftInput):
        """Code 3 changed to work → extreme penalty."""
        schedule = np.zeros((5, 14), dtype=int)
        # Intentionally set unavailable day to work (violation!)
        schedule[3, 3] = 0  # Should be 3 (unavailable)
        schedule[3, 10] = 3  # This one is correct

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = UnavailableDayHard()
        fn = template.compile({"penalty_per_violation": 1000.0})
        result = fn(ctx)
        assert result.penalty == 1000.0  # One violation


class TestClosedDayConstraint:
    """Tests for ClosedDayConstraint (定休日制約).

    kimachiya_shift_input weekdays = [0,1,2,3,4,5,6,0,1,2,3,4,5,6]
    So closed days (Sat=5, Sun=6) are at indices: 5, 6, 12, 13
    Employees: 0=川崎(正規), 1=斎藤(正規), 2=平田(パート), 3=島村(正規), 4=橋本(パート)
    """

    def _default_params(self, **overrides):
        params = {
            "closed_weekdays": "5,6",
            "override_open_days": "",
            "penalty_closed_day": 500.0,
            "penalty_parttime_override": 100.0,
        }
        params.update(overrides)
        return params

    def test_no_penalty_when_all_off_on_closed_days(
        self, kimachiya_shift_input: ShiftInput
    ):
        """All employees off on Sat/Sun → no penalty."""
        schedule = np.zeros((5, 14), dtype=int)
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        # Set all employees to holiday on closed days (5, 6, 12, 13)
        for d in [5, 6, 12, 13]:
            schedule[:, d] = 1

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = ClosedDayConstraint()
        fn = template.compile(self._default_params())
        result = fn(ctx)
        assert result.penalty == 0.0

    def test_penalty_when_working_on_closed_day(
        self, kimachiya_shift_input: ShiftInput
    ):
        """One employee working on a normal closed day → hard penalty."""
        schedule = np.ones((5, 14), dtype=int)  # all off
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        # Set weekdays to work
        for d in [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]:
            schedule[:, d] = 0
        # Employee 0 (正規) working on Saturday (index 5)
        schedule[0, 5] = 0

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = ClosedDayConstraint()
        fn = template.compile(self._default_params())
        result = fn(ctx)
        assert result.penalty == 500.0
        assert "定休日" in result.details
        assert "川崎聡" in result.details

    def test_penalty_multiple_violations(
        self, kimachiya_shift_input: ShiftInput
    ):
        """Two employees working on closed day → 2 × penalty."""
        schedule = np.ones((5, 14), dtype=int)
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        for d in [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]:
            schedule[:, d] = 0
        # Two employees working on Sunday (index 6)
        schedule[0, 6] = 0  # 川崎
        schedule[1, 6] = 0  # 斎藤

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = ClosedDayConstraint()
        fn = template.compile(self._default_params())
        result = fn(ctx)
        assert result.penalty == 1000.0  # 2 * 500

    def test_override_day_fulltime_no_penalty(
        self, kimachiya_shift_input: ShiftInput
    ):
        """Regular employee working on override day → no penalty."""
        schedule = np.ones((5, 14), dtype=int)
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        for d in [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]:
            schedule[:, d] = 0
        # 川崎(正規) working on Saturday (index 5), which is override day (day 6 in 1-indexed)
        schedule[0, 5] = 0

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = ClosedDayConstraint()
        fn = template.compile(self._default_params(override_open_days="6"))
        result = fn(ctx)
        assert result.penalty == 0.0  # Full-time on override → OK

    def test_override_day_parttime_penalty(
        self, kimachiya_shift_input: ShiftInput
    ):
        """Part-time employee working on override day → soft penalty."""
        schedule = np.ones((5, 14), dtype=int)
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        for d in [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]:
            schedule[:, d] = 0
        # 平田(パート, index=2) working on Saturday (index 5), override day 6
        schedule[2, 5] = 0

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = ClosedDayConstraint()
        fn = template.compile(self._default_params(override_open_days="6"))
        result = fn(ctx)
        assert result.penalty == 100.0  # Part-time on override → soft penalty
        assert "臨時営業" in result.details
        assert "パート" in result.details

    def test_override_only_affects_specified_days(
        self, kimachiya_shift_input: ShiftInput
    ):
        """Override only on one Saturday, other closed days still hard penalty."""
        schedule = np.ones((5, 14), dtype=int)
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        for d in [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]:
            schedule[:, d] = 0
        # 川崎(正規) on Saturday week1 (index 5) → override day 6
        schedule[0, 5] = 0
        # 川崎(正規) on Sunday week1 (index 6) → NOT override → hard penalty
        schedule[0, 6] = 0

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = ClosedDayConstraint()
        fn = template.compile(self._default_params(override_open_days="6"))
        result = fn(ctx)
        # index 5 is override → 0 penalty (full-time)
        # index 6 is NOT override → 500 penalty
        assert result.penalty == 500.0

    def test_multiple_override_days(
        self, kimachiya_shift_input: ShiftInput
    ):
        """Multiple override days specified."""
        schedule = np.ones((5, 14), dtype=int)
        schedule[3, 3] = 3
        schedule[3, 10] = 3
        for d in [0, 1, 2, 3, 4, 7, 8, 9, 10, 11]:
            schedule[:, d] = 0
        # 斎藤(正規) on Sat week1 (index 5) and Sat week2 (index 12)
        schedule[1, 5] = 0
        schedule[1, 12] = 0

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = ClosedDayConstraint()
        # Override both Saturdays: day 6 and day 13 (1-indexed)
        fn = template.compile(self._default_params(override_open_days="6,13"))
        result = fn(ctx)
        assert result.penalty == 0.0  # Both are override days, full-time employee

    def test_no_closed_weekdays(self, kimachiya_shift_input: ShiftInput):
        """Empty closed_weekdays → no penalty ever."""
        schedule = np.zeros((5, 14), dtype=int)  # everyone working every day
        schedule[3, 3] = 3
        schedule[3, 10] = 3

        ctx = ScheduleContext(schedule=schedule, shift_input=kimachiya_shift_input)
        template = ClosedDayConstraint()
        fn = template.compile(self._default_params(closed_weekdays=""))
        result = fn(ctx)
        assert result.penalty == 0.0

    def test_template_id(self):
        """Verify template_id."""
        template = ClosedDayConstraint()
        assert template.template_id == "closed_day"

    def test_name_ja(self):
        """Verify Japanese name."""
        template = ClosedDayConstraint()
        assert "定休日" in template.name_ja

    def test_category(self):
        """Verify category."""
        template = ClosedDayConstraint()
        assert template.category == "day"
