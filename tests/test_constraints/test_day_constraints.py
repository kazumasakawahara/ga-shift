"""Tests for day constraints."""

from __future__ import annotations

import numpy as np
import pytest

from ga_shift.constraints.day_constraints import RequiredWorkersMatch
from ga_shift.models.schedule import ScheduleContext


class TestRequiredWorkersMatch:
    def test_perfect_match_no_penalty(self, small_shift_input):
        # 3 employees, required=2 → 1 person off per day
        schedule = np.array([
            [0, 0, 0, 0, 0, 1, 1],
            [1, 0, 0, 0, 0, 0, 1],
            [0, 1, 1, 1, 1, 0, 0],  # This doesn't match perfectly, but let's test
        ])
        # Actually make it match: 2 workers each day
        schedule = np.array([
            [0, 0, 1, 0, 0, 1, 0],
            [0, 1, 0, 0, 1, 0, 0],
            [1, 0, 0, 1, 0, 0, 1],
        ])
        ctx = ScheduleContext(schedule=schedule, shift_input=small_shift_input)
        template = RequiredWorkersMatch()
        fn = template.compile({"penalty_per_diff": 4.0})
        result = fn(ctx)
        assert result.penalty == 0.0

    def test_penalty_for_mismatch(self, small_shift_input):
        # All workers present every day → 3 workers vs required 2
        schedule = np.zeros((3, 7), dtype=int)
        ctx = ScheduleContext(schedule=schedule, shift_input=small_shift_input)
        template = RequiredWorkersMatch()
        fn = template.compile({"penalty_per_diff": 4.0})
        result = fn(ctx)
        # Each day: 3 workers vs 2 required → diff=1 → penalty = 7 * 4.0 = 28.0
        assert result.penalty == 28.0
