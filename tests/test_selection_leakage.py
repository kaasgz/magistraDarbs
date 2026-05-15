"""Tests for leakage-safe selector feature preparation."""

from __future__ import annotations

import pandas as pd

from src.selection.modeling import is_leakage_column, prepare_selection_data


def test_prepare_selection_data_excludes_benchmark_target_source_and_solver_columns() -> None:
    """Only pre-solving structural columns should reach the selector model."""

    dataset = pd.DataFrame(
        [
            _row("inst_1", "solver_a", 4, 0.75, False),
            _row("inst_2", "solver_a", 6, 0.80, False),
            _row("inst_3", "solver_b", 8, 0.95, True),
            _row("inst_4", "solver_b", 10, 1.10, True),
        ]
    )

    prepared = prepare_selection_data(dataset)

    assert prepared.feature_columns == ("num_teams", "slot_pressure")
    assert set(prepared.excluded_columns).issuperset(
        {
            "dataset_type",
            "is_synthetic",
            "source_kind",
            "instance_source_path",
            "objective_solver_a",
            "benchmark_eligible_solver_count",
            "label_best_solver_source",
            "target_policy",
            "solver_support_status",
            "scoring_status",
            "runtime_seconds",
            "feasible",
            "status",
            "selected_solver",
            "true_best_solver",
            "single_best_solver_name",
            "regret_vs_virtual_best",
            "random_seed",
        }
    )


def test_is_leakage_column_recognizes_common_result_and_provenance_names() -> None:
    """The denylist should cover plausible future audit/result columns."""

    unsafe_columns = [
        "dataset_type",
        "is_synthetic",
        "source_kind",
        "source_file",
        "objective_cpsat_solver",
        "benchmark_best_solver_mean_objective",
        "solver_registry_name",
        "scoring_status",
        "target_eligible",
        "label_source",
        "selected_solver",
        "true_best_solver",
        "single_best_solver_name",
        "virtual_best_objective",
        "regret_vs_virtual_best",
        "delta_vs_single_best",
        "improvement_vs_single_best",
        "runtime_seconds",
        "feasible",
        "status",
        "random_seed",
    ]
    safe_columns = [
        "num_teams",
        "num_slots",
        "slot_pressure",
        "constraints_per_team",
        "number_of_constraint_types",
    ]

    assert all(is_leakage_column(column) for column in unsafe_columns)
    assert not any(is_leakage_column(column) for column in safe_columns)


def _row(
    instance_name: str,
    best_solver: str,
    num_teams: int,
    slot_pressure: float,
    synthetic: bool,
) -> dict[str, object]:
    """Build one mixed selection dataset row with deliberate leak columns."""

    return {
        "instance_name": instance_name,
        "best_solver": best_solver,
        "num_teams": num_teams,
        "slot_pressure": slot_pressure,
        "dataset_type": "synthetic" if synthetic else "real",
        "is_synthetic": synthetic,
        "source_kind": "synthetic" if synthetic else "real",
        "instance_source_path": f"data/raw/{instance_name}.xml",
        "objective_solver_a": 1.0,
        "benchmark_eligible_solver_count": 2,
        "label_best_solver_source": "benchmark",
        "target_policy": "feasible_numeric_objective",
        "solver_support_status": "supported",
        "scoring_status": "supported_feasible_run",
        "runtime_seconds": 1.0,
        "feasible": True,
        "status": "FEASIBLE",
        "selected_solver": best_solver,
        "true_best_solver": best_solver,
        "single_best_solver_name": "solver_a",
        "regret_vs_virtual_best": 0.0,
        "random_seed": 42,
    }
