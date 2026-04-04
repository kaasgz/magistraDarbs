"""Tests for selector training."""

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
import pytest

from src.selection.train_selector import train_selector


def test_train_selector_saves_model_metrics_and_feature_importance(tmp_path: Path) -> None:
    """Training should save the selector artifacts and report validation metrics."""

    dataset_csv = tmp_path / "selection_dataset.csv"
    model_path = tmp_path / "selector.joblib"
    importance_path = tmp_path / "feature_importance.csv"

    pd.DataFrame(
        [
            {
                "instance_name": f"inst_{index}",
                "num_teams": 4 if index < 6 else 8,
                "num_slots": 3 if index < 6 else 7,
                "constraints_per_team": 0.5 if index < 6 else 1.5,
                "objective_name": "compact" if index % 2 == 0 else "balanced",
                "objective_present": bool(index % 2),
                "best_solver": "solver_a" if index < 6 else "solver_b",
                "objective_solver_a": 1.0 if index < 6 else 9.0,
                "objective_solver_b": 9.0 if index < 6 else 1.0,
            }
            for index in range(12)
        ]
    ).to_csv(dataset_csv, index=False)

    result = train_selector(
        dataset_csv=dataset_csv,
        model_path=model_path,
        feature_importance_csv=importance_path,
        random_seed=7,
        test_size=0.25,
        split_strategy="repeated_holdout",
        repeats=3,
    )

    assert model_path.exists()
    assert importance_path.exists()
    assert joblib.load(model_path) is not None
    assert 0.0 <= result.accuracy <= 1.0
    assert result.balanced_accuracy is not None
    assert 0.0 <= result.balanced_accuracy <= 1.0
    assert list(result.confusion_matrix.index) == ["solver_a", "solver_b"]
    assert list(result.confusion_matrix.columns) == ["solver_a", "solver_b"]
    assert result.num_labeled_rows == 12
    assert result.num_validation_splits == 3
    assert result.split_strategy == "repeated_holdout"

    importance = pd.read_csv(importance_path)
    assert not importance.empty
    assert {"feature", "source_feature", "feature_group", "importance"}.issubset(importance.columns)
    assert not importance["feature"].str.contains("objective_solver_", regex=False).any()
    assert not importance["source_feature"].str.contains("objective_solver_", regex=False).any()


def test_train_selector_raises_for_dataset_without_labeled_rows(tmp_path: Path) -> None:
    """Training requires at least one non-missing best_solver label."""

    dataset_csv = tmp_path / "selection_dataset.csv"

    pd.DataFrame(
        [
            {"instance_name": "inst_1", "num_teams": 4, "best_solver": None},
            {"instance_name": "inst_2", "num_teams": 6, "best_solver": None},
        ]
    ).to_csv(dataset_csv, index=False)

    with pytest.raises(ValueError, match="does not contain any labeled rows"):
        train_selector(dataset_csv=dataset_csv)
