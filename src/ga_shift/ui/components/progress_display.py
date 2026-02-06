"""Progress display component for GA execution."""

from __future__ import annotations

import streamlit as st


class ProgressDisplay:
    """Manages progress bar and status text during GA execution."""

    def __init__(self, total_generations: int) -> None:
        self.total = total_generations
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
        self.score_text = st.empty()

    def update(self, generation: int, current_score: float, top_score: float) -> None:
        progress = generation / self.total
        self.progress_bar.progress(progress)
        self.status_text.text(f"世代: {generation}/{self.total}")
        self.score_text.text(
            f"現世代最高: {current_score:.0f} | 全世代最高: {top_score:.0f}"
        )

    def complete(self, final_score: float) -> None:
        self.progress_bar.progress(1.0)
        self.status_text.text(f"完了! 最終スコア: {final_score:.0f}")
