"""Validation helpers for benchmark result artifacts."""

from __future__ import annotations

import math
from collections.abc import Collection
from dataclasses import dataclass

import pandas as pd


REQUIRED_BENCHMARK_COLUMNS = {
    "instance_name",
    "solver_name",
    "objective_value",
    "runtime_seconds",
    "feasible",
    "status",
    "solver_registry_name",
    "random_seed",
    "configured_time_limit_seconds",
    "timestamp",
    "is_synthetic",
}


@dataclass(frozen=True, slots=True)
class BenchmarkValidationIssue:
    """One validation issue found in benchmark results."""

    code: str
    message: str


class BenchmarkValidationError(ValueError):
    """Raised when benchmark results fail validation."""


def validate_benchmark_results(
    results: pd.DataFrame,
    *,
    expected_solver_registry_names: Collection[str] | None = None,
) -> list[BenchmarkValidationIssue]:
    """Return validation issues for one benchmark result table."""

    missing_columns = sorted(REQUIRED_BENCHMARK_COLUMNS.difference(results.columns))
    if missing_columns:
        return [
            BenchmarkValidationIssue(
                code="missing_required_columns",
                message=(
                    "Benchmark results are missing required columns: "
                    + ", ".join(missing_columns)
                ),
            )
        ]

    frame = results.copy()
    frame["instance_name"] = frame["instance_name"].astype("string")
    frame["solver_name"] = frame["solver_name"].astype("string")
    frame["solver_registry_name"] = frame["solver_registry_name"].astype("string")
    frame["status"] = frame["status"].astype("string")
    frame["objective_value"] = pd.to_numeric(frame["objective_value"], errors="coerce")
    frame["runtime_seconds"] = pd.to_numeric(frame["runtime_seconds"], errors="coerce")
    frame["random_seed"] = pd.to_numeric(frame["random_seed"], errors="coerce")
    frame["configured_time_limit_seconds"] = pd.to_numeric(
        frame["configured_time_limit_seconds"],
        errors="coerce",
    )
    frame["feasible"] = frame["feasible"].map(_coerce_bool)
    frame["is_synthetic"] = frame["is_synthetic"].map(_coerce_bool)

    issues: list[BenchmarkValidationIssue] = []

    duplicate_mask = frame.duplicated(
        subset=[
            "instance_name",
            "solver_registry_name",
            "random_seed",
            "configured_time_limit_seconds",
        ],
        keep=False,
    )
    if duplicate_mask.any():
        issues.append(
            BenchmarkValidationIssue(
                code="duplicate_rows",
                message=(
                    "Benchmark results contain duplicate "
                    "instance/solver/seed/time-limit rows."
                ),
            )
        )

    invalid_runtime_mask = frame["runtime_seconds"].map(_is_invalid_runtime)
    if invalid_runtime_mask.any():
        issues.append(
            BenchmarkValidationIssue(
                code="invalid_runtime",
                message="Benchmark results contain negative or non-finite runtime values.",
            )
        )

    missing_feasible_objective_mask = frame["feasible"] & frame["objective_value"].isna()
    if missing_feasible_objective_mask.any():
        issues.append(
            BenchmarkValidationIssue(
                code="missing_feasible_objective",
                message="Feasible benchmark rows must provide a numeric objective value.",
            )
        )

    invalid_solver_name_mask = frame["solver_name"].isna() | (frame["solver_name"].str.strip() == "")
    if invalid_solver_name_mask.any():
        issues.append(
            BenchmarkValidationIssue(
                code="impossible_solver_name",
                message="Benchmark results contain blank or missing solver names.",
            )
        )

    if expected_solver_registry_names is not None:
        allowed_registry_names = {str(name) for name in expected_solver_registry_names}
        unexpected_registry_mask = ~frame["solver_registry_name"].isin(allowed_registry_names)
        if unexpected_registry_mask.any():
            issues.append(
                BenchmarkValidationIssue(
                    code="unexpected_solver_registry_name",
                    message=(
                        "Benchmark results contain solver registry names outside the configured "
                        "benchmark portfolio."
                    ),
                )
            )

    return issues


def ensure_valid_benchmark_results(
    results: pd.DataFrame,
    *,
    expected_solver_registry_names: Collection[str] | None = None,
) -> None:
    """Raise when benchmark results fail validation."""

    issues = validate_benchmark_results(
        results,
        expected_solver_registry_names=expected_solver_registry_names,
    )
    if not issues:
        return

    message = "; ".join(issue.message for issue in issues)
    raise BenchmarkValidationError(message)


def _coerce_bool(value: object) -> bool:
    """Convert CSV-style values into booleans."""

    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False

    normalized = str(value).strip().casefold()
    return normalized in {"true", "1", "yes", "y"}


def _is_invalid_runtime(value: object) -> bool:
    """Return whether the runtime value is missing, non-finite, or negative."""

    if value is None or pd.isna(value):
        return True
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return True
    return (not math.isfinite(numeric_value)) or numeric_value < 0.0
