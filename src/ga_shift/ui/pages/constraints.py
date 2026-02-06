"""Constraints page - constraint template configuration UI."""

from __future__ import annotations

import streamlit as st

from ga_shift.constraints.registry import get_registry
from ga_shift.models.constraint import ConstraintConfig, ConstraintSet
from ga_shift.ui.components.constraint_card import render_constraint_card

_CATEGORY_LABELS = {
    "employee": "社員制約",
    "day": "日別制約",
    "pattern": "パターン制約",
    "fairness": "公平性制約",
}

_CATEGORY_ORDER = ["pattern", "day", "employee", "fairness"]


def render_constraints_page() -> None:
    """Render the constraints configuration page."""
    st.header("制約設定")

    if "shift_input" not in st.session_state:
        st.warning("先に入力データをアップロードしてください。")
        return

    registry = get_registry()

    # Preset buttons
    st.subheader("プリセット")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("デフォルト（v2互換）", use_container_width=True):
            st.session_state["constraint_set"] = ConstraintSet.default_set()
            st.rerun()
    with col2:
        if st.button("全制約ON", use_container_width=True):
            all_configs = [
                ConstraintConfig(template_id=t.template_id, enabled=True)
                for t in registry.list_all()
            ]
            st.session_state["constraint_set"] = ConstraintSet(
                name="all", constraints=all_configs
            )
            st.rerun()
    with col3:
        if st.button("全制約OFF", use_container_width=True):
            st.session_state["constraint_set"] = ConstraintSet(name="none", constraints=[])
            st.rerun()

    # Initialize default if not present
    if "constraint_set" not in st.session_state:
        st.session_state["constraint_set"] = ConstraintSet.default_set()

    current_set: ConstraintSet = st.session_state["constraint_set"]
    existing_map = {c.template_id: c for c in current_set.constraints}

    st.divider()

    # Render by category
    new_configs: list[ConstraintConfig] = []

    for category in _CATEGORY_ORDER:
        templates = registry.list_by_category(category)
        if not templates:
            continue

        label = _CATEGORY_LABELS.get(category, category)
        st.subheader(f"{label}")

        for template in templates:
            existing = existing_map.get(template.template_id)
            with st.expander(
                f"{template.name_ja}",
                expanded=existing is not None and existing.enabled,
            ):
                st.caption(template.description)
                config = render_constraint_card(
                    template=template,
                    existing_config=existing,
                    key_prefix=category,
                )
                if config is not None:
                    new_configs.append(config)

    # Save back to session state
    st.session_state["constraint_set"] = ConstraintSet(
        name="custom", constraints=new_configs
    )

    # Summary
    st.divider()
    st.subheader("有効な制約")
    if new_configs:
        for c in new_configs:
            template = registry.get(c.template_id)
            st.write(f"- **{template.name_ja}** ({c.template_id})")
    else:
        st.info("制約が設定されていません。")
