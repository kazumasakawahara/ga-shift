"""ConstraintBuilderAgent - compiles constraint configurations."""

from __future__ import annotations

from typing import Any

from ga_shift.agents.base import BaseAgent
from ga_shift.constraints.base import CompiledConstraint
from ga_shift.constraints.registry import get_registry
from ga_shift.models.constraint import ConstraintSet


class ConstraintBuilderAgent(BaseAgent):
    """Compiles a ConstraintSet into executable CompiledConstraints."""

    @property
    def name(self) -> str:
        return "constraint_builder"

    def compile_constraints(
        self, constraint_set: ConstraintSet | None = None
    ) -> list[CompiledConstraint]:
        """Compile constraint set into penalty functions."""
        if constraint_set is None:
            constraint_set = ConstraintSet.default_set()
        registry = get_registry()
        return registry.compile_set(constraint_set)

    def _handle_compile_constraints(self, payload: dict[str, Any]) -> dict[str, Any]:
        cs_data = payload.get("constraint_set")
        cs = ConstraintSet.model_validate(cs_data) if cs_data else None
        compiled = self.compile_constraints(cs)
        return {"compiled_constraints": compiled}
