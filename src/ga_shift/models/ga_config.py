"""Genetic Algorithm configuration."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GAConfig(BaseModel):
    """Configuration for the Genetic Algorithm."""

    initial_population: int = Field(default=100, ge=10)
    elite_count: int = Field(default=20, ge=2)
    generation_count: int = Field(default=50, ge=1)
    crossover_rate: float = Field(default=0.5, ge=0.0, le=1.0)
    mutation_rate: float = Field(default=0.05, ge=0.0, le=1.0)
    mutation_gene_ratio: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Fraction of genes mutated when mutation occurs"
    )
