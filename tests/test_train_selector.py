# Tests for selector training.

from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd
import pytest

from src.selection.train_selector import main, train_selector


def test_train_selector_saves_model_metrics_and_feature_importance(tmp_path: Path) -> None:

    # Training should save the selector artifacts and report validation metrics.
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

    # Training requires at least one non-missing best_solver label.
    dataset_csv = tmp_path / "selection_dataset.csv"

    pd.DataFrame(
        [
            {"instance_name": "inst_1", "num_teams": 4, "best_solver": None},
            {"instance_name": "inst_2", "num_teams": 6, "best_solver": None},
        ]
    ).to_csv(dataset_csv, index=False)

    with pytest.raises(ValueError, match="does not contain any labeled rows"):
        train_selector(dataset_csv=dataset_csv)


def test_train_selector_cli_supports_full_mixed_dataset_outputs(tmp_path: Path) -> None:

    # Full-dataset CLI mode should write artifacts to explicit mixed-output paths.
    dataset_csv = tmp_path / "selection_dataset_full.csv"
    model_path = tmp_path / "full_selection" / "selector.joblib"
    importance_path = tmp_path / "full_selection" / "feature_importance.csv"
    run_summary_path = tmp_path / "full_selection" / "training_summary.json"
    config_path = tmp_path / "selector_config.yaml"

    pd.DataFrame(
        [
            {
                "instance_name": f"inst_{index}",
                "dataset_type": "synthetic" if index < 6 else "real",
                "num_teams": 4 if index < 6 else 8,
                "num_slots": 6 if index < 6 else 14,
                "best_solver": "solver_a" if index % 2 == 0 else "solver_b",
                "objective_solver_a": 1.0 if index % 2 == 0 else 5.0,
                "objective_solver_b": 5.0 if index % 2 == 0 else 1.0,
            }
            for index in range(12)
        ]
    ).to_csv(dataset_csv, index=False)
    config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  full_selection_dataset_csv: {dataset_csv.as_posix()}",
                f"  full_model_output: {model_path.as_posix()}",
                f"  full_feature_importance_csv: {importance_path.as_posix()}",
                f"  full_training_run_summary: {run_summary_path.as_posix()}",
                "split:",
                "  strategy: repeated_holdout",
                "  test_size: 0.25",
                "  repeats: 2",
                "selector:",
                "  model_choice: random_forest",
                "run:",
                "  random_seed: 11",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config_path), "--full-dataset"])

    assert exit_code == 0
    assert model_path.exists()
    assert importance_path.exists()
    assert run_summary_path.exists()
    importance = pd.read_csv(importance_path)
    assert "dataset_type" not in set(importance["source_feature"])
