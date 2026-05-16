# Tests for the refreshed mixed synthetic/real selection dataset builder.

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.selection.build_selection_dataset_full import build_selection_dataset_full
from src.selection.modeling import prepare_selection_data


def test_full_dataset_excludes_unsupported_and_not_configured_solvers_from_targets(
    tmp_path: Path,
) -> None:

    # Unsupported and not-configured rows must not win, even with low objectives.
    paths = _FullDatasetPaths(tmp_path)
    _write_features(
        paths.synthetic_features,
        [
            {"instance_name": "synthetic_supported", "num_teams": 4, "num_slots": 6, "shared": 1},
            {"instance_name": "synthetic_no_target", "num_teams": 6, "num_slots": 10, "shared": 2},
        ],
    )
    _write_features(
        paths.real_features,
        [{"instance_name": "real_supported", "num_teams": 8, "num_slots": 14, "shared": 3}],
    )
    _write_benchmarks(
        paths.synthetic_benchmarks,
        [
            _benchmark_row(
                "synthetic_supported",
                "unsupported_solver",
                objective=1.0,
                feasible=True,
                support="unsupported",
                scoring="unsupported_instance",
                status="UNSUPPORTED_INSTANCE",
            ),
            _benchmark_row(
                "synthetic_supported",
                "supported_solver",
                objective=5.0,
                feasible=True,
                support="supported",
                scoring="supported_feasible_run",
            ),
            _benchmark_row(
                "synthetic_supported",
                "partial_solver",
                objective=4.0,
                feasible=True,
                support="partially_supported",
                scoring="partially_modeled_run",
            ),
            _benchmark_row(
                "synthetic_no_target",
                "timefold",
                objective=0.0,
                feasible=True,
                support="not_configured",
                scoring="not_configured",
                status="NOT_CONFIGURED",
            ),
        ],
    )
    _write_benchmarks(
        paths.real_benchmarks,
        [
            _benchmark_row(
                "real_supported",
                "real_solver",
                objective=4.0,
                feasible=True,
                support="supported",
                scoring="supported_feasible_run",
            )
        ],
    )

    result_path = build_selection_dataset_full(
        synthetic_features_csv=paths.synthetic_features,
        synthetic_benchmark_csv=paths.synthetic_benchmarks,
        real_features_csv=paths.real_features,
        real_benchmark_csv=paths.real_benchmarks,
        output_csv=paths.output,
    )

    result = pd.read_csv(result_path)
    supported_row = result[result["instance_name"] == "synthetic_supported"].iloc[0]
    no_target_row = result[result["instance_name"] == "synthetic_no_target"].iloc[0]

    assert supported_row["best_solver"] == "partial_solver"
    assert int(supported_row["benchmark_unsupported_solver_count"]) == 1
    assert int(supported_row["benchmark_partially_supported_solver_count"]) == 1
    assert int(supported_row["benchmark_eligible_solver_count"]) == 2
    assert supported_row["benchmark_best_solver_scoring_status"] == "partially_modeled_run"
    assert "unsupported=1" in supported_row["benchmark_solver_support_coverage"]
    assert pd.isna(no_target_row["best_solver"])
    assert int(no_target_row["benchmark_not_configured_solver_count"]) == 1
    assert "objective_unsupported_solver" not in result.columns
    assert "objective_timefold" not in result.columns
    assert "objective_partial_solver" in result.columns
    assert paths.output.with_name("selection_dataset_full_run_summary.json").exists()

    prepared = prepare_selection_data(result)
    assert "dataset_type" not in prepared.feature_columns
    assert "benchmark_solver_support_coverage" not in prepared.feature_columns
    assert "objective_supported_solver" not in prepared.feature_columns


def test_full_dataset_tie_resolution_is_deterministic_after_seed_aggregation(
    tmp_path: Path,
) -> None:

    # Best-solver ties should use mean objective, mean runtime, then solver name.
    paths = _FullDatasetPaths(tmp_path)
    _write_features(
        paths.synthetic_features,
        [
            {"instance_name": "runtime_tie", "num_teams": 4, "num_slots": 6, "shared": 1},
            {"instance_name": "name_tie", "num_teams": 4, "num_slots": 6, "shared": 2},
        ],
    )
    _write_features(
        paths.real_features,
        [{"instance_name": "real_anchor", "num_teams": 8, "num_slots": 14, "shared": 3}],
    )
    _write_benchmarks(
        paths.synthetic_benchmarks,
        [
            _benchmark_row("runtime_tie", "solver_a", objective=5.0, runtime=3.0, seed=1),
            _benchmark_row("runtime_tie", "solver_a", objective=5.0, runtime=1.0, seed=2),
            _benchmark_row("runtime_tie", "solver_b", objective=5.0, runtime=1.0, seed=1),
            _benchmark_row("runtime_tie", "solver_b", objective=5.0, runtime=1.0, seed=2),
            _benchmark_row("name_tie", "solver_b", objective=2.0, runtime=1.0, seed=1),
            _benchmark_row("name_tie", "solver_a", objective=2.0, runtime=1.0, seed=1),
        ],
    )
    _write_benchmarks(
        paths.real_benchmarks,
        [_benchmark_row("real_anchor", "real_solver", objective=3.0)],
    )

    result_path = build_selection_dataset_full(
        synthetic_features_csv=paths.synthetic_features,
        synthetic_benchmark_csv=paths.synthetic_benchmarks,
        real_features_csv=paths.real_features,
        real_benchmark_csv=paths.real_benchmarks,
        output_csv=paths.output,
    )

    result = pd.read_csv(result_path)
    runtime_row = result[result["instance_name"] == "runtime_tie"].iloc[0]
    name_row = result[result["instance_name"] == "name_tie"].iloc[0]

    assert runtime_row["best_solver"] == "solver_b"
    assert float(runtime_row["benchmark_best_solver_mean_objective"]) == 5.0
    assert float(runtime_row["benchmark_best_solver_mean_runtime_seconds"]) == 1.0
    assert int(runtime_row["benchmark_best_solver_num_runs"]) == 2
    assert name_row["best_solver"] == "solver_a"
    assert set(result["dataset_type"]) == {"synthetic", "real"}


class _FullDatasetPaths:

    # Convenience paths for one full-dataset test.
    def __init__(self, root: Path) -> None:
        self.synthetic_features = root / "synthetic_features.csv"
        self.synthetic_benchmarks = root / "synthetic_benchmarks.csv"
        self.real_features = root / "real_features.csv"
        self.real_benchmarks = root / "real_benchmarks.csv"
        self.output = root / "selection_dataset_full.csv"


def _write_features(path: Path, rows: list[dict[str, object]]) -> None:

    # Write feature rows to CSV.
    pd.DataFrame(rows).to_csv(path, index=False)


def _write_benchmarks(path: Path, rows: list[dict[str, object]]) -> None:

    # Write benchmark rows to CSV.
    pd.DataFrame(rows).to_csv(path, index=False)


def _benchmark_row(
    instance_name: str,
    solver_name: str,
    *,
    objective: float | None,
    runtime: float = 1.0,
    feasible: bool = True,
    support: str = "supported",
    scoring: str = "supported_feasible_run",
    status: str = "FEASIBLE",
    seed: int = 42,
) -> dict[str, object]:

    # Build one benchmark row with scoring-contract columns.
    return {
        "instance_name": instance_name,
        "solver_name": f"{solver_name}_display",
        "solver_registry_name": solver_name,
        "objective_value": objective,
        "objective_value_valid": feasible and objective is not None and scoring == "supported_feasible_run",
        "runtime_seconds": runtime,
        "feasible": feasible,
        "status": status,
        "solver_support_status": support,
        "scoring_status": scoring,
        "random_seed": seed,
    }
