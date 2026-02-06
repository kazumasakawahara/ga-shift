"""GAEngineAgent - runs the GA optimization."""

from __future__ import annotations

from typing import Any, Callable

from ga_shift.agents.base import BaseAgent
from ga_shift.constraints.base import CompiledConstraint
from ga_shift.ga.engine import GARunner, ProgressCallback
from ga_shift.models.ga_config import GAConfig
from ga_shift.models.schedule import ShiftInput, ShiftResult


class GAEngineAgent(BaseAgent):
    """Runs the Genetic Algorithm optimization."""

    @property
    def name(self) -> str:
        return "ga_engine"

    def run_ga(
        self,
        shift_input: ShiftInput,
        constraints: list[CompiledConstraint],
        ga_config: GAConfig | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> ShiftResult:
        runner = GARunner(
            shift_input=shift_input,
            constraints=constraints,
            config=ga_config,
            progress_callback=progress_callback,
        )
        return runner.run()

    def _handle_run_ga(self, payload: dict[str, Any]) -> dict[str, Any]:
        shift_input = payload["shift_input"]
        constraints = payload["compiled_constraints"]
        ga_config_data = payload.get("ga_config")
        ga_config = GAConfig.model_validate(ga_config_data) if ga_config_data else None
        progress_callback = payload.get("progress_callback")

        result = self.run_ga(shift_input, constraints, ga_config, progress_callback)
        return {"shift_result": result}
