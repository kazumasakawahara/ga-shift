"""Tests for GA operators."""

from __future__ import annotations

import numpy as np
import pytest

from ga_shift.ga.operators import crossover_uniform, holiday_fix, mutation


class TestCrossoverUniform:
    def test_same_parents_produce_same_children(self):
        p1 = np.array([[0, 1, 0, 1], [1, 0, 1, 0]])
        ch1, ch2 = crossover_uniform(p1, p1.copy())
        np.testing.assert_array_equal(ch1, p1)
        np.testing.assert_array_equal(ch2, p1)

    def test_children_have_same_shape(self):
        p1 = np.array([[0, 1, 0], [1, 0, 1]])
        p2 = np.array([[1, 0, 1], [0, 1, 0]])
        ch1, ch2 = crossover_uniform(p1, p2)
        assert ch1.shape == p1.shape
        assert ch2.shape == p2.shape

    def test_children_contain_parent_genes(self):
        np.random.seed(42)
        p1 = np.array([[0, 0, 0], [0, 0, 0]])
        p2 = np.array([[1, 1, 1], [1, 1, 1]])
        ch1, ch2 = crossover_uniform(p1, p2)
        # Each gene should come from one parent
        for i in range(ch1.size):
            assert ch1.flat[i] in (0, 1)
            assert ch2.flat[i] in (0, 1)


class TestMutation:
    def test_no_mutation_with_zero_rate(self):
        child = np.array([[0, 1, 0, 1, 2]])
        result = mutation(child, mutation_rate=0.0)
        np.testing.assert_array_equal(result, child)

    def test_preserves_preferred_off(self):
        np.random.seed(42)
        child = np.array([[2, 2, 2, 2, 2]])
        result = mutation(child, mutation_rate=1.0, gene_ratio=1.0)
        # All 2s should be preserved
        np.testing.assert_array_equal(result, child)

    def test_mutation_flips_genes(self):
        np.random.seed(42)
        child = np.array([[0, 0, 0, 0, 0, 1, 1, 1, 1, 1]])
        result = mutation(child, mutation_rate=1.0, gene_ratio=0.5)
        # Some genes should have flipped
        assert not np.array_equal(result, child)


class TestHolidayFix:
    def test_corrects_excess_holidays(self, small_shift_input):
        # Give everyone 5 holidays (need 2)
        schedule = np.ones((3, 7), dtype=int)
        schedule[:, :2] = 0
        # Preserve preferred off
        schedule[0, 2] = 2
        result = holiday_fix(schedule, small_shift_input)
        for emp in small_shift_input.employees:
            actual = int(np.count_nonzero(result[emp.index]))
            assert actual == emp.required_holidays

    def test_corrects_deficit_holidays(self, small_shift_input):
        # Give everyone 0 holidays (need 2)
        schedule = np.zeros((3, 7), dtype=int)
        schedule[0, 2] = 2  # Preserve preferred off
        result = holiday_fix(schedule, small_shift_input)
        for emp in small_shift_input.employees:
            actual = int(np.count_nonzero(result[emp.index]))
            assert actual == emp.required_holidays

    def test_preserves_preferred_off(self, small_shift_input):
        schedule = np.zeros((3, 7), dtype=int)
        schedule[0, 2] = 2
        result = holiday_fix(schedule, small_shift_input)
        assert result[0, 2] == 2
