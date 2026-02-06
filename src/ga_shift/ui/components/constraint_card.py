"""Constraint configuration card component."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ga_shift.constraints.base import ConstraintTemplate
from ga_shift.models.constraint import ConstraintConfig, ParameterType


def render_constraint_card(
    template: ConstraintTemplate,
    existing_config: ConstraintConfig | None = None,
    key_prefix: str = "",
) -> ConstraintConfig | None:
    """Render a constraint card with toggle and parameter inputs.

    Returns a ConstraintConfig if enabled, None if disabled.
    """
    card_key = f"{key_prefix}_{template.template_id}"

    enabled = st.checkbox(
        f"**{template.name_ja}**",
        value=existing_config.enabled if existing_config else False,
        key=f"{card_key}_enabled",
        help=template.description,
    )

    if not enabled:
        return None

    params: dict[str, Any] = {}

    with st.container():
        cols = st.columns(min(len(template.parameters), 3)) if template.parameters else []

        for i, pdef in enumerate(template.parameters):
            col = cols[i % len(cols)] if cols else st
            default = (
                existing_config.parameters.get(pdef.name, pdef.default)
                if existing_config
                else pdef.default
            )

            with col:
                if pdef.param_type == ParameterType.INT:
                    params[pdef.name] = st.number_input(
                        pdef.display_name,
                        value=int(default),
                        min_value=int(pdef.min_value) if pdef.min_value is not None else None,
                        max_value=int(pdef.max_value) if pdef.max_value is not None else None,
                        step=1,
                        key=f"{card_key}_{pdef.name}",
                        help=pdef.description,
                    )
                elif pdef.param_type == ParameterType.FLOAT:
                    params[pdef.name] = st.number_input(
                        pdef.display_name,
                        value=float(default),
                        min_value=float(pdef.min_value) if pdef.min_value is not None else None,
                        max_value=float(pdef.max_value) if pdef.max_value is not None else None,
                        step=0.1,
                        format="%.1f",
                        key=f"{card_key}_{pdef.name}",
                        help=pdef.description,
                    )
                elif pdef.param_type == ParameterType.BOOL:
                    params[pdef.name] = st.checkbox(
                        pdef.display_name,
                        value=bool(default),
                        key=f"{card_key}_{pdef.name}",
                        help=pdef.description,
                    )
                elif pdef.param_type == ParameterType.SELECT:
                    params[pdef.name] = st.text_input(
                        pdef.display_name,
                        value=str(default),
                        key=f"{card_key}_{pdef.name}",
                        help=pdef.description,
                    )

    return ConstraintConfig(
        template_id=template.template_id,
        enabled=True,
        parameters=params,
    )
