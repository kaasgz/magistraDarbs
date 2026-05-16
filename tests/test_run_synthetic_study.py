# Tests for the multi-seed synthetic study pipeline.

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.experiments.generate_synthetic_dataset import generate_synthetic_study_dataset
from src.experiments.run_synthetic_study import (
    _build_aggregate_benchmark_summary,
    run_synthetic_study,
)


def test_run_synthetic_study_writes_per_seed_and_aggregate_outputs(tmp_path: Path) -> None:

    # A small synthetic study should keep per-seed and aggregate outputs separate.
    dataset_root = tmp_path / "data" / "raw" / "synthetic" / "study"
    processed_dir = tmp_path / "data" / "processed" / "synthetic_study"
    results_dir = tmp_path / "data" / "results" / "synthetic_study"
    config_path = tmp_path / "synthetic_study.yaml"

    generate_synthetic_study_dataset(
        n=6,
        seeds=(101,),
        output_root=dataset_root,
        difficulty_profile="easy",
    )
    config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  dataset_root: {dataset_root.as_posix()}",
                f"  processed_dir: {processed_dir.as_posix()}",
                f"  results_dir: {results_dir.as_posix()}",
                "run:",
                "  seeds: [11, 12]",
                "  time_limit_seconds: 1",
                "solvers:",
                "  selected:",
                "    - random_baseline",
                "    - timefold",
                "  settings:",
                "    timefold:",
                "      executable_path: null",
                "      time_limit_seconds: 1",
                "      command_arguments: []",
                "split:",
                "  strategy: holdout",
                "  test_size: 0.5",
                "  cross_validation_folds: null",
                "  repeats: 1",
                "selector:",
                "  model_choice: random_forest",
                "dataset:",
                "  include_solver_objectives: true",
                "",
            ]
        ),
        encoding="utf-8",
    )

    result = run_synthetic_study(config_path)

    benchmarks = pd.read_csv(result.benchmark_csv)
    benchmark_summary = pd.read_csv(result.aggregate_benchmark_summary_csv)
    selector_summary = pd.read_csv(result.aggregate_selector_summary_csv)

    assert result.features_csv.exists()
    assert result.selection_dataset_csv.exists()
    assert result.selector_evaluation_summary_csv.exists()
    assert result.summary_markdown.exists()
    assert len(result.seed_results) == 2
    assert {seed_result.seed for seed_result in result.seed_results} == {11, 12}
    assert all(seed_result.benchmark_csv.exists() for seed_result in result.seed_results)
    assert all(seed_result.selection_dataset_csv.exists() for seed_result in result.seed_results)
    assert all(seed_result.evaluation_summary_csv.exists() for seed_result in result.seed_results)

    assert set(benchmarks["benchmark_seed"]) == {11, 12}
    assert {
        "solver_support_status",
        "scoring_status",
        "modeling_scope",
        "scoring_notes",
        "objective_value_valid",
    } <= set(benchmarks.columns)
    assert set(benchmarks[benchmarks["solver_registry_name"] == "timefold"]["solver_support_status"]) == {
        "not_configured"
    }
    assert {"per_seed", "all_seeds"} <= set(benchmark_summary["summary_scope"])
    assert "all_seeds_mean" in set(selector_summary["summary_scope"])
    assert "Synthetic Study Summary" in result.summary_markdown.read_text(encoding="utf-8")


def test_aggregate_benchmark_summary_uses_only_valid_objectives() -> None:

    # Aggregate objective means should ignore partial and not-configured rows.
    benchmark_table = pd.DataFrame(
        [
            {
                "benchmark_seed": 1,
                "instance_name": "i1",
                "solver_registry_name": "random_baseline",
                "solver_name": "random_baseline",
                "solver_support_status": "partially_supported",
                "scoring_status": "partially_modeled_run",
                "status": "placeholder_feasible",
                "feasible": True,
                "objective_value": 100.0,
                "objective_value_valid": False,
                "runtime_seconds": 0.1,
            },
            {
                "benchmark_seed": 1,
                "instance_name": "i1",
                "solver_registry_name": "cpsat_solver",
                "solver_name": "cpsat_solver",
                "solver_support_status": "supported",
                "scoring_status": "supported_feasible_run",
                "status": "OPTIMAL",
                "feasible": True,
                "objective_value": 7.0,
                "objective_value_valid": True,
                "runtime_seconds": 0.2,
            },
            {
                "benchmark_seed": 1,
                "instance_name": "i1",
                "solver_registry_name": "timefold",
                "solver_name": "timefold",
                "solver_support_status": "not_configured",
                "scoring_status": "not_configured",
                "status": "NOT_CONFIGURED",
                "feasible": False,
                "objective_value": None,
                "objective_value_valid": False,
                "runtime_seconds": 0.0,
            },
        ]
    )

    summary = _build_aggregate_benchmark_summary(benchmark_table)
    all_seed_rows = summary[summary["summary_scope"] == "all_seeds"]
    cpsat_row = all_seed_rows[all_seed_rows["solver_registry_name"] == "cpsat_solver"].iloc[0]
    random_row = all_seed_rows[all_seed_rows["solver_registry_name"] == "random_baseline"].iloc[0]
    timefold_row = all_seed_rows[all_seed_rows["solver_registry_name"] == "timefold"].iloc[0]

    assert int(cpsat_row["valid_objective_runs"]) == 1
    assert float(cpsat_row["average_objective_value_valid"]) == 7.0
    assert int(random_row["valid_objective_runs"]) == 0
    assert pd.isna(random_row["average_objective_value_valid"])
    assert int(timefold_row["not_configured_runs"]) == 1
