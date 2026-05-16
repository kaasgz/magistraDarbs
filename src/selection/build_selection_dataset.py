# Build an algorithm selection dataset from features and benchmark results.
#
# This module merges one-row-per-instance structural features with solver
# benchmark outcomes to produce a training-ready selection dataset.
#
# Tie-breaking rule for ``best_solver`` in version 1:
#
# 1. Lower ``objective_value`` is better.
# 2. If objective values tie, lower ``runtime_seconds`` is better.
# 3. If both still tie, lexicographically smaller ``solver_name`` wins.
#
# Only feasible runs with numeric objective values are eligible for the
# ``best_solver`` target. Instances without an eligible solver keep a missing
# target value.

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.experiments.metrics import best_solver_per_instance
from src.selection.build_selection_dataset_full import (
    build_selection_dataset_full as build_refreshed_selection_dataset_full,
)
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
DEFAULT_SYNTHETIC_FEATURES_PATH = Path("data/processed/synthetic_study/features.csv")
DEFAULT_SYNTHETIC_BENCHMARKS_PATH = Path("data/results/synthetic_study/benchmark_results.csv")
DEFAULT_REAL_FEATURES_PATH = Path("data/processed/real_pipeline_current/features.csv")
DEFAULT_REAL_BENCHMARKS_PATH = Path("data/results/real_pipeline_current/benchmark_results.csv")
DEFAULT_FULL_OUTPUT_PATH = Path("data/processed/selection_dataset_full.csv")
REQUIRED_BENCHMARK_COLUMNS = {
    "instance_name",
    "solver_name",
    "objective_value",
    "runtime_seconds",
    "feasible",
    "status",
}
DATASET_TYPES = ("synthetic", "real")


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

    # Merge features and benchmark results into one selection dataset.
    #
    # Args:
    # features_csv: Path to ``data/processed/features.csv`` style data.
    # benchmark_csv: Path to ``data/results/benchmark_results.csv`` style data.
    # output_csv: Output CSV path.
    # include_solver_objectives: Whether to append one objective column per
    # solver using names like ``objective_<solver_name>``.
    # config_path: Optional YAML config path used for the run.
    # config: Optional loaded config snapshot to include in metadata.
    # run_summary_path: Optional JSON sidecar path for run metadata.
    #
    # Returns:
    # Path to the written selection dataset CSV.
    #
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


def build_full_selection_dataset(
    synthetic_features_csv: str | Path = DEFAULT_SYNTHETIC_FEATURES_PATH,
    synthetic_benchmark_csv: str | Path = DEFAULT_SYNTHETIC_BENCHMARKS_PATH,
    real_features_csv: str | Path = DEFAULT_REAL_FEATURES_PATH,
    real_benchmark_csv: str | Path = DEFAULT_REAL_BENCHMARKS_PATH,
    output_csv: str | Path = DEFAULT_FULL_OUTPUT_PATH,
    include_solver_objectives: bool = True,
    *,
    config_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    run_summary_path: str | Path | None = None,
) -> Path:

    # Build one full algorithm-selection dataset from synthetic and real results.
    #
    # The returned dataset keeps one row per source instance and adds
    # ``dataset_type`` with values ``synthetic`` or ``real``. Feature columns are
    # restricted to the schema shared by both sources so selector training sees a
    # consistent feature space.
    #
    output_path = Path(output_csv)
    source_inputs = {
        "synthetic": {
            "features_csv": Path(synthetic_features_csv),
            "benchmark_csv": Path(synthetic_benchmark_csv),
        },
        "real": {
            "features_csv": Path(real_features_csv),
            "benchmark_csv": Path(real_benchmark_csv),
        },
    }

    feature_frames: dict[str, pd.DataFrame] = {}
    benchmark_frames: dict[str, pd.DataFrame] = {}
    for dataset_type, paths in source_inputs.items():
        features = pd.read_csv(paths["features_csv"])
        benchmarks = pd.read_csv(paths["benchmark_csv"])
        _validate_features_frame(features)

        feature_frames[dataset_type] = features
        benchmark_frames[dataset_type] = _prepare_full_benchmark_frame(benchmarks)
        LOGGER.info(
            "Loaded %d %s feature rows and %d %s benchmark rows.",
            len(features.index),
            dataset_type,
            len(benchmarks.index),
            dataset_type,
        )

    feature_columns = _common_feature_columns(feature_frames)
    if not feature_columns:
        raise ValueError("Synthetic and real feature tables do not share any usable feature columns.")

    source_datasets: list[pd.DataFrame] = []
    objective_columns: set[str] = set()
    target_summary_by_source: dict[str, dict[str, int]] = {}
    unsupported_summary_by_source: dict[str, int] = {}
    solver_names_by_source: dict[str, list[str]] = {}

    for dataset_type in DATASET_TYPES:
        features = feature_frames[dataset_type]
        benchmarks = benchmark_frames[dataset_type]
        source_features = features.loc[:, ["instance_name", *feature_columns]].copy()
        source_features.insert(1, "dataset_type", dataset_type)

        source_dataset = source_features.merge(
            _build_target_frame(benchmarks),
            on="instance_name",
            how="left",
        )
        if include_solver_objectives:
            objective_frame = _build_solver_objective_frame(benchmarks)
            new_objective_columns = [column for column in objective_frame.columns if column != "instance_name"]
            objective_columns.update(new_objective_columns)
            source_dataset = source_dataset.merge(objective_frame, on="instance_name", how="left")

        source_datasets.append(source_dataset)
        target_summary_by_source[dataset_type] = _summarize_target_assignment(benchmarks)
        unsupported_summary_by_source[dataset_type] = _count_unsupported_or_not_configured_rows(benchmarks)
        solver_names_by_source[dataset_type] = sorted(
            benchmarks["solver_name"].dropna().astype(str).unique().tolist()
        )

    selection_dataset = pd.concat(source_datasets, ignore_index=True, sort=False)
    ordered_objective_columns = sorted(objective_columns)
    for column in ordered_objective_columns:
        if column not in selection_dataset.columns:
            selection_dataset[column] = pd.NA

    ordered_columns = [
        "instance_name",
        "dataset_type",
        *feature_columns,
        "best_solver",
        *ordered_objective_columns,
    ]
    selection_dataset = (
        selection_dataset.loc[:, ordered_columns]
        .sort_values(by=["dataset_type", "instance_name"], ascending=[True, True], kind="mergesort")
        .reset_index(drop=True)
    )

    missing_targets = int(selection_dataset["best_solver"].isna().sum())
    if missing_targets > 0:
        LOGGER.warning(
            "%d full selection dataset rows do not have an eligible best_solver target.",
            missing_targets,
        )

    ensure_parent_directory(output_path)
    selection_dataset.to_csv(output_path, index=False)
    summary_path = Path(run_summary_path) if run_summary_path is not None else default_run_summary_path(output_path)
    write_run_summary(
        summary_path,
        stage_name="full_selection_dataset_build",
        config_path=config_path,
        config=config,
        settings={
            "include_solver_objectives": include_solver_objectives,
            "dataset_types": list(DATASET_TYPES),
            "feature_schema_policy": "intersection_of_synthetic_and_real_features",
            "solver_name_policy": "solver_registry_name_when_available_else_solver_name",
        },
        inputs={
            "synthetic_features_csv": source_inputs["synthetic"]["features_csv"],
            "synthetic_benchmark_results_csv": source_inputs["synthetic"]["benchmark_csv"],
            "real_features_csv": source_inputs["real"]["features_csv"],
            "real_benchmark_results_csv": source_inputs["real"]["benchmark_csv"],
        },
        outputs={
            "selection_dataset_full_csv": output_path,
            "run_summary": summary_path,
        },
        results={
            "num_selection_rows": len(selection_dataset.index),
            "num_labeled_instances": int(selection_dataset["best_solver"].notna().sum()),
            "num_missing_targets": missing_targets,
            "rows_by_dataset_type": {
                dataset_type: int((selection_dataset["dataset_type"] == dataset_type).sum())
                for dataset_type in DATASET_TYPES
            },
            "target_summary_by_source": target_summary_by_source,
            "unsupported_or_not_configured_rows_by_source": unsupported_summary_by_source,
            "solver_names_by_source": solver_names_by_source,
            "feature_schema": _summarize_feature_schema(feature_frames, feature_columns),
        },
    )
    LOGGER.info(
        "Saved %d full selection dataset rows to %s",
        len(selection_dataset.index),
        output_path,
    )
    LOGGER.info("Saved full selection-dataset run summary to %s", summary_path)
    return output_path


def build_selection_dataset_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> Path:

    # Build the selection dataset using values from a YAML configuration file.
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

    # Create the command-line parser for selection dataset generation.
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
    parser.add_argument(
        "--full",
        action="store_true",
        help="Build data/processed/selection_dataset_full.csv from synthetic and real artifacts.",
    )
    parser.add_argument(
        "--synthetic-features",
        default=None,
        help="Synthetic feature table for --full mode.",
    )
    parser.add_argument(
        "--synthetic-benchmarks",
        default=None,
        help="Synthetic benchmark results for --full mode.",
    )
    parser.add_argument(
        "--real-features",
        default=None,
        help="Real feature table for --full mode.",
    )
    parser.add_argument(
        "--real-benchmarks",
        default=None,
        help="Real benchmark results for --full mode.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:

    # Run selection dataset generation from the command line.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = load_yaml_config(args.config)
        include_solver_objectives = False if args.no_solver_objectives else get_include_solver_objectives(config, True)
        if args.full:
            resolved_output_path = args.output or get_compat_path(
                config,
                ["paths.full_selection_dataset_csv"],
                DEFAULT_FULL_OUTPUT_PATH,
            )
            output_path = build_refreshed_selection_dataset_full(
                synthetic_features_csv=args.synthetic_features
                or get_compat_path(config, ["paths.synthetic_features_csv"], DEFAULT_SYNTHETIC_FEATURES_PATH),
                synthetic_benchmark_csv=args.synthetic_benchmarks
                or get_compat_path(
                    config,
                    ["paths.synthetic_benchmark_results_csv"],
                    DEFAULT_SYNTHETIC_BENCHMARKS_PATH,
                ),
                real_features_csv=args.real_features
                or get_compat_path(config, ["paths.real_features_csv", "paths.features_csv"], DEFAULT_REAL_FEATURES_PATH),
                real_benchmark_csv=args.real_benchmarks
                or get_compat_path(
                    config,
                    ["paths.real_benchmark_results_csv", "paths.benchmark_results_csv"],
                    DEFAULT_REAL_BENCHMARKS_PATH,
                ),
                output_csv=resolved_output_path,
                include_solver_objectives=include_solver_objectives,
                run_summary_path=get_compat_path(
                    config,
                    ["paths.full_selection_dataset_run_summary"],
                    default_run_summary_path(resolved_output_path),
                ),
            )
        else:
            resolved_output_path = args.output or get_compat_path(
                config,
                ["paths.selection_dataset_csv"],
                DEFAULT_OUTPUT_PATH,
            )
            output_path = build_selection_dataset(
                features_csv=args.features or get_compat_path(config, ["paths.features_csv"], DEFAULT_FEATURES_PATH),
                benchmark_csv=args.benchmarks
                or get_compat_path(config, ["paths.benchmark_results_csv"], DEFAULT_BENCHMARKS_PATH),
                output_csv=resolved_output_path,
                include_solver_objectives=include_solver_objectives,
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

    # Extract the per-instance best solver target from benchmark results.
    best_rows = best_solver_per_instance(benchmarks).rename(columns={"solver_name": "best_solver"})
    return best_rows.loc[:, ["instance_name", "best_solver"]]


def _build_solver_objective_frame(benchmarks: pd.DataFrame) -> pd.DataFrame:

    # Create one objective column per solver.
    #
    # If duplicate rows appear for the same instance and solver, the row chosen is
    # deterministic after sorting by:
    #
    # 1. ``objective_value`` ascending with missing values last.
    # 2. ``runtime_seconds`` ascending with missing values last.
    # 3. ``status`` ascending.
    #
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

    # Validate and normalize a benchmark table for dataset construction.
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
    frame["feasible"] = frame["feasible"].map(_coerce_feasible).astype(bool)
    return frame


def _prepare_full_benchmark_frame(benchmarks: pd.DataFrame) -> pd.DataFrame:

    # Normalize a benchmark table and use stable registry-level solver names.
    frame = _prepare_benchmark_frame(benchmarks)
    if "solver_registry_name" not in frame.columns:
        return frame

    registry_names = frame["solver_registry_name"].astype("string").str.strip()
    registry_names = registry_names.mask(registry_names == "", pd.NA)
    frame["solver_name"] = registry_names.fillna(frame["solver_name"]).astype("string")
    return frame


def _validate_features_frame(features: pd.DataFrame) -> None:

    # Validate that the feature table has the expected one-row-per-instance structure.
    if "instance_name" not in features.columns:
        raise ValueError("Feature table must contain an 'instance_name' column.")
    if features["instance_name"].duplicated().any():
        raise ValueError("Feature table must contain unique instance_name values.")


def _common_feature_columns(feature_frames: dict[str, pd.DataFrame]) -> list[str]:

    # Return feature columns shared by every dataset source.
    source_columns = {
        dataset_type: {
            column
            for column in frame.columns
            if column not in {"instance_name", "dataset_type"}
        }
        for dataset_type, frame in feature_frames.items()
    }
    common_columns = set.intersection(*(columns for columns in source_columns.values()))
    reference_type = next(dataset_type for dataset_type in DATASET_TYPES if dataset_type in feature_frames)
    return [
        column
        for column in feature_frames[reference_type].columns
        if column in common_columns and column not in {"instance_name", "dataset_type"}
    ]


def _summarize_feature_schema(
    feature_frames: dict[str, pd.DataFrame],
    common_feature_columns: list[str],
) -> dict[str, Any]:

    # Summarize how synthetic and real feature schemas were aligned.
    common = set(common_feature_columns)
    source_columns = {
        dataset_type: {
            column
            for column in frame.columns
            if column not in {"instance_name", "dataset_type"}
        }
        for dataset_type, frame in feature_frames.items()
    }
    all_columns = set().union(*source_columns.values()) if source_columns else set()
    return {
        "policy": "intersection_of_synthetic_and_real_features",
        "common_feature_column_count": len(common_feature_columns),
        "common_feature_columns": list(common_feature_columns),
        "source_specific_columns_dropped": {
            dataset_type: sorted(columns - common)
            for dataset_type, columns in source_columns.items()
        },
        "columns_missing_from_source": {
            dataset_type: sorted(all_columns - columns)
            for dataset_type, columns in source_columns.items()
        },
    }


def _count_unsupported_or_not_configured_rows(benchmarks: pd.DataFrame) -> int:

    # Count benchmark rows that should not be eligible because the solver did not run.
    if benchmarks.empty:
        return 0

    support_status = (
        benchmarks["solver_support_status"].astype("string")
        if "solver_support_status" in benchmarks.columns
        else pd.Series([""] * len(benchmarks.index), index=benchmarks.index, dtype="string")
    )
    status = (
        benchmarks["status"].astype("string")
        if "status" in benchmarks.columns
        else pd.Series([""] * len(benchmarks.index), index=benchmarks.index, dtype="string")
    )
    combined = (support_status.fillna("") + " " + status.fillna("")).str.strip().str.casefold()
    return int(combined.str.contains("not_configured|not configured|unsupported", regex=True).sum())


def _coerce_feasible(value: object) -> bool:

    # Normalize CSV-style feasibility values.
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def _summarize_target_assignment(benchmarks: pd.DataFrame) -> dict[str, int]:

    # Summarize target coverage and tie-breaking for auditability.
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
