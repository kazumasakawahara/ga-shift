"""Shift table display component."""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st

from ga_shift.models.schedule import ShiftInput, ShiftResult


def render_shift_table(shift_result: ShiftResult, shift_input: ShiftInput) -> None:
    """Render the shift table as a styled dataframe."""
    schedule = shift_result.best_schedule
    num_employees = shift_input.num_employees
    num_days = shift_input.num_days

    label_map = {0: "出", 1: "休", 2: "◎"}
    data: list[dict[str, str | int]] = []

    for emp in shift_input.employees:
        row_data: dict[str, str | int] = {"社員名": emp.name}
        actual_holidays = 0
        for d in range(num_days):
            val = int(schedule[emp.index, d])
            row_data[str(d + 1)] = label_map.get(val, str(val))
            if val in (1, 2):
                actual_holidays += 1
        row_data["実休日"] = actual_holidays
        row_data["契約"] = emp.required_holidays
        data.append(row_data)

    df = pd.DataFrame(data)
    df = df.set_index("社員名")

    def style_cell(val):
        if val == "休":
            return "background-color: #D9E2F3; color: #333"
        elif val == "◎":
            return "background-color: #FCE4EC; color: #FF0000; font-weight: bold"
        elif val == "出":
            return "background-color: #FFFFFF; color: #333"
        return ""

    day_cols = [str(d + 1) for d in range(num_days)]
    styled = df.style.map(style_cell, subset=day_cols)
    st.dataframe(styled, use_container_width=True, height=400)

    # Worker count summary
    st.subheader("出勤人数サマリー")
    binary = np.where(schedule == 2, 1, schedule)
    worker_data: dict[str, list] = {"日": [], "出勤人数": [], "必要人数": [], "差分": []}
    for d in range(num_days):
        holiday_count = int(np.sum(binary[:, d]))
        workers = num_employees - holiday_count
        required = int(shift_input.required_workers[d])
        worker_data["日"].append(d + 1)
        worker_data["出勤人数"].append(workers)
        worker_data["必要人数"].append(required)
        worker_data["差分"].append(workers - required)

    summary_df = pd.DataFrame(worker_data).set_index("日").T
    st.dataframe(summary_df, use_container_width=True)
