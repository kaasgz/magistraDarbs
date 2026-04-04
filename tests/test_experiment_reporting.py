"""Tests for thesis-friendly experiment reporting exports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.experiments.reporting import generate_thesis_artifacts


def test_generate_thesis_artifacts_writes_tables_plots_and_markdown(tmp_path: Path) -> None:
    """Reporting exports should create thesis-friendly CSV, PNG, and Markdown artifacts."""

    benchmark_csv = tmp_path / "benchmark_results.csv"
    evaluation_summary_csv = tmp_path / "selector_evaluation_summary.csv"
    feature_importance_csv = tmp_path / "feature_importance.csv"
    output_dir = tmp_path / "thesis_artifacts"

    pd.DataFrame(
        [
            {
                "instance_name": "inst_1",
                "solver_name": "solver_a",
                "objective_value": 1.0,
                "runtime_seconds": 1.0,
                "feasible": True,
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_1",
                "solver_name": "solver_b",
                "objective_value": 2.0,
                "runtime_seconds": 1.5,
                "feasible": True,
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_2",
                "solver_name": "solver_a",
                "objective_value": 4.0,
                "runtime_seconds": 1.1,
                "feasible": True,
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_2",
                "solver_name": "solver_b",
                "objective_value": 1.5,
                "runtime_seconds": 1.4,
                "feasible": True,
                "status": "OPTIMAL",
            },
        ]
    ).to_csv(benchmark_csv, index=False)

    pd.DataFrame(
        [
            {
                "summary_row_type": "split",
                "split_id": "holdout",
                "split_strategy": "holdout",
                "classification_accuracy": 1.0,
                "balanced_accuracy": 1.0,
                "average_selected_objective": 1.4,
                "average_virtual_best_objective": 1.25,
                "average_single_best_objective": 1.6,
                "regret_vs_virtual_best": 0.15,
                "delta_vs_single_best": -0.2,
                "improvement_vs_single_best": 0.2,
                "single_best_solver_name": "solver_a",
            },
            {
                "summary_row_type": "aggregate_mean",
                "split_id": "aggregate_mean",
                "split_strategy": "holdout",
                "classification_accuracy": 1.0,
                "balanced_accuracy": 1.0,
                "average_selected_objective": 1.4,
                "average_virtual_best_objective": 1.25,
                "average_single_best_objective": 1.6,
                "regret_vs_virtual_best": 0.15,
                "delta_vs_single_best": -0.2,
                "improvement_vs_single_best": 0.2,
                "single_best_solver_name": "solver_a",
            },
            {
                "summary_row_type": "aggregate_std",
                "split_id": "aggregate_std",
                "split_strategy": "holdout",
                "classification_accuracy": 0.0,
                "balanced_accuracy": 0.0,
                "average_selected_objective": 0.0,
                "average_virtual_best_objective": 0.0,
                "average_single_best_objective": 0.0,
                "regret_vs_virtual_best": 0.0,
                "delta_vs_single_best": 0.0,
                "improvement_vs_single_best": 0.0,
                "single_best_solver_name": "solver_a",
            },
        ]
    ).to_csv(evaluation_summary_csv, index=False)

    pd.DataFrame(
        [
            {
                "feature": "numeric__num_teams",
                "source_feature": "num_teams",
                "feature_group": "size",
                "importance": 0.55,
            },
            {
                "feature": "numeric__constraints_per_team",
                "source_feature": "constraints_per_team",
                "feature_group": "density",
                "importance": 0.30,
            },
            {
                "feature": "categorical__objective_name_compact",
                "source_feature": "objective_name",
                "feature_group": "objective",
                "importance": 0.15,
            },
        ]
    ).to_csv(feature_importance_csv, index=False)

    result = generate_thesis_artifacts(
        benchmark_csv=benchmark_csv,
        evaluation_summary_csv=evaluation_summary_csv,
        feature_importance_csv=feature_importance_csv,
        output_dir=output_dir,
    )

    solver_comparison = pd.read_csv(result.solver_comparison_csv)
    selector_summary = pd.read_csv(result.selector_summary_csv)
    importance_table = pd.read_csv(result.feature_importance_csv)
    summary_markdown = result.summary_markdown.read_text(encoding="utf-8")

    assert result.output_dir == output_dir
    assert result.solver_comparison_csv.exists()
    assert result.selector_summary_csv.exists()
    assert result.feature_importance_csv.exists()
    assert result.runtime_plot_png.exists()
    assert result.objective_plot_png.exists()
    assert result.summary_markdown.exists()

    assert {
        "solver_name",
        "num_instances_solved",
        "win_count",
        "average_objective",
        "average_runtime",
    }.issubset(solver_comparison.columns)
    assert set(selector_summary["method"]) == {
        "selector",
        "single_best_solver",
        "virtual_best_solver",
    }
    assert {
        "importance_rank",
        "source_feature",
        "feature_group",
        "importance_share",
        "cumulative_importance_share",
    }.issubset(importance_table.columns)
    assert importance_table.loc[0, "source_feature"] == "num_teams"
    assert result.runtime_plot_png.stat().st_size > 0
    assert result.objective_plot_png.stat().st_size > 0
    assert "Thesis Artifact Summary" in summary_markdown
    assert "Selector vs SBS vs VBS" in summary_markdown
