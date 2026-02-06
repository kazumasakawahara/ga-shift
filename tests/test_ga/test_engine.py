"""Tests for GA engine."""

from __future__ import annotations

import numpy as np
import pytest

from ga_shift.constraints.registry import get_registry
from ga_shift.ga.engine import GARunner
from ga_shift.models.constraint import ConstraintSet
from ga_shift.models.ga_config import GAConfig
from ga_shift.models.schedule import ShiftInput


class TestGARunner:
    def test_produces_valid_result(self, small_shift_input, fast_ga_config):
        registry = get_registry()
        compiled = registry.compile_set(ConstraintSet.default_set())
        runner = GARunner(small_shift_input, compiled, fast_ga_config)
        result = runner.run()

        assert result.best_schedule.shape == (
            small_shift_input.num_employees,
            small_shift_input.num_days,
        )
        assert result.best_score <= 0
        assert len(result.score_history) == fast_ga_config.generation_count

    def test_progress_callback_called(self, small_shift_input, fast_ga_config):
        registry = get_registry()
        compiled = registry.compile_set(ConstraintSet.default_set())
        calls = []

        def callback(gen, score, top):
            calls.append((gen, score, top))

        runner = GARunner(small_shift_input, compiled, fast_ga_config, callback)
        runner.run()
        assert len(calls) == fast_ga_config.generation_count

    def test_score_improves_or_stable(self, sample_shift_input):
        registry = get_registry()
        compiled = registry.compile_set(ConstraintSet.default_set())
        config = GAConfig(generation_count=10, initial_population=30, elite_count=5)
        runner = GARunner(sample_shift_input, compiled, config)
        result = runner.run()

        # Score history should be non-decreasing (improving)
        for i in range(1, len(result.score_history)):
            assert result.score_history[i] >= result.score_history[i - 1]
