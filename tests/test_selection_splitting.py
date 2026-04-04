"""Tests for reproducible selector split planning."""

from __future__ import annotations

import pandas as pd

from src.selection.splitting import build_selector_split_plan
from src.utils import SplitSettings


def test_repeated_holdout_split_plan_is_reproducible() -> None:
    """Repeated holdout should produce stable train/test assignments for one seed."""

    target = pd.Series(
        [
            "solver_a",
            "solver_a",
            "solver_a",
            "solver_a",
            "solver_b",
            "solver_b",
            "solver_b",
            "solver_b",
        ],
        dtype="string",
    )
    settings = SplitSettings(
        strategy="repeated_holdout",
        test_size=0.25,
        cross_validation_folds=None,
        repeats=4,
    )

    first_plan = build_selector_split_plan(target, settings, random_seed=11)
    second_plan = build_selector_split_plan(target, settings, random_seed=11)

    assert first_plan.strategy == "repeated_holdout"
    assert first_plan.notes == second_plan.notes
    assert [split.train_indices for split in first_plan.splits] == [split.train_indices for split in second_plan.splits]
    assert [split.test_indices for split in first_plan.splits] == [split.test_indices for split in second_plan.splits]


def test_repeated_kfold_falls_back_when_stratification_is_not_feasible() -> None:
    """Cross-validation should stay reproducible even when classes are too small for stratification."""

    target = pd.Series(
        ["solver_a", "solver_a", "solver_a", "solver_b"],
        dtype="string",
    )
    settings = SplitSettings(
        strategy="repeated_stratified_kfold",
        test_size=0.25,
        cross_validation_folds=3,
        repeats=2,
    )

    plan = build_selector_split_plan(target, settings, random_seed=5)

    assert plan.strategy == "repeated_stratified_kfold"
    assert len(plan.splits) == 6
    assert any("fell back to non-stratified folds" in note for note in plan.notes)
    assert not any(split.stratified for split in plan.splits)
