
from __future__ import annotations

import argparse
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TypeVar

import pandas as pd

from src.data_generation.synthetic_generator import (
    DifficultySelection,
    generate_synthetic_dataset,
)
from src.experiments.full_benchmark import (
    DEFAULT_FULL_SOLVER_PORTFOLIO,
    run_full_benchmark,
)
from src.features.build_feature_table import build_feature_table
from src.selection.build_selection_dataset import build_selection_dataset
from src.selection.evaluate_selector import SelectorEvaluationResult, evaluate_selector
from src.selection.train_selector import SelectorTrainingResult, train_selector
from src.utils import ensure_parent_directory, write_run_summary


LOGGER = logging.getLogger(__name__)

DEFAULT_DATASET_FOLDER = Path("data/raw/synthetic/generated")
DEFAULT_PROCESSED_DIR = Path("data/processed/thesis_pipeline")
DEFAULT_RESULTS_DIR = Path("data/results/thesis_pipeline")
DEFAULT_DATASET_SIZE = 100
DEFAULT_TIME_LIMIT_SECONDS = 60
DEFAULT_RANDOM_SEED = 42
DEFAULT_DIFFICULTY: DifficultySelection = "mixed"
DEFAULT_GENERATION_TIMESTAMP = "2026-01-01T00:00:00+00:00"
DEFAULT_SPLIT_STRATEGY = "repeated_stratified_kfold"
DEFAULT_TEST_SIZE = 0.25
DEFAULT_CROSS_VALIDATION_FOLDS = 3
DEFAULT_REPEATS = 3

_StepResult = TypeVar("_StepResult")


@dataclass(frozen=True, slots=True)
class DatasetStageResult:

    dataset_folder: Path
    metadata_csv: Path
    generated: bool
    reason: str
    num_instances: int


@dataclass(frozen=True, slots=True)
class SummaryStageResult:

    summary_report: Path
    run_summary_json: Path


@dataclass(frozen=True, slots=True)
class ThesisPipelineResult:

    dataset_folder: Path
    metadata_csv: Path
    features_csv: Path
    benchmark_csv: Path
    selection_dataset_csv: Path
    model_path: Path
    feature_importance_csv: Path | None
    evaluation_report_csv: Path
    evaluation_summary_csv: Path
    evaluation_summary_markdown: Path
    summary_report: Path
    run_summary_json: Path
    generated_dataset: bool
    num_instances: int
    selector_accuracy: float
    selector_regret_vs_virtual_best: float


class ThesisPipelineError(RuntimeError):

    def __init__(self, step_name: str, cause: Exception) -> None:
        self.step_name = step_name
        self.cause = cause
        super().__init__(f"{step_name} failed: {type(cause).__name__}: {cause}")


def run_thesis_pipeline(
    *,
    dataset_size: int = DEFAULT_DATASET_SIZE,
    time_limit_seconds: int = DEFAULT_TIME_LIMIT_SECONDS,
    seed: int = DEFAULT_RANDOM_SEED,
    dataset_folder: str | Path = DEFAULT_DATASET_FOLDER,
    processed_dir: str | Path = DEFAULT_PROCESSED_DIR,
    results_dir: str | Path = DEFAULT_RESULTS_DIR,
    difficulty: DifficultySelection = DEFAULT_DIFFICULTY,
    force_regenerate: bool = False,
    generation_timestamp: str = DEFAULT_GENERATION_TIMESTAMP,
    timefold_executable_path: str | Path | None = None,
    timefold_time_limit_seconds: int | None = None,
    timefold_command_arguments: Sequence[str] | None = None,
    split_strategy: str = DEFAULT_SPLIT_STRATEGY,
    test_size: float = DEFAULT_TEST_SIZE,
    cross_validation_folds: int | None = DEFAULT_CROSS_VALIDATION_FOLDS,
    repeats: int = DEFAULT_REPEATS,
) -> ThesisPipelineResult:

    _validate_pipeline_arguments(
        dataset_size=dataset_size,
        time_limit_seconds=time_limit_seconds,
        test_size=test_size,
        cross_validation_folds=cross_validation_folds,
        repeats=repeats,
    )

    dataset_path = Path(dataset_folder)
    processed_path = Path(processed_dir)
    results_path = Path(results_dir)
    artifact_paths = _build_artifact_paths(processed_path, results_path)

    total_steps = 7
    dataset_stage = _execute_step(
        1,
        total_steps,
        "Ensure synthetic dataset",
        lambda: _ensure_synthetic_dataset(
            dataset_folder=dataset_path,
            dataset_size=dataset_size,
            seed=seed,
            difficulty=difficulty,
            force_regenerate=force_regenerate,
            generation_timestamp=generation_timestamp,
        ),
        success_message=_dataset_success_message,
    )

    features_csv = _execute_step(
        2,
        total_steps,
        "Extract structural features",
        lambda: build_feature_table(
            input_folder=dataset_stage.dataset_folder,
            output_csv=artifact_paths["features_csv"],
            random_seed=seed,
            run_summary_path=artifact_paths["features_run_summary"],
        ),
        success_message=lambda path: f"Features saved to {path.as_posix()}",
    )

    benchmark_csv = _execute_step(
        3,
        total_steps,
        "Run full solver benchmark",
        lambda: run_full_benchmark(
            instance_folder=dataset_stage.dataset_folder,
            output_csv=artifact_paths["benchmark_csv"],
            time_limit_seconds=time_limit_seconds,
            random_seed=seed,
            timefold_executable_path=timefold_executable_path,
            timefold_time_limit_seconds=timefold_time_limit_seconds,
            timefold_command_arguments=timefold_command_arguments,
            run_summary_path=artifact_paths["benchmark_run_summary"],
        ),
        success_message=lambda path: f"Benchmark results saved to {path.as_posix()}",
    )

    selection_dataset_csv = _execute_step(
        4,
        total_steps,
        "Build selection dataset",
        lambda: build_selection_dataset(
            features_csv=features_csv,
            benchmark_csv=benchmark_csv,
            output_csv=artifact_paths["selection_dataset_csv"],
            include_solver_objectives=True,
            run_summary_path=artifact_paths["selection_dataset_run_summary"],
        ),
        success_message=lambda path: f"Selection dataset saved to {path.as_posix()}",
    )

    training_result = _execute_step(
        5,
        total_steps,
        "Train selector",
        lambda: train_selector(
            dataset_csv=selection_dataset_csv,
            model_path=artifact_paths["model_path"],
            feature_importance_csv=artifact_paths["feature_importance_csv"],
            random_seed=seed,
            test_size=test_size,
            split_strategy=split_strategy,
            cross_validation_folds=cross_validation_folds,
            repeats=repeats,
            run_summary_path=artifact_paths["training_run_summary"],
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
            report_csv=artifact_paths["evaluation_report_csv"],
            summary_csv=artifact_paths["evaluation_summary_csv"],
            summary_markdown=artifact_paths["evaluation_summary_markdown"],
            random_seed=seed,
            test_size=test_size,
            split_strategy=split_strategy,
            cross_validation_folds=cross_validation_folds,
            repeats=repeats,
            run_summary_path=artifact_paths["evaluation_run_summary"],
        ),
        success_message=_evaluation_success_message,
    )

    summary_stage = _execute_step(
        7,
        total_steps,
        "Write thesis summary report",
        lambda: _write_pipeline_summary(
            dataset_stage=dataset_stage,
            features_csv=features_csv,
            benchmark_csv=benchmark_csv,
            selection_dataset_csv=selection_dataset_csv,
            training_result=training_result,
            evaluation_result=evaluation_result,
            summary_report=artifact_paths["summary_report"],
            run_summary_json=artifact_paths["pipeline_run_summary"],
            dataset_size=dataset_size,
            time_limit_seconds=time_limit_seconds,
            seed=seed,
            difficulty=difficulty,
            generation_timestamp=generation_timestamp,
            split_strategy=split_strategy,
            test_size=test_size,
            cross_validation_folds=cross_validation_folds,
            repeats=repeats,
            timefold_executable_path=timefold_executable_path,
            timefold_time_limit_seconds=timefold_time_limit_seconds,
            timefold_command_arguments=timefold_command_arguments,
        ),
        success_message=lambda result: (
            f"Summary report saved to {result.summary_report.as_posix()}\n"
            f"Pipeline run summary saved to {result.run_summary_json.as_posix()}"
        ),
    )

    result = ThesisPipelineResult(
        dataset_folder=dataset_stage.dataset_folder,
        metadata_csv=dataset_stage.metadata_csv,
        features_csv=features_csv,
        benchmark_csv=benchmark_csv,
        selection_dataset_csv=selection_dataset_csv,
        model_path=training_result.model_path,
        feature_importance_csv=training_result.feature_importance_path,
        evaluation_report_csv=evaluation_result.report_path,
        evaluation_summary_csv=evaluation_result.summary_csv_path,
        evaluation_summary_markdown=evaluation_result.summary_markdown_path,
        summary_report=summary_stage.summary_report,
        run_summary_json=summary_stage.run_summary_json,
        generated_dataset=dataset_stage.generated,
        num_instances=dataset_stage.num_instances,
        selector_accuracy=evaluation_result.classification_accuracy,
        selector_regret_vs_virtual_best=evaluation_result.regret_vs_virtual_best,
    )
    _print_final_summary(result)
    return result


def build_argument_parser() -> argparse.ArgumentParser:

    parser = argparse.ArgumentParser(
        description="Run the thesis-mode experiment pipeline in one command.",
    )
    parser.add_argument(
        "--dataset-size",
        type=int,
        default=DEFAULT_DATASET_SIZE,
        help="Number of synthetic instances required for the run.",
    )
    parser.add_argument(
        "--time-limit-seconds",
        type=int,
        default=DEFAULT_TIME_LIMIT_SECONDS,
        help="Per-solver time limit used by the benchmark stage.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_RANDOM_SEED,
        help="Random seed used for generation, solvers, and selector splits.",
    )
    parser.add_argument(
        "--dataset-folder",
        default=str(DEFAULT_DATASET_FOLDER),
        help="Folder containing or receiving generated synthetic XML files.",
    )
    parser.add_argument(
        "--processed-dir",
        default=str(DEFAULT_PROCESSED_DIR),
        help="Folder for processed thesis pipeline artifacts.",
    )
    parser.add_argument(
        "--results-dir",
        default=str(DEFAULT_RESULTS_DIR),
        help="Folder for benchmark, model, evaluation, and report artifacts.",
    )
    parser.add_argument(
        "--difficulty",
        choices=("mixed", "easy", "medium", "hard"),
        default=DEFAULT_DIFFICULTY,
        help="Synthetic dataset difficulty profile.",
    )
    parser.add_argument(
        "--force-regenerate",
        action="store_true",
        help="Regenerate the synthetic dataset even if an existing batch matches.",
    )
    parser.add_argument(
        "--generation-timestamp",
        default=DEFAULT_GENERATION_TIMESTAMP,
        help="Timestamp embedded in generated synthetic XML for reproducibility.",
    )
    parser.add_argument(
        "--timefold-executable",
        default=None,
        help="Optional path to the external Timefold executable.",
    )
    parser.add_argument(
        "--timefold-time-limit-seconds",
        type=int,
        default=None,
        help="Optional Timefold-specific time limit override.",
    )
    parser.add_argument(
        "--timefold-command-arg",
        action="append",
        default=None,
        help="Extra argument passed to Timefold. Repeat for multiple arguments.",
    )
    parser.add_argument(
        "--split-strategy",
        choices=("holdout", "repeated_holdout", "repeated_stratified_kfold"),
        default=DEFAULT_SPLIT_STRATEGY,
        help="Selector validation split strategy.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=DEFAULT_TEST_SIZE,
        help="Holdout test fraction for holdout-style split strategies.",
    )
    parser.add_argument(
        "--cross-validation-folds",
        type=int,
        default=DEFAULT_CROSS_VALIDATION_FOLDS,
        help="Requested folds for repeated_stratified_kfold.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=DEFAULT_REPEATS,
        help="Number of selector validation repeats.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        run_thesis_pipeline(
            dataset_size=args.dataset_size,
            time_limit_seconds=args.time_limit_seconds,
            seed=args.seed,
            dataset_folder=args.dataset_folder,
            processed_dir=args.processed_dir,
            results_dir=args.results_dir,
            difficulty=args.difficulty,
            force_regenerate=args.force_regenerate,
            generation_timestamp=args.generation_timestamp,
            timefold_executable_path=args.timefold_executable,
            timefold_time_limit_seconds=args.timefold_time_limit_seconds,
            timefold_command_arguments=args.timefold_command_arg,
            split_strategy=args.split_strategy,
            test_size=args.test_size,
            cross_validation_folds=args.cross_validation_folds,
            repeats=args.repeats,
        )
    except ThesisPipelineError as exc:
        print(
            f"Thesis pipeline failed during '{exc.step_name}': "
            f"{type(exc.cause).__name__}: {exc.cause}",
            flush=True,
        )
        return 1
    except Exception as exc:
        print(f"Thesis pipeline failed: {type(exc).__name__}: {exc}", flush=True)
        return 1
    return 0


def _build_artifact_paths(processed_dir: Path, results_dir: Path) -> dict[str, Path]:

    return {
        "features_csv": processed_dir / "features.csv",
        "features_run_summary": processed_dir / "features_run_summary.json",
        "benchmark_csv": results_dir / "full_benchmark_results.csv",
        "benchmark_run_summary": results_dir / "full_benchmark_run_summary.json",
        "selection_dataset_csv": processed_dir / "selection_dataset.csv",
        "selection_dataset_run_summary": processed_dir / "selection_dataset_run_summary.json",
        "model_path": results_dir / "random_forest_selector.joblib",
        "feature_importance_csv": results_dir / "feature_importance.csv",
        "training_run_summary": results_dir / "selector_training_run_summary.json",
        "evaluation_report_csv": results_dir / "selector_evaluation.csv",
        "evaluation_summary_csv": results_dir / "selector_evaluation_summary.csv",
        "evaluation_summary_markdown": results_dir / "selector_evaluation_summary.md",
        "evaluation_run_summary": results_dir / "selector_evaluation_run_summary.json",
        "summary_report": results_dir / "thesis_pipeline_summary.md",
        "pipeline_run_summary": results_dir / "thesis_pipeline_run_summary.json",
    }


def _ensure_synthetic_dataset(
    *,
    dataset_folder: Path,
    dataset_size: int,
    seed: int,
    difficulty: DifficultySelection,
    force_regenerate: bool,
    generation_timestamp: str,
) -> DatasetStageResult:

    metadata_csv = dataset_folder / "metadata.csv"
    if force_regenerate:
        should_generate = True
        reason = "force_regenerate was requested"
    else:
        matches, reason = _dataset_matches_request(
            dataset_folder=dataset_folder,
            metadata_csv=metadata_csv,
            dataset_size=dataset_size,
            seed=seed,
            difficulty=difficulty,
        )
        should_generate = not matches

    if should_generate:
        LOGGER.info("Generating synthetic dataset because %s.", reason)
        generation = generate_synthetic_dataset(
            output_folder=dataset_folder,
            metadata_csv=metadata_csv,
            instance_count=dataset_size,
            random_seed=seed,
            difficulty=difficulty,
            generation_timestamp=generation_timestamp,
        )
        return DatasetStageResult(
            dataset_folder=generation.output_folder,
            metadata_csv=generation.metadata_csv,
            generated=True,
            reason=reason,
            num_instances=generation.instance_count,
        )

    return DatasetStageResult(
        dataset_folder=dataset_folder,
        metadata_csv=metadata_csv,
        generated=False,
        reason=reason,
        num_instances=len(list(dataset_folder.glob("*.xml"))),
    )


def _dataset_matches_request(
    *,
    dataset_folder: Path,
    metadata_csv: Path,
    dataset_size: int,
    seed: int,
    difficulty: DifficultySelection,
) -> tuple[bool, str]:

    if not dataset_folder.exists():
        return False, f"{dataset_folder.as_posix()} does not exist"
    if not dataset_folder.is_dir():
        return False, f"{dataset_folder.as_posix()} is not a folder"

    xml_files = sorted(dataset_folder.glob("*.xml"))
    if len(xml_files) != dataset_size:
        return False, f"found {len(xml_files)} XML files but requested {dataset_size}"
    if not metadata_csv.exists():
        return False, "metadata.csv is missing"

    try:
        metadata = pd.read_csv(metadata_csv)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError) as exc:
        return False, f"metadata.csv could not be read: {type(exc).__name__}"

    if len(metadata.index) != dataset_size:
        return False, f"metadata has {len(metadata.index)} rows but requested {dataset_size}"
    if "random_seed" not in metadata.columns:
        return False, "metadata is missing random_seed"
    if metadata.empty or _coerce_int(metadata.iloc[0]["random_seed"]) != seed:
        return False, "metadata random_seed does not match requested seed"
    if "difficulty" not in metadata.columns:
        return False, "metadata is missing difficulty"

    observed_difficulties = {
        str(value).strip().casefold()
        for value in metadata["difficulty"].dropna().tolist()
        if str(value).strip()
    }
    if difficulty == "mixed":
        expected_difficulties = {"easy", "medium", "hard"}
        if dataset_size >= len(expected_difficulties) and not expected_difficulties.issubset(
            observed_difficulties,
        ):
            return False, "metadata does not contain the expected mixed difficulty coverage"
    elif observed_difficulties != {difficulty}:
        return False, f"metadata difficulty does not match requested {difficulty}"

    return True, "existing dataset matches requested size, seed, and difficulty"


def _write_pipeline_summary(
    *,
    dataset_stage: DatasetStageResult,
    features_csv: Path,
    benchmark_csv: Path,
    selection_dataset_csv: Path,
    training_result: SelectorTrainingResult,
    evaluation_result: SelectorEvaluationResult,
    summary_report: Path,
    run_summary_json: Path,
    dataset_size: int,
    time_limit_seconds: int,
    seed: int,
    difficulty: DifficultySelection,
    generation_timestamp: str,
    split_strategy: str,
    test_size: float,
    cross_validation_folds: int | None,
    repeats: int,
    timefold_executable_path: str | Path | None,
    timefold_time_limit_seconds: int | None,
    timefold_command_arguments: Sequence[str] | None,
) -> SummaryStageResult:

    features = pd.read_csv(features_csv)
    benchmarks = pd.read_csv(benchmark_csv)
    selection_dataset = pd.read_csv(selection_dataset_csv)
    feature_importance = _read_optional_csv(training_result.feature_importance_path)

    labeled_rows = int(selection_dataset["best_solver"].notna().sum())
    feasible_runs = int(benchmarks["feasible"].astype(str).str.casefold().isin({"true", "1"}).sum())
    support_counts = _value_counts(benchmarks, "solver_support_status")
    status_counts = _value_counts(benchmarks, "status")

    ensure_parent_directory(summary_report)
    summary_report.write_text(
        _render_summary_markdown(
            dataset_stage=dataset_stage,
            features_csv=features_csv,
            benchmark_csv=benchmark_csv,
            selection_dataset_csv=selection_dataset_csv,
            training_result=training_result,
            evaluation_result=evaluation_result,
            feature_importance=feature_importance,
            dataset_size=dataset_size,
            time_limit_seconds=time_limit_seconds,
            seed=seed,
            difficulty=difficulty,
            generation_timestamp=generation_timestamp,
            split_strategy=split_strategy,
            test_size=test_size,
            cross_validation_folds=cross_validation_folds,
            repeats=repeats,
            timefold_executable_path=timefold_executable_path,
            timefold_time_limit_seconds=timefold_time_limit_seconds,
            timefold_command_arguments=timefold_command_arguments,
            feature_rows=len(features.index),
            benchmark_rows=len(benchmarks.index),
            selection_rows=len(selection_dataset.index),
            labeled_rows=labeled_rows,
            feasible_runs=feasible_runs,
            support_counts=support_counts,
            status_counts=status_counts,
        ),
        encoding="utf-8",
    )

    write_run_summary(
        run_summary_json,
        stage_name="thesis_pipeline",
        config_path=None,
        config=None,
        settings={
            "dataset_size": dataset_size,
            "time_limit_seconds": time_limit_seconds,
            "seed": seed,
            "difficulty": difficulty,
            "generation_timestamp": generation_timestamp,
            "solver_portfolio": DEFAULT_FULL_SOLVER_PORTFOLIO,
            "split_strategy": split_strategy,
            "test_size": test_size,
            "cross_validation_folds": cross_validation_folds,
            "repeats": repeats,
            "timefold_executable_path": str(timefold_executable_path)
            if timefold_executable_path is not None
            else None,
            "timefold_time_limit_seconds": timefold_time_limit_seconds,
            "timefold_command_arguments": list(timefold_command_arguments or ()),
        },
        inputs={
            "dataset_folder": dataset_stage.dataset_folder,
            "metadata_csv": dataset_stage.metadata_csv,
        },
        outputs={
            "features_csv": features_csv,
            "benchmark_csv": benchmark_csv,
            "selection_dataset_csv": selection_dataset_csv,
            "model_path": training_result.model_path,
            "feature_importance_csv": training_result.feature_importance_path,
            "evaluation_report_csv": evaluation_result.report_path,
            "evaluation_summary_csv": evaluation_result.summary_csv_path,
            "evaluation_summary_markdown": evaluation_result.summary_markdown_path,
            "summary_report": summary_report,
            "run_summary_json": run_summary_json,
        },
        results={
            "dataset_generated": dataset_stage.generated,
            "dataset_reason": dataset_stage.reason,
            "num_instances": dataset_stage.num_instances,
            "feature_rows": len(features.index),
            "benchmark_rows": len(benchmarks.index),
            "selection_rows": len(selection_dataset.index),
            "labeled_rows": labeled_rows,
            "feasible_runs": feasible_runs,
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
        summary_report=summary_report,
        run_summary_json=run_summary_json,
    )


def _render_summary_markdown(
    *,
    dataset_stage: DatasetStageResult,
    features_csv: Path,
    benchmark_csv: Path,
    selection_dataset_csv: Path,
    training_result: SelectorTrainingResult,
    evaluation_result: SelectorEvaluationResult,
    feature_importance: pd.DataFrame | None,
    dataset_size: int,
    time_limit_seconds: int,
    seed: int,
    difficulty: DifficultySelection,
    generation_timestamp: str,
    split_strategy: str,
    test_size: float,
    cross_validation_folds: int | None,
    repeats: int,
    timefold_executable_path: str | Path | None,
    timefold_time_limit_seconds: int | None,
    timefold_command_arguments: Sequence[str] | None,
    feature_rows: int,
    benchmark_rows: int,
    selection_rows: int,
    labeled_rows: int,
    feasible_runs: int,
    support_counts: dict[str, int],
    status_counts: dict[str, int],
) -> str:

    balanced_training = _format_optional_float(training_result.balanced_accuracy)
    balanced_evaluation = _format_optional_float(evaluation_result.balanced_accuracy)
    timefold_path = (
        str(timefold_executable_path)
        if timefold_executable_path is not None
        else "not configured"
    )

    lines = [
        "# Thesis Experiment Pipeline Summary",
        "",
        "## Settings",
        "",
        f"- Dataset size: `{dataset_size}`",
        f"- Difficulty profile: `{difficulty}`",
        f"- Random seed: `{seed}`",
        f"- Per-solver time limit: `{time_limit_seconds}` seconds",
        f"- Synthetic generation timestamp: `{generation_timestamp}`",
        f"- Solver portfolio: `{', '.join(DEFAULT_FULL_SOLVER_PORTFOLIO)}`",
        f"- Timefold executable: `{timefold_path}`",
        f"- Timefold time limit override: `{timefold_time_limit_seconds or 'none'}`",
        f"- Timefold extra arguments: `{list(timefold_command_arguments or ())}`",
        f"- Selector split strategy: `{split_strategy}`",
        f"- Test size: `{test_size}`",
        f"- Cross-validation folds: `{cross_validation_folds or 'none'}`",
        f"- Repeats: `{repeats}`",
        "",
        "## Artifacts",
        "",
        f"- Dataset folder: `{dataset_stage.dataset_folder.as_posix()}`",
        f"- Dataset metadata: `{dataset_stage.metadata_csv.as_posix()}`",
        f"- Feature table: `{features_csv.as_posix()}`",
        f"- Benchmark results: `{benchmark_csv.as_posix()}`",
        f"- Selection dataset: `{selection_dataset_csv.as_posix()}`",
        f"- Selector model: `{training_result.model_path.as_posix()}`",
        f"- Feature importance: `{_path_or_na(training_result.feature_importance_path)}`",
        f"- Selector evaluation report: `{evaluation_result.report_path.as_posix()}`",
        f"- Selector evaluation summary: `{evaluation_result.summary_csv_path.as_posix()}`",
        f"- Selector evaluation Markdown: `{evaluation_result.summary_markdown_path.as_posix()}`",
        "",
    ]
    lines.extend(
        [
            "## Headline Results",
            "",
            f"- Dataset action: `{'generated' if dataset_stage.generated else 'reused'}` ({dataset_stage.reason})",
            f"- XML instances: `{dataset_stage.num_instances}`",
            f"- Feature rows: `{feature_rows}`",
            f"- Benchmark rows: `{benchmark_rows}`",
            f"- Feasible solver runs: `{feasible_runs}`",
            f"- Selection rows: `{selection_rows}`",
            f"- Labeled selection rows: `{labeled_rows}`",
            f"- Training validation accuracy: `{training_result.accuracy:.4f}`",
            f"- Training balanced accuracy: `{balanced_training}`",
            f"- Evaluation accuracy: `{evaluation_result.classification_accuracy:.4f}`",
            f"- Evaluation balanced accuracy: `{balanced_evaluation}`",
            f"- Mean regret vs virtual best: `{evaluation_result.regret_vs_virtual_best:.4f}`",
            f"- Mean delta vs single best: `{evaluation_result.delta_vs_single_best:.4f}`",
            f"- Mean improvement vs single best: `{evaluation_result.improvement_vs_single_best:.4f}`",
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
            "- Synthetic instances are useful for controlled selector experiments, but they should be reported separately from real RobinX / ITC2021 benchmark evidence.",
            "- The Timefold row is included in the fixed portfolio even when no executable is configured; those runs are recorded as `not_configured` instead of failing the pipeline.",
            "- Selector training excludes benchmark-derived `objective_*` columns to avoid target leakage.",
            "",
        ]
    )
    return "\n".join(lines)


def _execute_step(
    step_index: int,
    total_steps: int,
    step_name: str,
    action: Callable[[], _StepResult],
    *,
    success_message: Callable[[_StepResult], str],
) -> _StepResult:

    print(f"[{step_index}/{total_steps}] {step_name}...", flush=True)
    started_at = time.perf_counter()
    try:
        result = action()
    except Exception as exc:
        elapsed = time.perf_counter() - started_at
        print(f"[{step_index}/{total_steps}] {step_name} failed after {elapsed:.2f}s", flush=True)
        raise ThesisPipelineError(step_name, exc) from exc

    elapsed = time.perf_counter() - started_at
    print(f"[{step_index}/{total_steps}] {step_name} completed in {elapsed:.2f}s", flush=True)
    message = success_message(result).strip()
    if message:
        print(message, flush=True)
    return result


def _validate_pipeline_arguments(
    *,
    dataset_size: int,
    time_limit_seconds: int,
    test_size: float,
    cross_validation_folds: int | None,
    repeats: int,
) -> None:

    if dataset_size < 2:
        raise ValueError("dataset_size must be at least 2 so the selector can be validated.")
    if time_limit_seconds <= 0:
        raise ValueError("time_limit_seconds must be positive.")
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be between 0 and 1.")
    if cross_validation_folds is not None and cross_validation_folds < 2:
        raise ValueError("cross_validation_folds must be at least 2 when provided.")
    if repeats <= 0:
        raise ValueError("repeats must be positive.")


def _dataset_success_message(result: DatasetStageResult) -> str:

    action = "Generated" if result.generated else "Reused"
    return (
        f"{action} {result.num_instances} synthetic instances in "
        f"{result.dataset_folder.as_posix()}\n"
        f"Dataset metadata: {result.metadata_csv.as_posix()}"
    )


def _training_success_message(result: SelectorTrainingResult) -> str:

    balanced = _format_optional_float(result.balanced_accuracy)
    return (
        f"Model saved to {result.model_path.as_posix()}\n"
        f"Feature importance: {_path_or_na(result.feature_importance_path)}\n"
        f"Validation accuracy: {result.accuracy:.4f}; balanced accuracy: {balanced}"
    )


def _evaluation_success_message(result: SelectorEvaluationResult) -> str:

    balanced = _format_optional_float(result.balanced_accuracy)
    return (
        f"Evaluation report: {result.report_path.as_posix()}\n"
        f"Evaluation summary CSV: {result.summary_csv_path.as_posix()}\n"
        f"Evaluation summary Markdown: {result.summary_markdown_path.as_posix()}\n"
        f"Accuracy: {result.classification_accuracy:.4f}; balanced accuracy: {balanced}\n"
        f"Regret vs virtual best: {result.regret_vs_virtual_best:.4f}"
    )


def _print_final_summary(result: ThesisPipelineResult) -> None:

    print("Thesis pipeline completed successfully.", flush=True)
    print(f"Benchmark results: {result.benchmark_csv.as_posix()}", flush=True)
    print(f"Selector evaluation: {result.evaluation_summary_csv.as_posix()}", flush=True)
    if result.feature_importance_csv is not None:
        print(f"Feature importance: {result.feature_importance_csv.as_posix()}", flush=True)
    print(f"Summary report: {result.summary_report.as_posix()}", flush=True)


def _value_counts(frame: pd.DataFrame, column: str) -> dict[str, int]:

    if column not in frame.columns:
        return {}
    counts = frame[column].fillna("missing").astype(str).value_counts().to_dict()
    return {str(key): int(value) for key, value in sorted(counts.items())}


def _read_optional_csv(path: Path | None) -> pd.DataFrame | None:

    if path is None or not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return None


def _render_count_table(counts: dict[str, int], label: str) -> list[str]:

    lines = [f"| {label} | count |", "| --- | ---: |"]
    if not counts:
        lines.append("| none | 0 |")
        return lines
    for key, value in counts.items():
        lines.append(f"| `{key}` | {value} |")
    return lines


def _render_feature_importance_table(feature_importance: pd.DataFrame | None) -> list[str]:

    if feature_importance is None or feature_importance.empty:
        return ["Feature importance was not available for this model."]

    required_columns = {"importance_rank", "source_feature", "feature_group", "importance"}
    if not required_columns.issubset(feature_importance.columns):
        return ["Feature importance CSV exists, but it does not have the expected columns."]

    lines = [
        "| rank | source_feature | feature_group | importance |",
        "| ---: | --- | --- | ---: |",
    ]
    top_rows = feature_importance.head(10)
    for row in top_rows.to_dict(orient="records"):
        lines.append(
            "| "
            f"{int(row['importance_rank'])} | "
            f"`{row['source_feature']}` | "
            f"`{row['feature_group']}` | "
            f"{float(row['importance']):.6f} |"
        )
    return lines


def _format_optional_float(value: float | None) -> str:

    if value is None or pd.isna(value):
        return "n/a"
    return f"{value:.4f}"


def _path_or_na(path: Path | None) -> str:

    if path is None:
        return "not written"
    return path.as_posix()


def _coerce_int(value: object) -> int | None:

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = [
    "DEFAULT_DATASET_FOLDER",
    "DEFAULT_DATASET_SIZE",
    "DEFAULT_PROCESSED_DIR",
    "DEFAULT_RANDOM_SEED",
    "DEFAULT_RESULTS_DIR",
    "DEFAULT_TIME_LIMIT_SECONDS",
    "DatasetStageResult",
    "SummaryStageResult",
    "ThesisPipelineError",
    "ThesisPipelineResult",
    "run_thesis_pipeline",
]


if __name__ == "__main__":
    raise SystemExit(main())
