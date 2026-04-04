"""Tests for selection dataset construction."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.selection.build_selection_dataset import build_selection_dataset


def test_build_selection_dataset_merges_features_targets_and_objectives(tmp_path: Path) -> None:
    """The selection dataset should combine features, target, and solver objectives."""

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
    """Ties should follow objective, runtime, then solver-name ordering."""

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
    """Instances without an eligible solver should keep a missing best_solver value."""

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
