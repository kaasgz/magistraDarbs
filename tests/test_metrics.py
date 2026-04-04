"""Tests for benchmark evaluation metrics."""

from __future__ import annotations

import pandas as pd
import pytest

from src.experiments.metrics import (
    average_objective_by_solver,
    average_runtime_by_solver,
    best_solver_per_instance,
    single_best_solver,
    virtual_best_solver,
)


def _sample_results() -> pd.DataFrame:
    """Create a compact benchmark table with CSV-like values."""

    return pd.DataFrame(
        [
            {
                "instance_name": "inst_1",
                "solver_name": "solver_a",
                "objective_value": "10.0",
                "runtime_seconds": "1.0",
                "feasible": "True",
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_1",
                "solver_name": "solver_b",
                "objective_value": "8.0",
                "runtime_seconds": "2.0",
                "feasible": "True",
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_1",
                "solver_name": "solver_c",
                "objective_value": None,
                "runtime_seconds": "0.5",
                "feasible": "False",
                "status": "FAILED:RuntimeError",
            },
            {
                "instance_name": "inst_2",
                "solver_name": "solver_a",
                "objective_value": "11.0",
                "runtime_seconds": "1.5",
                "feasible": "True",
                "status": "FEASIBLE",
            },
            {
                "instance_name": "inst_2",
                "solver_name": "solver_b",
                "objective_value": None,
                "runtime_seconds": "2.5",
                "feasible": "False",
                "status": "INFEASIBLE",
            },
            {
                "instance_name": "inst_2",
                "solver_name": "solver_c",
                "objective_value": "9.0",
                "runtime_seconds": "3.0",
                "feasible": "True",
                "status": "FEASIBLE",
            },
            {
                "instance_name": "inst_3",
                "solver_name": "solver_a",
                "objective_value": None,
                "runtime_seconds": "1.2",
                "feasible": "False",
                "status": "FAILED:ValueError",
            },
            {
                "instance_name": "inst_3",
                "solver_name": "solver_b",
                "objective_value": "7.0",
                "runtime_seconds": "2.2",
                "feasible": "True",
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_3",
                "solver_name": "solver_c",
                "objective_value": "5.0",
                "runtime_seconds": "4.0",
                "feasible": "True",
                "status": "OPTIMAL",
            },
            {
                "instance_name": "inst_4",
                "solver_name": "solver_a",
                "objective_value": None,
                "runtime_seconds": "1.1",
                "feasible": "False",
                "status": "FAILED:RuntimeError",
            },
            {
                "instance_name": "inst_4",
                "solver_name": "solver_b",
                "objective_value": "12.0",
                "runtime_seconds": "2.4",
                "feasible": "True",
                "status": "FEASIBLE",
            },
            {
                "instance_name": "inst_4",
                "solver_name": "solver_c",
                "objective_value": None,
                "runtime_seconds": "3.5",
                "feasible": "False",
                "status": "FAILED:RuntimeError",
            },
            {
                "instance_name": "inst_5",
                "solver_name": "solver_a",
                "objective_value": None,
                "runtime_seconds": "1.3",
                "feasible": "False",
                "status": "FAILED:RuntimeError",
            },
            {
                "instance_name": "inst_5",
                "solver_name": "solver_b",
                "objective_value": None,
                "runtime_seconds": "2.3",
                "feasible": "False",
                "status": "FAILED:RuntimeError",
            },
        ]
    )


def test_best_solver_per_instance_returns_best_feasible_rows_and_placeholders() -> None:
    """The per-instance best table should keep one row for every instance."""

    results = best_solver_per_instance(_sample_results())

    assert list(results["instance_name"]) == ["inst_1", "inst_2", "inst_3", "inst_4", "inst_5"]
    assert list(results["solver_name"].iloc[:4]) == ["solver_b", "solver_c", "solver_c", "solver_b"]
    assert pd.isna(results.loc[results["instance_name"] == "inst_5", "solver_name"]).all()
    assert results.loc[results["instance_name"] == "inst_5", "status"].item() == "NO_FEASIBLE_SOLVER"


def test_single_best_solver_prefers_coverage_then_average_objective() -> None:
    """The single best solver should follow the documented selection rule."""

    summary = single_best_solver(_sample_results())

    assert summary["solver_name"] == "solver_b"
    assert summary["num_instances_solved"] == 3
    assert summary["average_objective"] == pytest.approx(9.0)
    assert summary["average_runtime"] == pytest.approx(2.28)


def test_virtual_best_solver_aggregates_oracle_per_instance_choice() -> None:
    """The virtual best summary should aggregate the best feasible row per instance."""

    summary = virtual_best_solver(_sample_results())

    assert summary["solver_name"] == "virtual_best_solver"
    assert summary["num_instances"] == 5
    assert summary["num_instances_solved"] == 4
    assert summary["average_objective"] == pytest.approx(8.5)
    assert summary["average_runtime"] == pytest.approx(2.85)


def test_average_objective_and_runtime_by_solver_use_documented_filters() -> None:
    """Objective and runtime summaries should match the documented assumptions."""

    objective_summary = average_objective_by_solver(_sample_results())
    runtime_summary = average_runtime_by_solver(_sample_results())

    assert list(objective_summary["solver_name"]) == ["solver_c", "solver_b", "solver_a"]
    assert list(objective_summary["num_instances_solved"]) == [2, 3, 2]
    assert objective_summary.loc[objective_summary["solver_name"] == "solver_c", "average_objective"].item() == pytest.approx(7.0)

    assert list(runtime_summary["solver_name"]) == ["solver_a", "solver_b", "solver_c"]
    assert runtime_summary.loc[runtime_summary["solver_name"] == "solver_a", "average_runtime"].item() == pytest.approx(1.22)
    assert runtime_summary.loc[runtime_summary["solver_name"] == "solver_b", "num_feasible_runs"].item() == 3


def test_metrics_raise_helpful_error_when_columns_are_missing() -> None:
    """Metric helpers should validate the expected benchmark schema."""

    broken = pd.DataFrame([{"instance_name": "inst_1", "solver_name": "solver_a"}])

    with pytest.raises(ValueError, match="missing required columns"):
        average_objective_by_solver(broken)
