"""GA-Shift Streamlit application."""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="GA-Shift シフトスケジューラー",
    page_icon="📅",
    layout="wide",
)


def main() -> None:
    st.title("GA-Shift シフトスケジューラー")
    st.caption("遺伝的アルゴリズムによるシフト表自動作成")

    tab_upload, tab_constraints, tab_execution, tab_results = st.tabs(
        ["入力データ", "制約設定", "GA実行", "結果"]
    )

    with tab_upload:
        from ga_shift.ui.pages.upload import render_upload_page
        render_upload_page()

    with tab_constraints:
        from ga_shift.ui.pages.constraints import render_constraints_page
        render_constraints_page()

    with tab_execution:
        from ga_shift.ui.pages.execution import render_execution_page
        render_execution_page()

    with tab_results:
        from ga_shift.ui.pages.results import render_results_page
        render_results_page()


if __name__ == "__main__":
    main()
