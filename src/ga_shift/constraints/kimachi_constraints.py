"""Kimachiya-specific constraint templates.

Constraints for the Kimachiya cafe restaurant kitchen shift scheduling:
1. KitchenMinWorkers - Minimum 3 kitchen workers per day
2. SubstituteConstraint - Saito must cover Shimamura's absences (esp. Wednesday)
3. VacationDaysLimit - Don't exceed available paid leave
4. UnavailableDayHard - Code-3 cells must never be changed to work
"""

from __future__ import annotations

from typing import Any

import numpy as np

from ga_shift.constraints.base import ConstraintTemplate, PenaltyFunction, PenaltyResult
from ga_shift.models.constraint import ParameterDef, ParameterType
from ga_shift.models.employee import Section
from ga_shift.models.schedule import ScheduleContext


class KitchenMinWorkers(ConstraintTemplate):
    """Ensure minimum kitchen workers per day.

    Kitchen workers = employees in PREP, LUNCH, or PREP_LUNCH sections who are working.
    This is the most critical constraint for kimachiya.
    """

    @property
    def template_id(self) -> str:
        return "kitchen_min_workers"

    @property
    def name_ja(self) -> str:
        return "キッチン最低出勤人数"

    @property
    def category(self) -> str:
        return "day"

    @property
    def description(self) -> str:
        return "キッチン（仕込み＋ランチ）の出勤者合計が最低人数を下回った場合にペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="min_workers",
                display_name="キッチン最低人数",
                param_type=ParameterType.INT,
                default=3,
                min_value=1,
                max_value=10,
            ),
            ParameterDef(
                name="penalty_per_missing",
                display_name="不足1人あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=50.0,
                min_value=1.0,
                max_value=500.0,
                description="高ペナルティ推奨（最重要制約）",
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        min_workers = int(params["min_workers"])
        penalty_per = float(params["penalty_per_missing"])
        kitchen_sections = {Section.PREP, Section.LUNCH, Section.PREP_LUNCH}

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            # Find kitchen employee indices
            kitchen_indices = [
                emp.index
                for emp in ctx.shift_input.employees
                if emp.section in kitchen_sections
            ]
            if not kitchen_indices:
                return PenaltyResult()

            binary = ctx.binary_schedule
            total_penalty = 0.0
            details_parts: list[str] = []

            for day_idx in range(ctx.num_days):
                working = sum(
                    1 for idx in kitchen_indices if binary[idx, day_idx] == 0
                )
                if working < min_workers:
                    diff = min_workers - working
                    total_penalty += diff * penalty_per
                    details_parts.append(
                        f"{day_idx+1}日: キッチン{working}人(必要{min_workers}人)"
                    )

            return PenaltyResult(
                penalty=total_penalty, details="; ".join(details_parts)
            )

        return penalty_fn


class SubstituteConstraint(ConstraintTemplate):
    """Ensure substitute covers when primary worker is absent.

    Specifically for kimachiya: when Shimamura (chef) is absent (including
    every Wednesday), Saito must be working in the lunch section.
    """

    @property
    def template_id(self) -> str:
        return "substitute_constraint"

    @property
    def name_ja(self) -> str:
        return "代役制約（斎藤↔島村）"

    @property
    def category(self) -> str:
        return "employee"

    @property
    def description(self) -> str:
        return "島村不在日（水曜含む）に斎藤が出勤していない場合にペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="primary_name",
                display_name="主担当者名",
                param_type=ParameterType.SELECT,
                default="島村誠",
                description="不在時に代役が必要な社員名",
            ),
            ParameterDef(
                name="substitute_name",
                display_name="代役者名",
                param_type=ParameterType.SELECT,
                default="斎藤駿児",
                description="代役を務める社員名",
            ),
            ParameterDef(
                name="penalty_weight",
                display_name="ペナルティ重み",
                param_type=ParameterType.FLOAT,
                default=40.0,
                min_value=1.0,
                max_value=200.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        primary_name = str(params["primary_name"])
        substitute_name = str(params["substitute_name"])
        penalty_weight = float(params["penalty_weight"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            # Find primary and substitute employee indices
            primary_idx = None
            sub_idx = None
            for emp in ctx.shift_input.employees:
                if emp.name == primary_name:
                    primary_idx = emp.index
                if emp.name == substitute_name:
                    sub_idx = emp.index

            if primary_idx is None or sub_idx is None:
                return PenaltyResult()

            binary = ctx.binary_schedule
            total_penalty = 0.0
            details_parts: list[str] = []

            for day_idx in range(ctx.num_days):
                # Primary is absent (holiday/preferred off/unavailable)
                primary_absent = binary[primary_idx, day_idx] != 0
                # Substitute is also absent
                sub_absent = binary[sub_idx, day_idx] != 0

                if primary_absent and sub_absent:
                    total_penalty += penalty_weight
                    details_parts.append(
                        f"{day_idx+1}日: {primary_name}不在で{substitute_name}も休み"
                    )

            return PenaltyResult(
                penalty=total_penalty, details="; ".join(details_parts)
            )

        return penalty_fn


class VacationDaysLimit(ConstraintTemplate):
    """Penalize when preferred days off exceed available vacation days.

    This ensures employees don't request more paid leave than they have available.
    """

    @property
    def template_id(self) -> str:
        return "vacation_days_limit"

    @property
    def name_ja(self) -> str:
        return "有給日数上限"

    @property
    def category(self) -> str:
        return "employee"

    @property
    def description(self) -> str:
        return "希望休の合計が有給休暇取得可能日数を超えた場合に警告ペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="penalty_per_excess",
                display_name="超過1日あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=20.0,
                min_value=1.0,
                max_value=100.0,
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        penalty_per = float(params["penalty_per_excess"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            total_penalty = 0.0
            details_parts: list[str] = []

            for emp in ctx.shift_input.employees:
                if emp.available_vacation_days <= 0:
                    continue

                # Count preferred days off (code 2 = ◎)
                preferred_count = len(emp.preferred_days_off)

                if preferred_count > emp.available_vacation_days:
                    excess = preferred_count - emp.available_vacation_days
                    total_penalty += excess * penalty_per
                    details_parts.append(
                        f"{emp.name}: 希望休{preferred_count}日(有給残{emp.available_vacation_days}日)"
                    )

            return PenaltyResult(
                penalty=total_penalty, details="; ".join(details_parts)
            )

        return penalty_fn


class UnavailableDayHard(ConstraintTemplate):
    """Hard constraint: code-3 cells must remain as non-working.

    If GA accidentally assigns work on an unavailable day, apply extreme penalty.
    This should never happen if GA operators respect code 3, but serves as a safety net.
    """

    @property
    def template_id(self) -> str:
        return "unavailable_day_hard"

    @property
    def name_ja(self) -> str:
        return "出勤不可日保護"

    @property
    def category(self) -> str:
        return "employee"

    @property
    def description(self) -> str:
        return "出勤不可（×）のセルが出勤に変更された場合に極めて高いペナルティ"

    @property
    def parameters(self) -> list[ParameterDef]:
        return [
            ParameterDef(
                name="penalty_per_violation",
                display_name="違反1件あたりペナルティ",
                param_type=ParameterType.FLOAT,
                default=1000.0,
                min_value=100.0,
                max_value=10000.0,
                description="極高ペナルティ（ハード制約）",
            ),
        ]

    def compile(self, params: dict[str, Any]) -> PenaltyFunction:
        penalty_per = float(params["penalty_per_violation"])

        def penalty_fn(ctx: ScheduleContext) -> PenaltyResult:
            total_penalty = 0.0
            details_parts: list[str] = []

            base = ctx.shift_input.base_schedule
            schedule = ctx.schedule

            for emp in ctx.shift_input.employees:
                for day_idx in emp.unavailable_days:
                    d = day_idx - 1  # Convert 1-indexed to 0-indexed
                    if 0 <= d < ctx.num_days:
                        # Check if originally unavailable (3) but now set to work (0)
                        if base[emp.index, d] == 3 and schedule[emp.index, d] == 0:
                            total_penalty += penalty_per
                            details_parts.append(
                                f"{emp.name}: {day_idx}日が出勤不可なのに出勤"
                            )

            return PenaltyResult(
                penalty=total_penalty, details="; ".join(details_parts)
            )

        return penalty_fn
