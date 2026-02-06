"""GA engine - main optimization loop."""

from __future__ import annotations

import itertools
from typing import Callable

import numpy as np
from numpy.typing import NDArray

from ga_shift.constraints.base import CompiledConstraint
from ga_shift.ga.evaluation import evaluate_with_constraints
from ga_shift.ga.operators import crossover_uniform, holiday_fix, mutation
from ga_shift.ga.population import create_individual
from ga_shift.models.ga_config import GAConfig
from ga_shift.models.schedule import ShiftInput, ShiftResult

# Type for progress callback: (generation, best_score, top_score)
ProgressCallback = Callable[[int, float, float], None]


class GARunner:
    """Runs the Genetic Algorithm optimization.

    Migrated from ga_shift_v2.py:run_ga() with:
    - Constraint-based evaluation
    - Progress callback support
    - numpy array-based (no pandas DataFrames)
    """

    def __init__(
        self,
        shift_input: ShiftInput,
        constraints: list[CompiledConstraint],
        config: GAConfig | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> None:
        self.shift_input = shift_input
        self.constraints = constraints
        self.config = config or GAConfig()
        self.progress_callback = progress_callback

    def run(self) -> ShiftResult:
        cfg = self.config
        si = self.shift_input

        # 1. Generate initial population
        population: list[tuple[float, NDArray[np.int_]]] = []
        for _ in range(cfg.initial_population):
            ind = create_individual(si)
            ind = holiday_fix(ind, si)
            score, _ = evaluate_with_constraints(ind, si, self.constraints)
            population.append((score, ind))

        top: tuple[float, NDArray[np.int_]] | None = None
        history: list[float] = []

        # 2. Generation loop
        for gen in range(cfg.generation_count):
            # Sort by score descending (closer to 0 = better)
            population.sort(key=lambda x: -x[0])

            # Select elite
            population = population[: cfg.elite_count]

            # Track all-time best
            if top is None:
                top = population[0]
            elif population[0][0] > top[0]:
                top = population[0]
            else:
                population.append(top)

            history.append(top[0])

            # Progress callback
            if self.progress_callback:
                self.progress_callback(gen + 1, population[0][0], top[0])

            # Crossover: all combinations of elite pairs
            children: list[tuple[float, NDArray[np.int_]]] = []
            for k1, k2 in itertools.combinations(range(len(population)), 2):
                p1 = population[k1][1]
                p2 = population[k2][1]

                ch1, ch2 = crossover_uniform(p1, p2, cfg.crossover_rate)
                ch1 = mutation(ch1, cfg.mutation_rate, cfg.mutation_gene_ratio)
                ch2 = mutation(ch2, cfg.mutation_rate, cfg.mutation_gene_ratio)
                ch1 = holiday_fix(ch1, si)
                ch2 = holiday_fix(ch2, si)

                sc1, _ = evaluate_with_constraints(ch1, si, self.constraints)
                sc2, _ = evaluate_with_constraints(ch2, si, self.constraints)
                children.append((sc1, ch1))
                children.append((sc2, ch2))

            population = list(population) + children

        # Final: pick best
        population.sort(key=lambda x: -x[0])
        best_score = population[0][0]
        best_schedule = population[0][1]

        if top is not None and top[0] > best_score:
            best_score = top[0]
            best_schedule = top[1]

        return ShiftResult(
            best_schedule=best_schedule,
            best_score=best_score,
            score_history=history,
            generation_count=cfg.generation_count,
        )
