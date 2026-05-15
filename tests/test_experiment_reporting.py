"""Tests for thesis-friendly experiment reporting exports."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.experiments.reporting import generate_thesis_artifacts
from src.experiments.thesis_report import generate_thesis_benchmark_report, main as thesis_report_main


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


def test_generate_thesis_benchmark_report_writes_csv_and_markdown_tables(tmp_path: Path) -> None:
    """The thesis report generator should export reusable CSV and Markdown summaries."""

    benchmark_csv = tmp_path / "full_benchmark_results.csv"
    evaluation_summary_csv = tmp_path / "selector_evaluation_summary.csv"
    feature_importance_csv = tmp_path / "feature_importance.csv"
    output_dir = tmp_path / "reports"

    _write_report_benchmark_fixture(benchmark_csv)
    _write_report_evaluation_fixture(evaluation_summary_csv)
    _write_report_feature_importance_fixture(feature_importance_csv)

    result = generate_thesis_benchmark_report(
        benchmark_csv=benchmark_csv,
        evaluation_summary_csv=evaluation_summary_csv,
        feature_importance_csv=feature_importance_csv,
        output_dir=output_dir,
        top_feature_count=2,
    )

    solver_comparison = pd.read_csv(result.solver_comparison_csv)
    win_counts = pd.read_csv(result.win_counts_csv)
    average_objective = pd.read_csv(result.average_objective_csv)
    average_runtime = pd.read_csv(result.average_runtime_csv)
    selector_vs_baselines = pd.read_csv(result.selector_vs_baselines_csv)
    feature_importance = pd.read_csv(result.feature_importance_summary_csv)
    summary_markdown = result.summary_markdown.read_text(encoding="utf-8")

    assert result.output_dir == output_dir
    assert result.solver_comparison_markdown.exists()
    assert result.win_counts_markdown.exists()
    assert result.average_objective_markdown.exists()
    assert result.average_runtime_markdown.exists()
    assert result.selector_vs_baselines_markdown.exists()
    assert result.feature_importance_summary_markdown.exists()
    assert result.run_summary_json.exists()

    assert set(solver_comparison["result_scope"]) == {"real", "synthetic"}
    assert {
        "solver_registry_name",
        "num_instances_solved",
        "coverage_ratio",
        "win_count",
        "average_objective",
        "average_runtime_seconds",
    }.issubset(solver_comparison.columns)
    assert set(win_counts["result_scope"]) == {"real", "synthetic"}
    assert "average_objective" in average_objective.columns
    assert "average_runtime_seconds" in average_runtime.columns
    assert set(selector_vs_baselines["method"]) == {
        "selector",
        "single_best_solver",
        "virtual_best_solver",
    }
    assert set(selector_vs_baselines["result_scope"]) == {"mixed"}
    assert len(feature_importance.index) == 2
    assert feature_importance.loc[0, "source_feature"] == "num_teams"
    assert "Thesis Benchmark And Selector Report" in summary_markdown
    assert "Synthetic/Real Separation" in summary_markdown
    assert "Selector Vs Single Best Vs Virtual Best" in summary_markdown


def test_thesis_report_cli_uses_default_style_arguments(tmp_path: Path) -> None:
    """The CLI should generate reports with explicit input and output paths."""

    benchmark_csv = tmp_path / "full_benchmark_results.csv"
    evaluation_summary_csv = tmp_path / "selector_evaluation_summary.csv"
    feature_importance_csv = tmp_path / "feature_importance.csv"
    output_dir = tmp_path / "reports"

    _write_report_benchmark_fixture(benchmark_csv)
    _write_report_evaluation_fixture(evaluation_summary_csv)
    _write_report_feature_importance_fixture(feature_importance_csv)

    exit_code = thesis_report_main(
        [
            "--benchmark-csv",
            str(benchmark_csv),
            "--evaluation-summary-csv",
            str(evaluation_summary_csv),
            "--feature-importance-csv",
            str(feature_importance_csv),
            "--output-dir",
            str(output_dir),
            "--result-scope",
            "synthetic",
            "--top-feature-count",
            "2",
        ]
    )

    assert exit_code == 0
    assert (output_dir / "solver_comparison.csv").exists()
    assert (output_dir / "thesis_benchmark_report.md").exists()


def _write_report_benchmark_fixture(path: Path) -> None:
    """Write a mixed synthetic/real benchmark fixture."""

    pd.DataFrame(
        [
            {
                "instance_name": "synthetic_1",
                "solver_name": "solver_a",
                "solver_registry_name": "solver_a",
                "objective_value": 1.0,
                "runtime_seconds": 1.0,
                "feasible": True,
                "status": "OPTIMAL",
                "is_synthetic": True,
            },
            {
                "instance_name": "synthetic_1",
                "solver_name": "solver_b",
                "solver_registry_name": "solver_b",
                "objective_value": 2.0,
                "runtime_seconds": 0.5,
                "feasible": True,
                "status": "FEASIBLE",
                "is_synthetic": True,
            },
            {
                "instance_name": "real_1",
                "solver_name": "solver_a",
                "solver_registry_name": "solver_a",
                "objective_value": 3.0,
                "runtime_seconds": 2.0,
                "feasible": True,
                "status": "FEASIBLE",
                "is_synthetic": False,
            },
            {
                "instance_name": "real_1",
                "solver_name": "solver_b",
                "solver_registry_name": "solver_b",
                "objective_value": None,
                "runtime_seconds": 0.1,
                "feasible": False,
                "status": "NOT_CONFIGURED",
                "is_synthetic": False,
            },
        ]
    ).to_csv(path, index=False)


def _write_report_evaluation_fixture(path: Path) -> None:
    """Write a selector evaluation summary fixture."""

    pd.DataFrame(
        [
            {
                "summary_row_type": "split",
                "split_strategy": "holdout",
                "classification_accuracy": 0.75,
                "balanced_accuracy": 0.70,
                "average_selected_objective": 1.5,
                "average_virtual_best_objective": 1.0,
                "average_single_best_objective": 1.8,
                "regret_vs_virtual_best": 0.5,
                "delta_vs_single_best": -0.3,
                "single_best_solver_name": "solver_a",
            },
            {
                "summary_row_type": "aggregate_mean",
                "split_strategy": "holdout",
                "classification_accuracy": 0.75,
                "balanced_accuracy": 0.70,
                "average_selected_objective": 1.5,
                "average_virtual_best_objective": 1.0,
                "average_single_best_objective": 1.8,
                "regret_vs_virtual_best": 0.5,
                "delta_vs_single_best": -0.3,
                "single_best_solver_name": "solver_a",
            },
            {
                "summary_row_type": "aggregate_std",
                "split_strategy": "holdout",
                "classification_accuracy": 0.05,
                "balanced_accuracy": 0.10,
            },
        ]
    ).to_csv(path, index=False)


def _write_report_feature_importance_fixture(path: Path) -> None:
    """Write a feature importance fixture."""

    pd.DataFrame(
        [
            {
                "feature": "numeric__num_teams",
                "source_feature": "num_teams",
                "feature_group": "size",
                "importance": 0.6,
            },
            {
                "feature": "numeric__constraints_per_team",
                "source_feature": "constraints_per_team",
                "feature_group": "density",
                "importance": 0.3,
            },
            {
                "feature": "numeric__num_slots",
                "source_feature": "num_slots",
                "feature_group": "size",
                "importance": 0.1,
            },
        ]
    ).to_csv(path, index=False)
