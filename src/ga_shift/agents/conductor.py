"""ConductorAgent - orchestrates the full pipeline."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ga_shift.agents.base import BaseAgent
from ga_shift.agents.constraint_builder import ConstraintBuilderAgent
from ga_shift.agents.ga_engine import GAEngineAgent
from ga_shift.agents.reporter import ReporterAgent
from ga_shift.agents.validator import ValidatorAgent
from ga_shift.ga.engine import ProgressCallback
from ga_shift.models.constraint import ConstraintSet
from ga_shift.models.ga_config import GAConfig
from ga_shift.models.schedule import ShiftInput, ShiftResult
from ga_shift.models.validation import ValidationReport


class ConductorAgent(BaseAgent):
    """Orchestrates the full shift scheduling pipeline."""

    def __init__(self) -> None:
        self._constraint_builder = ConstraintBuilderAgent()
        self._ga_engine = GAEngineAgent()
        self._validator = ValidatorAgent()
        self._reporter = ReporterAgent()

    @property
    def name(self) -> str:
        return "conductor"

    def run_full_pipeline(
        self,
        shift_input: ShiftInput,
        constraint_set: ConstraintSet | None = None,
        ga_config: GAConfig | None = None,
        output_path: str | Path | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> dict[str, Any]:
        """Run the complete pipeline: compile → GA → validate → report.

        Returns dict with shift_result, validation_report, and output_path.
        """
        # 1. Compile constraints
        compiled = self._constraint_builder.compile_constraints(constraint_set)

        # 2. Run GA
        shift_result = self._ga_engine.run_ga(
            shift_input=shift_input,
            constraints=compiled,
            ga_config=ga_config,
            progress_callback=progress_callback,
        )

        # 3. Validate
        validation_report = self._validator.validate(
            shift_result=shift_result,
            shift_input=shift_input,
            constraints=compiled,
        )

        # 4. Generate report
        result: dict[str, Any] = {
            "shift_result": shift_result,
            "validation_report": validation_report,
        }

        if output_path:
            filepath = self._reporter.generate_excel(
                filepath=output_path,
                shift_result=shift_result,
                shift_input=shift_input,
                validation_report=validation_report,
            )
            result["output_path"] = str(filepath)

        return result

    def _handle_run_full_pipeline(self, payload: dict[str, Any]) -> dict[str, Any]:
        shift_input = payload["shift_input"]
        constraint_set_data = payload.get("constraint_set")
        constraint_set = (
            ConstraintSet.model_validate(constraint_set_data) if constraint_set_data else None
        )
        ga_config_data = payload.get("ga_config")
        ga_config = GAConfig.model_validate(ga_config_data) if ga_config_data else None
        output_path = payload.get("output_path")
        progress_callback = payload.get("progress_callback")

        return self.run_full_pipeline(
            shift_input=shift_input,
            constraint_set=constraint_set,
            ga_config=ga_config,
            output_path=output_path,
            progress_callback=progress_callback,
        )
