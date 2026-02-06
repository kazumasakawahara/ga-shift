"""Pattern-based constraints (work/holiday pattern analysis)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ga_shift.constraints.base import ConstraintTemplate, PenaltyFunction, PenaltyResult
from ga_shift.models.constraint import ParameterDef, ParameterType
from ga_shift.models.schedule import ScheduleContext


class AvoidLongConsecutiveWork(ConstraintTemplate):
    """Penalize consecutive work days exceeding a threshold.

    Migrated from ga_shift_v2.py evaluation_function: 5連勤以上ペナルティ.
    Original: -(consecutive_work - 4)^2 per segment.
    """

    @property
    def template_id(self) -> str:
        return "avoid_long_consecutive_work"

    @property
    def name_ja(self) -> str:
        return "長期連続勤務抑制"

    @property
    def category(self) -> str:
        return "pattern"

    @property
    def description(self) -> str:
        return "指定日数以上の連続勤務にペナルティを付与"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="threshold",
                display_name="連勤上限日数",
                param_type=ParameterType.INT,
                default=5,
                min_value=3,
                max_value=10,
                description="この日数以上の連勤にペナルティ",
            ),
            ParameterDef(
                name="penalty_weight",
                display_name="ペナルティ重み",
                param_type=ParameterType.FLOAT,
                default=1.0,
                min_value=0.1,
                max_value=100.0,
                description="ペナルティの重み係数",
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        threshold = int(params["threshold"])
        weight = float(params["penalty_weight"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule  # 1=holiday, 0=work
            total_penalty = 0.0
            details_parts: list[str] = []

            for emp_idx in range(ctx.num_employees):
                row = binary[emp_idx]
                consecutive = 0
                for day_idx in range(ctx.num_days):
                    if row[day_idx] == 0:  # work
                        consecutive += 1
                    else:
                        if consecutive >= threshold:
                            p = ((consecutive - (threshold - 1)) ** 2) * weight
                            total_penalty += p
                            details_parts.append(
                                f"社員{emp_idx}: {consecutive}連勤 (penalty={p:.1f})"
                            )
                        consecutive = 0
                # Check tail
                if consecutive >= threshold:
                    p = ((consecutive - (threshold - 1)) ** 2) * weight
                    total_penalty += p
                    details_parts.append(
                        f"社員{emp_idx}: {consecutive}連勤 (penalty={p:.1f})"
                    )

            return PenaltyResult(penalty=total_penalty, details="; ".join(details_parts))

        return penalty_fn


class NoIsolatedHolidays(ConstraintTemplate):
    """Penalize isolated holidays (tobishi pattern: holiday-work-holiday).

    Migrated from ga_shift_v2.py: '1 0 1' split pattern.
    Original: (count) * -10 per employee.
    """

    @property
    def template_id(self) -> str:
        return "no_isolated_holidays"

    @property
    def name_ja(self) -> str:
        return "飛び石連休抑制"

    @property
    def category(self) -> str:
        return "pattern"

    @property
    def description(self) -> str:
        return "休日-出勤-休日パターン（飛び石連休）にペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="penalty_weight",
                display_name="ペナルティ重み",
                param_type=ParameterType.FLOAT,
                default=10.0,
                min_value=0.1,
                max_value=100.0,
                description="1パターンあたりのペナルティ",
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        weight = float(params["penalty_weight"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            total_penalty = 0.0
            details_parts: list[str] = []

            for emp_idx in range(ctx.num_employees):
                row = binary[emp_idx]
                count = 0
                for d in range(1, ctx.num_days - 1):
                    if row[d - 1] == 1 and row[d] == 0 and row[d + 1] == 1:
                        count += 1
                if count > 0:
                    p = count * weight
                    total_penalty += p
                    details_parts.append(f"社員{emp_idx}: 飛び石{count}回 (penalty={p:.1f})")

            return PenaltyResult(penalty=total_penalty, details="; ".join(details_parts))

        return penalty_fn


class NoIsolatedWorkdays(ConstraintTemplate):
    """Penalize isolated work days (work surrounded by holidays)."""

    @property
    def template_id(self) -> str:
        return "no_isolated_workdays"

    @property
    def name_ja(self) -> str:
        return "孤立出勤日抑制"

    @property
    def category(self) -> str:
        return "pattern"

    @property
    def description(self) -> str:
        return "休日-出勤-休日パターン（孤立出勤日）にペナルティ。飛び石連休と同一パターン。"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="penalty_weight",
                display_name="ペナルティ重み",
                param_type=ParameterType.FLOAT,
                default=5.0,
                min_value=0.1,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        weight = float(params["penalty_weight"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            total_penalty = 0.0
            details_parts: list[str] = []

            for emp_idx in range(ctx.num_employees):
                row = binary[emp_idx]
                count = 0
                for d in range(1, ctx.num_days - 1):
                    if row[d - 1] == 1 and row[d] == 0 and row[d + 1] == 1:
                        count += 1
                if count > 0:
                    p = count * weight
                    total_penalty += p
                    details_parts.append(f"社員{emp_idx}: 孤立出勤{count}回 (penalty={p:.1f})")

            return PenaltyResult(penalty=total_penalty, details="; ".join(details_parts))

        return penalty_fn


class ConsecutiveHolidayBonus(ConstraintTemplate):
    """Give bonus (negative penalty) for consecutive holidays >= threshold."""

    @property
    def template_id(self) -> str:
        return "consecutive_holiday_bonus"

    @property
    def name_ja(self) -> str:
        return "連続休日ボーナス"

    @property
    def category(self) -> str:
        return "pattern"

    @property
    def description(self) -> str:
        return "連続休日が指定日数以上の場合にボーナス（負のペナルティ）を付与"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="threshold",
                display_name="連休最小日数",
                param_type=ParameterType.INT,
                default=2,
                min_value=2,
                max_value=7,
                description="この日数以上の連休にボーナス",
            ),
            ParameterDef(
                name="bonus_per_day",
                display_name="1日あたりボーナス",
                param_type=ParameterType.FLOAT,
                default=2.0,
                min_value=0.1,
                max_value=50.0,
                description="連休の日数 x この値を減点（負のペナルティ）",
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        threshold = int(params["threshold"])
        bonus = float(params["bonus_per_day"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            total_bonus = 0.0

            for emp_idx in range(ctx.num_employees):
                row = binary[emp_idx]
                consecutive = 0
                for day_idx in range(ctx.num_days):
                    if row[day_idx] == 1:
                        consecutive += 1
                    else:
                        if consecutive >= threshold:
                            total_bonus += consecutive * bonus
                        consecutive = 0
                if consecutive >= threshold:
                    total_bonus += consecutive * bonus

            # Bonus is negative penalty (reward)
            return PenaltyResult(penalty=-total_bonus)

        return penalty_fn
