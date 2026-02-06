"""ValidatorAgent - validates schedules against constraints."""

from __future__ import annotations

from typing import Any

import numpy as np

from ga_shift.agents.base import BaseAgent
from ga_shift.constraints.base import CompiledConstraint
from ga_shift.ga.evaluation import evaluate_with_constraints
from ga_shift.models.schedule import ShiftInput, ShiftResult
from ga_shift.models.validation import (
    ConstraintScore,
    ValidationReport,
    Violation,
    ViolationSeverity,
)


class ValidatorAgent(BaseAgent):
    """Validates a schedule and produces a detailed report."""

    @property
    def name(self) -> str:
        return "validator"

    def validate(
        self,
        shift_result: ShiftResult,
        shift_input: ShiftInput,
        constraints: list[CompiledConstraint],
    ) -> ValidationReport:
        schedule = shift_result.best_schedule
        _, constraint_results = evaluate_with_constraints(schedule, shift_input, constraints)

        constraint_scores: list[ConstraintScore] = []
        all_violations: list[Violation] = []
        total_penalty = 0.0

        for cid, presult in constraint_results:
            penalty = presult.penalty
            total_penalty += penalty
            violations: list[Violation] = []

            if penalty > 0:
                severity = (
                    ViolationSeverity.ERROR if penalty >= 10.0 else ViolationSeverity.WARNING
                )
                violations.append(
                    Violation(
                        constraint_id=cid,
                        message=presult.details or f"Penalty: {penalty:.1f}",
                        severity=severity,
                        penalty=penalty,
                    )
                )
                all_violations.extend(violations)

            constraint_scores.append(
                ConstraintScore(
                    constraint_id=cid,
                    constraint_name=cid,
                    penalty=penalty,
                    violations=violations,
                )
            )

        # Additional structural checks
        structural_violations = self._check_structural(schedule, shift_input)
        all_violations.extend(structural_violations)

        return ValidationReport(
            total_penalty=total_penalty,
            constraint_scores=constraint_scores,
            violations=all_violations,
        )

    def _check_structural(
        self, schedule: np.ndarray, shift_input: ShiftInput
    ) -> list[Violation]:
        """Check structural validity (holiday counts, preferred off preservation)."""
        violations: list[Violation] = []

        for emp in shift_input.employees:
            row = schedule[emp.index]
            actual_holidays = int(np.count_nonzero(row))
            if actual_holidays != emp.required_holidays:
                violations.append(
                    Violation(
                        constraint_id="structural_holiday_count",
                        message=f"{emp.name}: 休日{actual_holidays}日(契約{emp.required_holidays}日)",
                        severity=ViolationSeverity.ERROR,
                        employee_index=emp.index,
                    )
                )

            # Check preferred off preserved
            for day in emp.preferred_days_off:
                if row[day - 1] != 2:
                    violations.append(
                        Violation(
                            constraint_id="structural_preferred_off",
                            message=f"{emp.name}: {day}日の希望休が保持されていない",
                            severity=ViolationSeverity.ERROR,
                            employee_index=emp.index,
                            day_index=day - 1,
                        )
                    )

        return violations

    def _handle_validate(self, payload: dict[str, Any]) -> dict[str, Any]:
        shift_result = payload["shift_result"]
        shift_input = payload["shift_input"]
        constraints = payload["compiled_constraints"]
        report = self.validate(shift_result, shift_input, constraints)
        return {"validation_report": report}
