"""Population initialization for GA."""

from __future__ import annotations

import numpy as np
from numpy.typing import NDArray

from ga_shift.models.schedule import ShiftInput


def create_individual(shift_input: ShiftInput) -> NDArray[np.int_]:
    """Create a single individual (schedule) as numpy array.

    - Copies the base schedule
    - For each employee, randomly assigns holidays to reach target count
    - Preferred off (2) and unavailable (3) cells are preserved
    - Only cells with value 0 (available) are candidates for holiday placement

    Returns:
        numpy array of shape (num_employees, num_days)
    """
    schedule = shift_input.base_schedule.copy()

    for emp in shift_input.employees:
        row = schedule[emp.index]
        target = emp.required_holidays

        # Count existing non-work days (1=holiday, 2=preferred off, 3=unavailable)
        existing = int(np.count_nonzero(row))

        # Need to place (target - existing) additional holidays on available work days (0)
        work_indices = np.where(row == 0)[0]
        needed = target - existing
        if needed > 0 and len(work_indices) >= needed:
            chosen = np.random.choice(work_indices, size=needed, replace=False)
            row[chosen] = 1

    return schedule
