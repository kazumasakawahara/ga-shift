"""Results page - display and download GA results."""

from __future__ import annotations

import io
import tempfile
from pathlib import Path

import streamlit as st

from ga_shift.io.excel_writer import write_result_excel
from ga_shift.models.validation import ValidationReport, ViolationSeverity
from ga_shift.ui.components.shift_table import render_shift_table


def render_results_page() -> None:
    """Render the results page."""
    st.header("結果")

    if "pipeline_result" not in st.session_state:
        st.info("GAを実行すると結果がここに表示されます。")
        return

    result = st.session_state["pipeline_result"]
    si = st.session_state["shift_input"]
    shift_result = result["shift_result"]
    validation_report: ValidationReport = result["validation_report"]

    # Score summary
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("最終スコア", f"{shift_result.best_score:.0f}")
    with col2:
        st.metric("合計ペナルティ", f"{validation_report.total_penalty:.1f}")
    with col3:
        status = "OK" if validation_report.is_compliant else "要確認"
        st.metric("ステータス", status)

    st.divider()

    # Shift table
    st.subheader("シフト表")
    render_shift_table(shift_result, si)

    # Validation details
    st.subheader("バリデーション結果")

    # Constraint scores
    if validation_report.constraint_scores:
        st.write("**制約別スコア**")
        for cs in validation_report.constraint_scores:
            icon = "🟢" if cs.penalty == 0 else ("🔴" if cs.penalty >= 10 else "🟡")
            st.write(f"{icon} {cs.constraint_name}: ペナルティ {cs.penalty:.1f}")

    # Violations
    if validation_report.violations:
        st.write("**違反一覧**")
        for v in validation_report.violations:
            icon = "❌" if v.severity == ViolationSeverity.ERROR else "⚠️"
            st.write(f"{icon} [{v.constraint_id}] {v.message}")
    else:
        st.success("制約違反はありません。")

    st.divider()

    # Download
    st.subheader("ダウンロード")
    buf = io.BytesIO()
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
        write_result_excel(tmp.name, shift_result, si, validation_report)
        tmp_path = Path(tmp.name)

    buf.write(tmp_path.read_bytes())
    tmp_path.unlink()
    buf.seek(0)

    st.download_button(
        label="結果Excelをダウンロード",
        data=buf,
        file_name="shift_result.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
