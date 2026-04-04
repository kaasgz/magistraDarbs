"""Build an algorithm selection dataset from features and benchmark results.

This module merges one-row-per-instance structural features with solver
benchmark outcomes to produce a training-ready selection dataset.

Tie-breaking rule for ``best_solver`` in version 1:

1. Lower ``objective_value`` is better.
2. If objective values tie, lower ``runtime_seconds`` is better.
3. If both still tie, lexicographically smaller ``solver_name`` wins.

Only feasible runs with numeric objective values are eligible for the
``best_solver`` target. Instances without an eligible solver keep a missing
target value.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.experiments.metrics import best_solver_per_instance
from src.utils import (
    default_run_summary_path,
    ensure_parent_directory,
    get_compat_path,
    get_include_solver_objectives,
    load_yaml_config,
    write_run_summary,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("configs/selector_config.yaml")
DEFAULT_FEATURES_PATH = Path("data/processed/features.csv")
DEFAULT_BENCHMARKS_PATH = Path("data/results/benchmark_results.csv")
DEFAULT_OUTPUT_PATH = Path("data/processed/selection_dataset.csv")
REQUIRED_BENCHMARK_COLUMNS = {
    "instance_name",
    "solver_name",
    "objective_value",
    "runtime_seconds",
    "feasible",
    "status",
}


def build_selection_dataset(
    features_csv: str | Path = DEFAULT_FEATURES_PATH,
    benchmark_csv: str | Path = DEFAULT_BENCHMARKS_PATH,
    output_csv: str | Path = DEFAULT_OUTPUT_PATH,
    include_solver_objectives: bool = True,
    *,
    config_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    run_summary_path: str | Path | None = None,
) -> Path:
    """Merge features and benchmark results into one selection dataset.

    Args:
        features_csv: Path to ``data/processed/features.csv`` style data.
        benchmark_csv: Path to ``data/results/benchmark_results.csv`` style data.
        output_csv: Output CSV path.
        include_solver_objectives: Whether to append one objective column per
            solver using names like ``objective_<solver_name>``.
        config_path: Optional YAML config path used for the run.
        config: Optional loaded config snapshot to include in metadata.
        run_summary_path: Optional JSON sidecar path for run metadata.

    Returns:
        Path to the written selection dataset CSV.
    """

    features_path = Path(features_csv)
    benchmarks_path = Path(benchmark_csv)
    output_path = Path(output_csv)

    features = pd.read_csv(features_path)
    benchmarks = pd.read_csv(benchmarks_path)

    _validate_features_frame(features)
    LOGGER.info(
        "Loaded %d feature rows and %d benchmark rows.",
        len(features.index),
        len(benchmarks.index),
    )

    target_frame = _build_target_frame(benchmarks)
    selection_dataset = features.merge(target_frame, on="instance_name", how="left")
    target_summary = _summarize_target_assignment(benchmarks)

    objective_columns: list[str] = []
    if include_solver_objectives:
        objective_frame = _build_solver_objective_frame(benchmarks)
        objective_columns = [column for column in objective_frame.columns if column != "instance_name"]
        selection_dataset = selection_dataset.merge(objective_frame, on="instance_name", how="left")

    feature_columns = [column for column in features.columns if column != "instance_name"]
    ordered_columns = ["instance_name", *feature_columns, "best_solver", *objective_columns]
    selection_dataset = selection_dataset.loc[:, ordered_columns]

    missing_targets = int(selection_dataset["best_solver"].isna().sum())
    if missing_targets > 0:
        LOGGER.warning(
            "%d instances do not have an eligible best_solver target.",
            missing_targets,
        )

    ensure_parent_directory(output_path)
    selection_dataset.to_csv(output_path, index=False)
    summary_path = Path(run_summary_path) if run_summary_path is not None else default_run_summary_path(output_path)
    write_run_summary(
        summary_path,
        stage_name="selection_dataset_build",
        config_path=config_path,
        config=config,
        settings={
            "include_solver_objectives": include_solver_objectives,
        },
        inputs={
            "features_csv": features_path,
            "benchmark_results_csv": benchmarks_path,
        },
        outputs={
            "selection_dataset_csv": output_path,
            "run_summary": summary_path,
        },
        results={
            "num_feature_rows": len(features.index),
            "num_benchmark_rows": len(benchmarks.index),
            "num_selection_rows": len(selection_dataset.index),
            "num_labeled_instances": int(selection_dataset["best_solver"].notna().sum()),
            "num_missing_targets": missing_targets,
            "target_summary": target_summary,
        },
    )
    LOGGER.info(
        "Saved %d selection dataset rows to %s",
        len(selection_dataset.index),
        output_path,
    )
    LOGGER.info("Saved selection-dataset run summary to %s", summary_path)
    return output_path


def build_selection_dataset_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> Path:
    """Build the selection dataset using values from a YAML configuration file."""

    config = load_yaml_config(config_path)
    output_path = get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_OUTPUT_PATH)
    summary_path = get_compat_path(
        config,
        ["paths.selection_dataset_run_summary", "paths.run_summary", "paths.run_summary_path"],
        default_run_summary_path(output_path),
    )
    return build_selection_dataset(
        features_csv=get_compat_path(config, ["paths.features_csv"], DEFAULT_FEATURES_PATH),
        benchmark_csv=get_compat_path(config, ["paths.benchmark_results_csv"], DEFAULT_BENCHMARKS_PATH),
        output_csv=output_path,
        include_solver_objectives=get_include_solver_objectives(config, True),
        config_path=config_path,
        config=config,
        run_summary_path=summary_path,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for selection dataset generation."""

    parser = argparse.ArgumentParser(
        description="Merge features and benchmark results into a selection dataset.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the selector YAML configuration file.",
    )
    parser.add_argument(
        "--features",
        default=None,
        help="Path to the features CSV. Defaults to data/processed/features.csv.",
    )
    parser.add_argument(
        "--benchmarks",
        default=None,
        help="Path to the benchmark results CSV. Defaults to data/results/benchmark_results.csv.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path. Defaults to data/processed/selection_dataset.csv.",
    )
    parser.add_argument(
        "--no-solver-objectives",
        action="store_true",
        help="Do not include per-solver objective columns.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run selection dataset generation from the command line."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = load_yaml_config(args.config)
        resolved_output_path = args.output or get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_OUTPUT_PATH)
        output_path = build_selection_dataset(
            features_csv=args.features or get_compat_path(config, ["paths.features_csv"], DEFAULT_FEATURES_PATH),
            benchmark_csv=args.benchmarks
            or get_compat_path(config, ["paths.benchmark_results_csv"], DEFAULT_BENCHMARKS_PATH),
            output_csv=resolved_output_path,
            include_solver_objectives=(
                not args.no_solver_objectives
                if args.no_solver_objectives
                else get_include_solver_objectives(config, True)
            ),
            config_path=args.config,
            config=config,
            run_summary_path=get_compat_path(
                config,
                ["paths.selection_dataset_run_summary", "paths.run_summary", "paths.run_summary_path"],
                default_run_summary_path(resolved_output_path),
            ),
        )
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError) as exc:
        print(f"Failed to build selection dataset: {exc}", file=sys.stderr)
        return 1

    print(f"Selection dataset saved to {output_path}")
    return 0


def _build_target_frame(benchmarks: pd.DataFrame) -> pd.DataFrame:
    """Extract the per-instance best solver target from benchmark results."""

    best_rows = best_solver_per_instance(benchmarks).rename(columns={"solver_name": "best_solver"})
    return best_rows.loc[:, ["instance_name", "best_solver"]]


def _build_solver_objective_frame(benchmarks: pd.DataFrame) -> pd.DataFrame:
    """Create one objective column per solver.

    If duplicate rows appear for the same instance and solver, the row chosen is
    deterministic after sorting by:

    1. ``objective_value`` ascending with missing values last.
    2. ``runtime_seconds`` ascending with missing values last.
    3. ``status`` ascending.
    """

    frame = _prepare_benchmark_frame(benchmarks)
    if frame.empty:
        return pd.DataFrame(columns=["instance_name"])

    deduplicated = (
        frame.sort_values(
            by=["instance_name", "solver_name", "objective_value", "runtime_seconds", "status"],
            ascending=[True, True, True, True, True],
            na_position="last",
            kind="mergesort",
        )
        .drop_duplicates(subset=["instance_name", "solver_name"], keep="first")
        .copy()
    )
    deduplicated["objective_column"] = deduplicated["solver_name"].map(lambda value: f"objective_{value}")

    pivoted = (
        deduplicated.pivot(index="instance_name", columns="objective_column", values="objective_value")
        .reset_index()
    )
    objective_columns = sorted(column for column in pivoted.columns if column != "instance_name")
    return pivoted.loc[:, ["instance_name", *objective_columns]]


def _prepare_benchmark_frame(benchmarks: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize a benchmark table for dataset construction."""

    missing_columns = sorted(REQUIRED_BENCHMARK_COLUMNS.difference(benchmarks.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Benchmark results are missing required columns: {missing}")

    frame = benchmarks.copy()
    frame["instance_name"] = frame["instance_name"].astype("string")
    frame["solver_name"] = frame["solver_name"].astype("string")
    frame["status"] = frame["status"].astype("string")
    frame["objective_value"] = pd.to_numeric(frame["objective_value"], errors="coerce")
    frame["runtime_seconds"] = pd.to_numeric(frame["runtime_seconds"], errors="coerce")
    return frame


def _validate_features_frame(features: pd.DataFrame) -> None:
    """Validate that the feature table has the expected one-row-per-instance structure."""

    if "instance_name" not in features.columns:
        raise ValueError("Feature table must contain an 'instance_name' column.")
    if features["instance_name"].duplicated().any():
        raise ValueError("Feature table must contain unique instance_name values.")


def _summarize_target_assignment(benchmarks: pd.DataFrame) -> dict[str, int]:
    """Summarize target coverage and tie-breaking for auditability."""

    frame = _prepare_benchmark_frame(benchmarks)
    eligible = frame[frame["feasible"] & frame["objective_value"].notna()].copy()
    if frame.empty:
        return {
            "num_instances": 0,
            "num_instances_with_eligible_solver": 0,
            "num_instances_without_eligible_solver": 0,
            "num_instances_with_objective_ties": 0,
            "num_instances_with_runtime_ties_after_objective": 0,
        }

    all_instances = int(frame["instance_name"].nunique())
    if eligible.empty:
        return {
            "num_instances": all_instances,
            "num_instances_with_eligible_solver": 0,
            "num_instances_without_eligible_solver": all_instances,
            "num_instances_with_objective_ties": 0,
            "num_instances_with_runtime_ties_after_objective": 0,
        }

    objective_ties = 0
    runtime_ties = 0
    for _, instance_rows in eligible.groupby("instance_name", sort=True):
        min_objective = float(instance_rows["objective_value"].min())
        objective_rows = instance_rows[instance_rows["objective_value"] == min_objective]
        if len(objective_rows.index) > 1:
            objective_ties += 1
        min_runtime = float(objective_rows["runtime_seconds"].min())
        runtime_rows = objective_rows[objective_rows["runtime_seconds"] == min_runtime]
        if len(runtime_rows.index) > 1:
            runtime_ties += 1

    eligible_instances = int(eligible["instance_name"].nunique())
    return {
        "num_instances": all_instances,
        "num_instances_with_eligible_solver": eligible_instances,
        "num_instances_without_eligible_solver": all_instances - eligible_instances,
        "num_instances_with_objective_ties": objective_ties,
        "num_instances_with_runtime_ties_after_objective": runtime_ties,
    }


if __name__ == "__main__":
    raise SystemExit(main())
