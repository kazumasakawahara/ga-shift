"""Excel file reader for shift input data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ga_shift.models.employee import EmployeeInfo
from ga_shift.models.schedule import ShiftInput

# Mapping of Japanese weekday names to weekday index (0=Mon..6=Sun)
_WEEKDAY_MAP = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}


def read_shift_input(
    filepath: str | Path,
    sheet_name: str = "シフト表",
) -> ShiftInput:
    """Read shift input data from Excel file.

    Migrated from ga_shift_v2.py:read_xl() with Pydantic model output.
    Excel layout:
        - Row 4-13 (0-indexed), Col 1-31: Shift body (10 employees x 31 days)
        - Col 0: Employee names
        - Col 32: Holiday count per employee
        - Row 15, Col 1-31: Required workers per day
        - Row 2 or 3: Day headers with weekday info (e.g. "1(月)")
    """
    filepath = Path(filepath)
    pd.set_option("future.no_silent_downcasting", True)
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

    # Shift body: employees x days (iloc row 4..13, col 1..31)
    body = df.iloc[4:14, 1:32].copy()
    body = body.fillna(0)
    body = body.replace("◎", 2)

    num_employees = len(body)
    num_days = len(body.columns)

    # Convert to numpy int array
    base_schedule = body.values.astype(int)

    # Holiday count per employee
    holiday_col = df.iloc[4:14, 32].copy()
    holiday_col = holiday_col.to_numpy(dtype=float, na_value=0.0).astype(int)

    # Employee names
    employee_names = df.iloc[4:14, 0].fillna("").astype(str).values.tolist()

    # Required workers per day (row 15)
    required_raw = df.iloc[15, 1:32].copy()
    required_workers = required_raw.to_numpy(dtype=float, na_value=7.0).astype(int)

    # Extract day labels from row 2 and weekday info from row 2 or 3
    weekdays: list[int] = []
    day_labels: list[str] = []
    day_header_row = df.iloc[2, 1:32]
    weekday_row = df.iloc[3, 1:32]

    for i, val in enumerate(day_header_row):
        label = str(val) if pd.notna(val) else ""
        day_labels.append(label)

        # Try to extract weekday from day header first (e.g. "1(月)")
        weekday = _extract_weekday(label)
        if weekday == -1:
            # Fall back to dedicated weekday row (e.g. "月", "火")
            wval = weekday_row.iloc[i] if i < len(weekday_row) else None
            if pd.notna(wval):
                weekday = _extract_weekday(str(wval))
        weekdays.append(weekday)

    # Build EmployeeInfo list
    employees: list[EmployeeInfo] = []
    for i in range(num_employees):
        preferred = [
            j + 1 for j in range(num_days) if base_schedule[i, j] == 2
        ]
        employees.append(
            EmployeeInfo(
                index=i,
                name=employee_names[i],
                required_holidays=int(holiday_col[i]),
                preferred_days_off=preferred,
            )
        )

    return ShiftInput(
        num_employees=num_employees,
        num_days=num_days,
        employee_names=employee_names,
        employees=employees,
        required_workers=required_workers,
        base_schedule=base_schedule,
        day_labels=day_labels,
        weekdays=weekdays,
    )


def _extract_weekday(label: str) -> int:
    """Extract weekday index from a label like '1(月)'. Returns -1 if not found."""
    for char, idx in _WEEKDAY_MAP.items():
        if char in label:
            return idx
    return -1
