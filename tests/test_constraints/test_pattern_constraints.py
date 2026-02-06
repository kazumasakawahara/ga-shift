"""Tests for pattern constraints."""

from __future__ import annotations

import numpy as np
import pytest

from ga_shift.constraints.pattern_constraints import (
    AvoidLongConsecutiveWork,
    ConsecutiveHolidayBonus,
    NoIsolatedHolidays,
)
from ga_shift.models.schedule import ScheduleContext, ShiftInput


@pytest.fixture
def make_context(small_shift_input):
    def _make(schedule: np.ndarray) -> ScheduleContext:
        return ScheduleContext(schedule=schedule, shift_input=small_shift_input)
    return _make


class TestAvoidLongConsecutiveWork:
    def test_no_penalty_under_threshold(self, make_context):
        # 4 consecutive work days (threshold=5)
        schedule = np.array([
            [0, 0, 0, 0, 1, 1, 0],
            [0, 0, 0, 0, 1, 1, 0],
            [0, 0, 0, 0, 1, 1, 0],
        ])
        ctx = make_context(schedule)
        template = AvoidLongConsecutiveWork()
        fn = template.compile({"threshold": 5, "penalty_weight": 1.0})
        result = fn(ctx)
        assert result.penalty == 0.0

    def test_penalty_at_threshold(self, make_context):
        # 5 consecutive work days (threshold=5)
        schedule = np.array([
            [0, 0, 0, 0, 0, 1, 1],
            [1, 1, 0, 0, 0, 0, 0],
            [0, 0, 1, 1, 0, 0, 0],
        ])
        ctx = make_context(schedule)
        template = AvoidLongConsecutiveWork()
        fn = template.compile({"threshold": 5, "penalty_weight": 1.0})
        result = fn(ctx)
        # Employee 0: 5 consecutive → (5-4)^2 = 1
        # Employee 1: 5 consecutive → 1
        assert result.penalty > 0.0

    def test_weight_multiplier(self, make_context):
        schedule = np.array([
            [0, 0, 0, 0, 0, 1, 1],
            [1, 1, 1, 1, 1, 1, 1],
            [1, 1, 1, 1, 1, 1, 1],
        ])
        ctx = make_context(schedule)
        template = AvoidLongConsecutiveWork()
        fn1 = template.compile({"threshold": 5, "penalty_weight": 1.0})
        fn2 = template.compile({"threshold": 5, "penalty_weight": 2.0})
        assert fn2(ctx).penalty == fn1(ctx).penalty * 2


class TestNoIsolatedHolidays:
    def test_no_penalty_no_pattern(self, make_context):
        schedule = np.array([
            [0, 0, 0, 0, 0, 1, 1],
            [1, 1, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 1, 1],
        ])
        ctx = make_context(schedule)
        template = NoIsolatedHolidays()
        fn = template.compile({"penalty_weight": 10.0})
        result = fn(ctx)
        assert result.penalty == 0.0

    def test_detects_tobishi_pattern(self, make_context):
        # 1-0-1 pattern: holiday-work-holiday
        schedule = np.array([
            [0, 1, 0, 1, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
        ])
        ctx = make_context(schedule)
        template = NoIsolatedHolidays()
        fn = template.compile({"penalty_weight": 10.0})
        result = fn(ctx)
        # One pattern at positions 1,2,3
        assert result.penalty == 10.0


class TestConsecutiveHolidayBonus:
    def test_bonus_for_consecutive(self, make_context):
        schedule = np.array([
            [0, 0, 0, 0, 0, 1, 1],
            [0, 0, 0, 0, 0, 0, 0],
            [0, 0, 0, 0, 0, 0, 0],
        ])
        ctx = make_context(schedule)
        template = ConsecutiveHolidayBonus()
        fn = template.compile({"threshold": 2, "bonus_per_day": 2.0})
        result = fn(ctx)
        # Employee 0 has 2 consecutive holidays → bonus = 2 * 2.0 = 4.0
        # Penalty is negative (reward)
        assert result.penalty < 0
