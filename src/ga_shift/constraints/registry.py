"""Constraint registry - manages all available constraint templates."""

from __future__ import annotations

from typing import Any

from ga_shift.constraints.base import CompiledConstraint, ConstraintTemplate
from ga_shift.models.constraint import ConstraintConfig, ConstraintSet


class ConstraintRegistry:
    """Registry of all available constraint templates."""

    def __init__(self) -> None:
        self._templates: dict[str, ConstraintTemplate] = {}

    def register(self, template: ConstraintTemplate) -> None:
        self._templates[template.template_id] = template

    def get(self, template_id: str) -> ConstraintTemplate:
        if template_id not in self._templates:
            available = ", ".join(sorted(self._templates.keys()))
            raise KeyError(
                f"Unknown constraint template: {template_id}. Available: {available}"
            )
        return self._templates[template_id]

    def list_all(self) -> list[ConstraintTemplate]:
        return list(self._templates.values())

    def list_by_category(self, category: str) -> list[ConstraintTemplate]:
        return [t for t in self._templates.values() if t.category == category]

    def compile_config(self, config: ConstraintConfig) -> CompiledConstraint:
        """Compile a single constraint config into an executable constraint."""
        template = self.get(config.template_id)
        # Merge defaults with user-provided params
        merged = {}
        for pdef in template.parameters:
            merged[pdef.name] = config.parameters.get(pdef.name, pdef.default)
        penalty_fn = template.compile(merged)
        return CompiledConstraint(
            template_id=config.template_id,
            name_ja=template.name_ja,
            penalty_fn=penalty_fn,
            parameters=merged,
        )

    def compile_set(self, constraint_set: ConstraintSet) -> list[CompiledConstraint]:
        """Compile a full constraint set into executable constraints."""
        compiled = []
        for config in constraint_set.constraints:
            if config.enabled:
                compiled.append(self.compile_config(config))
        return compiled


# Global registry instance
_global_registry: ConstraintRegistry | None = None


def get_registry() -> ConstraintRegistry:
    """Get the global constraint registry, initializing if needed."""
    global _global_registry
    if _global_registry is None:
        _global_registry = _create_default_registry()
    return _global_registry


def _create_default_registry() -> ConstraintRegistry:
    """Create and populate the default registry with all built-in templates."""
    from ga_shift.constraints.day_constraints import (
        MaxWorkersOnDate,
        MinSkilledWorkers,
        MinWorkersOnDate,
        RequiredWorkersMatch,
    )
    from ga_shift.constraints.employee_constraints import (
        MaxConsecutiveWork,
        MinDaysOffPerWeek,
        RestAfterConsecutiveWork,
        WeekendRest,
    )
    from ga_shift.constraints.fairness_constraints import (
        EqualHolidayDistribution,
        EqualWeekendDistribution,
    )
    from ga_shift.constraints.kimachi_constraints import (
        ClosedDayConstraint,
        KitchenMinWorkers,
        SubstituteConstraint,
        UnavailableDayHard,
        VacationDaysLimit,
    )
    from ga_shift.constraints.pattern_constraints import (
        AvoidLongConsecutiveWork,
        ConsecutiveHolidayBonus,
        NoIsolatedHolidays,
        NoIsolatedWorkdays,
    )

    registry = ConstraintRegistry()
    for template_cls in [
        # Employee constraints
        MaxConsecutiveWork,
        WeekendRest,
        MinDaysOffPerWeek,
        RestAfterConsecutiveWork,
        # Day constraints
        MinWorkersOnDate,
        MaxWorkersOnDate,
        MinSkilledWorkers,
        RequiredWorkersMatch,
        # Pattern constraints
        AvoidLongConsecutiveWork,
        NoIsolatedHolidays,
        NoIsolatedWorkdays,
        ConsecutiveHolidayBonus,
        # Fairness constraints
        EqualWeekendDistribution,
        EqualHolidayDistribution,
        # Kimachiya constraints
        KitchenMinWorkers,
        SubstituteConstraint,
        VacationDaysLimit,
        UnavailableDayHard,
        ClosedDayConstraint,
    ]:
        registry.register(template_cls())
    return registry
