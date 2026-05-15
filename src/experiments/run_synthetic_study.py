"""Run a multi-seed synthetic benchmark study using the current thesis pipeline."""

from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

import pandas as pd

from src.experiments.full_benchmark import DEFAULT_FULL_SOLVER_PORTFOLIO
from src.experiments.run_benchmarks import run_benchmarks
from src.features.build_feature_table import build_feature_table
from src.selection.build_selection_dataset import build_selection_dataset
from src.selection.evaluate_selector import SelectorEvaluationResult, evaluate_selector
from src.selection.train_selector import SelectorTrainingResult, train_selector
from src.utils import (
    collect_xml_files,
    ensure_parent_directory,
    get_compat_value,
    get_include_solver_objectives,
    get_model_choice,
    get_selected_solvers,
    get_solver_settings_by_name,
    get_split_settings,
    get_time_limit_seconds,
    load_yaml_config,
    write_run_summary,
)


LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("configs/synthetic_study.yaml")
DEFAULT_DATASET_ROOT = Path("data/raw/synthetic/study")
DEFAULT_PROCESSED_DIR = Path("data/processed/synthetic_study")
DEFAULT_RESULTS_DIR = Path("data/results/synthetic_study")

_StepResult = TypeVar("_StepResult")

_SELECTOR_METRIC_COLUMNS = (
    "classification_accuracy",
    "balanced_accuracy",
    "average_selected_objective",
    "average_virtual_best_objective",
    "average_single_best_objective",
    "regret_vs_virtual_best",
    "delta_vs_single_best",
    "improvement_vs_single_best",
)


@dataclass(frozen=True, slots=True)
class SyntheticStudySettings:
    """Resolved configuration for one synthetic benchmark study."""

    dataset_root: Path
    processed_dir: Path
    results_dir: Path
    seeds: tuple[int, ...]
    time_limit_seconds: int
    solver_names: tuple[str, ...]
    solver_settings_by_name: dict[str, dict[str, object]]
    include_solver_objectives: bool
    model_name: str
    split_strategy: str
    test_size: float
    cross_validation_folds: int | None
    repeats: int
    config_path: Path | None
    config: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class SyntheticStudyArtifacts:
    """Top-level aggregate artifact paths for the synthetic study."""

    features_csv: Path
    features_run_summary: Path
    aggregate_benchmark_csv: Path
    aggregate_selection_dataset_csv: Path
    aggregate_evaluation_summary_csv: Path
    aggregate_benchmark_summary_csv: Path
    aggregate_selector_summary_csv: Path
    study_summary_markdown: Path
    study_run_summary_json: Path


@dataclass(frozen=True, slots=True)
class SeedStudyArtifacts:
    """Seed-specific artifact paths kept separate from aggregate outputs."""

    processed_dir: Path
    results_dir: Path
    benchmark_csv: Path
    benchmark_run_summary: Path
    selection_dataset_csv: Path
    selection_dataset_run_summary: Path
    model_path: Path
    feature_importance_csv: Path
    training_run_summary: Path
    evaluation_report_csv: Path
    evaluation_summary_csv: Path
    evaluation_summary_markdown: Path
    evaluation_run_summary: Path


@dataclass(frozen=True, slots=True)
class SeedStudyResult:
    """Outputs and selector metrics for one benchmark seed."""

    seed: int
    benchmark_csv: Path
    selection_dataset_csv: Path
    model_path: Path
    feature_importance_csv: Path | None
    evaluation_report_csv: Path
    evaluation_summary_csv: Path
    evaluation_summary_markdown: Path
    selector_accuracy: float
    selector_regret_vs_virtual_best: float


@dataclass(frozen=True, slots=True)
class SummaryStageResult:
    """Summary artifacts written after aggregation."""

    summary_markdown: Path
    run_summary_json: Path


@dataclass(frozen=True, slots=True)
class SyntheticStudyResult:
    """Main artifacts from a completed synthetic benchmark study."""

    features_csv: Path
    benchmark_csv: Path
    selection_dataset_csv: Path
    selector_evaluation_summary_csv: Path
    aggregate_benchmark_summary_csv: Path
    aggregate_selector_summary_csv: Path
    summary_markdown: Path
    run_summary_json: Path
    seed_results: tuple[SeedStudyResult, ...]
    num_instances: int
    num_benchmark_rows: int


class SyntheticStudyError(RuntimeError):
    """A critical synthetic study stage failed."""

    def __init__(self, step_name: str, cause: Exception) -> None:
        self.step_name = step_name
        self.cause = cause
        super().__init__(f"{step_name} failed: {type(cause).__name__}: {cause}")


def run_synthetic_study(config_path: str | Path = DEFAULT_CONFIG_PATH) -> SyntheticStudyResult:
    """Run the synthetic benchmark study described by one YAML configuration."""

    settings = _resolve_settings(config_path)
    artifacts = _build_artifact_paths(settings.processed_dir, settings.results_dir)
    _validate_settings(settings)
    _log_output_refresh(settings, artifacts)

    total_steps = 1 + (4 * len(settings.seeds)) + 2
    step_index = 1

    features_csv = _execute_step(
        step_index,
        total_steps,
        "Extract synthetic structural features",
        lambda: build_feature_table(
            input_folder=settings.dataset_root,
            output_csv=artifacts.features_csv,
            random_seed=settings.seeds[0],
            config_path=settings.config_path,
            config=settings.config,
            run_summary_path=artifacts.features_run_summary,
        ),
        success_message=lambda path: f"Features saved to {path.as_posix()}",
    )
    _validate_non_empty_csv(features_csv, "feature table")

    seed_results: list[SeedStudyResult] = []
    for seed in settings.seeds:
        seed_artifacts = _build_seed_artifact_paths(
            processed_dir=settings.processed_dir,
            results_dir=settings.results_dir,
            seed=seed,
        )

        step_index += 1
        benchmark_csv = _execute_step(
            step_index,
            total_steps,
            f"Run solver benchmark for seed {seed}",
            lambda seed=seed, seed_artifacts=seed_artifacts: run_benchmarks(
                instance_folder=str(settings.dataset_root),
                solver_names=list(settings.solver_names),
                time_limit_seconds=settings.time_limit_seconds,
                random_seed=seed,
                output_csv=seed_artifacts.benchmark_csv,
                config_path=settings.config_path,
                config=settings.config,
                run_summary_path=seed_artifacts.benchmark_run_summary,
                solver_settings_by_name=settings.solver_settings_by_name,
            ),
            success_message=lambda path: f"Seed benchmark results saved to {path.as_posix()}",
        )
        _validate_benchmark_output(
            benchmark_csv,
            solver_names=settings.solver_names,
            timefold_configured=_timefold_configured(settings.solver_settings_by_name),
        )

        step_index += 1
        selection_dataset_csv = _execute_step(
            step_index,
            total_steps,
            f"Build selection dataset for seed {seed}",
            lambda seed_artifacts=seed_artifacts, benchmark_csv=benchmark_csv: build_selection_dataset(
                features_csv=features_csv,
                benchmark_csv=benchmark_csv,
                output_csv=seed_artifacts.selection_dataset_csv,
                include_solver_objectives=settings.include_solver_objectives,
                config_path=settings.config_path,
                config=settings.config,
                run_summary_path=seed_artifacts.selection_dataset_run_summary,
            ),
            success_message=lambda path: f"Seed selection dataset saved to {path.as_posix()}",
        )
        _validate_labeled_selection_dataset(selection_dataset_csv)

        step_index += 1
        training_result = _execute_step(
            step_index,
            total_steps,
            f"Train selector for seed {seed}",
            lambda seed=seed, seed_artifacts=seed_artifacts: train_selector(
                dataset_csv=selection_dataset_csv,
                model_path=seed_artifacts.model_path,
                feature_importance_csv=seed_artifacts.feature_importance_csv,
                random_seed=seed,
                test_size=settings.test_size,
                model_name=settings.model_name,
                split_strategy=settings.split_strategy,
                cross_validation_folds=settings.cross_validation_folds,
                repeats=settings.repeats,
                config_path=settings.config_path,
                config=settings.config,
                run_summary_path=seed_artifacts.training_run_summary,
            ),
            success_message=_training_success_message,
        )

        step_index += 1
        evaluation_result = _execute_step(
            step_index,
            total_steps,
            f"Evaluate selector for seed {seed}",
            lambda seed=seed, seed_artifacts=seed_artifacts, training_result=training_result: evaluate_selector(
                dataset_csv=selection_dataset_csv,
                benchmark_csv=benchmark_csv,
                model_path=training_result.model_path,
                report_csv=seed_artifacts.evaluation_report_csv,
                summary_csv=seed_artifacts.evaluation_summary_csv,
                summary_markdown=seed_artifacts.evaluation_summary_markdown,
                random_seed=seed,
                test_size=settings.test_size,
                model_name=settings.model_name,
                split_strategy=settings.split_strategy,
                cross_validation_folds=settings.cross_validation_folds,
                repeats=settings.repeats,
                config_path=settings.config_path,
                config=settings.config,
                run_summary_path=seed_artifacts.evaluation_run_summary,
            ),
            success_message=_evaluation_success_message,
        )

        seed_results.append(
            SeedStudyResult(
                seed=seed,
                benchmark_csv=benchmark_csv,
                selection_dataset_csv=selection_dataset_csv,
                model_path=training_result.model_path,
                feature_importance_csv=training_result.feature_importance_path,
                evaluation_report_csv=evaluation_result.report_path,
                evaluation_summary_csv=evaluation_result.summary_csv_path,
                evaluation_summary_markdown=evaluation_result.summary_markdown_path,
                selector_accuracy=evaluation_result.classification_accuracy,
                selector_regret_vs_virtual_best=evaluation_result.regret_vs_virtual_best,
            )
        )

    step_index += 1
    _execute_step(
        step_index,
        total_steps,
        "Aggregate synthetic study outputs",
        lambda: _write_aggregate_outputs(
            seed_results=tuple(seed_results),
            artifacts=artifacts,
        ),
        success_message=lambda _: (
            f"Aggregate benchmark rows saved to {artifacts.aggregate_benchmark_csv.as_posix()}\n"
            f"Aggregate selector summary saved to {artifacts.aggregate_selector_summary_csv.as_posix()}"
        ),
    )

    step_index += 1
    summary_stage = _execute_step(
        step_index,
        total_steps,
        "Write synthetic study summary",
        lambda: _write_study_summary(
            settings=settings,
            artifacts=artifacts,
            seed_results=tuple(seed_results),
        ),
        success_message=lambda result: (
            f"Summary Markdown saved to {result.summary_markdown.as_posix()}\n"
            f"Summary JSON saved to {result.run_summary_json.as_posix()}"
        ),
    )

    features = pd.read_csv(features_csv)
    benchmarks = pd.read_csv(artifacts.aggregate_benchmark_csv)
    result = SyntheticStudyResult(
        features_csv=features_csv,
        benchmark_csv=artifacts.aggregate_benchmark_csv,
        selection_dataset_csv=artifacts.aggregate_selection_dataset_csv,
        selector_evaluation_summary_csv=artifacts.aggregate_evaluation_summary_csv,
        aggregate_benchmark_summary_csv=artifacts.aggregate_benchmark_summary_csv,
        aggregate_selector_summary_csv=artifacts.aggregate_selector_summary_csv,
        summary_markdown=summary_stage.summary_markdown,
        run_summary_json=summary_stage.run_summary_json,
        seed_results=tuple(seed_results),
        num_instances=len(features.index),
        num_benchmark_rows=len(benchmarks.index),
    )
    _print_final_summary(result)
    return result


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for synthetic study orchestration."""

    parser = argparse.ArgumentParser(
        description="Run the larger synthetic benchmark study into isolated artifacts.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the synthetic study YAML config.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the synthetic study from the command line."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        run_synthetic_study(args.config)
    except SyntheticStudyError as exc:
        print(
            f"Synthetic study failed during '{exc.step_name}': "
            f"{type(exc.cause).__name__}: {exc.cause}",
            flush=True,
        )
        return 1
    except Exception as exc:
        print(f"Synthetic study failed: {type(exc).__name__}: {exc}", flush=True)
        return 1
    return 0


def _resolve_settings(config_path: str | Path) -> SyntheticStudySettings:
    """Load and normalize one synthetic study config."""

    resolved_config_path = Path(config_path)
    config = load_yaml_config(resolved_config_path)
    split_settings = get_split_settings(config)

    raw_seeds = get_compat_value(config, ["run.seeds", "seeds"], None)
    seeds = _parse_seed_config(raw_seeds) if raw_seeds is not None else (
        int(get_compat_value(config, ["run.random_seed", "random_seed"], 42)),
    )

    return SyntheticStudySettings(
        dataset_root=Path(
            get_compat_value(
                config,
                ["paths.dataset_root", "paths.synthetic_dataset_root", "paths.instance_folder", "paths.input_folder"],
                DEFAULT_DATASET_ROOT,
            )
        ),
        processed_dir=Path(get_compat_value(config, ["paths.processed_dir"], DEFAULT_PROCESSED_DIR)),
        results_dir=Path(get_compat_value(config, ["paths.results_dir"], DEFAULT_RESULTS_DIR)),
        seeds=seeds,
        time_limit_seconds=get_time_limit_seconds(config, 60),
        solver_names=tuple(get_selected_solvers(config, list(DEFAULT_FULL_SOLVER_PORTFOLIO))),
        solver_settings_by_name=get_solver_settings_by_name(config),
        include_solver_objectives=get_include_solver_objectives(config, True),
        model_name=get_model_choice(config, "random_forest"),
        split_strategy=split_settings.strategy,
        test_size=split_settings.test_size,
        cross_validation_folds=split_settings.cross_validation_folds,
        repeats=split_settings.repeats,
        config_path=resolved_config_path,
        config=config,
    )


def _build_artifact_paths(processed_dir: Path, results_dir: Path) -> SyntheticStudyArtifacts:
    """Return stable aggregate artifact paths for the study."""

    return SyntheticStudyArtifacts(
        features_csv=processed_dir / "features.csv",
        features_run_summary=processed_dir / "features_run_summary.json",
        aggregate_benchmark_csv=results_dir / "benchmark_results.csv",
        aggregate_selection_dataset_csv=processed_dir / "selection_dataset.csv",
        aggregate_evaluation_summary_csv=results_dir / "selector_evaluation_summary.csv",
        aggregate_benchmark_summary_csv=results_dir / "aggregate_benchmark_summary.csv",
        aggregate_selector_summary_csv=results_dir / "aggregate_selector_summary.csv",
        study_summary_markdown=results_dir / "synthetic_study_summary.md",
        study_run_summary_json=results_dir / "synthetic_study_run_summary.json",
    )


def _build_seed_artifact_paths(
    *,
    processed_dir: Path,
    results_dir: Path,
    seed: int,
) -> SeedStudyArtifacts:
    """Return all seed-specific artifact paths."""

    seed_name = _seed_folder_name(seed)
    seed_processed_dir = processed_dir / "seeds" / seed_name
    seed_results_dir = results_dir / "seeds" / seed_name
    return SeedStudyArtifacts(
        processed_dir=seed_processed_dir,
        results_dir=seed_results_dir,
        benchmark_csv=seed_results_dir / "benchmark_results.csv",
        benchmark_run_summary=seed_results_dir / "benchmark_results_run_summary.json",
        selection_dataset_csv=seed_processed_dir / "selection_dataset.csv",
        selection_dataset_run_summary=seed_processed_dir / "selection_dataset_run_summary.json",
        model_path=seed_results_dir / "random_forest_selector.joblib",
        feature_importance_csv=seed_results_dir / "feature_importance.csv",
        training_run_summary=seed_results_dir / "selector_training_run_summary.json",
        evaluation_report_csv=seed_results_dir / "selector_evaluation.csv",
        evaluation_summary_csv=seed_results_dir / "selector_evaluation_summary.csv",
        evaluation_summary_markdown=seed_results_dir / "selector_evaluation_summary.md",
        evaluation_run_summary=seed_results_dir / "selector_evaluation_run_summary.json",
    )


def _validate_settings(settings: SyntheticStudySettings) -> None:
    """Validate critical settings before writing study artifacts."""

    if not settings.dataset_root.exists():
        raise FileNotFoundError(
            f"Synthetic dataset root does not exist: {settings.dataset_root}. "
            "Generate it first with src.experiments.generate_synthetic_dataset."
        )
    if not settings.dataset_root.is_dir():
        raise NotADirectoryError(f"Synthetic dataset root is not a folder: {settings.dataset_root}")

    xml_files = collect_xml_files(settings.dataset_root)
    if not xml_files:
        raise ValueError(f"No XML files found under {settings.dataset_root.as_posix()}.")

    if not settings.seeds:
        raise ValueError("At least one benchmark seed is required.")
    if len(set(settings.seeds)) != len(settings.seeds):
        raise ValueError("Benchmark seeds must be unique so per-seed outputs do not collide.")
    if settings.time_limit_seconds <= 0:
        raise ValueError("run.time_limit_seconds must be positive.")
    if not settings.solver_names:
        raise ValueError("At least one solver must be selected.")
    if len(set(settings.solver_names)) != len(settings.solver_names):
        raise ValueError("Selected solver names must be unique.")
    if not 0.0 < settings.test_size < 1.0:
        raise ValueError("split.test_size must be between 0 and 1.")
    if settings.cross_validation_folds is not None and settings.cross_validation_folds < 2:
        raise ValueError("split.cross_validation_folds must be at least 2 when provided.")
    if settings.repeats <= 0:
        raise ValueError("split.repeats must be positive.")

    _reject_legacy_root(settings.processed_dir, Path("data/processed"), "processed_dir")
    _reject_legacy_root(settings.results_dir, Path("data/results"), "results_dir")


def _reject_legacy_root(path: Path, legacy_root: Path, setting_name: str) -> None:
    """Reject top-level legacy artifact roots for this isolated study."""

    if path.resolve() == legacy_root.resolve():
        raise ValueError(
            f"paths.{setting_name} must be an isolated subfolder, not {legacy_root.as_posix()}."
        )


def _log_output_refresh(
    settings: SyntheticStudySettings,
    artifacts: SyntheticStudyArtifacts,
) -> None:
    """Log existing current-study artifacts before refreshing them."""

    existing = [
        artifacts.features_csv,
        artifacts.aggregate_benchmark_csv,
        artifacts.aggregate_selection_dataset_csv,
        artifacts.aggregate_evaluation_summary_csv,
        artifacts.aggregate_benchmark_summary_csv,
        artifacts.aggregate_selector_summary_csv,
        artifacts.study_summary_markdown,
        artifacts.study_run_summary_json,
    ]
    for seed in settings.seeds:
        seed_artifacts = _build_seed_artifact_paths(
            processed_dir=settings.processed_dir,
            results_dir=settings.results_dir,
            seed=seed,
        )
        existing.extend(
            [
                seed_artifacts.benchmark_csv,
                seed_artifacts.selection_dataset_csv,
                seed_artifacts.model_path,
                seed_artifacts.evaluation_summary_csv,
            ]
        )

    existing_paths = [path for path in existing if path.exists()]
    if not existing_paths:
        LOGGER.info("Writing synthetic study artifacts into a fresh isolated namespace.")
        return

    preview = ", ".join(path.as_posix() for path in existing_paths[:6])
    suffix = "" if len(existing_paths) <= 6 else f", and {len(existing_paths) - 6} more"
    LOGGER.info("Refreshing existing synthetic-study artifacts: %s%s", preview, suffix)


def _execute_step(
    step_index: int,
    total_steps: int,
    step_name: str,
    action: Callable[[], _StepResult],
    *,
    success_message: Callable[[_StepResult], str],
) -> _StepResult:
    """Run one study step with concise progress logging."""

    print(f"[{step_index}/{total_steps}] {step_name}...", flush=True)
    started_at = time.perf_counter()
    try:
        result = action()
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        print(f"[{step_index}/{total_steps}] {step_name} failed after {elapsed:.2f}s", flush=True)
        raise SyntheticStudyError(step_name, exc) from exc

    elapsed = time.perf_counter() - started_at
    print(f"[{step_index}/{total_steps}] {step_name} completed in {elapsed:.2f}s", flush=True)
    message = success_message(result).strip()
    if message:
        print(message, flush=True)
    return result


def _write_aggregate_outputs(
    *,
    seed_results: tuple[SeedStudyResult, ...],
    artifacts: SyntheticStudyArtifacts,
) -> tuple[Path, Path, Path, Path, Path]:
    """Concatenate per-seed outputs and write cross-seed aggregate summaries."""

    benchmark_table = _combine_seed_csvs(
        seed_results=seed_results,
        output_csv=artifacts.aggregate_benchmark_csv,
        path_getter=lambda result: result.benchmark_csv,
    )
    selection_table = _combine_seed_csvs(
        seed_results=seed_results,
        output_csv=artifacts.aggregate_selection_dataset_csv,
        path_getter=lambda result: result.selection_dataset_csv,
    )
    evaluation_summary = _combine_seed_csvs(
        seed_results=seed_results,
        output_csv=artifacts.aggregate_evaluation_summary_csv,
        path_getter=lambda result: result.evaluation_summary_csv,
    )

    benchmark_summary = _build_aggregate_benchmark_summary(benchmark_table)
    ensure_parent_directory(artifacts.aggregate_benchmark_summary_csv)
    benchmark_summary.to_csv(artifacts.aggregate_benchmark_summary_csv, index=False)

    selector_summary = _build_aggregate_selector_summary(evaluation_summary)
    ensure_parent_directory(artifacts.aggregate_selector_summary_csv)
    selector_summary.to_csv(artifacts.aggregate_selector_summary_csv, index=False)

    if selection_table.empty:
        raise ValueError("Aggregate selection dataset is empty.")

    return (
        artifacts.aggregate_benchmark_csv,
        artifacts.aggregate_selection_dataset_csv,
        artifacts.aggregate_evaluation_summary_csv,
        artifacts.aggregate_benchmark_summary_csv,
        artifacts.aggregate_selector_summary_csv,
    )


def _combine_seed_csvs(
    *,
    seed_results: tuple[SeedStudyResult, ...],
    output_csv: Path,
    path_getter: Callable[[SeedStudyResult], Path],
) -> pd.DataFrame:
    """Combine seed-specific CSVs after adding a benchmark_seed column."""

    frames: list[pd.DataFrame] = []
    for result in seed_results:
        frame = pd.read_csv(path_getter(result))
        frame.insert(0, "benchmark_seed", result.seed)
        frames.append(frame)

    combined = pd.concat(frames, ignore_index=True, sort=False) if frames else pd.DataFrame()
    ensure_parent_directory(output_csv)
    combined.to_csv(output_csv, index=False)
    return combined


def _build_aggregate_benchmark_summary(benchmark_table: pd.DataFrame) -> pd.DataFrame:
    """Summarize benchmark outcomes by seed, solver, and scoring status."""

    if benchmark_table.empty:
        return pd.DataFrame(columns=_benchmark_summary_columns())

    frame = benchmark_table.copy()
    frame["objective_value_numeric"] = pd.to_numeric(frame.get("objective_value"), errors="coerce")
    frame["runtime_seconds_numeric"] = pd.to_numeric(frame.get("runtime_seconds"), errors="coerce")
    frame["feasible_bool"] = frame.get("feasible", pd.Series(dtype="object")).map(_coerce_bool)
    if "objective_value_valid" in frame.columns:
        frame["objective_value_valid_bool"] = frame["objective_value_valid"].map(_coerce_bool)
    else:
        frame["objective_value_valid_bool"] = (
            frame["feasible_bool"] & frame["objective_value_numeric"].notna()
        )

    rows: list[dict[str, object]] = []
    per_seed_columns = [
        "benchmark_seed",
        "solver_registry_name",
        "solver_name",
        "solver_support_status",
        "scoring_status",
    ]
    all_seed_columns = [
        "solver_registry_name",
        "solver_name",
        "solver_support_status",
        "scoring_status",
    ]
    rows.extend(_benchmark_summary_rows(frame, group_columns=per_seed_columns, summary_scope="per_seed"))
    rows.extend(_benchmark_summary_rows(frame, group_columns=all_seed_columns, summary_scope="all_seeds"))
    return pd.DataFrame(rows, columns=_benchmark_summary_columns())


def _benchmark_summary_rows(
    frame: pd.DataFrame,
    *,
    group_columns: list[str],
    summary_scope: str,
) -> list[dict[str, object]]:
    """Build benchmark summary rows for one grouping level."""

    rows: list[dict[str, object]] = []
    for group_values, group in frame.groupby(group_columns, dropna=False, sort=True):
        values = _group_values(group_columns, group_values)
        valid_objective_rows = group[group["objective_value_valid_bool"]].copy()
        support_status = group["solver_support_status"].fillna("").astype(str).str.casefold()
        scoring_status = group["scoring_status"].fillna("").astype(str).str.casefold()
        status = group["status"].fillna("").astype(str).str.casefold()

        rows.append(
            {
                "summary_scope": summary_scope,
                "benchmark_seed": values.get("benchmark_seed", "all"),
                "solver_registry_name": values.get("solver_registry_name"),
                "solver_name": values.get("solver_name"),
                "solver_support_status": values.get("solver_support_status"),
                "scoring_status": values.get("scoring_status"),
                "num_runs": int(len(group.index)),
                "num_instances": int(group["instance_name"].nunique()) if "instance_name" in group else 0,
                "feasible_runs": int(group["feasible_bool"].sum()),
                "valid_objective_runs": int(group["objective_value_valid_bool"].sum()),
                "unsupported_runs": int((support_status == "unsupported").sum()),
                "not_configured_runs": int((support_status == "not_configured").sum()),
                "failed_runs": int(((scoring_status == "failed_run") | status.str.startswith("failed")).sum()),
                "average_objective_value_valid": _mean_or_none(
                    valid_objective_rows["objective_value_numeric"]
                ),
                "median_objective_value_valid": _median_or_none(
                    valid_objective_rows["objective_value_numeric"]
                ),
                "average_runtime_seconds": _mean_or_none(group["runtime_seconds_numeric"]),
            }
        )
    return rows


def _benchmark_summary_columns() -> list[str]:
    """Return the stable aggregate benchmark summary schema."""

    return [
        "summary_scope",
        "benchmark_seed",
        "solver_registry_name",
        "solver_name",
        "solver_support_status",
        "scoring_status",
        "num_runs",
        "num_instances",
        "feasible_runs",
        "valid_objective_runs",
        "unsupported_runs",
        "not_configured_runs",
        "failed_runs",
        "average_objective_value_valid",
        "median_objective_value_valid",
        "average_runtime_seconds",
    ]


def _build_aggregate_selector_summary(evaluation_summary: pd.DataFrame) -> pd.DataFrame:
    """Summarize selector aggregate metrics across benchmark seeds."""

    columns = [
        "summary_scope",
        "benchmark_seed",
        "num_seed_rows",
        "split_strategy",
        "single_best_solver_name",
        *_SELECTOR_METRIC_COLUMNS,
    ]
    if evaluation_summary.empty:
        return pd.DataFrame(columns=columns)

    aggregate_rows = evaluation_summary[
        (evaluation_summary["summary_row_type"].astype(str) == "aggregate_mean")
        & (evaluation_summary.get("dataset_type", "all").astype(str) == "all")
    ].copy()
    if aggregate_rows.empty:
        aggregate_rows = evaluation_summary[
            evaluation_summary["summary_row_type"].astype(str) == "aggregate_mean"
        ].copy()
    if aggregate_rows.empty:
        return pd.DataFrame(columns=columns)

    rows: list[dict[str, object]] = []
    for row in aggregate_rows.sort_values("benchmark_seed", kind="mergesort").to_dict(orient="records"):
        rows.append(
            {
                "summary_scope": "per_seed",
                "benchmark_seed": row["benchmark_seed"],
                "num_seed_rows": 1,
                "split_strategy": row.get("split_strategy"),
                "single_best_solver_name": row.get("single_best_solver_name"),
                **{metric: _optional_float(row.get(metric)) for metric in _SELECTOR_METRIC_COLUMNS},
            }
        )

    for summary_scope, reducer in (
        ("all_seeds_mean", "mean"),
        ("all_seeds_std", "std"),
        ("all_seeds_min", "min"),
        ("all_seeds_max", "max"),
    ):
        summary_row: dict[str, object] = {
            "summary_scope": summary_scope,
            "benchmark_seed": "all",
            "num_seed_rows": int(len(aggregate_rows.index)),
            "split_strategy": _stable_unique_or_none(aggregate_rows["split_strategy"]),
            "single_best_solver_name": _stable_unique_or_none(aggregate_rows["single_best_solver_name"]),
        }
        for metric in _SELECTOR_METRIC_COLUMNS:
            summary_row[metric] = _reduce_metric(aggregate_rows[metric], reducer)
        rows.append(summary_row)

    return pd.DataFrame(rows, columns=columns)


def _write_study_summary(
    *,
    settings: SyntheticStudySettings,
    artifacts: SyntheticStudyArtifacts,
    seed_results: tuple[SeedStudyResult, ...],
) -> SummaryStageResult:
    """Write Markdown and JSON summaries for the completed synthetic study."""

    features = pd.read_csv(artifacts.features_csv)
    benchmarks = pd.read_csv(artifacts.aggregate_benchmark_csv)
    selection_dataset = pd.read_csv(artifacts.aggregate_selection_dataset_csv)
    benchmark_summary = pd.read_csv(artifacts.aggregate_benchmark_summary_csv)
    selector_summary = pd.read_csv(artifacts.aggregate_selector_summary_csv)

    ensure_parent_directory(artifacts.study_summary_markdown)
    artifacts.study_summary_markdown.write_text(
        _render_summary_markdown(
            settings=settings,
            artifacts=artifacts,
            seed_results=seed_results,
            feature_rows=len(features.index),
            benchmark_rows=len(benchmarks.index),
            selection_rows=len(selection_dataset.index),
            support_counts=_value_counts(benchmarks, "solver_support_status"),
            scoring_counts=_value_counts(benchmarks, "scoring_status"),
            benchmark_summary=benchmark_summary,
            selector_summary=selector_summary,
        ),
        encoding="utf-8",
    )

    write_run_summary(
        artifacts.study_run_summary_json,
        stage_name="synthetic_study",
        config_path=settings.config_path,
        config=settings.config,
        settings={
            "dataset_root": settings.dataset_root,
            "processed_dir": settings.processed_dir,
            "results_dir": settings.results_dir,
            "seeds": list(settings.seeds),
            "time_limit_seconds": settings.time_limit_seconds,
            "solver_portfolio": list(settings.solver_names),
            "solver_settings_by_name": settings.solver_settings_by_name,
            "include_solver_objectives": settings.include_solver_objectives,
            "model_name": settings.model_name,
            "split_strategy": settings.split_strategy,
            "test_size": settings.test_size,
            "cross_validation_folds": settings.cross_validation_folds,
            "repeats": settings.repeats,
        },
        inputs={
            "dataset_root": settings.dataset_root,
        },
        outputs={
            "features_csv": artifacts.features_csv,
            "benchmark_results_csv": artifacts.aggregate_benchmark_csv,
            "selection_dataset_csv": artifacts.aggregate_selection_dataset_csv,
            "selector_evaluation_summary_csv": artifacts.aggregate_evaluation_summary_csv,
            "aggregate_benchmark_summary_csv": artifacts.aggregate_benchmark_summary_csv,
            "aggregate_selector_summary_csv": artifacts.aggregate_selector_summary_csv,
            "summary_markdown": artifacts.study_summary_markdown,
            "run_summary_json": artifacts.study_run_summary_json,
            "per_seed_outputs": {
                str(result.seed): {
                    "benchmark_csv": result.benchmark_csv,
                    "selection_dataset_csv": result.selection_dataset_csv,
                    "model_path": result.model_path,
                    "feature_importance_csv": result.feature_importance_csv,
                    "evaluation_report_csv": result.evaluation_report_csv,
                    "evaluation_summary_csv": result.evaluation_summary_csv,
                    "evaluation_summary_markdown": result.evaluation_summary_markdown,
                }
                for result in seed_results
            },
        },
        results={
            "num_instances": len(features.index),
            "num_seeds": len(settings.seeds),
            "num_benchmark_rows": len(benchmarks.index),
            "num_selection_rows": len(selection_dataset.index),
            "support_counts": _value_counts(benchmarks, "solver_support_status"),
            "scoring_counts": _value_counts(benchmarks, "scoring_status"),
            "selector_accuracy_by_seed": {
                str(result.seed): result.selector_accuracy for result in seed_results
            },
            "selector_regret_vs_virtual_best_by_seed": {
                str(result.seed): result.selector_regret_vs_virtual_best for result in seed_results
            },
        },
    )
    return SummaryStageResult(
        summary_markdown=artifacts.study_summary_markdown,
        run_summary_json=artifacts.study_run_summary_json,
    )


def _render_summary_markdown(
    *,
    settings: SyntheticStudySettings,
    artifacts: SyntheticStudyArtifacts,
    seed_results: tuple[SeedStudyResult, ...],
    feature_rows: int,
    benchmark_rows: int,
    selection_rows: int,
    support_counts: dict[str, int],
    scoring_counts: dict[str, int],
    benchmark_summary: pd.DataFrame,
    selector_summary: pd.DataFrame,
) -> str:
    """Render a concise thesis-oriented synthetic study summary."""

    timefold_path = _timefold_executable_text(settings.solver_settings_by_name)
    lines = [
        "# Synthetic Study Summary",
        "",
        "## Settings",
        "",
        f"- Synthetic dataset root: `{settings.dataset_root.as_posix()}`",
        f"- Processed artifact folder: `{settings.processed_dir.as_posix()}`",
        f"- Results artifact folder: `{settings.results_dir.as_posix()}`",
        f"- Benchmark seeds: `{', '.join(str(seed) for seed in settings.seeds)}`",
        f"- Per-solver time limit: `{settings.time_limit_seconds}` seconds",
        f"- Solver portfolio: `{', '.join(settings.solver_names)}`",
        f"- Timefold executable: `{timefold_path}`",
        f"- Selector model: `{settings.model_name}`",
        f"- Selector split: `{settings.split_strategy}`",
        f"- Cross-validation folds: `{settings.cross_validation_folds or 'none'}`",
        f"- Repeats: `{settings.repeats}`",
        "",
        "## Aggregate Artifacts",
        "",
        f"- Features: `{artifacts.features_csv.as_posix()}`",
        f"- Benchmark results: `{artifacts.aggregate_benchmark_csv.as_posix()}`",
        f"- Selection dataset: `{artifacts.aggregate_selection_dataset_csv.as_posix()}`",
        f"- Selector evaluation summary: `{artifacts.aggregate_evaluation_summary_csv.as_posix()}`",
        f"- Aggregate benchmark summary: `{artifacts.aggregate_benchmark_summary_csv.as_posix()}`",
        f"- Aggregate selector summary: `{artifacts.aggregate_selector_summary_csv.as_posix()}`",
        "",
        "## Per-Seed Outputs",
        "",
        "| seed | benchmark | selection dataset | selector summary |",
        "| ---: | --- | --- | --- |",
    ]
    for result in seed_results:
        lines.append(
            "| "
            f"{result.seed} | "
            f"`{result.benchmark_csv.as_posix()}` | "
            f"`{result.selection_dataset_csv.as_posix()}` | "
            f"`{result.evaluation_summary_csv.as_posix()}` |"
        )

    lines.extend(
        [
            "",
            "## Headline Counts",
            "",
            f"- Feature rows: `{feature_rows}`",
            f"- Benchmark rows across seeds: `{benchmark_rows}`",
            f"- Selection rows across seeds: `{selection_rows}`",
            "",
            "## Solver Support Status Counts",
            "",
            *_render_count_table(support_counts, "support_status"),
            "",
            "## Solver Scoring Status Counts",
            "",
            *_render_count_table(scoring_counts, "scoring_status"),
            "",
            "## Aggregate Selector Metrics",
            "",
            *_render_selector_summary_table(selector_summary),
            "",
            "## Aggregate Benchmark Notes",
            "",
            *_render_benchmark_note_table(benchmark_summary),
            "",
            "## Notes",
            "",
            "- Outputs are isolated under `data/processed/synthetic_study/` and `data/results/synthetic_study/` by default.",
            "- Per-seed artifacts are kept in `seeds/seed_XXXX/` subfolders; aggregate CSVs add `benchmark_seed` so repeated runs remain traceable.",
            "- Benchmark exports preserve the solver scoring contract columns, including `solver_support_status`, `scoring_status`, `modeling_scope`, and `scoring_notes`.",
            "- If Timefold has no executable path configured, its rows are recorded as `not_configured` instead of failing the study.",
            "",
        ]
    )
    return "\n".join(lines)


def _validate_non_empty_csv(csv_path: Path, label: str) -> None:
    """Fail early when a required stage writes an empty CSV."""

    table = pd.read_csv(csv_path)
    if table.empty:
        raise ValueError(f"The {label} is empty: {csv_path.as_posix()}")


def _validate_benchmark_output(
    benchmark_csv: Path,
    *,
    solver_names: tuple[str, ...],
    timefold_configured: bool,
) -> None:
    """Validate benchmark output and scoring-contract metadata."""

    table = pd.read_csv(benchmark_csv)
    if table.empty:
        raise ValueError("Benchmark results are empty.")

    required_columns = {
        "solver_registry_name",
        "solver_support_status",
        "scoring_status",
        "modeling_scope",
        "scoring_notes",
        "objective_value_valid",
    }
    missing_columns = sorted(required_columns.difference(table.columns))
    if missing_columns:
        raise ValueError(
            "Benchmark results are missing scoring-contract columns: "
            + ", ".join(missing_columns)
        )

    observed_solvers = set(table["solver_registry_name"].dropna().astype(str))
    missing_solvers = sorted(set(solver_names).difference(observed_solvers))
    if missing_solvers:
        raise ValueError(f"Benchmark results are missing solver rows for: {', '.join(missing_solvers)}")

    if "timefold" in solver_names and not timefold_configured:
        timefold_rows = table[table["solver_registry_name"].astype(str) == "timefold"]
        support_statuses = {
            str(value).strip().casefold()
            for value in timefold_rows["solver_support_status"].dropna()
        }
        statuses = {
            str(value).strip().casefold()
            for value in timefold_rows.get("status", pd.Series(dtype="string")).dropna()
        }
        if "not_configured" not in support_statuses.union(statuses):
            raise ValueError("Unconfigured Timefold rows were not marked as not_configured.")


def _validate_labeled_selection_dataset(selection_dataset_csv: Path) -> None:
    """Ensure selector training has at least two labeled rows."""

    dataset = pd.read_csv(selection_dataset_csv)
    if dataset.empty:
        raise ValueError("Selection dataset is empty.")
    if "best_solver" not in dataset.columns:
        raise ValueError("Selection dataset is missing the best_solver target column.")
    if int(dataset["best_solver"].notna().sum()) < 2:
        raise ValueError("Selection dataset must contain at least two labeled rows.")


def _training_success_message(result: SelectorTrainingResult) -> str:
    """Format one concise training success message."""

    return (
        f"Model saved to {result.model_path.as_posix()}\n"
        f"Feature importance: {_path_or_not_written(result.feature_importance_path)}\n"
        f"Validation accuracy: {result.accuracy:.4f}; "
        f"balanced accuracy: {_format_optional_float(result.balanced_accuracy)}"
    )


def _evaluation_success_message(result: SelectorEvaluationResult) -> str:
    """Format one concise evaluation success message."""

    return (
        f"Evaluation report: {result.report_path.as_posix()}\n"
        f"Evaluation summary CSV: {result.summary_csv_path.as_posix()}\n"
        f"Evaluation summary Markdown: {result.summary_markdown_path.as_posix()}\n"
        f"Accuracy: {result.classification_accuracy:.4f}; "
        f"regret vs virtual best: {result.regret_vs_virtual_best:.4f}"
    )


def _print_final_summary(result: SyntheticStudyResult) -> None:
    """Print a short completion summary after a successful study run."""

    print("Synthetic study completed successfully.", flush=True)
    print(f"Features: {result.features_csv.as_posix()}", flush=True)
    print(f"Benchmarks: {result.benchmark_csv.as_posix()}", flush=True)
    print(f"Selection dataset: {result.selection_dataset_csv.as_posix()}", flush=True)
    print(f"Selector evaluation summary: {result.selector_evaluation_summary_csv.as_posix()}", flush=True)
    print(f"Aggregate benchmark summary: {result.aggregate_benchmark_summary_csv.as_posix()}", flush=True)
    print(f"Aggregate selector summary: {result.aggregate_selector_summary_csv.as_posix()}", flush=True)
    print(f"Run summary: {result.run_summary_json.as_posix()}", flush=True)


def _parse_seed_config(value: object) -> tuple[int, ...]:
    """Parse benchmark seeds from YAML scalar, list, or comma-separated string."""

    if isinstance(value, bool):
        raise ValueError("Benchmark seeds must be integers, not booleans.")
    if isinstance(value, int):
        return (value,)
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",") if part.strip()]
    elif isinstance(value, list):
        parts = value
    else:
        raise ValueError("run.seeds must be an integer, string, or list of integers.")

    if not parts:
        raise ValueError("run.seeds must contain at least one seed.")

    seeds: list[int] = []
    for part in parts:
        if isinstance(part, bool):
            raise ValueError("Benchmark seeds must be integers, not booleans.")
        try:
            seeds.append(int(part))
        except (TypeError, ValueError) as exc:
            raise ValueError("run.seeds must contain only integers.") from exc
    return tuple(seeds)


def _timefold_configured(solver_settings_by_name: dict[str, dict[str, object]]) -> bool:
    """Return whether Timefold has a non-empty executable path configured."""

    value = solver_settings_by_name.get("timefold", {}).get("executable_path")
    if value is None:
        return False
    return bool(str(value).strip())


def _timefold_executable_text(solver_settings_by_name: dict[str, dict[str, object]]) -> str:
    """Return a readable Timefold executable setting."""

    value = solver_settings_by_name.get("timefold", {}).get("executable_path")
    if value is None or not str(value).strip():
        return "not configured"
    return str(value).strip()


def _seed_folder_name(seed: int) -> str:
    """Build a stable seed folder name."""

    prefix = "neg" if seed < 0 else ""
    return f"seed_{prefix}{abs(seed):04d}"


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    """Return stable value counts for an optional column."""

    if column not in frame.columns:
        return {}
    counts = frame[column].fillna("missing").astype(str).value_counts().sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def _render_count_table(counts: dict[str, int], label: str) -> list[str]:
    """Render a simple Markdown count table."""

    lines = [f"| {label} | count |", "| --- | ---: |"]
    if not counts:
        lines.append("| none | 0 |")
        return lines
    for key, value in counts.items():
        lines.append(f"| `{key}` | {value} |")
    return lines


def _render_selector_summary_table(selector_summary: pd.DataFrame) -> list[str]:
    """Render aggregate selector metrics for the Markdown summary."""

    if selector_summary.empty:
        return ["Selector aggregate summary is empty."]

    rows = selector_summary[selector_summary["summary_scope"].isin(["all_seeds_mean", "all_seeds_std"])]
    if rows.empty:
        rows = selector_summary.head(5)

    lines = [
        "| summary_scope | accuracy | balanced_accuracy | selected_objective | regret_vs_vbs | delta_vs_sbs |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows.to_dict(orient="records"):
        lines.append(
            "| "
            f"`{row.get('summary_scope')}` | "
            f"{_format_markdown_float(row.get('classification_accuracy'))} | "
            f"{_format_markdown_float(row.get('balanced_accuracy'))} | "
            f"{_format_markdown_float(row.get('average_selected_objective'))} | "
            f"{_format_markdown_float(row.get('regret_vs_virtual_best'))} | "
            f"{_format_markdown_float(row.get('delta_vs_single_best'))} |"
        )
    return lines


def _render_benchmark_note_table(benchmark_summary: pd.DataFrame) -> list[str]:
    """Render compact all-seed benchmark counts by solver."""

    if benchmark_summary.empty:
        return ["Benchmark aggregate summary is empty."]

    rows = benchmark_summary[benchmark_summary["summary_scope"] == "all_seeds"].copy()
    if rows.empty:
        rows = benchmark_summary.copy()
    rows = rows.sort_values(
        by=["solver_registry_name", "solver_support_status", "scoring_status"],
        kind="mergesort",
    )

    lines = [
        "| solver | support_status | scoring_status | runs | feasible | valid_objectives |",
        "| --- | --- | --- | ---: | ---: | ---: |",
    ]
    for row in rows.to_dict(orient="records"):
        lines.append(
            "| "
            f"`{row.get('solver_registry_name')}` | "
            f"`{row.get('solver_support_status')}` | "
            f"`{row.get('scoring_status')}` | "
            f"{int(row.get('num_runs') or 0)} | "
            f"{int(row.get('feasible_runs') or 0)} | "
            f"{int(row.get('valid_objective_runs') or 0)} |"
        )
    return lines


def _group_values(group_columns: list[str], group_values: object) -> dict[str, object]:
    """Normalize pandas group keys into a column-value mapping."""

    if len(group_columns) == 1:
        values = (group_values,)
    else:
        values = tuple(group_values)  # type: ignore[arg-type]
    return {
        column: (None if pd.isna(value) else value)
        for column, value in zip(group_columns, values, strict=True)
    }


def _coerce_bool(value: object) -> bool:
    """Convert CSV-style boolean values into booleans."""

    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def _mean_or_none(values: pd.Series) -> float | None:
    """Return a numeric mean when available."""

    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.mean())


def _median_or_none(values: pd.Series) -> float | None:
    """Return a numeric median when available."""

    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.median())


def _reduce_metric(values: pd.Series, reducer: str) -> float | None:
    """Reduce a selector metric column across seeds."""

    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    if reducer == "mean":
        return float(numeric.mean())
    if reducer == "std":
        if len(numeric.index) < 2:
            return None
        return float(numeric.std(ddof=1))
    if reducer == "min":
        return float(numeric.min())
    if reducer == "max":
        return float(numeric.max())
    raise ValueError(f"Unsupported metric reducer: {reducer}")


def _stable_unique_or_none(values: pd.Series) -> str | None:
    """Return a single stable value only when all non-empty values agree."""

    normalized = sorted(
        {
            str(value).strip()
            for value in values.tolist()
            if value is not None and not pd.isna(value) and str(value).strip()
        }
    )
    if len(normalized) == 1:
        return normalized[0]
    return None


def _optional_float(value: object) -> float | None:
    """Convert a scalar to a JSON/CSV-friendly float when possible."""

    if value is None or pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_optional_float(value: float | None) -> str:
    """Format optional float metrics consistently."""

    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.4f}"


def _format_markdown_float(value: object) -> str:
    """Format numeric values in Markdown tables."""

    number = _optional_float(value)
    if number is None:
        return "NA"
    return f"{number:.4f}"


def _path_or_not_written(path: Path | None) -> str:
    """Return a readable path value for optional artifacts."""

    if path is None:
        return "not written"
    return path.as_posix()


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_DATASET_ROOT",
    "DEFAULT_PROCESSED_DIR",
    "DEFAULT_RESULTS_DIR",
    "SeedStudyArtifacts",
    "SeedStudyResult",
    "SummaryStageResult",
    "SyntheticStudyArtifacts",
    "SyntheticStudyError",
    "SyntheticStudyResult",
    "SyntheticStudySettings",
    "run_synthetic_study",
]


if __name__ == "__main__":
    raise SystemExit(main())
