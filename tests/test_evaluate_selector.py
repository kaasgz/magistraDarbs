"""Tests for selector evaluation in algorithm-selection terms."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.selection.evaluate_selector import evaluate_selector
from src.selection.train_selector import train_selector


def test_evaluate_selector_creates_detailed_report_and_summaries(tmp_path: Path) -> None:
    """Selector evaluation should compare against single-best and virtual-best baselines."""

    dataset_csv = tmp_path / "selection_dataset.csv"
    benchmark_csv = tmp_path / "benchmark_results.csv"
    model_path = tmp_path / "selector.joblib"
    importance_path = tmp_path / "feature_importance.csv"
    report_path = tmp_path / "selector_evaluation.csv"
    summary_csv_path = tmp_path / "selector_evaluation_summary.csv"
    summary_markdown_path = tmp_path / "selector_evaluation_summary.md"

    dataset = pd.DataFrame(
        [
            {
                "instance_name": f"inst_{index}",
                "num_teams": 4 if index < 6 else 8,
                "num_slots": 3 if index < 6 else 7,
                "constraints_per_team": 0.5 if index < 6 else 1.5,
                "objective_name": "compact" if index % 2 == 0 else "balanced",
                "objective_present": bool(index % 2),
                "best_solver": "solver_a" if index < 6 else "solver_b",
            }
            for index in range(12)
        ]
    )
    dataset.to_csv(dataset_csv, index=False)

    benchmark_rows: list[dict[str, object]] = []
    for index in range(12):
        instance_name = f"inst_{index}"
        is_a_best = index < 6
        benchmark_rows.extend(
            [
                {
                    "instance_name": instance_name,
                    "solver_name": "solver_a",
                    "objective_value": 1.0 if is_a_best else 9.0,
                    "runtime_seconds": 1.0 + 0.01 * index,
                    "feasible": True,
                    "status": "OPTIMAL",
                },
                {
                    "instance_name": instance_name,
                    "solver_name": "solver_b",
                    "objective_value": 9.0 if is_a_best else 1.0,
                    "runtime_seconds": 1.2 + 0.01 * index,
                    "feasible": True,
                    "status": "OPTIMAL",
                },
            ]
        )
    pd.DataFrame(benchmark_rows).to_csv(benchmark_csv, index=False)

    train_selector(
        dataset_csv=dataset_csv,
        model_path=model_path,
        feature_importance_csv=importance_path,
        random_seed=7,
        split_strategy="repeated_stratified_kfold",
        cross_validation_folds=3,
        repeats=2,
    )

    result = evaluate_selector(
        dataset_csv=dataset_csv,
        benchmark_csv=benchmark_csv,
        model_path=model_path,
        report_csv=report_path,
        summary_csv=summary_csv_path,
        summary_markdown=summary_markdown_path,
        random_seed=7,
        split_strategy="repeated_stratified_kfold",
        cross_validation_folds=3,
        repeats=2,
    )

    report = pd.read_csv(report_path)
    summary = pd.read_csv(summary_csv_path)
    summary_markdown = summary_markdown_path.read_text(encoding="utf-8")

    assert report_path.exists()
    assert summary_csv_path.exists()
    assert summary_markdown_path.exists()
    assert list(report.columns) == [
        "split_id",
        "split_strategy",
        "repeat_index",
        "fold_index",
        "stratified_split",
        "instance_name",
        "selected_solver",
        "true_best_solver",
        "prediction_correct",
        "selected_solver_objective",
        "best_possible_objective",
        "single_best_solver",
        "single_best_solver_objective",
        "selected_objective_for_scoring",
        "single_best_objective_for_scoring",
        "regret_vs_virtual_best",
        "delta_vs_single_best",
        "improvement_vs_single_best",
    ]
    assert result.num_test_instances == len(report.index)
    assert result.num_validation_splits == 6
    assert 0.0 <= result.classification_accuracy <= 1.0
    assert result.balanced_accuracy is not None
    assert 0.0 <= result.balanced_accuracy <= 1.0
    assert result.average_selected_objective == pytest.approx(1.0)
    assert result.average_virtual_best_objective == pytest.approx(1.0)
    assert result.regret_vs_virtual_best == pytest.approx(0.0)
    assert result.improvement_vs_single_best >= 0.0
    assert "aggregate_mean" in set(summary["summary_row_type"])
    assert "aggregate_std" in set(summary["summary_row_type"])
    assert "Leakage control" in summary_markdown


def test_evaluate_selector_uses_fallback_scoring_for_missing_selected_objective(tmp_path: Path) -> None:
    """Missing selected objectives should still yield a deterministic score."""

    dataset_csv = tmp_path / "selection_dataset.csv"
    benchmark_csv = tmp_path / "benchmark_results.csv"
    model_path = tmp_path / "selector.joblib"
    importance_path = tmp_path / "feature_importance.csv"
    report_path = tmp_path / "selector_evaluation.csv"
    summary_csv_path = tmp_path / "selector_evaluation_summary.csv"
    summary_markdown_path = tmp_path / "selector_evaluation_summary.md"

    dataset = pd.DataFrame(
        [
            {
                "instance_name": f"inst_{index}",
                "num_teams": 4 if index < 4 else 8,
                "best_solver": "solver_a" if index < 4 else "solver_b",
            }
            for index in range(8)
        ]
    )
    dataset.to_csv(dataset_csv, index=False)

    benchmark_rows: list[dict[str, object]] = []
    for index in range(8):
        instance_name = f"inst_{index}"
        benchmark_rows.extend(
            [
                {
                    "instance_name": instance_name,
                    "solver_name": "solver_a",
                    "objective_value": 1.0 if index < 4 else None,
                    "runtime_seconds": 1.0,
                    "feasible": index < 4,
                    "status": "OPTIMAL" if index < 4 else "FAILED:RuntimeError",
                },
                {
                    "instance_name": instance_name,
                    "solver_name": "solver_b",
                    "objective_value": 5.0,
                    "runtime_seconds": 1.1,
                    "feasible": True,
                    "status": "OPTIMAL",
                },
            ]
        )
    pd.DataFrame(benchmark_rows).to_csv(benchmark_csv, index=False)

    train_selector(
        dataset_csv=dataset_csv,
        model_path=model_path,
        feature_importance_csv=importance_path,
        random_seed=3,
        test_size=0.25,
    )
    result = evaluate_selector(
        dataset_csv=dataset_csv,
        benchmark_csv=benchmark_csv,
        model_path=model_path,
        report_csv=report_path,
        summary_csv=summary_csv_path,
        summary_markdown=summary_markdown_path,
        random_seed=3,
        test_size=0.25,
    )

    report = pd.read_csv(report_path)
    assert not report.empty
    assert report["selected_objective_for_scoring"].notna().all()
    assert result.average_selected_objective >= result.average_virtual_best_objective
