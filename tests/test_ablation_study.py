# Tests for selector ablation-study support.

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.selection.ablation_study import run_ablation_study


def test_run_ablation_study_saves_summary_plot_and_report(tmp_path: Path) -> None:

    # Ablation study should evaluate the required feature subsets and save outputs.
    dataset_csv = tmp_path / "selection_dataset.csv"
    benchmark_csv = tmp_path / "benchmark_results.csv"
    summary_csv = tmp_path / "ablation_summary.csv"
    plot_path = tmp_path / "ablation_plot.png"
    report_markdown = tmp_path / "ablation_summary.md"

    pd.DataFrame(
        [
            {
                "instance_name": f"inst_{index}",
                "num_teams": 4 if index < 6 else 8,
                "num_slots": 3 if index < 6 else 7,
                "num_hard_constraints": 2 if index < 6 else 7,
                "num_soft_constraints": 1 if index < 6 else 5,
                "constraints_per_team": 0.5 if index < 6 else 1.5,
                "objective_name": "compact" if index % 2 == 0 else "balanced",
                "objective_present": True,
                "best_solver": "solver_a" if index < 6 else "solver_b",
            }
            for index in range(12)
        ]
    ).to_csv(dataset_csv, index=False)

    benchmark_rows: list[dict[str, object]] = []
    for index in range(12):
        instance_name = f"inst_{index}"
        solver_a_best = index < 6
        benchmark_rows.extend(
            [
                {
                    "instance_name": instance_name,
                    "solver_name": "solver_a",
                    "objective_value": 1.0 if solver_a_best else 9.0,
                    "runtime_seconds": 1.0 + 0.01 * index,
                    "feasible": True,
                    "status": "OPTIMAL",
                },
                {
                    "instance_name": instance_name,
                    "solver_name": "solver_b",
                    "objective_value": 9.0 if solver_a_best else 1.0,
                    "runtime_seconds": 1.1 + 0.01 * index,
                    "feasible": True,
                    "status": "OPTIMAL",
                },
            ]
        )
    pd.DataFrame(benchmark_rows).to_csv(benchmark_csv, index=False)

    result = run_ablation_study(
        dataset_csv=dataset_csv,
        benchmark_csv=benchmark_csv,
        summary_csv=summary_csv,
        plot_path=plot_path,
        report_markdown=report_markdown,
        random_seed=7,
        split_strategy="repeated_stratified_kfold",
        cross_validation_folds=3,
        repeats=2,
    )

    summary = pd.read_csv(summary_csv)
    report = report_markdown.read_text(encoding="utf-8")

    assert result.summary_csv_path == summary_csv
    assert result.plot_path == plot_path
    assert result.report_markdown_path == report_markdown
    assert summary_csv.exists()
    assert plot_path.exists()
    assert report_markdown.exists()
    assert set(summary["feature_set_name"]) == {
        "size_only",
        "size_plus_constraint_composition",
        "all_features",
    }
    assert result.best_feature_set_name in set(summary["feature_set_name"])
    assert "Selector Ablation Summary" in report
