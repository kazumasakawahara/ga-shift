"""Employee-centric constraints."""

from __future__ import annotations

from typing import Any

import numpy as np

from ga_shift.constraints.base import ConstraintTemplate, PenaltyFunction, PenaltyResult
from ga_shift.models.constraint import ParameterDef, ParameterType
from ga_shift.models.schedule import ScheduleContext


class MaxConsecutiveWork(ConstraintTemplate):
    """Hard limit on consecutive work days."""

    @property
    def template_id(self) -> str:
        return "max_consecutive_work"

    @property
    def name_ja(self) -> str:
        return "連続勤務上限"

    @property
    def category(self) -> str:
        return "employee"

    @property
    def description(self) -> str:
        return "連続勤務日数の上限を設定。超過分にペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="max_days",
                display_name="連勤上限日数",
                param_type=ParameterType.INT,
                default=6,
                min_value=1,
                max_value=14,
            ),
            ParameterDef(
                name="penalty_per_day",
                display_name="超過1日あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=10.0,
                min_value=0.1,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        max_days = int(params["max_days"])
        penalty_per_day = float(params["penalty_per_day"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            total_penalty = 0.0
            details_parts: list[str] = []

            for emp_idx in range(ctx.num_employees):
                row = binary[emp_idx]
                consecutive = 0
                for day_idx in range(ctx.num_days):
                    if row[day_idx] == 0:  # work
                        consecutive += 1
                    else:
                        if consecutive > max_days:
                            over = consecutive - max_days
                            p = over * penalty_per_day
                            total_penalty += p
                            details_parts.append(
                                f"社員{emp_idx}: {consecutive}連勤(上限{max_days})"
                            )
                        consecutive = 0
                if consecutive > max_days:
                    over = consecutive - max_days
                    total_penalty += over * penalty_per_day

            return PenaltyResult(penalty=total_penalty, details="; ".join(details_parts))

        return penalty_fn


class WeekendRest(ConstraintTemplate):
    """Ensure employees get some weekends off."""

    @property
    def template_id(self) -> str:
        return "weekend_rest"

    @property
    def name_ja(self) -> str:
        return "週末休日確保"

    @property
    def category(self) -> str:
        return "employee"

    @property
    def description(self) -> str:
        return "月内で最低限の週末（土日）休日を確保"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="min_weekend_offs",
                display_name="最低週末休日数",
                param_type=ParameterType.INT,
                default=2,
                min_value=0,
                max_value=10,
                description="月内で最低限確保する土日休日の数",
            ),
            ParameterDef(
                name="penalty_per_missing",
                display_name="不足1日あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=5.0,
                min_value=0.1,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        min_offs = int(params["min_weekend_offs"])
        penalty_per = float(params["penalty_per_missing"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            weekdays = ctx.shift_input.weekdays
            total_penalty = 0.0

            # Find weekend day indices (Sat=5, Sun=6)
            weekend_indices = [d for d, w in enumerate(weekdays) if w in (5, 6)]
            if not weekend_indices:
                return PenaltyResult()

            for emp_idx in range(ctx.num_employees):
                row = binary[emp_idx]
                weekend_offs = sum(1 for d in weekend_indices if row[d] == 1)
                if weekend_offs < min_offs:
                    shortfall = min_offs - weekend_offs
                    total_penalty += shortfall * penalty_per

            return PenaltyResult(penalty=total_penalty)

        return penalty_fn


class MinDaysOffPerWeek(ConstraintTemplate):
    """Ensure minimum days off per 7-day window."""

    @property
    def template_id(self) -> str:
        return "min_days_off_per_week"

    @property
    def name_ja(self) -> str:
        return "週当たり最低休日"

    @property
    def category(self) -> str:
        return "employee"

    @property
    def description(self) -> str:
        return "7日間スライディングウィンドウで最低休日数を確保"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="min_off",
                display_name="週最低休日数",
                param_type=ParameterType.INT,
                default=1,
                min_value=1,
                max_value=4,
            ),
            ParameterDef(
                name="penalty_per_missing",
                display_name="不足1日あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=8.0,
                min_value=0.1,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        min_off = int(params["min_off"])
        penalty_per = float(params["penalty_per_missing"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            total_penalty = 0.0

            for emp_idx in range(ctx.num_employees):
                row = binary[emp_idx]
                for start in range(0, ctx.num_days - 6):
                    window = row[start : start + 7]
                    offs = int(np.sum(window))
                    if offs < min_off:
                        total_penalty += (min_off - offs) * penalty_per

            return PenaltyResult(penalty=total_penalty)

        return penalty_fn


class RestAfterConsecutiveWork(ConstraintTemplate):
    """Ensure a rest day after N consecutive work days."""

    @property
    def template_id(self) -> str:
        return "rest_after_consecutive_work"

    @property
    def name_ja(self) -> str:
        return "連勤後の休日確保"

    @property
    def category(self) -> str:
        return "employee"

    @property
    def description(self) -> str:
        return "指定日数の連続勤務後に休日がない場合にペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="consecutive_threshold",
                display_name="連勤日数閾値",
                param_type=ParameterType.INT,
                default=5,
                min_value=2,
                max_value=10,
            ),
            ParameterDef(
                name="penalty_weight",
                display_name="ペナルティ重み",
                param_type=ParameterType.FLOAT,
                default=8.0,
                min_value=0.1,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        threshold = int(params["consecutive_threshold"])
        weight = float(params["penalty_weight"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            total_penalty = 0.0

            for emp_idx in range(ctx.num_employees):
                row = binary[emp_idx]
                consecutive = 0
                for day_idx in range(ctx.num_days):
                    if row[day_idx] == 0:  # work
                        consecutive += 1
                    else:
                        consecutive = 0

                    if consecutive == threshold:
                        # Check if next day is a rest
                        if day_idx + 1 < ctx.num_days and row[day_idx + 1] == 0:
                            total_penalty += weight

            return PenaltyResult(penalty=total_penalty)

        return penalty_fn
