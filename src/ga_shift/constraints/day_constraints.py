"""Day-level constraints (per-day worker counts and requirements)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ga_shift.constraints.base import ConstraintTemplate, PenaltyFunction, PenaltyResult
from ga_shift.models.constraint import ParameterDef, ParameterType
from ga_shift.models.schedule import ScheduleContext


class RequiredWorkersMatch(ConstraintTemplate):
    """Penalize deviation from required worker count per day.

    Migrated from ga_shift_v2.py evaluation_function: 縦方向評価.
    Original: diff * -4 per day.
    """

    @property
    def template_id(self) -> str:
        return "required_workers_match"

    @property
    def name_ja(self) -> str:
        return "必要出勤人数の充足"

    @property
    def category(self) -> str:
        return "day"

    @property
    def description(self) -> str:
        return "各日の出勤人数が必要人数と異なる場合にペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="penalty_per_diff",
                display_name="人数差1人あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=4.0,
                min_value=0.1,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        penalty_per_diff = float(params["penalty_per_diff"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            binary = ctx.binary_schedule
            required = ctx.shift_input.required_workers
            total_penalty = 0.0
            details_parts: list[str] = []

            for day_idx in range(ctx.num_days):
                col = binary[:, day_idx]
                holiday_count = int(np.sum(col))
                workers = ctx.num_employees - holiday_count
                diff = abs(workers - int(required[day_idx]))
                if diff > 0:
                    p = diff * penalty_per_diff
                    total_penalty += p
                    details_parts.append(
                        f"{day_idx+1}日: {workers}人(必要{required[day_idx]}人)"
                    )

            return PenaltyResult(penalty=total_penalty, details="; ".join(details_parts))

        return penalty_fn


class MinWorkersOnDate(ConstraintTemplate):
    """Ensure minimum workers on specific dates."""

    @property
    def template_id(self) -> str:
        return "min_workers_on_date"

    @property
    def name_ja(self) -> str:
        return "特定日の最低出勤人数"

    @property
    def category(self) -> str:
        return "day"

    @property
    def description(self) -> str:
        return "指定した日に最低限の出勤人数を確保"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="target_days",
                display_name="対象日（カンマ区切り）",
                param_type=ParameterType.SELECT,
                default="",
                description="1-indexed day numbers, comma-separated",
            ),
            ParameterDef(
                name="min_workers",
                display_name="最低出勤人数",
                param_type=ParameterType.INT,
                default=5,
                min_value=1,
                max_value=50,
            ),
            ParameterDef(
                name="penalty_per_missing",
                display_name="不足1人あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=10.0,
                min_value=0.1,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        target_str = str(params.get("target_days", ""))
        target_days = _parse_day_list(target_str)
        min_workers = int(params["min_workers"])
        penalty_per = float(params["penalty_per_missing"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            if not target_days:
                return PenaltyResult()
            binary = ctx.binary_schedule
            total_penalty = 0.0
            for day_1indexed in target_days:
                day_idx = day_1indexed - 1
                if 0 <= day_idx < ctx.num_days:
                    workers = ctx.num_employees - int(np.sum(binary[:, day_idx]))
                    if workers < min_workers:
                        total_penalty += (min_workers - workers) * penalty_per
            return PenaltyResult(penalty=total_penalty)

        return penalty_fn


class MaxWorkersOnDate(ConstraintTemplate):
    """Limit maximum workers on specific dates."""

    @property
    def template_id(self) -> str:
        return "max_workers_on_date"

    @property
    def name_ja(self) -> str:
        return "特定日の最大出勤人数"

    @property
    def category(self) -> str:
        return "day"

    @property
    def description(self) -> str:
        return "指定した日に出勤人数の上限を設定"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="target_days",
                display_name="対象日（カンマ区切り）",
                param_type=ParameterType.SELECT,
                default="",
                description="1-indexed day numbers, comma-separated",
            ),
            ParameterDef(
                name="max_workers",
                display_name="最大出勤人数",
                param_type=ParameterType.INT,
                default=8,
                min_value=1,
                max_value=50,
            ),
            ParameterDef(
                name="penalty_per_excess",
                display_name="超過1人あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=10.0,
                min_value=0.1,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        target_str = str(params.get("target_days", ""))
        target_days = _parse_day_list(target_str)
        max_workers = int(params["max_workers"])
        penalty_per = float(params["penalty_per_excess"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            if not target_days:
                return PenaltyResult()
            binary = ctx.binary_schedule
            total_penalty = 0.0
            for day_1indexed in target_days:
                day_idx = day_1indexed - 1
                if 0 <= day_idx < ctx.num_days:
                    workers = ctx.num_employees - int(np.sum(binary[:, day_idx]))
                    if workers > max_workers:
                        total_penalty += (workers - max_workers) * penalty_per
            return PenaltyResult(penalty=total_penalty)

        return penalty_fn


class MinSkilledWorkers(ConstraintTemplate):
    """Ensure minimum skilled workers per day (placeholder for attribute-based)."""

    @property
    def template_id(self) -> str:
        return "min_skilled_workers"

    @property
    def name_ja(self) -> str:
        return "スキル別最低出勤人数"

    @property
    def category(self) -> str:
        return "day"

    @property
    def description(self) -> str:
        return "特定スキルを持つ社員の最低出勤人数を確保"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="skill_name",
                display_name="スキル名",
                param_type=ParameterType.SELECT,
                default="",
            ),
            ParameterDef(
                name="min_count",
                display_name="最低人数",
                param_type=ParameterType.INT,
                default=1,
                min_value=1,
                max_value=20,
            ),
            ParameterDef(
                name="penalty_per_missing",
                display_name="不足1人あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=15.0,
                min_value=0.1,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        skill_name = str(params.get("skill_name", ""))
        min_count = int(params["min_count"])
        penalty_per = float(params["penalty_per_missing"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            if not skill_name:
                return PenaltyResult()

            # Find employees with the specified skill
            skilled_indices = []
            for emp in ctx.shift_input.employees:
                for attr in emp.attributes:
                    if attr.name == skill_name:
                        skilled_indices.append(emp.index)
                        break

            if not skilled_indices:
                return PenaltyResult()

            binary = ctx.binary_schedule
            total_penalty = 0.0
            for day_idx in range(ctx.num_days):
                working_skilled = sum(
                    1 for idx in skilled_indices if binary[idx, day_idx] == 0
                )
                if working_skilled < min_count:
                    total_penalty += (min_count - working_skilled) * penalty_per

            return PenaltyResult(penalty=total_penalty)

        return penalty_fn


def _parse_day_list(s: str) -> list[int]:
    """Parse comma-separated day numbers."""
    if not s or not s.strip():
        return []
    result = []
    for part in s.split(","):
        part = part.strip()
        if part.isdigit():
            result.append(int(part))
    return result
