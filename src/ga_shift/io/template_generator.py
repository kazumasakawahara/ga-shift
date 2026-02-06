"""Excel template generator for shift input data."""

from __future__ import annotations

import calendar
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

_WEEKDAY_JA = ["月", "火", "水", "木", "金", "土", "日"]


def generate_template(
    filepath: str | Path,
    year: int,
    month: int,
    num_employees: int = 10,
    default_holidays: int = 9,
    default_required: int = 7,
    employee_names: list[str] | None = None,
) -> Path:
    """Generate an Excel template for shift input.

    Args:
        filepath: Output file path.
        year: Target year (e.g. 2026).
        month: Target month (1-12).
        num_employees: Number of employees (default: 10).
        default_holidays: Default holiday count per employee.
        default_required: Default required workers per day.
        employee_names: Optional list of employee names.

    Returns:
        Path to the generated file.

    The generated layout matches the format expected by excel_reader.py:
        Row 0: Title
        Row 1: (empty)
        Row 2: Column headers - "社員名", 1..N, "休日数"
        Row 3: Weekday row  - "曜日", Mon/Tue/..., (empty)
        Row 4..(4+num_employees-1): Employee rows
        Row (4+num_employees): (empty)
        Row (4+num_employees+1): Required workers - "必要人数", N, N, ...
    """
    filepath = Path(filepath)
    num_days = calendar.monthrange(year, month)[1]

    wb = Workbook()
    ws = wb.active
    ws.title = "シフト表"

    # --- Styles ---
    title_font = Font(bold=True, size=14, name="Arial")
    header_font = Font(bold=True, size=11, name="Arial")
    center = Alignment(horizontal="center", vertical="center")
    wrap_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin"),
    )
    blue_fill = PatternFill("solid", fgColor="DAEEF3")
    green_fill = PatternFill("solid", fgColor="E2EFDA")
    yellow_fill = PatternFill("solid", fgColor="FFFFCC")
    orange_fill = PatternFill("solid", fgColor="FFC000")
    sat_fill = PatternFill("solid", fgColor="CCE5FF")
    sun_fill = PatternFill("solid", fgColor="FFCCCC")
    weekday_font = Font(size=10, name="Arial")
    sat_font = Font(size=10, name="Arial", color="0000FF")
    sun_font = Font(size=10, name="Arial", color="FF0000")

    # --- Row 0: Title ---
    ws.cell(row=1, column=1, value=f"シフト表（{year}年{month}月）")
    ws.cell(row=1, column=1).font = title_font

    # --- Row 2 (excel row 3): Column headers ---
    header_row = 3

    cell = ws.cell(row=header_row, column=1, value="社員名")
    cell.font = header_font
    cell.fill = blue_fill
    cell.alignment = center
    cell.border = thin_border

    for d in range(1, num_days + 1):
        col = d + 1
        cell = ws.cell(row=header_row, column=col, value=d)
        cell.font = header_font
        cell.fill = blue_fill
        cell.alignment = center
        cell.border = thin_border

        # Color Sat/Sun headers
        weekday_idx = calendar.weekday(year, month, d)
        if weekday_idx == 5:  # Saturday
            cell.fill = sat_fill
            cell.font = Font(bold=True, size=11, name="Arial", color="0000FF")
        elif weekday_idx == 6:  # Sunday
            cell.fill = sun_fill
            cell.font = Font(bold=True, size=11, name="Arial", color="FF0000")

    holiday_col = num_days + 2
    cell = ws.cell(row=header_row, column=holiday_col, value="休日数")
    cell.font = header_font
    cell.fill = yellow_fill
    cell.alignment = center
    cell.border = thin_border

    # --- Row 3 (excel row 4): Weekday names ---
    weekday_row = 4

    cell = ws.cell(row=weekday_row, column=1, value="曜日")
    cell.font = weekday_font
    cell.fill = blue_fill
    cell.alignment = center
    cell.border = thin_border

    for d in range(1, num_days + 1):
        col = d + 1
        weekday_idx = calendar.weekday(year, month, d)
        weekday_name = _WEEKDAY_JA[weekday_idx]

        cell = ws.cell(row=weekday_row, column=col, value=weekday_name)
        cell.alignment = center
        cell.border = thin_border

        if weekday_idx == 5:
            cell.font = sat_font
            cell.fill = sat_fill
        elif weekday_idx == 6:
            cell.font = sun_font
            cell.fill = sun_fill
        else:
            cell.font = weekday_font

    # --- Row 4..(4+N-1) (excel row 5..): Employee rows ---
    if employee_names is None:
        employee_names = [f"社員{chr(65 + i)}" for i in range(num_employees)]
    else:
        # Pad or truncate to num_employees
        while len(employee_names) < num_employees:
            employee_names.append(f"社員{len(employee_names) + 1}")
        employee_names = employee_names[:num_employees]

    for emp_idx in range(num_employees):
        row = 5 + emp_idx  # excel 1-indexed

        # Employee name
        cell = ws.cell(row=row, column=1, value=employee_names[emp_idx])
        cell.font = Font(name="Arial", size=11)
        cell.fill = green_fill
        cell.alignment = center
        cell.border = thin_border

        # Day cells (empty = available for GA scheduling)
        for d in range(1, num_days + 1):
            col = d + 1
            cell = ws.cell(row=row, column=col)
            cell.alignment = center
            cell.border = thin_border

            # Light background for Sat/Sun
            weekday_idx = calendar.weekday(year, month, d)
            if weekday_idx == 5:
                cell.fill = PatternFill("solid", fgColor="EBF5FF")
            elif weekday_idx == 6:
                cell.fill = PatternFill("solid", fgColor="FFF0F0")

        # Holiday count
        cell = ws.cell(row=row, column=holiday_col, value=default_holidays)
        cell.font = Font(name="Arial", size=11)
        cell.fill = yellow_fill
        cell.alignment = center
        cell.border = thin_border

    # --- Empty row ---
    # (excel_reader expects row 14 = empty, row 15 = required workers)
    # but that's 0-indexed. In our layout: row (5+N) is empty, row (5+N+1) is required.

    # --- Required workers row ---
    req_row = 5 + num_employees + 1  # Skip one empty row

    cell = ws.cell(row=req_row, column=1, value="必要人数")
    cell.font = header_font
    cell.fill = orange_fill
    cell.alignment = center
    cell.border = thin_border

    for d in range(1, num_days + 1):
        col = d + 1
        cell = ws.cell(row=req_row, column=col, value=default_required)
        cell.font = Font(name="Arial", size=11)
        cell.fill = orange_fill
        cell.alignment = center
        cell.border = thin_border

    # --- Instructions sheet ---
    ws_help = wb.create_sheet("入力ガイド")
    _write_instructions(ws_help, year, month, num_employees, num_days)

    # --- Column widths ---
    ws.column_dimensions["A"].width = 12
    for col_idx in range(2, holiday_col + 1):
        ws.column_dimensions[get_column_letter(col_idx)].width = 4.5
    ws.column_dimensions[get_column_letter(holiday_col)].width = 8

    # Freeze pane: fix employee name column and header rows
    ws.freeze_panes = "B5"

    wb.save(str(filepath))
    return filepath


def _write_instructions(ws, year: int, month: int, num_employees: int, num_days: int) -> None:
    """Write the instructions sheet."""
    title_font = Font(bold=True, size=14, name="Arial")
    header_font = Font(bold=True, size=12, name="Arial")
    body_font = Font(size=11, name="Arial")

    instructions = [
        (f"GA-Shift シフト表入力ガイド（{year}年{month}月）", title_font),
        ("", body_font),
        ("【シフト表シートの入力方法】", header_font),
        ("", body_font),
        ("1. 社員名", header_font),
        ("   A列に社員名が入っています。必要に応じて変更してください。", body_font),
        ("", body_font),
        ("2. 希望休の入力", header_font),
        ("   希望休のセルに「◎」を入力してください。", body_font),
        ("   ◎のセルはGAが変更しない固定休日として扱われます。", body_font),
        ("   空欄のセルはGAがスケジューリング対象とします。", body_font),
        ("", body_font),
        ("3. 休日数", header_font),
        (f"   AG列（{num_days + 1}列目）に各社員の契約休日数を入力してください。", body_font),
        ("   希望休（◎）の数もこの休日数に含まれます。", body_font),
        ("   例: 休日数=9、◎が2個 → GAが残り7日の休日を自動配置", body_font),
        ("", body_font),
        ("4. 必要人数", header_font),
        ("   最下行に各日の必要出勤人数を入力してください。", body_font),
        ("   日によって必要人数が異なる場合は個別に変更してください。", body_font),
        ("", body_font),
        ("【エンコーディング（内部処理用）】", header_font),
        ("   空欄(0) = 出勤可能（GAがスケジューリング）", body_font),
        ("   ◎(2) = 希望休（固定、GAは変更しない）", body_font),
        ("   ※ GAが休日を割り当てると 1 になります", body_font),
        ("", body_font),
        ("【注意事項】", header_font),
        ("   - シート名は「シフト表」のまま変更しないでください", body_font),
        ("   - 行・列の挿入・削除はしないでください", body_font),
        (f"   - 社員数は{num_employees}名固定です", body_font),
        (f"   - 日数は{num_days}日（{year}年{month}月）です", body_font),
        ("   - 休日数は希望休を含む合計数です", body_font),
    ]

    for row_idx, (text, font) in enumerate(instructions, 1):
        cell = ws.cell(row=row_idx, column=1, value=text)
        cell.font = font

    ws.column_dimensions["A"].width = 80


def main() -> None:
    """CLI entry point for template generation."""
    import argparse

    parser = argparse.ArgumentParser(description="GA-Shift テンプレート生成")
    parser.add_argument("--year", type=int, required=True, help="年（例: 2026）")
    parser.add_argument("--month", type=int, required=True, help="月（1-12）")
    parser.add_argument("--employees", type=int, default=10, help="社員数（デフォルト: 10）")
    parser.add_argument("--holidays", type=int, default=9, help="デフォルト休日数")
    parser.add_argument("--required", type=int, default=7, help="デフォルト必要出勤人数")
    parser.add_argument("-o", "--output", default=None, help="出力ファイルパス")
    args = parser.parse_args()

    if args.output is None:
        args.output = f"shift_input_{args.year}_{args.month:02d}.xlsx"

    filepath = generate_template(
        filepath=args.output,
        year=args.year,
        month=args.month,
        num_employees=args.employees,
        default_holidays=args.holidays,
        default_required=args.required,
    )
    print(f"テンプレート生成完了: {filepath}")


if __name__ == "__main__":
    main()
