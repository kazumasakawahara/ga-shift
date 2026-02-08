"""GA operators: crossover, mutation, holiday_fix."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from ga_shift.models.schedule import ShiftInput


def crossover_uniform(
    parent1: NDArray[np.int_],
    parent2: NDArray[np.int_],
    rate: float = 0.5,
) -> tuple[NDArray[np.int_], NDArray[np.int_]]:
    """Uniform crossover on flattened arrays.

    Migrated from ga_shift_v2.py:crossover().
    - Same genes → inherit directly
    - Different genes → swap with probability (1-rate)
    """
    p1 = parent1.flatten()
    p2 = parent2.flatten()

    # Vectorized: create mask for different genes
    diff_mask = p1 != p2
    swap_mask = diff_mask & (np.random.random(len(p1)) >= rate)

    ch1 = p1.copy()
    ch2 = p2.copy()
    ch1[swap_mask] = p2[swap_mask]
    ch2[swap_mask] = p1[swap_mask]

    shape = parent1.shape
    return ch1.reshape(shape), ch2.reshape(shape)


def mutation(
    child: NDArray[np.int_],
    mutation_rate: float = 0.05,
    gene_ratio: float = 0.1,
) -> NDArray[np.int_]:
    """Mutation operator.

    - mutation_rate chance of triggering mutation
    - When triggered, flip gene_ratio fraction of mutable genes (0↔1)
    - Codes 2 (preferred off) and 3 (unavailable) are never changed
    """
    if np.random.random() >= mutation_rate:
        return child

    result = child.copy()
    flat = result.flatten()

    # Only mutate genes that are 0 or 1 (mutable)
    mutable_indices = np.where((flat == 0) | (flat == 1))[0]
    if len(mutable_indices) == 0:
        return result

    mutation_count = max(1, int(len(mutable_indices) * gene_ratio))
    chosen = np.random.choice(mutable_indices, size=min(mutation_count, len(mutable_indices)), replace=False)

    for idx in chosen:
        if flat[idx] == 0:
            flat[idx] = 1
        elif flat[idx] == 1:
            flat[idx] = 0

    return flat.reshape(child.shape)


def holiday_fix(
    schedule: NDArray[np.int_],
    shift_input: ShiftInput,
) -> NDArray[np.int_]:
    """Adjust holiday counts to match contract requirements.

    Uses np.random.choice for efficiency.
    Codes 2 (preferred off) and 3 (unavailable) count as non-work days
    and are never modified. Only values 0 and 1 are adjusted.
    """
    result = schedule.copy()

    for emp in shift_input.employees:
        row = result[emp.index]
        target = emp.required_holidays

        # Count all non-work days: 1 (GA holiday), 2 (preferred off), 3 (unavailable)
        actual = int(np.count_nonzero(row))
        diff = actual - target

        if diff == 0:
            continue

        if diff > 0:
            # Too many holidays → convert some GA-assigned holidays (1) back to work (0)
            holiday_indices = np.where(row == 1)[0]
            if len(holiday_indices) >= diff:
                to_remove = np.random.choice(holiday_indices, size=diff, replace=False)
                row[to_remove] = 0
            else:
                row[holiday_indices] = 0
        else:
            # Too few holidays → convert some available work days (0) to holiday (1)
            work_indices = np.where(row == 0)[0]
            need = -diff
            if len(work_indices) >= need:
                to_add = np.random.choice(work_indices, size=need, replace=False)
                row[to_add] = 1
            else:
                row[work_indices] = 1

    return result
