# Tests for benchmark validation helpers.

from __future__ import annotations

import pandas as pd
import pytest

from src.experiments.benchmark_validation import (
    BenchmarkValidationError,
    ensure_valid_benchmark_results,
    validate_benchmark_results,
)


def test_validate_benchmark_results_accepts_traceable_rows() -> None:

    # A well-formed benchmark table should pass validation.
    frame = pd.DataFrame(
        [
            {
                "instance_name": "inst_1",
                "solver_name": "random_baseline",
                "solver_registry_name": "random_baseline",
                "objective_value": 10.0,
                "objective_sense": "lower_is_better",
                "objective_value_valid": True,
                "runtime_seconds": 0.1,
                "feasible": True,
                "status": "OPTIMAL",
                "solver_support_status": "supported",
                "scoring_status": "supported_feasible_run",
                "modeling_scope": "test scope",
                "scoring_notes": "test note",
                "random_seed": 7,
                "configured_time_limit_seconds": 1,
                "timestamp": "2026-04-04T12:00:00+00:00",
                "is_synthetic": True,
                "instance_source_path": "data/raw/demo.xml",
                "solver_metadata_json": "{}",
                "error_message": "",
            }
        ]
    )

    issues = validate_benchmark_results(
        frame,
        expected_solver_registry_names={"random_baseline"},
    )

    assert issues == []
    ensure_valid_benchmark_results(frame, expected_solver_registry_names={"random_baseline"})


def test_validate_benchmark_results_flags_duplicates_and_invalid_values() -> None:

    # Duplicate rows and impossible numeric values should be reported.
    frame = pd.DataFrame(
        [
            {
                "instance_name": "inst_1",
                "solver_name": "random_baseline",
                "solver_registry_name": "random_baseline",
                "objective_value": None,
                "objective_sense": "lower_is_better",
                "objective_value_valid": False,
                "runtime_seconds": -0.5,
                "feasible": True,
                "status": "OPTIMAL",
                "solver_support_status": "supported",
                "scoring_status": "supported_feasible_run",
                "modeling_scope": "test scope",
                "scoring_notes": "test note",
                "random_seed": 7,
                "configured_time_limit_seconds": 1,
                "timestamp": "2026-04-04T12:00:00+00:00",
                "is_synthetic": True,
                "instance_source_path": "data/raw/demo.xml",
                "solver_metadata_json": "{}",
                "error_message": "",
            },
            {
                "instance_name": "inst_1",
                "solver_name": "random_baseline",
                "solver_registry_name": "random_baseline",
                "objective_value": None,
                "objective_sense": "lower_is_better",
                "objective_value_valid": False,
                "runtime_seconds": -0.5,
                "feasible": True,
                "status": "OPTIMAL",
                "solver_support_status": "supported",
                "scoring_status": "supported_feasible_run",
                "modeling_scope": "test scope",
                "scoring_notes": "test note",
                "random_seed": 7,
                "configured_time_limit_seconds": 1,
                "timestamp": "2026-04-04T12:00:01+00:00",
                "is_synthetic": True,
                "instance_source_path": "data/raw/demo.xml",
                "solver_metadata_json": "{}",
                "error_message": "",
            },
        ]
    )

    issues = validate_benchmark_results(
        frame,
        expected_solver_registry_names={"random_baseline"},
    )
    issue_codes = {issue.code for issue in issues}

    assert "duplicate_rows" in issue_codes
    assert "invalid_runtime" in issue_codes
    assert "missing_feasible_objective" in issue_codes


def test_ensure_valid_benchmark_results_rejects_unexpected_solver_registry_names() -> None:

    # Rows outside the configured solver portfolio should fail validation.
    frame = pd.DataFrame(
        [
            {
                "instance_name": "inst_1",
                "solver_name": "mystery_solver",
                "solver_registry_name": "mystery_solver",
                "objective_value": None,
                "objective_sense": "lower_is_better",
                "objective_value_valid": False,
                "runtime_seconds": 0.1,
                "feasible": False,
                "status": "FAILED:KeyError",
                "solver_support_status": "failed",
                "scoring_status": "failed_run",
                "modeling_scope": "test scope",
                "scoring_notes": "missing",
                "random_seed": 7,
                "configured_time_limit_seconds": 1,
                "timestamp": "2026-04-04T12:00:00+00:00",
                "is_synthetic": False,
                "instance_source_path": "data/raw/real.xml",
                "solver_metadata_json": "{}",
                "error_message": "missing",
            }
        ]
    )

    with pytest.raises(BenchmarkValidationError):
        ensure_valid_benchmark_results(frame, expected_solver_registry_names={"random_baseline"})
