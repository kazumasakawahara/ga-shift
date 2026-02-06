"""Tests for ConductorAgent (E2E pipeline)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ga_shift.agents.conductor import ConductorAgent
from ga_shift.models.ga_config import GAConfig
from ga_shift.models.schedule import ShiftInput


class TestConductorAgent:
    def test_full_pipeline(self, sample_shift_input):
        conductor = ConductorAgent()
        result = conductor.run_full_pipeline(
            shift_input=sample_shift_input,
            ga_config=GAConfig(generation_count=5, initial_population=20, elite_count=5),
        )

        assert "shift_result" in result
        assert "validation_report" in result
        sr = result["shift_result"]
        vr = result["validation_report"]

        assert sr.best_schedule.shape == (
            sample_shift_input.num_employees,
            sample_shift_input.num_days,
        )
        assert sr.best_score <= 0
        assert vr.total_penalty >= 0

    def test_pipeline_with_excel_output(self, sample_shift_input):
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as f:
            output_path = f.name

        conductor = ConductorAgent()
        result = conductor.run_full_pipeline(
            shift_input=sample_shift_input,
            ga_config=GAConfig(generation_count=3, initial_population=20, elite_count=5),
            output_path=output_path,
        )

        assert Path(result["output_path"]).exists()
        Path(output_path).unlink()

    def test_pipeline_with_progress(self, sample_shift_input):
        progress_calls = []

        def callback(gen, score, top):
            progress_calls.append(gen)

        conductor = ConductorAgent()
        conductor.run_full_pipeline(
            shift_input=sample_shift_input,
            ga_config=GAConfig(generation_count=3, initial_population=20, elite_count=5),
            progress_callback=callback,
        )

        assert len(progress_calls) == 3
