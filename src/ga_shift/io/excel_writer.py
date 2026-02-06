"""Excel writer for shift results."""

from __future__ import annotations

from pathlib import Path

import numpy as np
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from ga_shift.models.schedule import ShiftInput, ShiftResult
from ga_shift.models.validation import ValidationReport


def write_result_excel(
    filepath: str | Path,
    shift_result: ShiftResult,
    shift_input: ShiftInput,
    validation_report: ValidationReport | None = None,
) -> None:
    """Write GA result to Excel file.

    Migrated from ga_shift_v2.py:save_result_to_excel() with validation sheet.
    """
    filepath = Path(filepath)
    wb = Workbook()

    _write_schedule_sheet(wb.active, shift_result, shift_input)
    if validation_report:
        _write_validation_sheet(wb, validation_report)

    wb.save(str(filepath))


def _write_schedule_sheet(
    ws, shift_result: ShiftResult, shift_input: ShiftInput
) -> None:
    ws.title = "GA結果シフト表"

    header_font = Font(bold=True, size=11, name="Arial")
    center = Alignment(horizontal="center", vertical="center")
    border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    blue_fill = PatternFill("solid", fgColor="DAEEF3")
    green_fill = PatternFill("solid", fgColor="E2EFDA")
    yellow_fill = PatternFill("solid", fgColor="FFFF00")
    red_font = Font(color="FF0000", bold=True, name="Arial")
    work_fill = PatternFill("solid", fgColor="FFFFFF")
    holiday_fill = PatternFill("solid", fgColor="D9E2F3")
    preferred_fill = PatternFill("solid", fgColor="FCE4EC")

    schedule = shift_result.best_schedule
    num_employees = shift_input.num_employees
    num_days = shift_input.num_days

    # Title
    ws.cell(row=1, column=1, value="GA最適化シフト表")
    ws.cell(row=1, column=1).font = Font(bold=True, size=14, name="Arial")

    # Header row
    ws.cell(row=3, column=1, value="社員名")
    ws.cell(row=3, column=1).font = header_font
    ws.cell(row=3, column=1).fill = blue_fill
    ws.cell(row=3, column=1).alignment = center
    ws.cell(row=3, column=1).border = border

    for d in range(num_days):
        cell = ws.cell(row=3, column=d + 2, value=d + 1)
        cell.font = header_font
        cell.fill = blue_fill
        cell.alignment = center
        cell.border = border

    col_actual = num_days + 2
    col_contract = num_days + 3
    for col, label in [(col_actual, "実休日"), (col_contract, "契約")]:
        cell = ws.cell(row=3, column=col, value=label)
        cell.font = header_font
        cell.fill = yellow_fill
        cell.alignment = center
        cell.border = border

    # Data rows
    label_map = {0: "出", 1: "休", 2: "◎"}

    for emp in shift_input.employees:
        row_num = 4 + emp.index
        ws.cell(row=row_num, column=1, value=emp.name)
        ws.cell(row=row_num, column=1).font = Font(name="Arial", size=11)
        ws.cell(row=row_num, column=1).fill = green_fill
        ws.cell(row=row_num, column=1).alignment = center
        ws.cell(row=row_num, column=1).border = border

        actual_holidays = 0
        for d in range(num_days):
            val = int(schedule[emp.index, d])
            cell = ws.cell(row=row_num, column=d + 2)
            cell.value = label_map.get(val, str(val))
            cell.alignment = center
            cell.border = border

            if val == 0:
                cell.fill = work_fill
            elif val == 1:
                cell.fill = holiday_fill
                actual_holidays += 1
            elif val == 2:
                cell.fill = preferred_fill
                cell.font = red_font
                actual_holidays += 1

        ws.cell(row=row_num, column=col_actual, value=actual_holidays)
        ws.cell(row=row_num, column=col_actual).alignment = center
        ws.cell(row=row_num, column=col_actual).border = border

        cell = ws.cell(row=row_num, column=col_contract, value=emp.required_holidays)
        cell.alignment = center
        cell.border = border
        cell.fill = yellow_fill

    # Worker count summary
    summary_row = 4 + num_employees + 1
    ws.cell(row=summary_row, column=1, value="出勤人数")
    ws.cell(row=summary_row, column=1).font = header_font
    ws.cell(row=summary_row, column=1).fill = PatternFill("solid", fgColor="FFC000")
    ws.cell(row=summary_row, column=1).alignment = center
    ws.cell(row=summary_row, column=1).border = border

    binary = np.where(schedule == 2, 1, schedule)
    for d in range(num_days):
        holiday_count = int(np.sum(binary[:, d]))
        workers = num_employees - holiday_count
        cell = ws.cell(row=summary_row, column=d + 2, value=workers)
        cell.alignment = center
        cell.border = border
        target = int(shift_input.required_workers[d])
        if workers < target:
            cell.fill = PatternFill("solid", fgColor="FF9999")
        elif workers > target:
            cell.fill = PatternFill("solid", fgColor="FFFF99")
        else:
            cell.fill = PatternFill("solid", fgColor="99FF99")

    # Required workers row
    req_row = summary_row + 1
    ws.cell(row=req_row, column=1, value="必要人数")
    ws.cell(row=req_row, column=1).font = header_font
    ws.cell(row=req_row, column=1).fill = PatternFill("solid", fgColor="FFC000")
    ws.cell(row=req_row, column=1).alignment = center
    ws.cell(row=req_row, column=1).border = border
    for d in range(num_days):
        cell = ws.cell(row=req_row, column=d + 2, value=int(shift_input.required_workers[d]))
        cell.alignment = center
        cell.border = border
        cell.fill = PatternFill("solid", fgColor="FFC000")

    # Column widths
    ws.column_dimensions["A"].width = 12
    for col_idx in range(2, col_contract + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 5
    ws.column_dimensions[get_column_letter(col_actual)].width = 8
    ws.column_dimensions[get_column_letter(col_contract)].width = 6


def _write_validation_sheet(wb: Workbook, report: ValidationReport) -> None:
    ws = wb.create_sheet("バリデーション結果")

    header_font = Font(bold=True, size=11, name="Arial")
    center = Alignment(horizontal="center", vertical="center")

    ws.cell(row=1, column=1, value="バリデーション結果")
    ws.cell(row=1, column=1).font = Font(bold=True, size=14, name="Arial")

    ws.cell(row=3, column=1, value=f"合計ペナルティ: {report.total_penalty:.1f}")
    ws.cell(row=4, column=1, value=f"エラー数: {report.error_count}")
    ws.cell(row=5, column=1, value=f"警告数: {report.warning_count}")

    # Constraint scores table
    row = 7
    for col, header in enumerate(["制約ID", "ペナルティ", "違反数"], 1):
        ws.cell(row=row, column=col, value=header).font = header_font

    for cs in report.constraint_scores:
        row += 1
        ws.cell(row=row, column=1, value=cs.constraint_id)
        ws.cell(row=row, column=2, value=cs.penalty)
        ws.cell(row=row, column=3, value=len(cs.violations))

    # Violations detail
    row += 2
    ws.cell(row=row, column=1, value="違反詳細").font = header_font
    row += 1
    for col, header in enumerate(["制約ID", "重要度", "メッセージ"], 1):
        ws.cell(row=row, column=col, value=header).font = header_font

    for v in report.violations:
        row += 1
        ws.cell(row=row, column=1, value=v.constraint_id)
        ws.cell(row=row, column=2, value=v.severity.value)
        ws.cell(row=row, column=3, value=v.message)
