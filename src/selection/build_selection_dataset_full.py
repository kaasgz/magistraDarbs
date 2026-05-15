"""Build the refreshed mixed synthetic/real algorithm-selection dataset.

This module is intentionally separate from the older ``--full`` mode in
``build_selection_dataset.py`` because the refreshed thesis workflow uses the
current real-data rerun artifacts and the larger synthetic-study artifacts.
The builder keeps the same selection-dataset style: one feature row becomes one
selection row, lower objectives are better, and ties are deterministic.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils import default_run_summary_path, ensure_parent_directory, write_run_summary


LOGGER = logging.getLogger(__name__)

DEFAULT_SYNTHETIC_FEATURES_CSV = Path("data/processed/synthetic_study/features.csv")
DEFAULT_SYNTHETIC_BENCHMARK_CSV = Path("data/results/synthetic_study/benchmark_results.csv")
DEFAULT_REAL_FEATURES_CSV = Path("data/processed/real_pipeline_current/features.csv")
DEFAULT_REAL_BENCHMARK_CSV = Path("data/results/real_pipeline_current/benchmark_results.csv")
DEFAULT_OUTPUT_CSV = Path("data/processed/selection_dataset_full.csv")
DEFAULT_NOTES_MARKDOWN = Path("docs/selection_dataset_full_notes.md")
DATASET_TYPES = ("synthetic", "real")

REQUIRED_BENCHMARK_COLUMNS = {
    "instance_name",
    "solver_name",
    "objective_value",
    "runtime_seconds",
    "feasible",
    "status",
}

BAD_SUPPORT_STATUSES = {"unsupported", "not_configured", "failed"}
BAD_SCORING_STATUSES = {"unsupported_instance", "not_configured", "failed_run"}
BAD_STATUS_MARKERS = (
    "unsupported",
    "not_configured",
    "not configured",
    "failed",
    "execution_error",
    "invalid_output",
    "invalid_solution",
    "timeout",
)
PARTIAL_SUPPORT_STATUSES = {"partially_supported", "simplified_baseline"}


@dataclass(frozen=True, slots=True)
class FullSelectionDatasetSources:
    """Input artifacts for one refreshed mixed selection-dataset build."""

    synthetic_features_csv: Path
    synthetic_benchmark_csv: Path
    real_features_csv: Path
    real_benchmark_csv: Path


@dataclass(frozen=True, slots=True)
class SourceBuildResult:
    """Intermediate dataset pieces for one source."""

    dataset_type: str
    dataset: pd.DataFrame
    objective_columns: tuple[str, ...]
    summary: dict[str, object]


def build_selection_dataset_full(
    *,
    synthetic_features_csv: str | Path = DEFAULT_SYNTHETIC_FEATURES_CSV,
    synthetic_benchmark_csv: str | Path = DEFAULT_SYNTHETIC_BENCHMARK_CSV,
    real_features_csv: str | Path = DEFAULT_REAL_FEATURES_CSV,
    real_benchmark_csv: str | Path = DEFAULT_REAL_BENCHMARK_CSV,
    output_csv: str | Path = DEFAULT_OUTPUT_CSV,
    include_solver_objectives: bool = True,
    run_summary_path: str | Path | None = None,
) -> Path:
    """Build ``selection_dataset_full.csv`` from refreshed real and synthetic outputs."""

    sources = FullSelectionDatasetSources(
        synthetic_features_csv=Path(synthetic_features_csv),
        synthetic_benchmark_csv=Path(synthetic_benchmark_csv),
        real_features_csv=Path(real_features_csv),
        real_benchmark_csv=Path(real_benchmark_csv),
    )
    output_path = Path(output_csv)
    _validate_input_paths(sources)

    feature_frames = {
        "synthetic": pd.read_csv(sources.synthetic_features_csv),
        "real": pd.read_csv(sources.real_features_csv),
    }
    benchmark_frames = {
        "synthetic": pd.read_csv(sources.synthetic_benchmark_csv),
        "real": pd.read_csv(sources.real_benchmark_csv),
    }

    for dataset_type, features in feature_frames.items():
        _validate_features_frame(features, dataset_type=dataset_type)

    feature_columns = _common_feature_columns(feature_frames)
    if not feature_columns:
        raise ValueError("Synthetic and real feature tables do not share any usable feature columns.")

    source_results: list[SourceBuildResult] = []
    objective_columns: set[str] = set()
    for dataset_type in DATASET_TYPES:
        result = _build_source_dataset(
            dataset_type=dataset_type,
            features=feature_frames[dataset_type],
            benchmarks=benchmark_frames[dataset_type],
            feature_columns=feature_columns,
            include_solver_objectives=include_solver_objectives,
        )
        source_results.append(result)
        objective_columns.update(result.objective_columns)
        LOGGER.info(
            "Prepared %d %s rows with %d labeled targets.",
            len(result.dataset.index),
            dataset_type,
            int(result.dataset["best_solver"].notna().sum()),
        )

    selection_dataset = pd.concat(
        [result.dataset for result in source_results],
        ignore_index=True,
        sort=False,
    )
    ordered_objective_columns = sorted(objective_columns)
    for column in ordered_objective_columns:
        if column not in selection_dataset.columns:
            selection_dataset[column] = pd.NA

    benchmark_metadata_columns = [
        "benchmark_solver_support_coverage",
        "benchmark_total_solver_count",
        "benchmark_eligible_solver_count",
        "benchmark_supported_solver_count",
        "benchmark_partially_supported_solver_count",
        "benchmark_unsupported_solver_count",
        "benchmark_not_configured_solver_count",
        "benchmark_failed_solver_count",
        "benchmark_best_solver_support_status",
        "benchmark_best_solver_scoring_status",
        "benchmark_best_solver_mean_objective",
        "benchmark_best_solver_mean_runtime_seconds",
        "benchmark_best_solver_num_runs",
    ]
    ordered_columns = [
        "instance_name",
        "dataset_type",
        *feature_columns,
        "best_solver",
        *benchmark_metadata_columns,
        *ordered_objective_columns,
    ]
    selection_dataset = (
        selection_dataset.loc[:, ordered_columns]
        .sort_values(by=["dataset_type", "instance_name"], ascending=[True, True], kind="mergesort")
        .reset_index(drop=True)
    )

    ensure_parent_directory(output_path)
    selection_dataset.to_csv(output_path, index=False)

    summary_path = Path(run_summary_path) if run_summary_path is not None else default_run_summary_path(output_path)
    _write_summary(
        summary_path=summary_path,
        sources=sources,
        output_csv=output_path,
        include_solver_objectives=include_solver_objectives,
        feature_frames=feature_frames,
        feature_columns=feature_columns,
        selection_dataset=selection_dataset,
        source_results=source_results,
    )

    LOGGER.info("Saved %d mixed selection rows to %s", len(selection_dataset.index), output_path)
    LOGGER.info("Saved full selection-dataset run summary to %s", summary_path)
    return output_path


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for refreshed full selection-dataset construction."""

    parser = argparse.ArgumentParser(
        description="Build data/processed/selection_dataset_full.csv from refreshed synthetic and real artifacts.",
    )
    parser.add_argument(
        "--synthetic-features",
        default=str(DEFAULT_SYNTHETIC_FEATURES_CSV),
        help="Synthetic-study feature table.",
    )
    parser.add_argument(
        "--synthetic-benchmarks",
        default=str(DEFAULT_SYNTHETIC_BENCHMARK_CSV),
        help="Synthetic-study aggregate benchmark results.",
    )
    parser.add_argument(
        "--real-features",
        default=str(DEFAULT_REAL_FEATURES_CSV),
        help="Current real-data feature table.",
    )
    parser.add_argument(
        "--real-benchmarks",
        default=str(DEFAULT_REAL_BENCHMARK_CSV),
        help="Current real-data benchmark results.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Output CSV path.",
    )
    parser.add_argument(
        "--run-summary",
        default=None,
        help="Optional run-summary JSON path.",
    )
    parser.add_argument(
        "--no-solver-objectives",
        action="store_true",
        help="Do not include benchmark-derived objective_<solver> columns.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run refreshed full selection-dataset construction from the command line."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        output_path = build_selection_dataset_full(
            synthetic_features_csv=args.synthetic_features,
            synthetic_benchmark_csv=args.synthetic_benchmarks,
            real_features_csv=args.real_features,
            real_benchmark_csv=args.real_benchmarks,
            output_csv=args.output,
            include_solver_objectives=not args.no_solver_objectives,
            run_summary_path=args.run_summary,
        )
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        print(f"Failed to build refreshed full selection dataset: {exc}", file=sys.stderr)
        return 1

    print(f"Full selection dataset saved to {output_path}")
    return 0


def _build_source_dataset(
    *,
    dataset_type: str,
    features: pd.DataFrame,
    benchmarks: pd.DataFrame,
    feature_columns: list[str],
    include_solver_objectives: bool,
) -> SourceBuildResult:
    """Build one source-specific dataset with target and benchmark metadata."""

    frame = _prepare_benchmark_frame(benchmarks)
    target_frame, target_summary = _build_target_frame(frame)
    coverage_frame = _build_coverage_frame(frame)

    source_dataset = features.loc[:, ["instance_name", *feature_columns]].copy()
    source_dataset.insert(1, "dataset_type", dataset_type)
    source_dataset = source_dataset.merge(target_frame, on="instance_name", how="left")
    source_dataset = source_dataset.merge(coverage_frame, on="instance_name", how="left")

    objective_columns: tuple[str, ...] = ()
    if include_solver_objectives:
        objective_frame = _build_solver_objective_frame(frame)
        objective_columns = tuple(column for column in objective_frame.columns if column != "instance_name")
        source_dataset = source_dataset.merge(objective_frame, on="instance_name", how="left")

    _fill_benchmark_metadata_defaults(source_dataset)
    summary = {
        "dataset_type": dataset_type,
        "num_feature_rows": len(features.index),
        "num_benchmark_rows": len(benchmarks.index),
        "num_selection_rows": len(source_dataset.index),
        "num_labeled_instances": int(source_dataset["best_solver"].notna().sum()),
        "num_missing_targets": int(source_dataset["best_solver"].isna().sum()),
        **target_summary,
    }
    return SourceBuildResult(
        dataset_type=dataset_type,
        dataset=source_dataset,
        objective_columns=objective_columns,
        summary=summary,
    )


def _build_target_frame(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """Return deterministic best-solver labels from target-eligible rows."""

    eligible = frame[frame["target_eligible"]].copy()
    columns = [
        "instance_name",
        "best_solver",
        "benchmark_best_solver_support_status",
        "benchmark_best_solver_scoring_status",
        "benchmark_best_solver_mean_objective",
        "benchmark_best_solver_mean_runtime_seconds",
        "benchmark_best_solver_num_runs",
    ]
    if eligible.empty:
        return pd.DataFrame(columns=columns), _target_summary(frame, pd.DataFrame())

    aggregated = _aggregate_solver_runs(eligible)
    best_rows = (
        aggregated.sort_values(
            by=["instance_name", "mean_objective", "mean_runtime_seconds", "solver_name"],
            ascending=[True, True, True, True],
            na_position="last",
            kind="mergesort",
        )
        .groupby("instance_name", sort=True, as_index=False)
        .head(1)
        .rename(
            columns={
                "solver_name": "best_solver",
                "support_status_summary": "benchmark_best_solver_support_status",
                "scoring_status_summary": "benchmark_best_solver_scoring_status",
                "mean_objective": "benchmark_best_solver_mean_objective",
                "mean_runtime_seconds": "benchmark_best_solver_mean_runtime_seconds",
                "num_runs": "benchmark_best_solver_num_runs",
            }
        )
    )
    return best_rows.loc[:, columns].reset_index(drop=True), _target_summary(frame, aggregated)


def _aggregate_solver_runs(eligible: pd.DataFrame) -> pd.DataFrame:
    """Aggregate repeated seed rows to one candidate per instance and solver."""

    return (
        eligible.groupby(["instance_name", "solver_name"], as_index=False, sort=True)
        .agg(
            mean_objective=("objective_value", "mean"),
            mean_runtime_seconds=("runtime_seconds", "mean"),
            num_runs=("solver_name", "size"),
            support_status_summary=("solver_support_status", _stable_status_summary),
            scoring_status_summary=("scoring_status", _stable_status_summary),
        )
        .reset_index(drop=True)
    )


def _build_solver_objective_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Create objective_<solver> columns from target-eligible solver means."""

    eligible = frame[frame["target_eligible"]].copy()
    if eligible.empty:
        return pd.DataFrame(columns=["instance_name"])

    aggregated = _aggregate_solver_runs(eligible)
    aggregated["objective_column"] = aggregated["solver_name"].map(lambda value: f"objective_{value}")
    pivoted = (
        aggregated.pivot(index="instance_name", columns="objective_column", values="mean_objective")
        .reset_index()
    )
    objective_columns = sorted(column for column in pivoted.columns if column != "instance_name")
    return pivoted.loc[:, ["instance_name", *objective_columns]]


def _build_coverage_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Build one benchmark-coverage row per instance."""

    if frame.empty:
        return pd.DataFrame(columns=_coverage_columns())

    rows: list[dict[str, object]] = []
    for instance_name, instance_rows in frame.groupby("instance_name", sort=True):
        solver_groups = list(instance_rows.groupby("solver_name", sort=True))
        total_solver_count = len(solver_groups)
        eligible_solver_count = sum(bool(group["target_eligible"].any()) for _, group in solver_groups)
        supported_solver_count = sum(_solver_has_support(group, "supported") for _, group in solver_groups)
        partially_supported_solver_count = sum(_solver_has_partial_support(group) for _, group in solver_groups)
        unsupported_solver_count = sum(_solver_has_support(group, "unsupported") for _, group in solver_groups)
        not_configured_solver_count = sum(_solver_has_support(group, "not_configured") for _, group in solver_groups)
        failed_solver_count = sum(_solver_has_failure(group) for _, group in solver_groups)

        rows.append(
            {
                "instance_name": instance_name,
                "benchmark_solver_support_coverage": _format_coverage(
                    eligible_solver_count=eligible_solver_count,
                    total_solver_count=total_solver_count,
                    supported_solver_count=supported_solver_count,
                    partially_supported_solver_count=partially_supported_solver_count,
                    unsupported_solver_count=unsupported_solver_count,
                    not_configured_solver_count=not_configured_solver_count,
                    failed_solver_count=failed_solver_count,
                ),
                "benchmark_total_solver_count": total_solver_count,
                "benchmark_eligible_solver_count": eligible_solver_count,
                "benchmark_supported_solver_count": supported_solver_count,
                "benchmark_partially_supported_solver_count": partially_supported_solver_count,
                "benchmark_unsupported_solver_count": unsupported_solver_count,
                "benchmark_not_configured_solver_count": not_configured_solver_count,
                "benchmark_failed_solver_count": failed_solver_count,
            }
        )
    return pd.DataFrame(rows, columns=_coverage_columns())


def _prepare_benchmark_frame(benchmarks: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize benchmark rows for full-dataset construction."""

    missing_columns = sorted(REQUIRED_BENCHMARK_COLUMNS.difference(benchmarks.columns))
    if missing_columns:
        raise ValueError(f"Benchmark results are missing required columns: {', '.join(missing_columns)}")

    frame = benchmarks.copy()
    frame["instance_name"] = frame["instance_name"].astype("string")
    frame["solver_name"] = _canonical_solver_names(frame)
    frame["status"] = frame["status"].astype("string")
    frame["objective_value"] = pd.to_numeric(frame["objective_value"], errors="coerce")
    frame["runtime_seconds"] = pd.to_numeric(frame["runtime_seconds"], errors="coerce")
    frame["feasible"] = frame["feasible"].map(_coerce_bool).astype(bool)

    if "solver_support_status" not in frame.columns:
        frame["solver_support_status"] = "unknown"
    frame["solver_support_status"] = frame["solver_support_status"].fillna("unknown").astype("string")
    frame["solver_support_status_norm"] = frame["solver_support_status"].map(_normalize_status)

    if "scoring_status" not in frame.columns:
        frame["scoring_status"] = frame.apply(_derive_scoring_status, axis=1)
    frame["scoring_status"] = frame["scoring_status"].fillna("unknown").astype("string")
    frame["scoring_status_norm"] = frame["scoring_status"].map(_normalize_status)
    frame["status_norm"] = frame["status"].map(_normalize_status)

    if "objective_value_valid" in frame.columns:
        frame["objective_value_valid_bool"] = frame["objective_value_valid"].map(_coerce_bool).astype(bool)
    else:
        frame["objective_value_valid_bool"] = frame["feasible"] & frame["objective_value"].notna()

    frame["target_eligible"] = (
        frame["feasible"]
        & frame["objective_value"].notna()
        & ~frame.apply(_is_excluded_solver_outcome, axis=1)
    )
    return frame


def _canonical_solver_names(frame: pd.DataFrame) -> pd.Series:
    """Use registry names when available so labels are consistent across sources."""

    solver_names = frame["solver_name"].astype("string").str.strip()
    if "solver_registry_name" not in frame.columns:
        return solver_names

    registry_names = frame["solver_registry_name"].astype("string").str.strip()
    registry_names = registry_names.mask(registry_names == "", pd.NA)
    return registry_names.fillna(solver_names).astype("string")


def _derive_scoring_status(row: pd.Series) -> str:
    """Derive a conservative scoring status for older benchmark files."""

    support_status = _normalize_status(row.get("solver_support_status"))
    status = _normalize_status(row.get("status"))
    if support_status == "not_configured" or "not_configured" in status:
        return "not_configured"
    if support_status == "unsupported" or "unsupported" in status:
        return "unsupported_instance"
    if "failed" in status:
        return "failed_run"
    if bool(row.get("feasible")) and pd.notna(row.get("objective_value")):
        return "legacy_feasible_run"
    return "legacy_infeasible_run"


def _is_excluded_solver_outcome(row: pd.Series) -> bool:
    """Return whether a solver row is ineligible for target determination."""

    support_status = str(row.get("solver_support_status_norm") or "")
    scoring_status = str(row.get("scoring_status_norm") or "")
    status = str(row.get("status_norm") or "")
    if support_status in BAD_SUPPORT_STATUSES:
        return True
    if scoring_status in BAD_SCORING_STATUSES:
        return True
    return any(marker in status for marker in BAD_STATUS_MARKERS)


def _common_feature_columns(feature_frames: dict[str, pd.DataFrame]) -> list[str]:
    """Return feature columns shared by all source feature tables."""

    source_columns = {
        dataset_type: {
            column
            for column in frame.columns
            if column not in {"instance_name", "dataset_type"}
        }
        for dataset_type, frame in feature_frames.items()
    }
    common = set.intersection(*(columns for columns in source_columns.values()))
    reference = feature_frames["synthetic"]
    return [
        column
        for column in reference.columns
        if column in common and column not in {"instance_name", "dataset_type"}
    ]


def _target_summary(frame: pd.DataFrame, aggregated: pd.DataFrame) -> dict[str, int]:
    """Return target-eligibility and tie-resolution counts."""

    total_instances = int(frame["instance_name"].nunique()) if "instance_name" in frame else 0
    eligible_instances = int(aggregated["instance_name"].nunique()) if not aggregated.empty else 0
    objective_ties = 0
    runtime_ties = 0
    if not aggregated.empty:
        for _, rows in aggregated.groupby("instance_name", sort=True):
            min_objective = float(rows["mean_objective"].min())
            objective_rows = rows[rows["mean_objective"] == min_objective]
            if len(objective_rows.index) > 1:
                objective_ties += 1
            min_runtime = float(objective_rows["mean_runtime_seconds"].min())
            runtime_rows = objective_rows[objective_rows["mean_runtime_seconds"] == min_runtime]
            if len(runtime_rows.index) > 1:
                runtime_ties += 1

    return {
        "num_instances_with_eligible_solver": eligible_instances,
        "num_instances_without_eligible_solver": total_instances - eligible_instances,
        "num_target_eligible_solver_rows": int(frame["target_eligible"].sum()) if "target_eligible" in frame else 0,
        "num_excluded_unsupported_or_not_configured_rows": int(
            frame.apply(_is_excluded_solver_outcome, axis=1).sum()
        )
        if not frame.empty
        else 0,
        "num_instances_with_objective_ties": objective_ties,
        "num_instances_with_runtime_ties_after_objective": runtime_ties,
    }


def _write_summary(
    *,
    summary_path: Path,
    sources: FullSelectionDatasetSources,
    output_csv: Path,
    include_solver_objectives: bool,
    feature_frames: dict[str, pd.DataFrame],
    feature_columns: list[str],
    selection_dataset: pd.DataFrame,
    source_results: list[SourceBuildResult],
) -> None:
    """Write a run-summary JSON sidecar for the mixed dataset."""

    write_run_summary(
        summary_path,
        stage_name="selection_dataset_full_current_build",
        config_path=None,
        config=None,
        settings={
            "include_solver_objectives": include_solver_objectives,
            "dataset_types": list(DATASET_TYPES),
            "feature_schema_policy": "intersection_of_synthetic_and_real_features",
            "target_policy": "feasible_numeric_objective_excluding_unsupported_not_configured_failed",
            "multi_seed_policy": "mean_objective_then_mean_runtime_then_solver_name",
            "notes_markdown": DEFAULT_NOTES_MARKDOWN,
        },
        inputs={
            "synthetic_features_csv": sources.synthetic_features_csv,
            "synthetic_benchmark_csv": sources.synthetic_benchmark_csv,
            "real_features_csv": sources.real_features_csv,
            "real_benchmark_csv": sources.real_benchmark_csv,
        },
        outputs={
            "selection_dataset_full_csv": output_csv,
            "run_summary": summary_path,
            "notes_markdown": DEFAULT_NOTES_MARKDOWN,
        },
        results={
            "num_selection_rows": len(selection_dataset.index),
            "num_labeled_instances": int(selection_dataset["best_solver"].notna().sum()),
            "num_missing_targets": int(selection_dataset["best_solver"].isna().sum()),
            "rows_by_dataset_type": _value_counts(selection_dataset, "dataset_type"),
            "target_summary_by_source": {
                result.dataset_type: result.summary for result in source_results
            },
            "feature_schema": _feature_schema_summary(feature_frames, feature_columns),
        },
    )


def _feature_schema_summary(
    feature_frames: dict[str, pd.DataFrame],
    common_feature_columns: list[str],
) -> dict[str, object]:
    """Summarize how source feature schemas were aligned."""

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


def _validate_input_paths(sources: FullSelectionDatasetSources) -> None:
    """Fail fast when required refreshed artifacts are missing."""

    for path in (
        sources.synthetic_features_csv,
        sources.synthetic_benchmark_csv,
        sources.real_features_csv,
        sources.real_benchmark_csv,
    ):
        if not path.exists():
            raise FileNotFoundError(f"Required full-dataset input does not exist: {path}")
        if not path.is_file():
            raise ValueError(f"Required full-dataset input is not a file: {path}")


def _validate_features_frame(features: pd.DataFrame, *, dataset_type: str) -> None:
    """Validate one feature table."""

    if "instance_name" not in features.columns:
        raise ValueError(f"{dataset_type} features are missing the instance_name column.")
    if features["instance_name"].duplicated().any():
        raise ValueError(f"{dataset_type} features must contain unique instance_name values.")
    if features.empty:
        raise ValueError(f"{dataset_type} features are empty.")


def _fill_benchmark_metadata_defaults(dataset: pd.DataFrame) -> None:
    """Fill metadata columns for feature rows with no benchmark rows."""

    count_columns = [
        "benchmark_total_solver_count",
        "benchmark_eligible_solver_count",
        "benchmark_supported_solver_count",
        "benchmark_partially_supported_solver_count",
        "benchmark_unsupported_solver_count",
        "benchmark_not_configured_solver_count",
        "benchmark_failed_solver_count",
        "benchmark_best_solver_num_runs",
    ]
    for column in count_columns:
        if column in dataset.columns:
            dataset[column] = dataset[column].fillna(0).astype(int)

    if "benchmark_solver_support_coverage" in dataset.columns:
        dataset["benchmark_solver_support_coverage"] = dataset[
            "benchmark_solver_support_coverage"
        ].fillna("eligible=0/0; supported=0; partial=0; unsupported=0; not_configured=0; failed=0")


def _coverage_columns() -> list[str]:
    """Return stable coverage metadata columns."""

    return [
        "instance_name",
        "benchmark_solver_support_coverage",
        "benchmark_total_solver_count",
        "benchmark_eligible_solver_count",
        "benchmark_supported_solver_count",
        "benchmark_partially_supported_solver_count",
        "benchmark_unsupported_solver_count",
        "benchmark_not_configured_solver_count",
        "benchmark_failed_solver_count",
    ]


def _format_coverage(
    *,
    eligible_solver_count: int,
    total_solver_count: int,
    supported_solver_count: int,
    partially_supported_solver_count: int,
    unsupported_solver_count: int,
    not_configured_solver_count: int,
    failed_solver_count: int,
) -> str:
    """Format benchmark coverage into one compact auditable string."""

    return (
        f"eligible={eligible_solver_count}/{total_solver_count}; "
        f"supported={supported_solver_count}; "
        f"partial={partially_supported_solver_count}; "
        f"unsupported={unsupported_solver_count}; "
        f"not_configured={not_configured_solver_count}; "
        f"failed={failed_solver_count}"
    )


def _solver_has_support(group: pd.DataFrame, support_status: str) -> bool:
    """Return whether one solver group has a normalized support status."""

    return bool((group["solver_support_status_norm"] == support_status).any())


def _solver_has_partial_support(group: pd.DataFrame) -> bool:
    """Return whether one solver group has partial or simplified support."""

    statuses = set(group["solver_support_status_norm"].dropna().astype(str))
    return bool(statuses.intersection(PARTIAL_SUPPORT_STATUSES)) or any(
        "partial" in status or "simplified" in status for status in statuses
    )


def _solver_has_failure(group: pd.DataFrame) -> bool:
    """Return whether one solver group contains a failed run."""

    scoring_statuses = set(group["scoring_status_norm"].dropna().astype(str))
    statuses = set(group["status_norm"].dropna().astype(str))
    return "failed_run" in scoring_statuses or any("failed" in status for status in statuses)


def _stable_status_summary(values: pd.Series) -> str:
    """Return one status or a deterministic mixed-status marker."""

    statuses = sorted(
        {
            str(value).strip()
            for value in values.dropna().tolist()
            if str(value).strip()
        }
    )
    if not statuses:
        return "unknown"
    if len(statuses) == 1:
        return statuses[0]
    return "mixed:" + "|".join(statuses)


def _normalize_status(value: object) -> str:
    """Normalize status-like values for comparisons."""

    if value is None or pd.isna(value):
        return ""
    return str(value).strip().casefold().replace("-", "_").replace(" ", "_")


def _coerce_bool(value: object) -> bool:
    """Convert CSV-style boolean values into booleans."""

    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    """Return stable value counts for a dataframe column."""

    if column not in frame.columns:
        return {}
    counts = frame[column].fillna("missing").astype(str).value_counts().sort_index()
    return {str(key): int(value) for key, value in counts.items()}


__all__ = [
    "DEFAULT_OUTPUT_CSV",
    "DEFAULT_REAL_BENCHMARK_CSV",
    "DEFAULT_REAL_FEATURES_CSV",
    "DEFAULT_SYNTHETIC_BENCHMARK_CSV",
    "DEFAULT_SYNTHETIC_FEATURES_CSV",
    "FullSelectionDatasetSources",
    "SourceBuildResult",
    "build_selection_dataset_full",
]


if __name__ == "__main__":
    raise SystemExit(main())
