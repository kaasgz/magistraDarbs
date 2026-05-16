# Tests for selection dataset construction.

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.selection.build_selection_dataset import build_full_selection_dataset, build_selection_dataset, main
from src.selection.modeling import prepare_selection_data


def test_build_selection_dataset_merges_features_targets_and_objectives(tmp_path: Path) -> None:

    # The selection dataset should combine features, target, and solver objectives.
    features_csv = tmp_path / "features.csv"
    benchmarks_csv = tmp_path / "benchmark_results.csv"
    output_csv = tmp_path / "selection_dataset.csv"

    pd.DataFrame(
        [
            {"instance_name": "inst_1", "num_teams": 4, "num_slots": 3},
            {"instance_name": "inst_2", "num_teams": 6, "num_slots": 5},
        ]
    ).to_csv(features_csv, index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "inst_1",
                "solver_name": "solver_a",
                "objective_value": 10.0,
                "runtime_seconds": 2.0,
                "feasible": True,
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_1",
                "solver_name": "solver_b",
                "objective_value": 8.0,
                "runtime_seconds": 1.5,
                "feasible": True,
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_2",
                "solver_name": "solver_a",
                "objective_value": 7.0,
                "runtime_seconds": 2.5,
                "feasible": True,
                "status": "FEASIBLE",
            },
            {
                "instance_name": "inst_2",
                "solver_name": "solver_b",
                "objective_value": None,
                "runtime_seconds": 3.0,
                "feasible": False,
                "status": "FAILED:RuntimeError",
            },
        ]
    ).to_csv(benchmarks_csv, index=False)

    build_selection_dataset(features_csv, benchmarks_csv, output_csv)

    result = pd.read_csv(output_csv)

    assert list(result.columns) == [
        "instance_name",
        "num_teams",
        "num_slots",
        "best_solver",
        "objective_solver_a",
        "objective_solver_b",
    ]
    assert list(result["best_solver"]) == ["solver_b", "solver_a"]
    assert result.loc[result["instance_name"] == "inst_1", "objective_solver_b"].item() == 8.0
    assert pd.isna(result.loc[result["instance_name"] == "inst_2", "objective_solver_b"]).item()


def test_build_selection_dataset_breaks_ties_deterministically(tmp_path: Path) -> None:

    # Ties should follow objective, runtime, then solver-name ordering.
    features_csv = tmp_path / "features.csv"
    benchmarks_csv = tmp_path / "benchmark_results.csv"
    output_csv = tmp_path / "selection_dataset.csv"

    pd.DataFrame(
        [
            {"instance_name": "inst_fast", "num_teams": 4},
            {"instance_name": "inst_alpha", "num_teams": 4},
        ]
    ).to_csv(features_csv, index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "inst_fast",
                "solver_name": "solver_a",
                "objective_value": 10.0,
                "runtime_seconds": 2.0,
                "feasible": True,
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_fast",
                "solver_name": "solver_b",
                "objective_value": 10.0,
                "runtime_seconds": 1.0,
                "feasible": True,
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_alpha",
                "solver_name": "solver_b",
                "objective_value": 5.0,
                "runtime_seconds": 1.0,
                "feasible": True,
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_alpha",
                "solver_name": "solver_a",
                "objective_value": 5.0,
                "runtime_seconds": 1.0,
                "feasible": True,
                "status": "OPTIMAL",
            },
        ]
    ).to_csv(benchmarks_csv, index=False)

    build_selection_dataset(features_csv, benchmarks_csv, output_csv)

    result = pd.read_csv(output_csv)

    assert result.loc[result["instance_name"] == "inst_fast", "best_solver"].item() == "solver_b"
    assert result.loc[result["instance_name"] == "inst_alpha", "best_solver"].item() == "solver_a"


def test_build_selection_dataset_can_skip_objective_columns_and_keep_missing_targets(tmp_path: Path) -> None:

    # Instances without an eligible solver should keep a missing best_solver value.
    features_csv = tmp_path / "features.csv"
    benchmarks_csv = tmp_path / "benchmark_results.csv"
    output_csv = tmp_path / "selection_dataset.csv"

    pd.DataFrame(
        [
            {"instance_name": "inst_1", "num_teams": 4},
            {"instance_name": "inst_2", "num_teams": 6},
        ]
    ).to_csv(features_csv, index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "inst_1",
                "solver_name": "solver_a",
                "objective_value": 9.0,
                "runtime_seconds": 1.0,
                "feasible": True,
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_2",
                "solver_name": "solver_a",
                "objective_value": None,
                "runtime_seconds": 1.5,
                "feasible": False,
                "status": "FAILED:RuntimeError",
            },
        ]
    ).to_csv(benchmarks_csv, index=False)

    build_selection_dataset(
        features_csv,
        benchmarks_csv,
        output_csv,
        include_solver_objectives=False,
    )

    result = pd.read_csv(output_csv)

    assert list(result.columns) == ["instance_name", "num_teams", "best_solver"]
    assert result.loc[result["instance_name"] == "inst_1", "best_solver"].item() == "solver_a"
    assert pd.isna(result.loc[result["instance_name"] == "inst_2", "best_solver"]).item()


def test_build_full_selection_dataset_combines_synthetic_and_real_sources(tmp_path: Path) -> None:

    # Full dataset construction should label sources and use canonical solver names.
    synthetic_features_csv = tmp_path / "synthetic_features.csv"
    synthetic_benchmarks_csv = tmp_path / "synthetic_benchmarks.csv"
    real_features_csv = tmp_path / "real_features.csv"
    real_benchmarks_csv = tmp_path / "real_benchmarks.csv"
    output_csv = tmp_path / "selection_dataset_full.csv"

    pd.DataFrame(
        [
            {
                "instance_name": "synthetic_1",
                "num_teams": 4,
                "num_slots": 6,
                "shared_feature": 1.5,
                "synthetic_only": 99,
            },
            {
                "instance_name": "synthetic_unsupported",
                "num_teams": 6,
                "num_slots": 10,
                "shared_feature": 2.5,
                "synthetic_only": 88,
            },
        ]
    ).to_csv(synthetic_features_csv, index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "real_1",
                "num_teams": 8,
                "num_slots": 14,
                "shared_feature": 3.5,
                "real_only": 77,
            }
        ]
    ).to_csv(real_features_csv, index=False)

    pd.DataFrame(
        [
            {
                "instance_name": "synthetic_1",
                "solver_name": "cpsat_round_robin",
                "solver_registry_name": "cpsat_solver",
                "objective_value": 5.0,
                "runtime_seconds": 1.0,
                "feasible": True,
                "solver_support_status": "supported",
                "status": "FEASIBLE",
            },
            {
                "instance_name": "synthetic_1",
                "solver_name": "random_baseline",
                "solver_registry_name": "random_baseline",
                "objective_value": 9.0,
                "runtime_seconds": 0.2,
                "feasible": True,
                "solver_support_status": "simplified_baseline",
                "status": "FEASIBLE",
            },
            {
                "instance_name": "synthetic_unsupported",
                "solver_name": "timefold",
                "solver_registry_name": "timefold",
                "objective_value": None,
                "runtime_seconds": 0.0,
                "feasible": False,
                "solver_support_status": "not_configured",
                "status": "NOT_CONFIGURED",
            },
        ]
    ).to_csv(synthetic_benchmarks_csv, index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "real_1",
                "solver_name": "simulated_annealing_baseline",
                "solver_registry_name": "simulated_annealing_solver",
                "objective_value": 11.0,
                "runtime_seconds": 2.0,
                "feasible": True,
                "solver_support_status": "simplified_baseline",
                "status": "FEASIBLE",
            },
            {
                "instance_name": "real_1",
                "solver_name": "timefold",
                "solver_registry_name": "timefold",
                "objective_value": None,
                "runtime_seconds": 0.1,
                "feasible": False,
                "solver_support_status": "unsupported_instance",
                "status": "UNSUPPORTED_INSTANCE",
            },
        ]
    ).to_csv(real_benchmarks_csv, index=False)

    result_path = build_full_selection_dataset(
        synthetic_features_csv=synthetic_features_csv,
        synthetic_benchmark_csv=synthetic_benchmarks_csv,
        real_features_csv=real_features_csv,
        real_benchmark_csv=real_benchmarks_csv,
        output_csv=output_csv,
    )

    result = pd.read_csv(result_path)

    assert result_path == output_csv
    assert list(result.columns) == [
        "instance_name",
        "dataset_type",
        "num_teams",
        "num_slots",
        "shared_feature",
        "best_solver",
        "objective_cpsat_solver",
        "objective_random_baseline",
        "objective_simulated_annealing_solver",
        "objective_timefold",
    ]
    assert set(result["dataset_type"]) == {"synthetic", "real"}
    assert "synthetic_only" not in result.columns
    assert "real_only" not in result.columns
    assert result.loc[result["instance_name"] == "synthetic_1", "best_solver"].item() == "cpsat_solver"
    assert result.loc[result["instance_name"] == "real_1", "best_solver"].item() == "simulated_annealing_solver"
    assert pd.isna(result.loc[result["instance_name"] == "synthetic_unsupported", "best_solver"]).item()
    assert pd.isna(result.loc[result["instance_name"] == "synthetic_unsupported", "objective_timefold"]).item()
    assert output_csv.with_name("selection_dataset_full_run_summary.json").exists()

    prepared = prepare_selection_data(result)
    assert "dataset_type" not in prepared.feature_columns
    assert "dataset_type" in prepared.excluded_columns


def test_full_selection_dataset_cli_writes_expected_output(tmp_path: Path) -> None:

    # The existing builder CLI should support the combined full-dataset mode.
    synthetic_features_csv = tmp_path / "synthetic_features.csv"
    synthetic_benchmarks_csv = tmp_path / "synthetic_benchmarks.csv"
    real_features_csv = tmp_path / "real_features.csv"
    real_benchmarks_csv = tmp_path / "real_benchmarks.csv"
    output_csv = tmp_path / "selection_dataset_full.csv"
    config_path = tmp_path / "selector_config.yaml"

    pd.DataFrame([{"instance_name": "synthetic_1", "num_teams": 4}]).to_csv(
        synthetic_features_csv,
        index=False,
    )
    pd.DataFrame([{"instance_name": "real_1", "num_teams": 6}]).to_csv(real_features_csv, index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "synthetic_1",
                "solver_name": "solver_a",
                "objective_value": 1.0,
                "runtime_seconds": 1.0,
                "feasible": True,
                "status": "FEASIBLE",
            }
        ]
    ).to_csv(synthetic_benchmarks_csv, index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "real_1",
                "solver_name": "solver_b",
                "objective_value": 2.0,
                "runtime_seconds": 1.0,
                "feasible": True,
                "status": "FEASIBLE",
            }
        ]
    ).to_csv(real_benchmarks_csv, index=False)
    config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  synthetic_features_csv: {synthetic_features_csv.as_posix()}",
                f"  synthetic_benchmark_results_csv: {synthetic_benchmarks_csv.as_posix()}",
                f"  real_features_csv: {real_features_csv.as_posix()}",
                f"  real_benchmark_results_csv: {real_benchmarks_csv.as_posix()}",
                f"  full_selection_dataset_csv: {output_csv.as_posix()}",
                "dataset:",
                "  include_solver_objectives: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    exit_code = main(["--config", str(config_path), "--full"])

    result = pd.read_csv(output_csv)
    assert exit_code == 0
    assert list(result["dataset_type"]) == ["real", "synthetic"]
    assert list(result["best_solver"]) == ["solver_b", "solver_a"]
    assert "benchmark_solver_support_coverage" in result.columns
    assert "benchmark_eligible_solver_count" in result.columns
