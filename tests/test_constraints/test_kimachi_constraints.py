"""Tests for kimachiya-specific constraints."""

from __future__ import annotations

import numpy as np
import pytest

from ga_shift.constraints.kimachi_constraints import (
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
