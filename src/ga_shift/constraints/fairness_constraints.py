"""Fairness constraints (equitable distribution of holidays)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ga_shift.constraints.base import ConstraintTemplate, PenaltyFunction, PenaltyResult
from ga_shift.models.constraint import ParameterDef, ParameterType
from ga_shift.models.schedule import ScheduleContext


class EqualWeekendDistribution(ConstraintTemplate):
    """Penalize unequal distribution of weekend holidays among employees."""

    @property
    def template_id(self) -> str:
        return "equal_weekend_distribution"

    @property
    def name_ja(self) -> str:
        return "週末休日の公平配分"

    @property
    def category(self) -> str:
        return "fairness"

    @property
    def description(self) -> str:
        return "社員間で週末休日数の差が大きい場合にペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="max_diff",
                display_name="許容差",
                param_type=ParameterType.INT,
                default=2,
                min_value=0,
                max_value=10,
                description="社員間の週末休日数の最大許容差",
            ),
            ParameterDef(
                name="penalty_per_excess",
                display_name="超過1日あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=3.0,
                min_value=0.1,
                max_value=50.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        max_diff = int(params["max_diff"])
        penalty_per = float(params["penalty_per_excess"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            weekdays = ctx.shift_input.weekdays
            weekend_indices = [d for d, w in enumerate(weekdays) if w in (5, 6)]
            if not weekend_indices:
                return PenaltyResult()

            weekend_offs = []
            for emp_idx in range(ctx.num_employees):
                count = sum(1 for d in weekend_indices if binary[emp_idx, d] == 1)
                weekend_offs.append(count)

            actual_diff = max(weekend_offs) - min(weekend_offs)
            if actual_diff > max_diff:
                penalty = (actual_diff - max_diff) * penalty_per
                return PenaltyResult(
                    penalty=penalty,
                    details=f"週末休日差: {actual_diff}日(許容{max_diff}日)",
                )

            return PenaltyResult()

        return penalty_fn


class EqualHolidayDistribution(ConstraintTemplate):
    """Penalize unequal distribution of holidays across weekdays."""

    @property
    def template_id(self) -> str:
        return "equal_holiday_distribution"

    @property
    def name_ja(self) -> str:
        return "休日の曜日偏り抑制"

    @property
    def category(self) -> str:
        return "fairness"

    @property
    def description(self) -> str:
        return "社員の休日が特定の曜日に偏る場合にペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="penalty_weight",
                display_name="ペナルティ重み",
                param_type=ParameterType.FLOAT,
                default=1.0,
                min_value=0.1,
                max_value=50.0,
                description="曜日分布の標準偏差 x この値",
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        weight = float(params["penalty_weight"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            weekdays = ctx.shift_input.weekdays
            total_penalty = 0.0

            if not weekdays or all(w == -1 for w in weekdays):
                return PenaltyResult()

            for emp_idx in range(ctx.num_employees):
                row = binary[emp_idx]
                # Count holidays per weekday (0-6)
                weekday_counts = np.zeros(7)
                for d, w in enumerate(weekdays):
                    if w >= 0 and row[d] == 1:
                        weekday_counts[w] += 1

                # Penalize high standard deviation
                if np.sum(weekday_counts) > 0:
                    std = float(np.std(weekday_counts))
                    total_penalty += std * weight

            return PenaltyResult(penalty=total_penalty)

        return penalty_fn
