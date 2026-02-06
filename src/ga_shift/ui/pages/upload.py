"""Upload page - Excel file upload and data preview."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from ga_shift.io.excel_reader import read_shift_input


def render_upload_page() -> None:
    """Render the upload page."""
    st.header("入力データ")

    uploaded_file = st.file_uploader(
        "シフト入力Excelファイルをアップロード",
        type=["xlsx", "xls"],
        key="shift_upload",
    )

    if uploaded_file is not None:
        try:
            shift_input = read_shift_input(uploaded_file)
            st.session_state["shift_input"] = shift_input
            st.success(
                f"読み込み完了: {shift_input.num_employees}名 x {shift_input.num_days}日"
            )
        except Exception as e:
            st.error(f"読み込みエラー: {e}")
            return

    if "shift_input" not in st.session_state:
        st.info("Excelファイルをアップロードしてください。")
        return

    si = st.session_state["shift_input"]

    # Employee info table
    st.subheader("社員情報")
    emp_data = []
    for emp in si.employees:
        emp_data.append({
            "社員名": emp.name,
            "契約休日数": emp.required_holidays,
            "希望休": ", ".join(str(d) for d in emp.preferred_days_off) or "なし",
        })
    st.dataframe(pd.DataFrame(emp_data), use_container_width=True, hide_index=True)

    # Base schedule preview
    st.subheader("入力シフト表（希望休マーク付き）")
    label_map = {0: "出", 2: "◎"}
    preview_data: list[dict[str, str]] = []
    for emp in si.employees:
        row: dict[str, str] = {"社員名": emp.name}
        for d in range(si.num_days):
            val = int(si.base_schedule[emp.index, d])
            row[str(d + 1)] = label_map.get(val, str(val))
        preview_data.append(row)

    preview_df = pd.DataFrame(preview_data).set_index("社員名")

    def style_preferred(val):
        if val == "◎":
            return "background-color: #FCE4EC; color: #FF0000; font-weight: bold"
        return ""

    styled = preview_df.style.map(style_preferred)
    st.dataframe(styled, use_container_width=True, height=400)

    # Required workers
    st.subheader("必要出勤人数")
    req_data = {"日": list(range(1, si.num_days + 1)), "必要人数": si.required_workers.tolist()}
    req_df = pd.DataFrame(req_data).set_index("日").T
    st.dataframe(req_df, use_container_width=True)
