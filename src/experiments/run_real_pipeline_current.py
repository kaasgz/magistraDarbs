"""Run the current real-data core pipeline in an isolated artifact namespace.

This orchestrator is intentionally thin: it reuses the existing parser,
feature-table builder, full solver benchmark, selection-dataset builder,
selector training, and selector evaluation modules. Its job is to make the
real-data rerun reproducible and keep its outputs separate from legacy default
artifacts.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, fields
from pathlib import Path
from typing import Any, TypeVar

import pandas as pd

from src.experiments.full_benchmark import DEFAULT_FULL_SOLVER_PORTFOLIO, run_full_benchmark
from src.features.build_feature_table import build_feature_table
from src.parsers.real_dataset_inventory import (
    build_real_dataset_inventory,
    real_dataset_inventory_report,
)
from src.selection.build_selection_dataset import build_selection_dataset
from src.selection.evaluate_selector import SelectorEvaluationResult, evaluate_selector
from src.selection.train_selector import SelectorTrainingResult, train_selector
from src.utils import (
    collect_xml_files,
    ensure_parent_directory,
    get_compat_value,
    get_include_solver_objectives,
    get_model_choice,
    get_random_seed,
    get_solver_settings_by_name,
    get_split_settings,
    get_time_limit_seconds,
    load_yaml_config,
    write_run_summary,
)


LOGGER = logging.getLogger(__name__)

DEFAULT_CONFIG_PATH = Path("configs/real_pipeline_current.yaml")
DEFAULT_INSTANCE_FOLDER = Path("data/raw/real")
DEFAULT_PROCESSED_DIR = Path("data/processed/real_pipeline_current")
DEFAULT_RESULTS_DIR = Path("data/results/real_pipeline_current")

_StepResult = TypeVar("_StepResult")


@dataclass(frozen=True, slots=True)
class RealPipelineSettings:
    """Resolved settings for one current real-data pipeline rerun."""

    input_folder: Path
    processed_dir: Path
    results_dir: Path
    random_seed: int
    time_limit_seconds: int
    fail_on_unparseable_inventory: bool
    include_solver_objectives: bool
    model_name: str
    split_strategy: str
    test_size: float
    cross_validation_folds: int | None
    repeats: int
    timefold_executable_path: Path | None
    timefold_time_limit_seconds: int | None
    timefold_command_arguments: tuple[str, ...]
    config_path: Path | None
    config: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class RealPipelineArtifacts:
    """All artifact paths written by the current real-data pipeline."""

    inventory_csv: Path
    features_csv: Path
    features_run_summary: Path
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
    pipeline_summary_markdown: Path
    pipeline_run_summary_json: Path


@dataclass(frozen=True, slots=True)
class SummaryStageResult:
    """Summary artifacts written at the end of the real-data pipeline."""

    summary_markdown: Path
    run_summary_json: Path


@dataclass(frozen=True, slots=True)
class RealPipelineResult:
    """Main artifacts and headline metrics from one real-data rerun."""

    inventory_csv: Path
    features_csv: Path
    benchmark_csv: Path
    selection_dataset_csv: Path
    model_path: Path
    feature_importance_csv: Path | None
    evaluation_report_csv: Path
    evaluation_summary_csv: Path
    evaluation_summary_markdown: Path
    summary_markdown: Path
    run_summary_json: Path
    num_xml_files: int
    num_parseable_files: int
    selector_accuracy: float
    selector_regret_vs_virtual_best: float


class RealPipelineError(RuntimeError):
    """A critical real-data pipeline step failed."""

    def __init__(self, step_name: str, cause: Exception) -> None:
        self.step_name = step_name
        self.cause = cause
        super().__init__(f"{step_name} failed: {type(cause).__name__}: {cause}")


def run_real_pipeline_current(config_path: str | Path = DEFAULT_CONFIG_PATH) -> RealPipelineResult:
    """Run the current real-data pipeline using one YAML configuration file."""

    settings = _resolve_settings(config_path)
    artifacts = _build_artifact_paths(settings.processed_dir, settings.results_dir)
    _validate_pipeline_settings(settings, artifacts)
    _log_output_refresh(artifacts)

    total_steps = 7

    inventory_csv = _execute_step(
        1,
        total_steps,
        "Scan real dataset inventory",
        lambda: build_real_dataset_inventory(
            input_folder=settings.input_folder,
            output_csv=artifacts.inventory_csv,
        ),
        success_message=lambda path: real_dataset_inventory_report(path),
    )
    _validate_inventory(
        inventory_csv=inventory_csv,
        fail_on_unparseable=settings.fail_on_unparseable_inventory,
    )

    features_csv = _execute_step(
        2,
        total_steps,
        "Extract structural features",
        lambda: build_feature_table(
            input_folder=settings.input_folder,
            output_csv=artifacts.features_csv,
            random_seed=settings.random_seed,
            config_path=settings.config_path,
            config=settings.config,
            run_summary_path=artifacts.features_run_summary,
        ),
        success_message=lambda path: f"Features saved to {path.as_posix()}",
    )
    _validate_non_empty_csv(features_csv, "feature table")

    benchmark_csv = _execute_step(
        3,
        total_steps,
        "Run full solver benchmark",
        lambda: run_full_benchmark(
            instance_folder=settings.input_folder,
            output_csv=artifacts.benchmark_csv,
            time_limit_seconds=settings.time_limit_seconds,
            random_seed=settings.random_seed,
            timefold_executable_path=settings.timefold_executable_path,
            timefold_time_limit_seconds=settings.timefold_time_limit_seconds,
            timefold_command_arguments=settings.timefold_command_arguments,
            run_summary_path=artifacts.benchmark_run_summary,
        ),
        success_message=lambda path: f"Benchmark results saved to {path.as_posix()}",
    )
    _validate_timefold_status(benchmark_csv, timefold_configured=settings.timefold_executable_path is not None)

    selection_dataset_csv = _execute_step(
        4,
        total_steps,
        "Build selection dataset",
        lambda: build_selection_dataset(
            features_csv=features_csv,
            benchmark_csv=benchmark_csv,
            output_csv=artifacts.selection_dataset_csv,
            include_solver_objectives=settings.include_solver_objectives,
            config_path=settings.config_path,
            config=settings.config,
            run_summary_path=artifacts.selection_dataset_run_summary,
        ),
        success_message=lambda path: f"Selection dataset saved to {path.as_posix()}",
    )
    _validate_labeled_selection_dataset(selection_dataset_csv)

    training_result = _execute_step(
        5,
        total_steps,
        "Train selector",
        lambda: train_selector(
            dataset_csv=selection_dataset_csv,
            model_path=artifacts.model_path,
            feature_importance_csv=artifacts.feature_importance_csv,
            random_seed=settings.random_seed,
            test_size=settings.test_size,
            model_name=settings.model_name,
            split_strategy=settings.split_strategy,
            cross_validation_folds=settings.cross_validation_folds,
            repeats=settings.repeats,
            config_path=settings.config_path,
            config=settings.config,
            run_summary_path=artifacts.training_run_summary,
        ),
        success_message=_training_success_message,
    )

    evaluation_result = _execute_step(
        6,
        total_steps,
        "Evaluate selector",
        lambda: evaluate_selector(
            dataset_csv=selection_dataset_csv,
            benchmark_csv=benchmark_csv,
            model_path=training_result.model_path,
            report_csv=artifacts.evaluation_report_csv,
            summary_csv=artifacts.evaluation_summary_csv,
            summary_markdown=artifacts.evaluation_summary_markdown,
            random_seed=settings.random_seed,
            test_size=settings.test_size,
            model_name=settings.model_name,
            split_strategy=settings.split_strategy,
            cross_validation_folds=settings.cross_validation_folds,
            repeats=settings.repeats,
            config_path=settings.config_path,
            config=settings.config,
            run_summary_path=artifacts.evaluation_run_summary,
        ),
        success_message=_evaluation_success_message,
    )

    summary_stage = _execute_step(
        7,
        total_steps,
        "Write real pipeline summary",
        lambda: _write_pipeline_summary(
            settings=settings,
            artifacts=artifacts,
            training_result=training_result,
            evaluation_result=evaluation_result,
        ),
        success_message=lambda result: (
            f"Summary Markdown saved to {result.summary_markdown.as_posix()}\n"
            f"Summary JSON saved to {result.run_summary_json.as_posix()}"
        ),
    )

    inventory_counts = _inventory_counts(inventory_csv)
    result = RealPipelineResult(
        inventory_csv=inventory_csv,
        features_csv=features_csv,
        benchmark_csv=benchmark_csv,
        selection_dataset_csv=selection_dataset_csv,
        model_path=training_result.model_path,
        feature_importance_csv=training_result.feature_importance_path,
        evaluation_report_csv=evaluation_result.report_path,
        evaluation_summary_csv=evaluation_result.summary_csv_path,
        evaluation_summary_markdown=evaluation_result.summary_markdown_path,
        summary_markdown=summary_stage.summary_markdown,
        run_summary_json=summary_stage.run_summary_json,
        num_xml_files=inventory_counts["total_files"],
        num_parseable_files=inventory_counts["parseable_files"],
        selector_accuracy=evaluation_result.classification_accuracy,
        selector_regret_vs_virtual_best=evaluation_result.regret_vs_virtual_best,
    )
    _print_final_summary(result)
    return result


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the current real-data rerun."""

    parser = argparse.ArgumentParser(
        description="Run the current real-data pipeline into isolated artifacts.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the current real-data pipeline YAML config.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the current real-data pipeline from the command line."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        run_real_pipeline_current(args.config)
    except RealPipelineError as exc:
        print(
            f"Real-data pipeline failed during '{exc.step_name}': "
            f"{type(exc.cause).__name__}: {exc.cause}",
            flush=True,
        )
        return 1
    except Exception as exc:
        print(f"Real-data pipeline failed: {type(exc).__name__}: {exc}", flush=True)
        return 1
    return 0


def _resolve_settings(config_path: str | Path) -> RealPipelineSettings:
    """Resolve pipeline settings from a YAML config."""

    resolved_config_path = Path(config_path)
    config = load_yaml_config(resolved_config_path)
    split_settings = get_split_settings(config)
    solver_settings = get_solver_settings_by_name(config)
    timefold_settings = solver_settings.get("timefold", {})

    input_folder = Path(
        get_compat_value(config, ["paths.instance_folder", "paths.input_folder"], DEFAULT_INSTANCE_FOLDER)
    )
    processed_dir = Path(get_compat_value(config, ["paths.processed_dir"], DEFAULT_PROCESSED_DIR))
    results_dir = Path(get_compat_value(config, ["paths.results_dir"], DEFAULT_RESULTS_DIR))

    return RealPipelineSettings(
        input_folder=input_folder,
        processed_dir=processed_dir,
        results_dir=results_dir,
        random_seed=get_random_seed(config, 42),
        time_limit_seconds=get_time_limit_seconds(config, 60),
        fail_on_unparseable_inventory=bool(
            get_compat_value(config, ["run.fail_on_unparseable_inventory"], False)
        ),
        include_solver_objectives=get_include_solver_objectives(config, True),
        model_name=get_model_choice(config, "random_forest"),
        split_strategy=split_settings.strategy,
        test_size=split_settings.test_size,
        cross_validation_folds=split_settings.cross_validation_folds,
        repeats=split_settings.repeats,
        timefold_executable_path=_optional_path(timefold_settings.get("executable_path")),
        timefold_time_limit_seconds=_optional_int(timefold_settings.get("time_limit_seconds")),
        timefold_command_arguments=_optional_string_tuple(timefold_settings.get("command_arguments")),
        config_path=resolved_config_path,
        config=config,
    )


def _build_artifact_paths(processed_dir: Path, results_dir: Path) -> RealPipelineArtifacts:
    """Return stable current-pipeline artifact paths."""

    return RealPipelineArtifacts(
        inventory_csv=processed_dir / "real_dataset_inventory.csv",
        features_csv=processed_dir / "features.csv",
        features_run_summary=processed_dir / "features_run_summary.json",
        benchmark_csv=results_dir / "benchmark_results.csv",
        benchmark_run_summary=results_dir / "benchmark_results_run_summary.json",
        selection_dataset_csv=processed_dir / "selection_dataset.csv",
        selection_dataset_run_summary=processed_dir / "selection_dataset_run_summary.json",
        model_path=results_dir / "random_forest_selector.joblib",
        feature_importance_csv=results_dir / "feature_importance.csv",
        training_run_summary=results_dir / "selector_training_run_summary.json",
        evaluation_report_csv=results_dir / "selector_evaluation.csv",
        evaluation_summary_csv=results_dir / "selector_evaluation_summary.csv",
        evaluation_summary_markdown=results_dir / "selector_evaluation_summary.md",
        evaluation_run_summary=results_dir / "selector_evaluation_run_summary.json",
        pipeline_summary_markdown=results_dir / "real_pipeline_current_summary.md",
        pipeline_run_summary_json=results_dir / "real_pipeline_current_run_summary.json",
    )


def _validate_pipeline_settings(
    settings: RealPipelineSettings,
    artifacts: RealPipelineArtifacts,
) -> None:
    """Validate settings before any stage writes artifacts."""

    if not settings.input_folder.exists():
        raise FileNotFoundError(f"Real input folder does not exist: {settings.input_folder}")
    if not settings.input_folder.is_dir():
        raise NotADirectoryError(f"Real input path is not a folder: {settings.input_folder}")

    xml_files = collect_xml_files(settings.input_folder)
    if not xml_files:
        raise ValueError(f"No XML files found under {settings.input_folder.as_posix()}.")

    if settings.time_limit_seconds <= 0:
        raise ValueError("run.time_limit_seconds must be positive.")
    if not 0.0 < settings.test_size < 1.0:
        raise ValueError("split.test_size must be between 0 and 1.")
    if settings.cross_validation_folds is not None and settings.cross_validation_folds < 2:
        raise ValueError("split.cross_validation_folds must be at least 2 when provided.")
    if settings.repeats <= 0:
        raise ValueError("split.repeats must be positive.")

    _reject_legacy_root(settings.processed_dir, Path("data/processed"), "processed_dir")
    _reject_legacy_root(settings.results_dir, Path("data/results"), "results_dir")
    _validate_artifact_namespace(settings, artifacts)

    if settings.timefold_executable_path is None:
        LOGGER.info(
            "Timefold executable is not configured; Timefold benchmark rows will be marked "
            "NOT_CONFIGURED/not_configured."
        )
    elif not _timefold_executable_exists(settings.timefold_executable_path):
        raise FileNotFoundError(
            f"Configured Timefold executable does not exist: {settings.timefold_executable_path}"
        )


def _reject_legacy_root(path: Path, legacy_root: Path, setting_name: str) -> None:
    """Reject legacy top-level artifact roots for this isolated rerun."""

    if path.resolve() == legacy_root.resolve():
        raise ValueError(
            f"paths.{setting_name} must be an isolated subfolder, not {legacy_root.as_posix()}."
        )


def _validate_artifact_namespace(
    settings: RealPipelineSettings,
    artifacts: RealPipelineArtifacts,
) -> None:
    """Ensure all outputs stay under the configured isolated folders."""

    processed_root = settings.processed_dir.resolve()
    results_root = settings.results_dir.resolve()
    for field_name, output_path in _artifact_items(artifacts):
        root = processed_root if field_name in _processed_artifact_fields() else results_root
        if not _is_relative_to(output_path.resolve(), root):
            raise ValueError(
                f"Artifact {field_name} must stay under {root.as_posix()}: "
                f"{output_path.as_posix()}"
            )


def _processed_artifact_fields() -> set[str]:
    """Return artifact dataclass fields that belong under processed_dir."""

    return {
        "inventory_csv",
        "features_csv",
        "features_run_summary",
        "selection_dataset_csv",
        "selection_dataset_run_summary",
    }


def _is_relative_to(path: Path, root: Path) -> bool:
    """Return whether ``path`` is inside ``root`` without requiring Python 3.9 APIs."""

    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _timefold_executable_exists(executable_path: Path) -> bool:
    """Return whether the configured Timefold executable can be launched."""

    if executable_path.exists():
        return True
    return shutil.which(str(executable_path)) is not None


def _log_output_refresh(artifacts: RealPipelineArtifacts) -> None:
    """Log any current-pipeline artifacts that already exist before refreshing them."""

    existing = [path for _, path in _artifact_items(artifacts) if path.exists()]
    if not existing:
        LOGGER.info("Writing all current real-data artifacts into a fresh isolated namespace.")
        return

    preview = ", ".join(path.as_posix() for path in existing[:6])
    suffix = "" if len(existing) <= 6 else f", and {len(existing) - 6} more"
    LOGGER.info("Refreshing existing current-pipeline artifacts: %s%s", preview, suffix)


def _artifact_items(artifacts: RealPipelineArtifacts) -> list[tuple[str, Path]]:
    """Return artifact dataclass fields as name/path pairs."""

    return [(field.name, getattr(artifacts, field.name)) for field in fields(artifacts)]


def _execute_step(
    step_index: int,
    total_steps: int,
    step_name: str,
    action: Callable[[], _StepResult],
    *,
    success_message: Callable[[_StepResult], str],
) -> _StepResult:
    """Run one pipeline step with clean progress logs."""

    print(f"[{step_index}/{total_steps}] {step_name}...", flush=True)
    started_at = time.perf_counter()
    try:
        result = action()
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        print(f"[{step_index}/{total_steps}] {step_name} failed after {elapsed:.2f}s", flush=True)
        raise RealPipelineError(step_name, exc) from exc

    elapsed = time.perf_counter() - started_at
    print(f"[{step_index}/{total_steps}] {step_name} completed in {elapsed:.2f}s", flush=True)
    message = success_message(result).strip()
    if message:
        print(message, flush=True)
    return result


def _validate_inventory(inventory_csv: Path, *, fail_on_unparseable: bool) -> None:
    """Validate inventory output and optionally fail on any unparseable files."""

    counts = _inventory_counts(inventory_csv)
    if counts["total_files"] <= 0:
        raise ValueError("Inventory did not find any XML files.")
    if counts["parseable_files"] <= 0:
        raise ValueError("Inventory did not find any parseable XML files.")
    if fail_on_unparseable and counts["failed_files"] > 0:
        raise ValueError(
            f"Inventory found {counts['failed_files']} unparseable XML files; "
            "set run.fail_on_unparseable_inventory=false to continue with parseable files."
        )


def _validate_non_empty_csv(csv_path: Path, label: str) -> None:
    """Fail early when a required stage writes an empty CSV."""

    table = pd.read_csv(csv_path)
    if table.empty:
        raise ValueError(f"The {label} is empty: {csv_path.as_posix()}")


def _validate_timefold_status(benchmark_csv: Path, *, timefold_configured: bool) -> None:
    """Verify the Timefold benchmark rows communicate configured support explicitly."""

    table = pd.read_csv(benchmark_csv)
    if table.empty:
        raise ValueError("Benchmark results are empty.")

    observed_solvers = set(table["solver_registry_name"].dropna().astype(str))
    missing_solvers = sorted(set(DEFAULT_FULL_SOLVER_PORTFOLIO).difference(observed_solvers))
    if missing_solvers:
        raise ValueError(f"Benchmark results are missing solver rows for: {', '.join(missing_solvers)}")

    timefold_rows = table[table["solver_registry_name"].astype(str) == "timefold"]
    if timefold_rows.empty:
        raise ValueError("Benchmark results are missing Timefold rows.")

    support_statuses = {
        str(value).strip().casefold()
        for value in timefold_rows.get("solver_support_status", pd.Series(dtype="string")).dropna()
    }
    statuses = {
        str(value).strip().casefold()
        for value in timefold_rows.get("status", pd.Series(dtype="string")).dropna()
    }
    if not timefold_configured and "not_configured" not in support_statuses.union(statuses):
        raise ValueError("Unconfigured Timefold rows were not marked as not_configured.")


def _validate_labeled_selection_dataset(selection_dataset_csv: Path) -> None:
    """Ensure the selector has enough labeled rows to run validation."""

    dataset = pd.read_csv(selection_dataset_csv)
    if dataset.empty:
        raise ValueError("Selection dataset is empty.")
    if "best_solver" not in dataset.columns:
        raise ValueError("Selection dataset is missing the best_solver target column.")
    labeled_rows = int(dataset["best_solver"].notna().sum())
    if labeled_rows < 2:
        raise ValueError(
            "Selection dataset must contain at least two labeled rows before selector training."
        )


def _write_pipeline_summary(
    *,
    settings: RealPipelineSettings,
    artifacts: RealPipelineArtifacts,
    training_result: SelectorTrainingResult,
    evaluation_result: SelectorEvaluationResult,
) -> SummaryStageResult:
    """Write Markdown and JSON summaries for the complete real-data rerun."""

    inventory = pd.read_csv(artifacts.inventory_csv)
    features = pd.read_csv(artifacts.features_csv)
    benchmarks = pd.read_csv(artifacts.benchmark_csv)
    selection_dataset = pd.read_csv(artifacts.selection_dataset_csv)
    feature_importance = _read_optional_csv(training_result.feature_importance_path)

    inventory_counts = _inventory_counts(artifacts.inventory_csv)
    support_counts = _value_counts(benchmarks, "solver_support_status")
    status_counts = _value_counts(benchmarks, "status")
    solver_rows = _value_counts(benchmarks, "solver_registry_name")
    labeled_rows = int(selection_dataset["best_solver"].notna().sum())
    feasible_runs = int(benchmarks["feasible"].map(_coerce_bool).sum()) if "feasible" in benchmarks else 0

    ensure_parent_directory(artifacts.pipeline_summary_markdown)
    artifacts.pipeline_summary_markdown.write_text(
        _render_summary_markdown(
            settings=settings,
            artifacts=artifacts,
            training_result=training_result,
            evaluation_result=evaluation_result,
            feature_importance=feature_importance,
            inventory_rows=len(inventory.index),
            feature_rows=len(features.index),
            benchmark_rows=len(benchmarks.index),
            selection_rows=len(selection_dataset.index),
            labeled_rows=labeled_rows,
            feasible_runs=feasible_runs,
            inventory_counts=inventory_counts,
            support_counts=support_counts,
            status_counts=status_counts,
            solver_rows=solver_rows,
        ),
        encoding="utf-8",
    )

    write_run_summary(
        artifacts.pipeline_run_summary_json,
        stage_name="real_pipeline_current",
        config_path=settings.config_path,
        config=settings.config,
        settings={
            "random_seed": settings.random_seed,
            "time_limit_seconds": settings.time_limit_seconds,
            "solver_portfolio": DEFAULT_FULL_SOLVER_PORTFOLIO,
            "include_solver_objectives": settings.include_solver_objectives,
            "model_name": settings.model_name,
            "split_strategy": settings.split_strategy,
            "test_size": settings.test_size,
            "cross_validation_folds": settings.cross_validation_folds,
            "repeats": settings.repeats,
            "timefold_executable_path": settings.timefold_executable_path,
            "timefold_time_limit_seconds": settings.timefold_time_limit_seconds,
            "timefold_command_arguments": list(settings.timefold_command_arguments),
            "fail_on_unparseable_inventory": settings.fail_on_unparseable_inventory,
        },
        inputs={
            "instance_folder": settings.input_folder,
        },
        outputs={
            "inventory_csv": artifacts.inventory_csv,
            "features_csv": artifacts.features_csv,
            "benchmark_csv": artifacts.benchmark_csv,
            "selection_dataset_csv": artifacts.selection_dataset_csv,
            "model_path": training_result.model_path,
            "feature_importance_csv": training_result.feature_importance_path,
            "evaluation_report_csv": evaluation_result.report_path,
            "evaluation_summary_csv": evaluation_result.summary_csv_path,
            "evaluation_summary_markdown": evaluation_result.summary_markdown_path,
            "summary_markdown": artifacts.pipeline_summary_markdown,
            "run_summary_json": artifacts.pipeline_run_summary_json,
        },
        results={
            **inventory_counts,
            "feature_rows": len(features.index),
            "benchmark_rows": len(benchmarks.index),
            "selection_rows": len(selection_dataset.index),
            "labeled_rows": labeled_rows,
            "feasible_runs": feasible_runs,
            "solver_rows": solver_rows,
            "support_counts": support_counts,
            "status_counts": status_counts,
            "training_accuracy": training_result.accuracy,
            "training_balanced_accuracy": training_result.balanced_accuracy,
            "evaluation_accuracy": evaluation_result.classification_accuracy,
            "evaluation_balanced_accuracy": evaluation_result.balanced_accuracy,
            "regret_vs_virtual_best": evaluation_result.regret_vs_virtual_best,
            "delta_vs_single_best": evaluation_result.delta_vs_single_best,
            "improvement_vs_single_best": evaluation_result.improvement_vs_single_best,
        },
    )
    return SummaryStageResult(
        summary_markdown=artifacts.pipeline_summary_markdown,
        run_summary_json=artifacts.pipeline_run_summary_json,
    )


def _render_summary_markdown(
    *,
    settings: RealPipelineSettings,
    artifacts: RealPipelineArtifacts,
    training_result: SelectorTrainingResult,
    evaluation_result: SelectorEvaluationResult,
    feature_importance: pd.DataFrame | None,
    inventory_rows: int,
    feature_rows: int,
    benchmark_rows: int,
    selection_rows: int,
    labeled_rows: int,
    feasible_runs: int,
    inventory_counts: dict[str, int],
    support_counts: dict[str, int],
    status_counts: dict[str, int],
    solver_rows: dict[str, int],
) -> str:
    """Render a concise thesis-oriented Markdown run summary."""

    timefold_path = (
        settings.timefold_executable_path.as_posix()
        if settings.timefold_executable_path is not None
        else "not configured"
    )
    lines = [
        "# Current Real-Data Pipeline Summary",
        "",
        "## Settings",
        "",
        f"- Real input folder: `{settings.input_folder.as_posix()}`",
        f"- Processed artifact folder: `{settings.processed_dir.as_posix()}`",
        f"- Results artifact folder: `{settings.results_dir.as_posix()}`",
        f"- Random seed: `{settings.random_seed}`",
        f"- Per-solver time limit: `{settings.time_limit_seconds}` seconds",
        f"- Solver portfolio: `{', '.join(DEFAULT_FULL_SOLVER_PORTFOLIO)}`",
        f"- Timefold executable: `{timefold_path}`",
        f"- Selector split: `{settings.split_strategy}`",
        f"- Cross-validation folds: `{settings.cross_validation_folds or 'none'}`",
        f"- Repeats: `{settings.repeats}`",
        "",
        "## Artifacts",
        "",
        f"- Real dataset inventory: `{artifacts.inventory_csv.as_posix()}`",
        f"- Features: `{artifacts.features_csv.as_posix()}`",
        f"- Benchmark results: `{artifacts.benchmark_csv.as_posix()}`",
        f"- Selection dataset: `{artifacts.selection_dataset_csv.as_posix()}`",
        f"- Selector model: `{training_result.model_path.as_posix()}`",
        f"- Feature importance: `{_path_or_not_written(training_result.feature_importance_path)}`",
        f"- Selector evaluation: `{evaluation_result.report_path.as_posix()}`",
        f"- Selector evaluation summary CSV: `{evaluation_result.summary_csv_path.as_posix()}`",
        f"- Selector evaluation summary Markdown: `{evaluation_result.summary_markdown_path.as_posix()}`",
        "",
        "## Headline Results",
        "",
        f"- Inventory rows: `{inventory_rows}`",
        f"- XML files: `{inventory_counts['total_files']}`",
        f"- Parseable XML files: `{inventory_counts['parseable_files']}`",
        f"- Failed XML files: `{inventory_counts['failed_files']}`",
        f"- Feature rows: `{feature_rows}`",
        f"- Benchmark rows: `{benchmark_rows}`",
        f"- Feasible solver runs: `{feasible_runs}`",
        f"- Selection rows: `{selection_rows}`",
        f"- Labeled selection rows: `{labeled_rows}`",
        f"- Training validation accuracy: `{training_result.accuracy:.4f}`",
        f"- Training balanced accuracy: `{_format_optional_float(training_result.balanced_accuracy)}`",
        f"- Evaluation accuracy: `{evaluation_result.classification_accuracy:.4f}`",
        f"- Evaluation balanced accuracy: `{_format_optional_float(evaluation_result.balanced_accuracy)}`",
        f"- Mean regret vs virtual best: `{evaluation_result.regret_vs_virtual_best:.4f}`",
        f"- Mean delta vs single best: `{evaluation_result.delta_vs_single_best:.4f}`",
        "",
        "## Rows By Solver",
        "",
        *_render_count_table(solver_rows, "solver"),
        "",
        "## Solver Support Status Counts",
        "",
        *_render_count_table(support_counts, "support_status"),
        "",
        "## Solver Run Status Counts",
        "",
        *_render_count_table(status_counts, "status"),
        "",
        "## Top Feature Importance",
        "",
        *_render_feature_importance_table(feature_importance),
        "",
        "## Notes",
        "",
        "- Outputs are isolated under the current real-data pipeline folders and do not overwrite legacy default artifacts.",
        "- Timefold is included in the fixed portfolio. When no executable is configured, its rows are recorded as `not_configured` rather than failing the run.",
        "- Selector training excludes benchmark-derived `objective_*` columns to avoid target leakage.",
        "",
    ]
    return "\n".join(lines)


def _training_success_message(result: SelectorTrainingResult) -> str:
    """Format one concise training-stage success message."""

    return (
        f"Model saved to {result.model_path.as_posix()}\n"
        f"Feature importance: {_path_or_not_written(result.feature_importance_path)}\n"
        f"Validation accuracy: {result.accuracy:.4f}; "
        f"balanced accuracy: {_format_optional_float(result.balanced_accuracy)}"
    )


def _evaluation_success_message(result: SelectorEvaluationResult) -> str:
    """Format one concise evaluation-stage success message."""

    return (
        f"Evaluation report: {result.report_path.as_posix()}\n"
        f"Evaluation summary CSV: {result.summary_csv_path.as_posix()}\n"
        f"Evaluation summary Markdown: {result.summary_markdown_path.as_posix()}\n"
        f"Accuracy: {result.classification_accuracy:.4f}; "
        f"balanced accuracy: {_format_optional_float(result.balanced_accuracy)}\n"
        f"Regret vs virtual best: {result.regret_vs_virtual_best:.4f}"
    )


def _print_final_summary(result: RealPipelineResult) -> None:
    """Print a short completion summary after a successful run."""

    print("Current real-data pipeline completed successfully.", flush=True)
    print(f"Inventory: {result.inventory_csv.as_posix()}", flush=True)
    print(f"Features: {result.features_csv.as_posix()}", flush=True)
    print(f"Benchmarks: {result.benchmark_csv.as_posix()}", flush=True)
    print(f"Selection dataset: {result.selection_dataset_csv.as_posix()}", flush=True)
    print(f"Selector evaluation summary: {result.evaluation_summary_csv.as_posix()}", flush=True)
    print(f"Run summary: {result.run_summary_json.as_posix()}", flush=True)


def _inventory_counts(inventory_csv: Path) -> dict[str, int]:
    """Return inventory parseability counts."""

    inventory = pd.read_csv(inventory_csv)
    total_files = int(len(inventory.index))
    parseable_files = (
        int(inventory["parseable"].map(_coerce_bool).sum()) if "parseable" in inventory.columns else 0
    )
    return {
        "total_files": total_files,
        "parseable_files": parseable_files,
        "failed_files": total_files - parseable_files,
    }


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:
    """Return stable value counts for an optional dataframe column."""

    if column not in frame.columns:
        return {}
    counts = frame[column].fillna("missing").astype(str).value_counts().sort_index()
    return {str(key): int(value) for key, value in counts.items()}


def _read_optional_csv(path: Path | None) -> pd.DataFrame | None:
    """Read an optional CSV file for reporting."""

    if path is None or not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return None


def _render_count_table(counts: dict[str, int], label: str) -> list[str]:
    """Render one simple Markdown table from value counts."""

    lines = [f"| {label} | count |", "| --- | ---: |"]
    if not counts:
        lines.append("| none | 0 |")
        return lines
    for key, value in counts.items():
        lines.append(f"| `{key}` | {value} |")
    return lines


def _render_feature_importance_table(feature_importance: pd.DataFrame | None) -> list[str]:
    """Render the top feature-importance rows for the summary report."""

    if feature_importance is None or feature_importance.empty:
        return ["Feature importance was not available for this model."]

    required_columns = {"importance_rank", "source_feature", "feature_group", "importance"}
    if not required_columns.issubset(feature_importance.columns):
        return ["Feature importance CSV exists, but it does not have the expected columns."]

    lines = [
        "| rank | source_feature | feature_group | importance |",
        "| ---: | --- | --- | ---: |",
    ]
    for row in feature_importance.head(10).to_dict(orient="records"):
        lines.append(
            "| "
            f"{int(row['importance_rank'])} | "
            f"`{row['source_feature']}` | "
            f"`{row['feature_group']}` | "
            f"{float(row['importance']):.6f} |"
        )
    return lines


def _coerce_bool(value: object) -> bool:
    """Convert CSV-style boolean values into booleans."""

    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def _format_optional_float(value: float | None) -> str:
    """Format optional float metrics consistently."""

    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.4f}"


def _path_or_not_written(path: Path | None) -> str:
    """Return a readable path value for optional artifacts."""

    if path is None:
        return "not written"
    return path.as_posix()


def _optional_path(value: object) -> Path | None:
    """Convert a nullable path-like config value."""

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Path(text)


def _optional_int(value: object) -> int | None:
    """Convert a nullable integer config value."""

    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("Integer configuration values must not be booleans.")
    return int(value)


def _optional_string_tuple(value: object) -> tuple[str, ...]:
    """Convert nullable command arguments into a tuple of strings."""

    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("Timefold command_arguments must be a list.")
    return tuple(str(item) for item in value)


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_INSTANCE_FOLDER",
    "DEFAULT_PROCESSED_DIR",
    "DEFAULT_RESULTS_DIR",
    "RealPipelineArtifacts",
    "RealPipelineError",
    "RealPipelineResult",
    "RealPipelineSettings",
    "run_real_pipeline_current",
]


if __name__ == "__main__":
    raise SystemExit(main())
