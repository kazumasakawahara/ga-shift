"""ReporterAgent - generates Excel output."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ga_shift.agents.base import BaseAgent
from ga_shift.io.excel_writer import write_result_excel
from ga_shift.models.schedule import ShiftInput, ShiftResult
from ga_shift.models.validation import ValidationReport


class ReporterAgent(BaseAgent):
    """Generates Excel report from results."""

    @property
    def name(self) -> str:
        return "reporter"

    def generate_excel(
        self,
        filepath: str | Path,
        shift_result: ShiftResult,
        shift_input: ShiftInput,
        validation_report: ValidationReport | None = None,
    ) -> Path:
        filepath = Path(filepath)
        write_result_excel(filepath, shift_result, shift_input, validation_report)
        return filepath

    def _handle_generate_excel(self, payload: dict[str, Any]) -> dict[str, Any]:
        filepath = self.generate_excel(
            filepath=payload["filepath"],
            shift_result=payload["shift_result"],
            shift_input=payload["shift_input"],
            validation_report=payload.get("validation_report"),
        )
        return {"filepath": str(filepath)}
