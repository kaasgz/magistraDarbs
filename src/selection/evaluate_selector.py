# Evaluate a selector in algorithm-selection terms.
#
# The evaluation workflow is intentionally more rigorous than the training step:
#
# - selector predictions are generated out-of-sample on reproducible validation
# splits instead of reusing an in-sample fitted model
# - the single best solver baseline is computed from each training split only
# - the virtual best solver baseline is computed independently on each test split
# - both split-level and aggregate summaries are saved for thesis reporting

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from sklearn.metrics import balanced_accuracy_score

from src.experiments.metrics import best_solver_per_instance, single_best_solver as single_best_solver_metric
from src.selection.modeling import prepare_selection_data
from src.selection.train_selector import DEFAULT_DATASET_PATH, DEFAULT_FULL_DATASET_PATH, DEFAULT_FULL_MODEL_PATH
from src.selection.validation import (
    aggregate_metric,
    metric_standard_deviation,
    run_selector_validation,
    summarize_label_distribution,
)
from src.utils import (
    SplitSettings,
    default_run_summary_path,
    ensure_parent_directory,
    get_compat_path,
    get_model_choice,
    get_random_seed,
    get_split_settings,
    load_yaml_config,
    write_run_summary,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("configs/selector_config.yaml")
DEFAULT_BENCHMARKS_PATH = Path("data/results/benchmark_results.csv")
DEFAULT_REPORT_PATH = Path("data/results/selector_evaluation.csv")
DEFAULT_SUMMARY_CSV_PATH = Path("data/results/selector_evaluation_summary.csv")
DEFAULT_SUMMARY_MARKDOWN_PATH = Path("data/results/selector_evaluation_summary.md")
DEFAULT_MODEL_PATH = Path("data/results/random_forest_selector.joblib")
DEFAULT_FULL_SYNTHETIC_BENCHMARKS_PATH = Path("data/results/synthetic_study/benchmark_results.csv")
DEFAULT_FULL_REAL_BENCHMARKS_PATH = Path("data/results/real_pipeline_current/benchmark_results.csv")
DEFAULT_FULL_COMBINED_BENCHMARKS_PATH = Path("data/results/full_selection/combined_benchmark_results.csv")
DEFAULT_FULL_REPORT_PATH = Path("data/results/full_selection/selector_evaluation.csv")
DEFAULT_FULL_SUMMARY_CSV_PATH = Path("data/results/full_selection/selector_evaluation_summary.csv")
DEFAULT_FULL_SUMMARY_MARKDOWN_PATH = Path("data/results/full_selection/selector_evaluation_summary.md")
DEFAULT_FULL_EVALUATION_RUN_SUMMARY_PATH = Path("data/results/full_selection/selector_evaluation_run_summary.json")
REQUIRED_BENCHMARK_COLUMNS = {
    "instance_name",
    "solver_name",
    "objective_value",
    "runtime_seconds",
    "feasible",
    "status",
}


@dataclass(slots=True)
class SelectorEvaluationResult:

    # Summary of selector evaluation across reproducible validation splits.
    report_path: Path
    summary_csv_path: Path
    summary_markdown_path: Path
    single_best_solver_name: str | None
    classification_accuracy: float
    balanced_accuracy: float | None
    average_selected_objective: float
    average_virtual_best_objective: float
    average_single_best_objective: float
    regret_vs_virtual_best: float
    delta_vs_single_best: float
    improvement_vs_single_best: float
    num_test_instances: int
    num_validation_splits: int
    split_strategy: str


def evaluate_selector(
    dataset_csv: str | Path = DEFAULT_DATASET_PATH,
    benchmark_csv: str | Path = DEFAULT_BENCHMARKS_PATH,
    model_path: str | Path | None = None,
    report_csv: str | Path = DEFAULT_REPORT_PATH,
    summary_csv: str | Path = DEFAULT_SUMMARY_CSV_PATH,
    summary_markdown: str | Path = DEFAULT_SUMMARY_MARKDOWN_PATH,
    random_seed: int = 42,
    test_size: float = 0.25,
    model_name: str = "random_forest",
    *,
    split_strategy: str = "holdout",
    cross_validation_folds: int | None = None,
    repeats: int = 1,
    config_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    run_summary_path: str | Path | None = None,
) -> SelectorEvaluationResult:

    # Evaluate the selector against single-best and virtual-best baselines.
    #
    # The ``model_path`` argument is retained for artifact traceability, but the
    # evaluation itself retrains the selector inside each validation split so the
    # reported metrics stay fully out-of-sample.
    #
    dataset = pd.read_csv(Path(dataset_csv))
    benchmarks = pd.read_csv(Path(benchmark_csv))
    dataset_type_by_instance = _dataset_type_lookup(dataset)
    prepared_data = prepare_selection_data(dataset)
    split_settings = SplitSettings(
        strategy=split_strategy,
        test_size=test_size,
        cross_validation_folds=cross_validation_folds,
        repeats=repeats,
    )
    validation_result = run_selector_validation(
        prepared_data,
        model_name=model_name,
        random_seed=random_seed,
        split_settings=split_settings,
    )

    benchmark_frame = _prepare_benchmark_frame(benchmarks)

    detailed_reports: list[pd.DataFrame] = []
    objective_summary_rows: list[dict[str, object]] = []
    for split in validation_result.split_plan.splits:
        split_predictions = validation_result.predictions[
            validation_result.predictions["split_id"] == split.split_id
        ].reset_index(drop=True)
        split_validation_summary = validation_result.split_summary[
            validation_result.split_summary["split_id"] == split.split_id
        ].iloc[0]

        train_instances = prepared_data.instance_names.iloc[list(split.train_indices)].astype(str)
        train_benchmarks = benchmark_frame[benchmark_frame["instance_name"].isin(train_instances)].copy()
        test_benchmarks = benchmark_frame[
            benchmark_frame["instance_name"].isin(split_predictions["instance_name"].astype(str))
        ].copy()

        single_best_summary = single_best_solver_metric(train_benchmarks)
        single_best_solver_name = _coerce_string(single_best_summary.get("solver_name"))

        split_report = _build_detailed_report(
            split_predictions=split_predictions,
            test_benchmarks=test_benchmarks,
            single_best_solver_name=single_best_solver_name,
            dataset_type_by_instance=dataset_type_by_instance,
        )
        split_report.insert(0, "stratified_split", split.stratified)
        split_report.insert(0, "fold_index", split.fold_index)
        split_report.insert(0, "repeat_index", split.repeat_index)
        split_report.insert(0, "split_strategy", split.strategy)
        split_report.insert(0, "split_id", split.split_id)
        detailed_reports.append(split_report)

        average_selected_objective = float(split_report["selected_objective_for_scoring"].mean())
        average_virtual_best_objective = float(split_report["best_possible_objective"].mean())
        average_single_best_objective = float(split_report["single_best_objective_for_scoring"].mean())
        regret_vs_virtual_best = average_selected_objective - average_virtual_best_objective
        delta_vs_single_best = average_selected_objective - average_single_best_objective

        objective_summary_rows.append(
            {
                "summary_row_type": "split",
                "dataset_type": "all",
                "split_id": split.split_id,
                "split_strategy": split.strategy,
                "repeat_index": split.repeat_index,
                "fold_index": split.fold_index,
                "stratified_split": split.stratified,
                "single_best_solver_name": single_best_solver_name,
                "num_train_rows": int(split_validation_summary["num_train_rows"]),
                "num_test_rows": int(split_validation_summary["num_test_rows"]),
                "num_train_classes": int(split_validation_summary["num_train_classes"]),
                "num_test_classes": int(split_validation_summary["num_test_classes"]),
                "classification_accuracy": float(split_validation_summary["classification_accuracy"]),
                "balanced_accuracy": _coerce_float(split_validation_summary["balanced_accuracy"]),
                "average_selected_objective": average_selected_objective,
                "average_virtual_best_objective": average_virtual_best_objective,
                "average_single_best_objective": average_single_best_objective,
                "regret_vs_virtual_best": regret_vs_virtual_best,
                "delta_vs_single_best": delta_vs_single_best,
                "improvement_vs_single_best": -delta_vs_single_best,
            }
        )
        objective_summary_rows.extend(
            _build_dataset_type_split_rows(
                split_report=split_report,
                split=split,
                prepared_data=prepared_data,
                train_indices=list(split.train_indices),
                single_best_solver_name=single_best_solver_name,
                dataset_type_by_instance=dataset_type_by_instance,
            )
        )

    report = pd.concat(detailed_reports, ignore_index=True) if detailed_reports else pd.DataFrame()
    split_summary = pd.DataFrame(objective_summary_rows)
    overall_split_summary = _overall_split_rows(split_summary)
    summary = _build_evaluation_summary(
        split_summary=split_summary,
        split_strategy=validation_result.split_plan.strategy,
    )

    report_path = Path(report_csv)
    summary_csv_path = Path(summary_csv)
    summary_markdown_path = Path(summary_markdown)
    ensure_parent_directory(report_path)
    ensure_parent_directory(summary_csv_path)
    ensure_parent_directory(summary_markdown_path)
    report.to_csv(report_path, index=False)
    summary.to_csv(summary_csv_path, index=False)
    summary_markdown_path.write_text(
        _build_summary_markdown(
            split_summary=split_summary,
            summary=summary,
            split_notes=validation_result.split_plan.notes,
            split_strategy=validation_result.split_plan.strategy,
        ),
        encoding="utf-8",
    )

    classification_accuracy = aggregate_metric(overall_split_summary["classification_accuracy"])
    balanced_accuracy = aggregate_metric(overall_split_summary["balanced_accuracy"])
    average_selected_objective = aggregate_metric(overall_split_summary["average_selected_objective"])
    average_virtual_best_objective = aggregate_metric(overall_split_summary["average_virtual_best_objective"])
    average_single_best_objective = aggregate_metric(overall_split_summary["average_single_best_objective"])
    regret_vs_virtual_best = aggregate_metric(overall_split_summary["regret_vs_virtual_best"])
    delta_vs_single_best = aggregate_metric(overall_split_summary["delta_vs_single_best"])

    if (
        classification_accuracy is None
        or average_selected_objective is None
        or average_virtual_best_objective is None
        or average_single_best_objective is None
        or regret_vs_virtual_best is None
        or delta_vs_single_best is None
    ):
        raise ValueError("Selector evaluation did not produce complete aggregate metrics.")

    single_best_solver_name = summarize_label_distribution(overall_split_summary["single_best_solver_name"].tolist())
    improvement_vs_single_best = -delta_vs_single_best

    LOGGER.info("Validation strategy: %s", validation_result.split_plan.strategy)
    LOGGER.info("Validation splits: %d", len(overall_split_summary.index))
    LOGGER.info("Mean classification accuracy: %.4f", classification_accuracy)
    if balanced_accuracy is None:
        LOGGER.info("Mean balanced accuracy: not applicable")
    else:
        LOGGER.info("Mean balanced accuracy: %.4f", balanced_accuracy)
    LOGGER.info("Mean selected objective: %.4f", average_selected_objective)
    LOGGER.info("Mean virtual-best objective: %.4f", average_virtual_best_objective)
    LOGGER.info("Mean single-best objective: %.4f", average_single_best_objective)
    LOGGER.info("Mean regret vs virtual best: %.4f", regret_vs_virtual_best)
    LOGGER.info("Mean delta vs single best: %.4f", delta_vs_single_best)
    LOGGER.info("Saved detailed selector evaluation report to %s", report_path)
    LOGGER.info("Saved selector evaluation summary CSV to %s", summary_csv_path)
    LOGGER.info("Saved selector evaluation summary Markdown to %s", summary_markdown_path)

    result = SelectorEvaluationResult(
        report_path=report_path,
        summary_csv_path=summary_csv_path,
        summary_markdown_path=summary_markdown_path,
        single_best_solver_name=single_best_solver_name,
        classification_accuracy=classification_accuracy,
        balanced_accuracy=balanced_accuracy,
        average_selected_objective=average_selected_objective,
        average_virtual_best_objective=average_virtual_best_objective,
        average_single_best_objective=average_single_best_objective,
        regret_vs_virtual_best=regret_vs_virtual_best,
        delta_vs_single_best=delta_vs_single_best,
        improvement_vs_single_best=improvement_vs_single_best,
        num_test_instances=len(report.index),
        num_validation_splits=len(overall_split_summary.index),
        split_strategy=validation_result.split_plan.strategy,
    )
    summary_path = Path(run_summary_path) if run_summary_path is not None else default_run_summary_path(report_path)
    write_run_summary(
        summary_path,
        stage_name="selector_evaluation",
        config_path=config_path,
        config=config,
        settings={
            "random_seed": random_seed,
            "model_name": model_name,
            "split_strategy": validation_result.split_plan.strategy,
            "test_size": test_size,
            "cross_validation_folds": cross_validation_folds,
            "repeats": repeats,
            "split_notes": list(validation_result.split_plan.notes),
            "evaluation_uses_out_of_sample_validation": True,
            "model_path_recorded_for_traceability_only": model_path is not None,
        },
        inputs={
            "selection_dataset_csv": Path(dataset_csv),
            "benchmark_results_csv": Path(benchmark_csv),
            "model_output": Path(model_path) if model_path is not None else None,
        },
        outputs={
            "evaluation_report_csv": report_path,
            "evaluation_summary_csv": summary_csv_path,
            "evaluation_summary_markdown": summary_markdown_path,
            "run_summary": summary_path,
        },
        results={
            "single_best_solver_name": result.single_best_solver_name,
            "classification_accuracy": result.classification_accuracy,
            "balanced_accuracy": result.balanced_accuracy,
            "average_selected_objective": result.average_selected_objective,
            "average_virtual_best_objective": result.average_virtual_best_objective,
            "average_single_best_objective": result.average_single_best_objective,
            "regret_vs_virtual_best": result.regret_vs_virtual_best,
            "delta_vs_single_best": result.delta_vs_single_best,
            "improvement_vs_single_best": result.improvement_vs_single_best,
            "num_test_instances": result.num_test_instances,
            "num_validation_splits": result.num_validation_splits,
            "metrics_by_dataset_type": _aggregate_metrics_by_dataset_type(summary),
        },
    )
    LOGGER.info("Saved selector-evaluation run summary to %s", summary_path)
    return result


def evaluate_full_selector(
    dataset_csv: str | Path = DEFAULT_FULL_DATASET_PATH,
    synthetic_benchmark_csv: str | Path = DEFAULT_FULL_SYNTHETIC_BENCHMARKS_PATH,
    real_benchmark_csv: str | Path = DEFAULT_FULL_REAL_BENCHMARKS_PATH,
    combined_benchmark_csv: str | Path = DEFAULT_FULL_COMBINED_BENCHMARKS_PATH,
    model_path: str | Path | None = DEFAULT_FULL_MODEL_PATH,
    report_csv: str | Path = DEFAULT_FULL_REPORT_PATH,
    summary_csv: str | Path = DEFAULT_FULL_SUMMARY_CSV_PATH,
    summary_markdown: str | Path = DEFAULT_FULL_SUMMARY_MARKDOWN_PATH,
    random_seed: int = 42,
    test_size: float = 0.25,
    model_name: str = "random_forest",
    *,
    split_strategy: str = "holdout",
    cross_validation_folds: int | None = None,
    repeats: int = 1,
    config_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    run_summary_path: str | Path | None = None,
) -> SelectorEvaluationResult:

    # Evaluate the selector on the combined synthetic/real selection dataset.
    combined_path = _write_combined_full_benchmarks(
        synthetic_benchmark_csv=Path(synthetic_benchmark_csv),
        real_benchmark_csv=Path(real_benchmark_csv),
        output_csv=Path(combined_benchmark_csv),
    )
    return evaluate_selector(
        dataset_csv=dataset_csv,
        benchmark_csv=combined_path,
        model_path=model_path,
        report_csv=report_csv,
        summary_csv=summary_csv,
        summary_markdown=summary_markdown,
        random_seed=random_seed,
        test_size=test_size,
        model_name=model_name,
        split_strategy=split_strategy,
        cross_validation_folds=cross_validation_folds,
        repeats=repeats,
        config_path=config_path,
        config=config,
        run_summary_path=run_summary_path,
    )


def evaluate_selector_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> SelectorEvaluationResult:

    # Evaluate the selector using values loaded from a YAML configuration file.
    config = load_yaml_config(config_path)
    split_settings = get_split_settings(config)
    report_path = get_compat_path(config, ["paths.evaluation_report_csv"], DEFAULT_REPORT_PATH)
    summary_csv_path = get_compat_path(
        config,
        ["paths.evaluation_summary_csv"],
        DEFAULT_SUMMARY_CSV_PATH,
    )
    summary_markdown_path = get_compat_path(
        config,
        ["paths.evaluation_summary_markdown"],
        DEFAULT_SUMMARY_MARKDOWN_PATH,
    )
    summary_path = get_compat_path(
        config,
        ["paths.evaluation_run_summary", "paths.run_summary", "paths.run_summary_path"],
        default_run_summary_path(report_path),
    )
    return evaluate_selector(
        dataset_csv=get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_DATASET_PATH),
        benchmark_csv=get_compat_path(config, ["paths.benchmark_results_csv"], DEFAULT_BENCHMARKS_PATH),
        model_path=get_compat_path(config, ["paths.model_output"], DEFAULT_MODEL_PATH),
        report_csv=report_path,
        summary_csv=summary_csv_path,
        summary_markdown=summary_markdown_path,
        random_seed=get_random_seed(config, 42),
        test_size=split_settings.test_size,
        model_name=get_model_choice(config, "random_forest"),
        split_strategy=split_settings.strategy,
        cross_validation_folds=split_settings.cross_validation_folds,
        repeats=split_settings.repeats,
        config_path=config_path,
        config=config,
        run_summary_path=summary_path,
    )


def evaluate_full_selector_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> SelectorEvaluationResult:

    # Evaluate the selector using the combined synthetic/real dataset paths from config.
    config = load_yaml_config(config_path)
    split_settings = get_split_settings(config)
    report_path = get_compat_path(config, ["paths.full_evaluation_report_csv"], DEFAULT_FULL_REPORT_PATH)
    summary_path = get_compat_path(
        config,
        ["paths.full_evaluation_run_summary"],
        DEFAULT_FULL_EVALUATION_RUN_SUMMARY_PATH,
    )
    return evaluate_full_selector(
        dataset_csv=get_compat_path(config, ["paths.full_selection_dataset_csv"], DEFAULT_FULL_DATASET_PATH),
        synthetic_benchmark_csv=get_compat_path(
            config,
            ["paths.synthetic_benchmark_results_csv"],
            DEFAULT_FULL_SYNTHETIC_BENCHMARKS_PATH,
        ),
        real_benchmark_csv=get_compat_path(
            config,
            ["paths.real_benchmark_results_csv", "paths.benchmark_results_csv"],
            DEFAULT_FULL_REAL_BENCHMARKS_PATH,
        ),
        combined_benchmark_csv=get_compat_path(
            config,
            ["paths.full_combined_benchmark_results_csv"],
            DEFAULT_FULL_COMBINED_BENCHMARKS_PATH,
        ),
        model_path=get_compat_path(config, ["paths.full_model_output"], DEFAULT_FULL_MODEL_PATH),
        report_csv=report_path,
        summary_csv=get_compat_path(config, ["paths.full_evaluation_summary_csv"], DEFAULT_FULL_SUMMARY_CSV_PATH),
        summary_markdown=get_compat_path(
            config,
            ["paths.full_evaluation_summary_markdown"],
            DEFAULT_FULL_SUMMARY_MARKDOWN_PATH,
        ),
        random_seed=get_random_seed(config, 42),
        test_size=split_settings.test_size,
        model_name=get_model_choice(config, "random_forest"),
        split_strategy=split_settings.strategy,
        cross_validation_folds=split_settings.cross_validation_folds,
        repeats=split_settings.repeats,
        config_path=config_path,
        config=config,
        run_summary_path=summary_path,
    )


def build_argument_parser() -> argparse.ArgumentParser:

    # Create the command-line parser for selector evaluation.
    parser = argparse.ArgumentParser(
        description="Evaluate a selector using benchmark objectives and validation splits.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the selector YAML configuration file.",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to the selection dataset CSV.",
    )
    parser.add_argument(
        "--full-dataset",
        action="store_true",
        help="Evaluate data/processed/selection_dataset_full.csv and write full_selection outputs.",
    )
    parser.add_argument(
        "--benchmarks",
        default=None,
        help="Path to the benchmark results CSV. In --full-dataset mode this can point to a precombined benchmark CSV.",
    )
    parser.add_argument(
        "--synthetic-benchmarks",
        default=None,
        help="Synthetic benchmark results used to build the combined full benchmark CSV.",
    )
    parser.add_argument(
        "--real-benchmarks",
        default=None,
        help="Real benchmark results used to build the combined full benchmark CSV.",
    )
    parser.add_argument(
        "--combined-benchmarks-output",
        default=None,
        help="Output path for the combined full benchmark CSV in --full-dataset mode.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Optional trained selector model path recorded for traceability.",
    )
    parser.add_argument(
        "--report-output",
        default=None,
        help="Output path for the detailed evaluation report CSV.",
    )
    parser.add_argument(
        "--summary-output",
        default=None,
        help="Output path for the concise evaluation summary CSV.",
    )
    parser.add_argument(
        "--summary-markdown",
        default=None,
        help="Output path for the concise evaluation summary Markdown file.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Random seed used to reproduce validation splits.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=None,
        help="Fraction of labeled rows reserved for testing in holdout-style strategies.",
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="Selector model family. Version 1 supports: random_forest.",
    )
    parser.add_argument(
        "--split-strategy",
        default=None,
        help="Data split strategy: holdout, repeated_holdout, or repeated_stratified_kfold.",
    )
    parser.add_argument(
        "--cross-validation-folds",
        type=int,
        default=None,
        help="Number of folds for repeated_stratified_kfold.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=None,
        help="Number of validation repeats for repeated strategies.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:

    # Run selector evaluation from the command line.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = load_yaml_config(args.config)
        split_settings = get_split_settings(config)
        random_seed = args.random_seed if args.random_seed is not None else get_random_seed(config, 42)
        test_size = args.test_size if args.test_size is not None else split_settings.test_size
        model_name = args.model_name or get_model_choice(config, "random_forest")
        split_strategy = args.split_strategy or split_settings.strategy
        cross_validation_folds = (
            args.cross_validation_folds
            if args.cross_validation_folds is not None
            else split_settings.cross_validation_folds
        )
        repeats = args.repeats if args.repeats is not None else split_settings.repeats

        if args.full_dataset:
            resolved_report_path = args.report_output or get_compat_path(
                config,
                ["paths.full_evaluation_report_csv"],
                DEFAULT_FULL_REPORT_PATH,
            )
            if args.benchmarks:
                result = evaluate_selector(
                    dataset_csv=args.dataset
                    or get_compat_path(config, ["paths.full_selection_dataset_csv"], DEFAULT_FULL_DATASET_PATH),
                    benchmark_csv=args.benchmarks,
                    model_path=args.model or get_compat_path(config, ["paths.full_model_output"], DEFAULT_FULL_MODEL_PATH),
                    report_csv=resolved_report_path,
                    summary_csv=args.summary_output
                    or get_compat_path(config, ["paths.full_evaluation_summary_csv"], DEFAULT_FULL_SUMMARY_CSV_PATH),
                    summary_markdown=args.summary_markdown
                    or get_compat_path(
                        config,
                        ["paths.full_evaluation_summary_markdown"],
                        DEFAULT_FULL_SUMMARY_MARKDOWN_PATH,
                    ),
                    random_seed=random_seed,
                    test_size=test_size,
                    model_name=model_name,
                    split_strategy=split_strategy,
                    cross_validation_folds=cross_validation_folds,
                    repeats=repeats,
                    config_path=args.config,
                    config=config,
                    run_summary_path=get_compat_path(
                        config,
                        ["paths.full_evaluation_run_summary"],
                        DEFAULT_FULL_EVALUATION_RUN_SUMMARY_PATH,
                    ),
                )
            else:
                result = evaluate_full_selector(
                    dataset_csv=args.dataset
                    or get_compat_path(config, ["paths.full_selection_dataset_csv"], DEFAULT_FULL_DATASET_PATH),
                    synthetic_benchmark_csv=args.synthetic_benchmarks
                    or get_compat_path(
                        config,
                        ["paths.synthetic_benchmark_results_csv"],
                        DEFAULT_FULL_SYNTHETIC_BENCHMARKS_PATH,
                    ),
                    real_benchmark_csv=args.real_benchmarks
                    or get_compat_path(
                        config,
                        ["paths.real_benchmark_results_csv", "paths.benchmark_results_csv"],
                        DEFAULT_FULL_REAL_BENCHMARKS_PATH,
                    ),
                    combined_benchmark_csv=args.combined_benchmarks_output
                    or get_compat_path(
                        config,
                        ["paths.full_combined_benchmark_results_csv"],
                        DEFAULT_FULL_COMBINED_BENCHMARKS_PATH,
                    ),
                    model_path=args.model
                    or get_compat_path(config, ["paths.full_model_output"], DEFAULT_FULL_MODEL_PATH),
                    report_csv=resolved_report_path,
                    summary_csv=args.summary_output
                    or get_compat_path(config, ["paths.full_evaluation_summary_csv"], DEFAULT_FULL_SUMMARY_CSV_PATH),
                    summary_markdown=args.summary_markdown
                    or get_compat_path(
                        config,
                        ["paths.full_evaluation_summary_markdown"],
                        DEFAULT_FULL_SUMMARY_MARKDOWN_PATH,
                    ),
                    random_seed=random_seed,
                    test_size=test_size,
                    model_name=model_name,
                    split_strategy=split_strategy,
                    cross_validation_folds=cross_validation_folds,
                    repeats=repeats,
                    config_path=args.config,
                    config=config,
                    run_summary_path=get_compat_path(
                        config,
                        ["paths.full_evaluation_run_summary"],
                        DEFAULT_FULL_EVALUATION_RUN_SUMMARY_PATH,
                    ),
                )
        else:
            resolved_report_path = args.report_output or get_compat_path(
                config,
                ["paths.evaluation_report_csv"],
                DEFAULT_REPORT_PATH,
            )
            result = evaluate_selector(
                dataset_csv=args.dataset
                or get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_DATASET_PATH),
                benchmark_csv=args.benchmarks
                or get_compat_path(config, ["paths.benchmark_results_csv"], DEFAULT_BENCHMARKS_PATH),
                model_path=args.model or get_compat_path(config, ["paths.model_output"], DEFAULT_MODEL_PATH),
                report_csv=resolved_report_path,
                summary_csv=args.summary_output
                or get_compat_path(config, ["paths.evaluation_summary_csv"], DEFAULT_SUMMARY_CSV_PATH),
                summary_markdown=args.summary_markdown
                or get_compat_path(config, ["paths.evaluation_summary_markdown"], DEFAULT_SUMMARY_MARKDOWN_PATH),
                random_seed=random_seed,
                test_size=test_size,
                model_name=model_name,
                split_strategy=split_strategy,
                cross_validation_folds=cross_validation_folds,
                repeats=repeats,
                config_path=args.config,
                config=config,
                run_summary_path=get_compat_path(
                    config,
                    ["paths.evaluation_run_summary", "paths.run_summary", "paths.run_summary_path"],
                    default_run_summary_path(resolved_report_path),
                ),
            )
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError) as exc:
        print(f"Failed to evaluate selector: {exc}", file=sys.stderr)
        return 1

    print(f"Selector evaluation report saved to {result.report_path}")
    return 0


def _write_combined_full_benchmarks(
    *,
    synthetic_benchmark_csv: Path,
    real_benchmark_csv: Path,
    output_csv: Path,
) -> Path:

    # Write a canonical benchmark table for mixed synthetic/real evaluation.
    synthetic = _load_full_benchmark_source(synthetic_benchmark_csv, dataset_type="synthetic")
    real = _load_full_benchmark_source(real_benchmark_csv, dataset_type="real")
    combined = pd.concat([synthetic, real], ignore_index=True, sort=False)
    combined = combined.sort_values(
        by=["dataset_type", "instance_name", "solver_name", "runtime_seconds"],
        ascending=[True, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    ensure_parent_directory(output_csv)
    combined.to_csv(output_csv, index=False)
    return output_csv


def _load_full_benchmark_source(path: Path, *, dataset_type: str) -> pd.DataFrame:

    # Load one benchmark source and normalize solver names for full evaluation.
    frame = pd.read_csv(path)
    missing_columns = sorted(REQUIRED_BENCHMARK_COLUMNS.difference(frame.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Benchmark results are missing required columns: {missing}")

    frame = frame.copy()
    if "solver_registry_name" in frame.columns:
        registry_names = frame["solver_registry_name"].astype("string").str.strip()
        registry_names = registry_names.mask(registry_names == "", pd.NA)
        frame["solver_name"] = registry_names.fillna(frame["solver_name"]).astype("string")
    frame["dataset_type"] = dataset_type
    return frame


def _dataset_type_lookup(dataset: pd.DataFrame) -> dict[str, str]:

    # Return source labels keyed by instance name when a mixed dataset is used.
    if "dataset_type" not in dataset.columns:
        return {}
    if dataset["instance_name"].duplicated().any():
        raise ValueError("Mixed dataset evaluation requires unique instance_name values across dataset_type.")

    lookup_frame = dataset.loc[:, ["instance_name", "dataset_type"]].dropna(subset=["instance_name"])
    return {
        str(row["instance_name"]): str(row["dataset_type"])
        for row in lookup_frame.to_dict(orient="records")
        if str(row.get("dataset_type", "")).strip()
    }


def _prepare_benchmark_frame(benchmarks: pd.DataFrame) -> pd.DataFrame:

    # Validate and normalize benchmark results for evaluation lookup.
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

    deduplicated = (
        frame.sort_values(
            by=["instance_name", "solver_name", "objective_value", "runtime_seconds", "status"],
            ascending=[True, True, True, True, True],
            na_position="last",
            kind="mergesort",
        )
        .drop_duplicates(subset=["instance_name", "solver_name"], keep="first")
        .reset_index(drop=True)
    )
    return deduplicated


def _build_detailed_report(
    *,
    split_predictions: pd.DataFrame,
    test_benchmarks: pd.DataFrame,
    single_best_solver_name: str | None,
    dataset_type_by_instance: dict[str, str] | None = None,
) -> pd.DataFrame:

    # Build one detailed evaluation row per test instance in one split.
    true_best_frame = best_solver_per_instance(test_benchmarks).rename(columns={"solver_name": "true_best_solver"})
    true_best_lookup = true_best_frame.set_index("instance_name")
    benchmark_lookup = test_benchmarks.set_index(["instance_name", "solver_name"])

    rows: list[dict[str, Any]] = []
    for row in split_predictions.to_dict(orient="records"):
        instance_name = str(row["instance_name"])
        selected_solver = _coerce_string(row.get("predicted_solver")) or ""
        true_best_solver = _coerce_string(row.get("true_best_solver")) or _coerce_string(
            true_best_lookup.loc[instance_name, "true_best_solver"] if instance_name in true_best_lookup.index else None
        )

        selected_entry = _lookup_solver_entry(benchmark_lookup, instance_name, selected_solver)
        true_best_entry = _lookup_solver_entry(benchmark_lookup, instance_name, true_best_solver)
        single_best_entry = _lookup_solver_entry(benchmark_lookup, instance_name, single_best_solver_name)

        worst_feasible_objective = _worst_feasible_objective_for_instance(test_benchmarks, instance_name)
        selected_objective_for_scoring = _score_objective(
            selected_entry.get("objective_value"),
            worst_feasible_objective,
        )
        single_best_objective_for_scoring = (
            _score_objective(single_best_entry.get("objective_value"), worst_feasible_objective)
            if single_best_solver_name
            else float("nan")
        )

        best_possible_objective = _coerce_float(true_best_entry.get("objective_value"))
        regret_vs_virtual_best = (
            selected_objective_for_scoring - best_possible_objective
            if pd.notna(selected_objective_for_scoring) and pd.notna(best_possible_objective)
            else float("nan")
        )
        delta_vs_single_best = (
            selected_objective_for_scoring - single_best_objective_for_scoring
            if pd.notna(selected_objective_for_scoring) and pd.notna(single_best_objective_for_scoring)
            else float("nan")
        )

        report_row: dict[str, Any] = {"instance_name": instance_name}
        if dataset_type_by_instance:
            report_row["dataset_type"] = dataset_type_by_instance.get(instance_name, "unknown")
        report_row.update(
            {
                "selected_solver": selected_solver,
                "true_best_solver": true_best_solver,
                "prediction_correct": bool(selected_solver == true_best_solver),
                "selected_solver_objective": _coerce_float(selected_entry.get("objective_value")),
                "best_possible_objective": best_possible_objective,
                "single_best_solver": single_best_solver_name,
                "single_best_solver_objective": _coerce_float(single_best_entry.get("objective_value")),
                "selected_objective_for_scoring": selected_objective_for_scoring,
                "single_best_objective_for_scoring": single_best_objective_for_scoring,
                "regret_vs_virtual_best": regret_vs_virtual_best,
                "delta_vs_single_best": delta_vs_single_best,
                "improvement_vs_single_best": (
                    -delta_vs_single_best if pd.notna(delta_vs_single_best) else float("nan")
                ),
            }
        )
        rows.append(report_row)

    return pd.DataFrame(rows).sort_values("instance_name", kind="mergesort").reset_index(drop=True)


def _lookup_solver_entry(
    benchmark_lookup: pd.DataFrame,
    instance_name: str,
    solver_name: str | None,
) -> dict[str, Any]:

    # Return one benchmark row for an instance-solver pair, if present.
    if not solver_name:
        return {}

    key = (instance_name, solver_name)
    if key not in benchmark_lookup.index:
        return {}

    row = benchmark_lookup.loc[key]
    if isinstance(row, pd.DataFrame):
        row = row.iloc[0]
    return row.to_dict()


def _worst_feasible_objective_for_instance(test_benchmarks: pd.DataFrame, instance_name: str) -> float:

    # Return the worst feasible objective observed for an instance.
    instance_rows = test_benchmarks[
        (test_benchmarks["instance_name"] == instance_name)
        & test_benchmarks["feasible"]
        & test_benchmarks["objective_value"].notna()
    ]
    if instance_rows.empty:
        return float("nan")
    return float(instance_rows["objective_value"].max())


def _score_objective(objective_value: object, fallback_value: float) -> float:

    # Convert an actual objective into a scoring value with deterministic fallback.
    actual = _coerce_float(objective_value)
    if pd.notna(actual):
        return actual
    return fallback_value


def _build_dataset_type_split_rows(
    *,
    split_report: pd.DataFrame,
    split: Any,
    prepared_data: Any,
    train_indices: list[int],
    single_best_solver_name: str | None,
    dataset_type_by_instance: dict[str, str],
) -> list[dict[str, object]]:

    # Build per-source split metrics for mixed synthetic/real evaluation.
    if not dataset_type_by_instance or "dataset_type" not in split_report.columns:
        return []

    train_rows = pd.DataFrame(
        {
            "instance_name": prepared_data.instance_names.iloc[train_indices].astype(str).tolist(),
            "best_solver": prepared_data.target.iloc[train_indices].astype(str).tolist(),
        }
    )
    train_rows["dataset_type"] = train_rows["instance_name"].map(dataset_type_by_instance).fillna("unknown")

    source_rows: list[dict[str, object]] = []
    for dataset_type, rows in split_report.groupby("dataset_type", sort=True):
        train_source_rows = train_rows[train_rows["dataset_type"] == dataset_type]
        classification_accuracy = float(rows["prediction_correct"].astype(bool).mean())
        balanced_accuracy = _balanced_accuracy_for_rows(rows)
        average_selected_objective = float(rows["selected_objective_for_scoring"].mean())
        average_virtual_best_objective = float(rows["best_possible_objective"].mean())
        average_single_best_objective = float(rows["single_best_objective_for_scoring"].mean())
        regret_vs_virtual_best = average_selected_objective - average_virtual_best_objective
        delta_vs_single_best = average_selected_objective - average_single_best_objective

        source_rows.append(
            {
                "summary_row_type": "split_dataset_type",
                "dataset_type": str(dataset_type),
                "split_id": split.split_id,
                "split_strategy": split.strategy,
                "repeat_index": split.repeat_index,
                "fold_index": split.fold_index,
                "stratified_split": split.stratified,
                "single_best_solver_name": single_best_solver_name,
                "num_train_rows": int(len(train_source_rows.index)),
                "num_test_rows": int(len(rows.index)),
                "num_train_classes": int(train_source_rows["best_solver"].nunique()),
                "num_test_classes": int(rows["true_best_solver"].astype(str).nunique()),
                "classification_accuracy": classification_accuracy,
                "balanced_accuracy": balanced_accuracy,
                "average_selected_objective": average_selected_objective,
                "average_virtual_best_objective": average_virtual_best_objective,
                "average_single_best_objective": average_single_best_objective,
                "regret_vs_virtual_best": regret_vs_virtual_best,
                "delta_vs_single_best": delta_vs_single_best,
                "improvement_vs_single_best": -delta_vs_single_best,
            }
        )
    return source_rows


def _balanced_accuracy_for_rows(rows: pd.DataFrame) -> float | None:

    # Compute balanced accuracy for a detailed report group when meaningful.
    if rows["true_best_solver"].astype(str).nunique() < 2:
        return None
    return float(
        balanced_accuracy_score(
            rows["true_best_solver"].astype(str),
            rows["selected_solver"].astype(str),
        )
    )


def _overall_split_rows(split_summary: pd.DataFrame) -> pd.DataFrame:

    # Return only whole-split rows from a mixed summary table.
    if split_summary.empty or "summary_row_type" not in split_summary.columns:
        return split_summary
    return split_summary[split_summary["summary_row_type"] == "split"].copy()


def _build_evaluation_summary(
    *,
    split_summary: pd.DataFrame,
    split_strategy: str,
) -> pd.DataFrame:

    # Create one concise summary table with split rows and aggregate rows.
    metric_columns = [
        "classification_accuracy",
        "balanced_accuracy",
        "average_selected_objective",
        "average_virtual_best_objective",
        "average_single_best_objective",
        "regret_vs_virtual_best",
        "delta_vs_single_best",
        "improvement_vs_single_best",
    ]

    if split_summary.empty:
        return pd.DataFrame(
            columns=[
                "summary_row_type",
                "dataset_type",
                "split_id",
                "split_strategy",
                "repeat_index",
                "fold_index",
                "stratified_split",
                "single_best_solver_name",
                "num_train_rows",
                "num_test_rows",
                "num_train_classes",
                "num_test_classes",
                *metric_columns,
            ]
        )

    if "dataset_type" not in split_summary.columns:
        split_summary = split_summary.copy()
        split_summary["dataset_type"] = "all"

    overall_rows = _overall_split_rows(split_summary)
    aggregate_mean = {
        "summary_row_type": "aggregate_mean",
        "dataset_type": "all",
        "split_id": "aggregate_mean",
        "split_strategy": split_strategy,
        "repeat_index": None,
        "fold_index": None,
        "stratified_split": None,
        "single_best_solver_name": summarize_label_distribution(overall_rows["single_best_solver_name"].tolist()),
        "num_train_rows": float(overall_rows["num_train_rows"].mean()),
        "num_test_rows": float(overall_rows["num_test_rows"].mean()),
        "num_train_classes": float(overall_rows["num_train_classes"].mean()),
        "num_test_classes": float(overall_rows["num_test_classes"].mean()),
    }
    aggregate_std = {
        "summary_row_type": "aggregate_std",
        "dataset_type": "all",
        "split_id": "aggregate_std",
        "split_strategy": split_strategy,
        "repeat_index": None,
        "fold_index": None,
        "stratified_split": None,
        "single_best_solver_name": None,
        "num_train_rows": metric_standard_deviation(overall_rows["num_train_rows"]),
        "num_test_rows": metric_standard_deviation(overall_rows["num_test_rows"]),
        "num_train_classes": metric_standard_deviation(overall_rows["num_train_classes"]),
        "num_test_classes": metric_standard_deviation(overall_rows["num_test_classes"]),
    }
    for column in metric_columns:
        aggregate_mean[column] = aggregate_metric(overall_rows[column])
        aggregate_std[column] = metric_standard_deviation(overall_rows[column])

    aggregate_rows = [aggregate_mean, aggregate_std]
    dataset_type_rows = split_summary[split_summary["summary_row_type"] == "split_dataset_type"].copy()
    if not dataset_type_rows.empty:
        for dataset_type, rows in dataset_type_rows.groupby("dataset_type", sort=True):
            source_mean = {
                "summary_row_type": "aggregate_dataset_type_mean",
                "dataset_type": str(dataset_type),
                "split_id": f"aggregate_dataset_type_mean_{dataset_type}",
                "split_strategy": split_strategy,
                "repeat_index": None,
                "fold_index": None,
                "stratified_split": None,
                "single_best_solver_name": summarize_label_distribution(rows["single_best_solver_name"].tolist()),
                "num_train_rows": float(rows["num_train_rows"].mean()),
                "num_test_rows": float(rows["num_test_rows"].mean()),
                "num_train_classes": float(rows["num_train_classes"].mean()),
                "num_test_classes": float(rows["num_test_classes"].mean()),
            }
            source_std = {
                "summary_row_type": "aggregate_dataset_type_std",
                "dataset_type": str(dataset_type),
                "split_id": f"aggregate_dataset_type_std_{dataset_type}",
                "split_strategy": split_strategy,
                "repeat_index": None,
                "fold_index": None,
                "stratified_split": None,
                "single_best_solver_name": None,
                "num_train_rows": metric_standard_deviation(rows["num_train_rows"]),
                "num_test_rows": metric_standard_deviation(rows["num_test_rows"]),
                "num_train_classes": metric_standard_deviation(rows["num_train_classes"]),
                "num_test_classes": metric_standard_deviation(rows["num_test_classes"]),
            }
            for column in metric_columns:
                source_mean[column] = aggregate_metric(rows[column])
                source_std[column] = metric_standard_deviation(rows[column])
            aggregate_rows.extend([source_mean, source_std])

    return pd.concat(
        [
            split_summary,
            pd.DataFrame(aggregate_rows),
        ],
        ignore_index=True,
    )


def _build_summary_markdown(
    *,
    split_summary: pd.DataFrame,
    summary: pd.DataFrame,
    split_notes: tuple[str, ...],
    split_strategy: str,
) -> str:

    # Render a concise Markdown summary for thesis reporting.
    mean_row = summary[summary["summary_row_type"] == "aggregate_mean"].iloc[0]
    std_row = summary[summary["summary_row_type"] == "aggregate_std"].iloc[0]
    lines = [
        "# Selector Evaluation Summary",
        "",
        f"- Split strategy: `{split_strategy}`",
        f"- Validation splits: `{len(_overall_split_rows(split_summary).index)}`",
        "- Leakage control: training excludes benchmark-derived `objective_*` columns and computes SBS on the training partition only.",
        "- Interpretation: objectives are compared inside the current target policy; support and scoring-status columns must be read before making broader solver-quality claims.",
        "",
        "| Metric | Mean | Std |",
        "| --- | ---: | ---: |",
    ]

    for metric_name in [
        "classification_accuracy",
        "balanced_accuracy",
        "average_selected_objective",
        "average_virtual_best_objective",
        "average_single_best_objective",
        "regret_vs_virtual_best",
        "delta_vs_single_best",
        "improvement_vs_single_best",
    ]:
        lines.append(
            "| "
            f"{metric_name} | {_format_markdown_value(mean_row[metric_name])} | {_format_markdown_value(std_row[metric_name])} |"
        )

    by_source = summary[summary["summary_row_type"] == "aggregate_dataset_type_mean"].copy()
    if not by_source.empty:
        lines.extend(
            [
                "",
                "## Metrics By Dataset Type",
                "",
                "| Dataset Type | Accuracy | Balanced Accuracy | Selected Objective | Regret Vs VBS | Delta Vs SBS |",
                "| --- | ---: | ---: | ---: | ---: | ---: |",
            ]
        )
        for row in by_source.sort_values("dataset_type", kind="mergesort").to_dict(orient="records"):
            lines.append(
                "| "
                f"{row['dataset_type']} | "
                f"{_format_markdown_value(row.get('classification_accuracy'))} | "
                f"{_format_markdown_value(row.get('balanced_accuracy'))} | "
                f"{_format_markdown_value(row.get('average_selected_objective'))} | "
                f"{_format_markdown_value(row.get('regret_vs_virtual_best'))} | "
                f"{_format_markdown_value(row.get('delta_vs_single_best'))} |"
            )

    if split_notes:
        lines.extend(
            [
                "",
                "## Split Notes",
                "",
                *[f"- {note}" for note in split_notes],
            ]
        )

    return "\n".join(lines) + "\n"


def _format_markdown_value(value: object) -> str:

    # Format numeric summary values for Markdown output.
    numeric = _coerce_float(value)
    if pd.isna(numeric):
        return "NA"
    return f"{numeric:.4f}"


def _aggregate_metrics_by_dataset_type(summary: pd.DataFrame) -> dict[str, dict[str, float | None]]:

    # Return source-specific aggregate metrics for run summaries.
    if summary.empty or "dataset_type" not in summary.columns:
        return {}
    rows = summary[summary["summary_row_type"] == "aggregate_dataset_type_mean"]
    metrics: dict[str, dict[str, float | None]] = {}
    for row in rows.to_dict(orient="records"):
        dataset_type = str(row.get("dataset_type") or "unknown")
        metrics[dataset_type] = {
            "classification_accuracy": _json_float(row.get("classification_accuracy")),
            "balanced_accuracy": _json_float(row.get("balanced_accuracy")),
            "average_selected_objective": _json_float(row.get("average_selected_objective")),
            "average_virtual_best_objective": _json_float(row.get("average_virtual_best_objective")),
            "average_single_best_objective": _json_float(row.get("average_single_best_objective")),
            "regret_vs_virtual_best": _json_float(row.get("regret_vs_virtual_best")),
            "delta_vs_single_best": _json_float(row.get("delta_vs_single_best")),
        }
    return metrics


def _json_float(value: object) -> float | None:

    # Return a JSON-safe float value.
    numeric = _coerce_float(value)
    if pd.isna(numeric):
        return None
    return float(numeric)


def _coerce_feasible(value: object) -> bool:

    # Normalize a CSV-style feasibility value to a Python boolean.
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False

    normalized = str(value).strip().casefold()
    if normalized in {"true", "1", "yes", "y"}:
        return True
    if normalized in {"false", "0", "no", "n", ""}:
        return False
    return False


def _coerce_string(value: object) -> str | None:

    # Convert a scalar to a normalized string, if possible.
    if value is None or pd.isna(value):
        return None
    normalized = str(value).strip()
    return normalized or None


def _coerce_float(value: object) -> float:

    # Convert a scalar to float, returning ``nan`` on failure.
    if value is None or pd.isna(value):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


__all__ = [
    "DEFAULT_BENCHMARKS_PATH",
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_FULL_COMBINED_BENCHMARKS_PATH",
    "DEFAULT_FULL_EVALUATION_RUN_SUMMARY_PATH",
    "DEFAULT_FULL_REAL_BENCHMARKS_PATH",
    "DEFAULT_FULL_REPORT_PATH",
    "DEFAULT_FULL_SUMMARY_CSV_PATH",
    "DEFAULT_FULL_SUMMARY_MARKDOWN_PATH",
    "DEFAULT_FULL_SYNTHETIC_BENCHMARKS_PATH",
    "DEFAULT_MODEL_PATH",
    "DEFAULT_REPORT_PATH",
    "DEFAULT_SUMMARY_CSV_PATH",
    "DEFAULT_SUMMARY_MARKDOWN_PATH",
    "SelectorEvaluationResult",
    "evaluate_full_selector",
    "evaluate_full_selector_from_config",
    "evaluate_selector",
    "evaluate_selector_from_config",
]


if __name__ == "__main__":
    raise SystemExit(main())
