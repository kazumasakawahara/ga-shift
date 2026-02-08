"""Template page - generate shift input Excel template for any facility."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import streamlit as st

from ga_shift.io.template_generator import EmployeePreset, generate_template

_WEEKDAY_LABELS = ["月曜", "火曜", "水曜", "木曜", "金曜", "土曜", "日曜"]
_SECTION_OPTIONS = ["", "仕込み", "ランチ", "仕込み・ランチ", "ホール"]
_TYPE_OPTIONS = ["正規", "パート"]


def render_template_page() -> None:
    """Render the template generation page."""
    st.header("テンプレート生成")
    st.caption("事業所の情報を入力して、シフト表テンプレートExcelを作成します。")

    # --- Year / Month ---
    col_y, col_m = st.columns(2)
    with col_y:
        year = st.number_input("年", value=2026, min_value=2020, max_value=2030, step=1)
    with col_m:
        month = st.number_input("月", value=3, min_value=1, max_value=12, step=1)

    st.divider()

    # --- Facility settings ---
    st.subheader("事業所設定")
    col_req, col_closed = st.columns(2)

    with col_req:
        default_required = st.number_input(
            "1日あたりの必要出勤人数",
            value=3,
            min_value=1,
            max_value=50,
            step=1,
            help="定休日以外の日の必要出勤人数（デフォルト値）",
        )
        use_kitchen = st.checkbox(
            "キッチン人数として設定",
            value=False,
            help="チェックすると「必要人数（キッチン）」としてExcelに出力します",
        )

    with col_closed:
        closed_days = st.multiselect(
            "定休日（曜日）",
            options=list(range(7)),
            default=[5, 6],
            format_func=lambda x: _WEEKDAY_LABELS[x],
            help="定休日の曜日を選択（必要出勤人数が0になります）",
        )

    st.divider()

    # --- Employee list ---
    st.subheader("社員情報")
    num_employees = st.number_input(
        "社員数", value=5, min_value=1, max_value=30, step=1
    )

    # Initialize employee data in session state
    if "template_employees" not in st.session_state:
        st.session_state["template_employees"] = _default_employees(5)

    # Adjust list size
    current = st.session_state["template_employees"]
    if len(current) < num_employees:
        for i in range(len(current), num_employees):
            current.append({
                "name": f"社員{i + 1}",
                "type": "正規",
                "section": "",
                "vacation": 0,
                "holidays": 9,
                "unavailable": [],
            })
    elif len(current) > num_employees:
        st.session_state["template_employees"] = current[:num_employees]
        current = st.session_state["template_employees"]

    # Employee input form
    for i in range(num_employees):
        emp = current[i]
        with st.expander(f"社員{i + 1}: {emp['name']}", expanded=(i < 3)):
            c1, c2, c3, c4 = st.columns([3, 2, 3, 2])
            with c1:
                emp["name"] = st.text_input(
                    "名前", value=emp["name"], key=f"emp_name_{i}"
                )
            with c2:
                type_idx = _TYPE_OPTIONS.index(emp["type"]) if emp["type"] in _TYPE_OPTIONS else 0
                emp["type"] = st.selectbox(
                    "雇用形態",
                    options=_TYPE_OPTIONS,
                    index=type_idx,
                    key=f"emp_type_{i}",
                )
            with c3:
                sec_idx = _SECTION_OPTIONS.index(emp["section"]) if emp["section"] in _SECTION_OPTIONS else 0
                emp["section"] = st.selectbox(
                    "セクション",
                    options=_SECTION_OPTIONS,
                    index=sec_idx,
                    key=f"emp_section_{i}",
                )
            with c4:
                emp["holidays"] = st.number_input(
                    "休日数",
                    value=emp["holidays"],
                    min_value=1,
                    max_value=25,
                    step=1,
                    key=f"emp_holidays_{i}",
                )

            c5, c6 = st.columns(2)
            with c5:
                emp["vacation"] = st.number_input(
                    "有休残日数",
                    value=emp["vacation"],
                    min_value=0,
                    max_value=40,
                    step=1,
                    key=f"emp_vacation_{i}",
                )
            with c6:
                emp["unavailable"] = st.multiselect(
                    "出勤不可曜日",
                    options=list(range(7)),
                    default=emp["unavailable"],
                    format_func=lambda x: _WEEKDAY_LABELS[x],
                    key=f"emp_unavail_{i}",
                )

    st.divider()

    # --- Generate button ---
    if st.button("テンプレートExcelを生成", type="primary", use_container_width=True):
        presets = []
        for emp in current:
            presets.append(
                EmployeePreset(
                    name=emp["name"],
                    employee_type=emp["type"],
                    section=emp["section"],
                    vacation_days=emp["vacation"],
                    holidays=emp["holidays"],
                    unavailable_weekdays=emp["unavailable"],
                )
            )

        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        generate_template(
            filepath=tmp_path,
            year=int(year),
            month=int(month),
            employee_presets=presets,
            default_required=int(default_required),
            kitchen_required=int(default_required) if use_kitchen else None,
            closed_weekdays=closed_days if closed_days else None,
        )

        buf = io.BytesIO()
        buf.write(Path(tmp_path).read_bytes())
        Path(tmp_path).unlink(missing_ok=True)
        buf.seek(0)

        filename = f"shift_template_{int(year)}_{int(month):02d}.xlsx"

        st.success(f"テンプレート生成完了: {filename}")
        st.download_button(
            label="テンプレートExcelをダウンロード",
            data=buf,
            file_name=filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )


def _default_employees(count: int) -> list[dict]:
    """Create default employee data list."""
    return [
        {
            "name": f"社員{i + 1}",
            "type": "正規",
            "section": "",
            "vacation": 0,
            "holidays": 9,
            "unavailable": [],
        }
        for i in range(count)
    ]
