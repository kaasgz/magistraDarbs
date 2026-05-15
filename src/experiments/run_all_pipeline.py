"""Run the main thesis pipeline in one explicit, reproducible order."""

from __future__ import annotations

import argparse
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, TypeVar

from src.experiments.run_benchmarks import (
    DEFAULT_CONFIG_PATH as DEFAULT_BENCHMARK_CONFIG_PATH,
    run_benchmarks_from_config,
)
from src.features.build_feature_table import (
    DEFAULT_CONFIG_PATH as DEFAULT_FEATURE_CONFIG_PATH,
    build_feature_table_from_config,
)
from src.parsers.real_dataset_inventory import (
    DEFAULT_REAL_INPUT_FOLDER,
    DEFAULT_REAL_OUTPUT_PATH,
    build_real_dataset_inventory,
    real_dataset_inventory_report,
)
from src.selection.build_selection_dataset import build_selection_dataset_from_config
from src.selection.evaluate_selector import SelectorEvaluationResult
from src.selection.evaluate_selector import evaluate_selector_from_config
from src.selection.train_selector import SelectorTrainingResult
from src.selection.train_selector import train_selector_from_config
from src.utils import get_compat_path, get_compat_value, load_yaml_config


DEFAULT_SELECTOR_CONFIG_PATH = Path("configs/selector_config.yaml")

_StepResult = TypeVar("_StepResult")


@dataclass(frozen=True, slots=True)
class PipelineSettings:
    """Resolved settings used by the run-all pipeline helper."""

    feature_config_path: Path
    benchmark_config_path: Path
    selector_config_path: Path
    include_inventory: bool
    inventory_input_folder: Path
    inventory_output_csv: Path


@dataclass(slots=True)
class PipelineRunResult:
    """Summary of the written artifacts from one full pipeline run."""

    inventory_csv: Path | None
    features_csv: Path
    benchmark_csv: Path
    selection_dataset_csv: Path
    model_path: Path
    feature_importance_csv: Path | None
    evaluation_report_csv: Path
    evaluation_summary_csv: Path
    evaluation_summary_markdown: Path


class PipelineRunError(RuntimeError):
    """A critical pipeline step failed and the run was stopped."""

    def __init__(self, step_name: str, cause: Exception) -> None:
        self.step_name = step_name
        self.cause = cause
        super().__init__(f"{step_name} failed: {type(cause).__name__}: {cause}")


def run_all_pipeline(
    config_path: str | Path | None = None,
    *,
    include_inventory: bool | None = None,
) -> PipelineRunResult:
    """Run the core thesis pipeline in the documented order."""

    settings = _resolve_pipeline_settings(config_path, include_inventory=include_inventory)
    total_steps = 6 if settings.include_inventory else 5
    step_index = 0

    inventory_csv: Path | None = None
    if settings.include_inventory:
        step_index += 1
        inventory_csv = _execute_step(
            step_index,
            total_steps,
            "Build dataset inventory",
            lambda: build_real_dataset_inventory(
                input_folder=settings.inventory_input_folder,
                output_csv=settings.inventory_output_csv,
            ),
            success_message=lambda path: real_dataset_inventory_report(path),
        )

    step_index += 1
    features_csv = _execute_step(
        step_index,
        total_steps,
        "Build feature table",
        lambda: build_feature_table_from_config(settings.feature_config_path),
        success_message=lambda path: f"Features saved to {path.as_posix()}",
    )

    step_index += 1
    benchmark_csv = _execute_step(
        step_index,
        total_steps,
        "Run benchmarks",
        lambda: run_benchmarks_from_config(settings.benchmark_config_path),
        success_message=lambda path: f"Benchmark results saved to {path.as_posix()}",
    )

    step_index += 1
    selection_dataset_csv = _execute_step(
        step_index,
        total_steps,
        "Build selection dataset",
        lambda: build_selection_dataset_from_config(settings.selector_config_path),
        success_message=lambda path: f"Selection dataset saved to {path.as_posix()}",
    )

    step_index += 1
    training_result = _execute_step(
        step_index,
        total_steps,
        "Train selector",
        lambda: train_selector_from_config(settings.selector_config_path),
        success_message=_training_success_message,
    )

    step_index += 1
    evaluation_result = _execute_step(
        step_index,
        total_steps,
        "Evaluate selector",
        lambda: evaluate_selector_from_config(settings.selector_config_path),
        success_message=_evaluation_success_message,
    )

    result = PipelineRunResult(
        inventory_csv=inventory_csv,
        features_csv=features_csv,
        benchmark_csv=benchmark_csv,
        selection_dataset_csv=selection_dataset_csv,
        model_path=training_result.model_path,
        feature_importance_csv=training_result.feature_importance_path,
        evaluation_report_csv=evaluation_result.report_path,
        evaluation_summary_csv=evaluation_result.summary_csv_path,
        evaluation_summary_markdown=evaluation_result.summary_markdown_path,
    )
    _print_final_summary(result)
    return result


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the run-all pipeline helper."""

    parser = argparse.ArgumentParser(
        description="Run the main thesis pipeline in one explicit, reproducible order.",
    )
    parser.add_argument(
        "--config",
        default=None,
        help=(
            "Optional pipeline YAML config that points to the feature, benchmark, "
            "and selector config files."
        ),
    )
    inventory_group = parser.add_mutually_exclusive_group()
    inventory_group.add_argument(
        "--with-inventory",
        dest="include_inventory",
        action="store_true",
        help="Build the dataset inventory before the main pipeline steps.",
    )
    inventory_group.add_argument(
        "--skip-inventory",
        dest="include_inventory",
        action="store_false",
        help="Skip the optional dataset inventory step.",
    )
    parser.set_defaults(include_inventory=None)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the full pipeline from the command line."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        run_all_pipeline(
            config_path=args.config,
            include_inventory=args.include_inventory,
        )
    except PipelineRunError as exc:
        print(f"Pipeline failed during '{exc.step_name}': {type(exc.cause).__name__}: {exc.cause}")
        return 1
    except Exception as exc:
        print(f"Pipeline failed: {type(exc).__name__}: {exc}")
        return 1
    return 0


def _resolve_pipeline_settings(
    config_path: str | Path | None,
    *,
    include_inventory: bool | None,
) -> PipelineSettings:
    """Resolve pipeline-level settings and stage-config paths."""

    pipeline_config = load_yaml_config(config_path) if config_path is not None else {}

    feature_config_path = get_compat_path(
        pipeline_config,
        ["paths.feature_config", "feature_config"],
        DEFAULT_FEATURE_CONFIG_PATH,
    )
    benchmark_config_path = get_compat_path(
        pipeline_config,
        ["paths.benchmark_config", "benchmark_config"],
        DEFAULT_BENCHMARK_CONFIG_PATH,
    )
    selector_config_path = get_compat_path(
        pipeline_config,
        ["paths.selector_config", "selector_config"],
        DEFAULT_SELECTOR_CONFIG_PATH,
    )

    feature_stage_config = load_yaml_config(feature_config_path)
    inventory_input_folder = get_compat_path(
        pipeline_config,
        ["paths.inventory_input_folder", "inventory_input_folder"],
        get_compat_path(
            feature_stage_config,
            ["paths.instance_folder", "paths.input_folder"],
            DEFAULT_REAL_INPUT_FOLDER,
        ),
    )
    inventory_output_csv = get_compat_path(
        pipeline_config,
        ["paths.inventory_output_csv", "inventory_output_csv"],
        DEFAULT_REAL_OUTPUT_PATH,
    )

    resolved_include_inventory = include_inventory
    if resolved_include_inventory is None:
        resolved_include_inventory = bool(
            get_compat_value(
                pipeline_config,
                ["run.include_inventory", "include_inventory"],
                False,
            )
        )

    return PipelineSettings(
        feature_config_path=feature_config_path,
        benchmark_config_path=benchmark_config_path,
        selector_config_path=selector_config_path,
        include_inventory=resolved_include_inventory,
        inventory_input_folder=inventory_input_folder,
        inventory_output_csv=inventory_output_csv,
    )


def _execute_step(
    step_index: int,
    total_steps: int,
    step_name: str,
    action: Callable[[], _StepResult],
    *,
    success_message: Callable[[_StepResult], str],
) -> _StepResult:
    """Run one pipeline step with a readable progress log."""

    print(f"[{step_index}/{total_steps}] {step_name}...", flush=True)
    started_at = time.perf_counter()
    try:
        result = action()
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        print(
            f"[{step_index}/{total_steps}] {step_name} failed after {elapsed:.2f}s",
            flush=True,
        )
        raise PipelineRunError(step_name, exc) from exc

    elapsed = time.perf_counter() - started_at
    print(
        f"[{step_index}/{total_steps}] {step_name} completed in {elapsed:.2f}s",
        flush=True,
    )
    message = success_message(result).strip()
    if message:
        print(message, flush=True)
    return result


def _training_success_message(result: SelectorTrainingResult) -> str:
    """Format one concise success message for selector training."""

    importance_path = (
        result.feature_importance_path.as_posix()
        if result.feature_importance_path is not None
        else "not written"
    )
    balanced = "n/a" if result.balanced_accuracy is None else f"{result.balanced_accuracy:.4f}"
    return (
        f"Model saved to {result.model_path.as_posix()}\n"
        f"Feature importance: {importance_path}\n"
        f"Validation accuracy: {result.accuracy:.4f}; balanced accuracy: {balanced}"
    )


def _evaluation_success_message(result: SelectorEvaluationResult) -> str:
    """Format one concise success message for selector evaluation."""

    balanced = "n/a" if result.balanced_accuracy is None else f"{result.balanced_accuracy:.4f}"
    return (
        f"Evaluation report: {result.report_path.as_posix()}\n"
        f"Evaluation summary CSV: {result.summary_csv_path.as_posix()}\n"
        f"Evaluation summary Markdown: {result.summary_markdown_path.as_posix()}\n"
        f"Accuracy: {result.classification_accuracy:.4f}; balanced accuracy: {balanced}"
    )


def _print_final_summary(result: PipelineRunResult) -> None:
    """Print one short final summary after a successful pipeline run."""

    print("Pipeline completed successfully.", flush=True)
    if result.inventory_csv is not None:
        print(f"Inventory: {result.inventory_csv.as_posix()}", flush=True)
    print(f"Features: {result.features_csv.as_posix()}", flush=True)
    print(f"Benchmarks: {result.benchmark_csv.as_posix()}", flush=True)
    print(f"Selection dataset: {result.selection_dataset_csv.as_posix()}", flush=True)
    print(f"Model: {result.model_path.as_posix()}", flush=True)
    if result.feature_importance_csv is not None:
        print(f"Feature importance: {result.feature_importance_csv.as_posix()}", flush=True)
    print(f"Evaluation summary CSV: {result.evaluation_summary_csv.as_posix()}", flush=True)
    print(f"Evaluation summary Markdown: {result.evaluation_summary_markdown.as_posix()}", flush=True)


__all__ = [
    "PipelineRunError",
    "PipelineRunResult",
    "PipelineSettings",
    "run_all_pipeline",
]


if __name__ == "__main__":
    raise SystemExit(main())
