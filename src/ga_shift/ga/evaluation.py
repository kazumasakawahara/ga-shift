"""Evaluation function using compiled constraints."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from ga_shift.constraints.base import CompiledConstraint, PenaltyResult
from ga_shift.models.schedule import ScheduleContext, ShiftInput


def evaluate_with_constraints(
    schedule: NDArray[np.int_],
    shift_input: ShiftInput,
    constraints: list[CompiledConstraint],
) -> tuple[float, list[tuple[str, PenaltyResult]]]:
    """Evaluate a schedule against compiled constraints.

    Returns:
        (total_score, list of (constraint_id, PenaltyResult))
        Score is negative (0 = perfect, lower = worse) for compatibility with ga_shift_v2.py.
    """
    ctx = ScheduleContext(schedule=schedule, shift_input=shift_input)

    total_penalty = 0.0
    results: list[tuple[str, PenaltyResult]] = []

    for constraint in constraints:
        result = constraint.penalty_fn(ctx)
        total_penalty += result.penalty
        results.append((constraint.template_id, result))

    # Score is negative penalty (0 = best, more negative = worse)
    score = -total_penalty
    return score, results
