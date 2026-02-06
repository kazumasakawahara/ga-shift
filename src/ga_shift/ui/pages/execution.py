"""Execution page - GA run with progress display."""

from __future__ import annotations

import streamlit as st

from ga_shift.agents.conductor import ConductorAgent
from ga_shift.models.constraint import ConstraintSet
from ga_shift.models.ga_config import GAConfig
from ga_shift.ui.components.progress_display import ProgressDisplay


def render_execution_page() -> None:
    """Render the GA execution page."""
    st.header("GA実行")

    if "shift_input" not in st.session_state:
        st.warning("先に入力データをアップロードしてください。")
        return

    si = st.session_state["shift_input"]
    constraint_set: ConstraintSet = st.session_state.get(
        "constraint_set", ConstraintSet.default_set()
    )

    # GA configuration
    st.subheader("GA設定")
    col1, col2, col3 = st.columns(3)
    with col1:
        generation_count = st.number_input(
            "世代数", value=50, min_value=1, max_value=500, step=10
        )
    with col2:
        elite_count = st.number_input(
            "エリート数", value=20, min_value=2, max_value=100, step=5
        )
    with col3:
        initial_pop = st.number_input(
            "初期個体数", value=100, min_value=10, max_value=1000, step=10
        )

    col4, col5, col6 = st.columns(3)
    with col4:
        crossover_rate = st.slider("交叉率", 0.0, 1.0, 0.5, 0.05)
    with col5:
        mutation_rate = st.slider("突然変異率", 0.0, 0.5, 0.05, 0.01)
    with col6:
        mutation_gene_ratio = st.slider("変異遺伝子割合", 0.0, 0.5, 0.1, 0.01)

    ga_config = GAConfig(
        generation_count=generation_count,
        elite_count=elite_count,
        initial_population=initial_pop,
        crossover_rate=crossover_rate,
        mutation_rate=mutation_rate,
        mutation_gene_ratio=mutation_gene_ratio,
    )

    # Active constraints summary
    enabled = [c for c in constraint_set.constraints if c.enabled]
    st.info(f"有効な制約: {len(enabled)}個")

    st.divider()

    # Run button
    if st.button("GA実行", type="primary", use_container_width=True):
        progress = ProgressDisplay(ga_config.generation_count)
        conductor = ConductorAgent()

        with st.spinner("GAを実行中..."):
            result = conductor.run_full_pipeline(
                shift_input=si,
                constraint_set=constraint_set,
                ga_config=ga_config,
                progress_callback=progress.update,
            )

        progress.complete(result["shift_result"].best_score)
        st.session_state["pipeline_result"] = result

        # Score history chart
        st.subheader("スコア推移")
        history = result["shift_result"].score_history
        st.line_chart({"スコア": history})

        st.success("GA実行が完了しました。「結果」タブで結果を確認してください。")
