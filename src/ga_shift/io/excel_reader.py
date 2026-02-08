"""Excel file reader for shift input data."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from ga_shift.models.employee import EmployeeInfo, EmployeeType, Section
from ga_shift.models.schedule import ShiftInput

# Mapping of Japanese weekday names to weekday index (0=Mon..6=Sun)
_WEEKDAY_MAP = {"月": 0, "火": 1, "水": 2, "木": 3, "金": 4, "土": 5, "日": 6}

# Section string to enum mapping
_SECTION_MAP = {
    "仕込み": Section.PREP,
    "ランチ": Section.LUNCH,
    "仕込み・ランチ": Section.PREP_LUNCH,
    "ホール": Section.HALL,
}

# Column layout constants (matching template_generator)
# A(0)=社員名, B(1)=雇用形態, C(2)=セクション, D(3)=有休残日数, E(4)onwards=日付
_DAY_COL_START = 4  # 0-indexed column where day data starts


def read_shift_input(
    filepath: str | Path,
    sheet_name: str = "シフト表",
) -> ShiftInput:
    """Read shift input data from Excel file.

    New Excel layout (kimachiya format):
        - Row 0: Title
        - Row 1: (empty)
        - Row 2: Headers - "社員名", "雇用形態", "セクション", "有休残日数", 1..N, "休日数"
        - Row 3: Weekday row
        - Row 4+: Employee data (dynamic count)
        - After employees: empty row, then required workers row
    """
    filepath = Path(filepath)
    pd.set_option("future.no_silent_downcasting", True)
    df = pd.read_excel(filepath, sheet_name=sheet_name, header=None)

    # --- Auto-detect number of days from header row ---
    header_row = df.iloc[2]
    num_days = 0
    for col_idx in range(_DAY_COL_START, len(header_row)):
        val = header_row.iloc[col_idx]
        if pd.notna(val):
            try:
                day_num = int(val)
                if 1 <= day_num <= 31:
                    num_days = day_num
                else:
                    break
            except (ValueError, TypeError):
                break  # Hit "休日数" or other non-day column
        else:
            break

    if num_days == 0:
        raise ValueError("Could not detect number of days from header row")

    # Holiday count column index (0-indexed)
    holiday_col_idx = _DAY_COL_START + num_days

    # --- Auto-detect number of employees ---
    emp_start_row = 4  # 0-indexed row where employee data starts
    num_employees = 0
    for row_idx in range(emp_start_row, len(df)):
        name_val = df.iloc[row_idx, 0]
        if pd.isna(name_val) or str(name_val).strip() == "":
            break
        # Check if this row is a "必要人数" row (not an employee)
        name_str = str(name_val).strip()
        if "必要人数" in name_str:
            break
        num_employees += 1

    if num_employees == 0:
        raise ValueError("No employee data found")

    # --- Read shift body ---
    body = df.iloc[
        emp_start_row : emp_start_row + num_employees,
        _DAY_COL_START : _DAY_COL_START + num_days,
    ].copy()
    body = body.fillna(0)
    body = body.replace("◎", 2)
    body = body.replace("×", 3)

    base_schedule = body.values.astype(int)

    # --- Read employee info columns ---
    employee_names = (
        df.iloc[emp_start_row : emp_start_row + num_employees, 0]
        .fillna("")
        .astype(str)
        .values.tolist()
    )

    emp_types_raw = (
        df.iloc[emp_start_row : emp_start_row + num_employees, 1]
        .fillna("正規")
        .astype(str)
        .values.tolist()
    )

    sections_raw = (
        df.iloc[emp_start_row : emp_start_row + num_employees, 2]
        .fillna("")
        .astype(str)
        .values.tolist()
    )

    vacation_days_raw = (
        df.iloc[emp_start_row : emp_start_row + num_employees, 3]
        .fillna(0)
        .values
    )

    # Holiday count per employee
    holiday_raw = df.iloc[
        emp_start_row : emp_start_row + num_employees, holiday_col_idx
    ].copy()
    holiday_counts = holiday_raw.to_numpy(dtype=float, na_value=0.0).astype(int)

    # --- Find required workers row ---
    # Search for a row containing "必要人数" after the employee rows
    required_workers = np.full(num_days, 3, dtype=int)  # Default: 3
    required_kitchen_workers = None

    for row_idx in range(emp_start_row + num_employees, min(len(df), emp_start_row + num_employees + 5)):
        label_val = df.iloc[row_idx, 0]
        if pd.notna(label_val) and "必要人数" in str(label_val):
            req_raw = df.iloc[row_idx, _DAY_COL_START : _DAY_COL_START + num_days].copy()
            req_vals = req_raw.to_numpy(dtype=float, na_value=3.0).astype(int)

            label_str = str(label_val).strip()
            if "キッチン" in label_str:
                required_kitchen_workers = req_vals
                required_workers = req_vals  # Use kitchen requirement as overall too
            else:
                required_workers = req_vals

    # --- Extract weekday info ---
    weekdays: list[int] = []
    day_labels: list[str] = []
    day_header_row = df.iloc[2, _DAY_COL_START : _DAY_COL_START + num_days]
    weekday_row = df.iloc[3, _DAY_COL_START : _DAY_COL_START + num_days]

    for i, val in enumerate(day_header_row):
        label = str(val) if pd.notna(val) else ""
        day_labels.append(label)

        weekday = _extract_weekday(label)
        if weekday == -1:
            wval = weekday_row.iloc[i] if i < len(weekday_row) else None
            if pd.notna(wval):
                weekday = _extract_weekday(str(wval))
        weekdays.append(weekday)

    # --- Build EmployeeInfo list ---
    employees: list[EmployeeInfo] = []
    for i in range(num_employees):
        preferred = [j + 1 for j in range(num_days) if base_schedule[i, j] == 2]
        unavailable = [j + 1 for j in range(num_days) if base_schedule[i, j] == 3]

        # Parse employee type
        emp_type_str = emp_types_raw[i].strip()
        if emp_type_str == "パート":
            emp_type = EmployeeType.PART_TIME
        else:
            emp_type = EmployeeType.FULL_TIME

        # Parse section
        section_str = sections_raw[i].strip()
        section = _SECTION_MAP.get(section_str)

        # Parse vacation days
        try:
            vac_days = int(float(vacation_days_raw[i]))
        except (ValueError, TypeError):
            vac_days = 0

        employees.append(
            EmployeeInfo(
                index=i,
                name=employee_names[i],
                required_holidays=int(holiday_counts[i]),
                preferred_days_off=preferred,
                employee_type=emp_type,
                section=section,
                available_vacation_days=vac_days,
                unavailable_days=unavailable,
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
        required_kitchen_workers=required_kitchen_workers,
    )


def _extract_weekday(label: str) -> int:
    """Extract weekday index from a label like '1(月)'. Returns -1 if not found."""
    for char, idx in _WEEKDAY_MAP.items():
        if char in label:
            return idx
    return -1
