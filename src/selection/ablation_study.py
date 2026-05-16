# Ablation study support for selector interpretability.

from __future__ import annotations

import argparse
import logging
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd


matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.selection.evaluate_selector import (
    DEFAULT_BENCHMARKS_PATH,
    evaluate_selector,
)
from src.selection.feature_groups import default_ablation_feature_sets
from src.selection.modeling import INSTANCE_COLUMN, TARGET_COLUMN, prepare_selection_data
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
DEFAULT_DATASET_PATH = Path("data/processed/selection_dataset.csv")
DEFAULT_ABLATION_SUMMARY_CSV = Path("data/results/selector_ablation_summary.csv")
DEFAULT_ABLATION_PLOT = Path("data/results/selector_ablation_regret.png")
DEFAULT_ABLATION_REPORT = Path("data/results/selector_ablation_summary.md")


@dataclass(slots=True)
class AblationStudyResult:

    # Summary of one selector ablation study run.
    summary_csv_path: Path
    plot_path: Path
    report_markdown_path: Path
    best_feature_set_name: str
    num_feature_sets: int


def run_ablation_study(
    dataset_csv: str | Path = DEFAULT_DATASET_PATH,
    benchmark_csv: str | Path = DEFAULT_BENCHMARKS_PATH,
    summary_csv: str | Path = DEFAULT_ABLATION_SUMMARY_CSV,
    plot_path: str | Path = DEFAULT_ABLATION_PLOT,
    report_markdown: str | Path = DEFAULT_ABLATION_REPORT,
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
) -> AblationStudyResult:

    # Run a small thesis-facing ablation study over selector feature groups.
    dataset_path = Path(dataset_csv)
    benchmark_path = Path(benchmark_csv)
    dataset = pd.read_csv(dataset_path)
    prepared_data = prepare_selection_data(dataset)
    feature_sets = default_ablation_feature_sets(prepared_data.feature_columns)
    if len(feature_sets) < 3:
        raise ValueError("Ablation study requires at least three feature subsets.")

    split_settings = SplitSettings(
        strategy=split_strategy,
        test_size=test_size,
        cross_validation_folds=cross_validation_folds,
        repeats=repeats,
    )

    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="selector_ablation_") as temp_dir:
        temp_path = Path(temp_dir)
        for feature_set in feature_sets:
            subset_dataset = dataset.loc[:, [INSTANCE_COLUMN, *feature_set.feature_columns, TARGET_COLUMN]].copy()
            subset_dataset_path = temp_path / f"{feature_set.name}_dataset.csv"
            subset_dataset.to_csv(subset_dataset_path, index=False)

            subset_result = evaluate_selector(
                dataset_csv=subset_dataset_path,
                benchmark_csv=benchmark_path,
                model_path=None,
                report_csv=temp_path / f"{feature_set.name}_report.csv",
                summary_csv=temp_path / f"{feature_set.name}_summary.csv",
                summary_markdown=temp_path / f"{feature_set.name}_summary.md",
                random_seed=random_seed,
                test_size=split_settings.test_size,
                model_name=model_name,
                split_strategy=split_settings.strategy,
                cross_validation_folds=split_settings.cross_validation_folds,
                repeats=split_settings.repeats,
            )
            subset_summary = pd.read_csv(temp_path / f"{feature_set.name}_summary.csv")
            mean_row = subset_summary[subset_summary["summary_row_type"] == "aggregate_mean"].iloc[0]
            std_row = subset_summary[subset_summary["summary_row_type"] == "aggregate_std"].iloc[0]
            rows.append(
                {
                    "feature_set_name": feature_set.name,
                    "feature_set_title": feature_set.title,
                    "feature_groups": ", ".join(feature_set.groups),
                    "num_features": len(feature_set.feature_columns),
                    "feature_columns": ", ".join(feature_set.feature_columns),
                    "classification_accuracy_mean": _coerce_float(mean_row["classification_accuracy"]),
                    "classification_accuracy_std": _coerce_float(std_row["classification_accuracy"]),
                    "balanced_accuracy_mean": _coerce_float(mean_row["balanced_accuracy"]),
                    "balanced_accuracy_std": _coerce_float(std_row["balanced_accuracy"]),
                    "average_selected_objective_mean": _coerce_float(mean_row["average_selected_objective"]),
                    "average_selected_objective_std": _coerce_float(std_row["average_selected_objective"]),
                    "average_virtual_best_objective_mean": _coerce_float(mean_row["average_virtual_best_objective"]),
                    "average_single_best_objective_mean": _coerce_float(mean_row["average_single_best_objective"]),
                    "regret_vs_virtual_best_mean": subset_result.regret_vs_virtual_best,
                    "regret_vs_virtual_best_std": _coerce_float(std_row["regret_vs_virtual_best"]),
                    "delta_vs_single_best_mean": subset_result.delta_vs_single_best,
                    "delta_vs_single_best_std": _coerce_float(std_row["delta_vs_single_best"]),
                    "num_validation_splits": subset_result.num_validation_splits,
                }
            )

    summary_frame = pd.DataFrame(rows).sort_values(
        by=["regret_vs_virtual_best_mean", "delta_vs_single_best_mean", "classification_accuracy_mean", "feature_set_name"],
        ascending=[True, True, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    if summary_frame.empty:
        raise ValueError("Ablation study did not produce any results.")

    best_feature_set_name = str(summary_frame.loc[0, "feature_set_name"])
    summary_output_path = ensure_parent_directory(summary_csv)
    summary_frame.to_csv(summary_output_path, index=False)

    plot_output_path = ensure_parent_directory(plot_path)
    _plot_ablation_summary(summary_frame, plot_output_path)

    report_output_path = ensure_parent_directory(report_markdown)
    report_output_path.write_text(
        _build_ablation_markdown_report(summary_frame, split_settings),
        encoding="utf-8",
    )

    result = AblationStudyResult(
        summary_csv_path=summary_output_path,
        plot_path=plot_output_path,
        report_markdown_path=report_output_path,
        best_feature_set_name=best_feature_set_name,
        num_feature_sets=len(summary_frame.index),
    )
    summary_path = Path(run_summary_path) if run_summary_path is not None else default_run_summary_path(summary_output_path)
    write_run_summary(
        summary_path,
        stage_name="selector_ablation_study",
        config_path=config_path,
        config=config,
        settings={
            "random_seed": random_seed,
            "model_name": model_name,
            "split_strategy": split_settings.strategy,
            "test_size": split_settings.test_size,
            "cross_validation_folds": split_settings.cross_validation_folds,
            "repeats": split_settings.repeats,
        },
        inputs={
            "selection_dataset_csv": dataset_path,
            "benchmark_results_csv": benchmark_path,
        },
        outputs={
            "ablation_summary_csv": summary_output_path,
            "ablation_plot": plot_output_path,
            "ablation_report_markdown": report_output_path,
            "run_summary": summary_path,
        },
        results={
            "best_feature_set_name": result.best_feature_set_name,
            "num_feature_sets": result.num_feature_sets,
        },
    )
    LOGGER.info("Saved selector ablation summary to %s", summary_output_path)
    LOGGER.info("Saved selector ablation plot to %s", plot_output_path)
    LOGGER.info("Saved selector ablation report to %s", report_output_path)
    LOGGER.info("Saved selector ablation run summary to %s", summary_path)
    return result


def run_ablation_study_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> AblationStudyResult:

    # Run the selector ablation study using values loaded from a YAML configuration file.
    config = load_yaml_config(config_path)
    split_settings = get_split_settings(config)
    summary_csv = get_compat_path(config, ["paths.ablation_summary_csv"], DEFAULT_ABLATION_SUMMARY_CSV)
    run_summary = get_compat_path(
        config,
        ["paths.ablation_run_summary", "paths.run_summary", "paths.run_summary_path"],
        default_run_summary_path(summary_csv),
    )
    return run_ablation_study(
        dataset_csv=get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_DATASET_PATH),
        benchmark_csv=get_compat_path(config, ["paths.benchmark_results_csv"], DEFAULT_BENCHMARKS_PATH),
        summary_csv=summary_csv,
        plot_path=get_compat_path(config, ["paths.ablation_plot"], DEFAULT_ABLATION_PLOT),
        report_markdown=get_compat_path(config, ["paths.ablation_report_markdown"], DEFAULT_ABLATION_REPORT),
        random_seed=get_random_seed(config, 42),
        test_size=split_settings.test_size,
        model_name=get_model_choice(config, "random_forest"),
        split_strategy=split_settings.strategy,
        cross_validation_folds=split_settings.cross_validation_folds,
        repeats=split_settings.repeats,
        config_path=config_path,
        config=config,
        run_summary_path=run_summary,
    )


def build_argument_parser() -> argparse.ArgumentParser:

    # Create the command-line parser for selector ablation studies.
    parser = argparse.ArgumentParser(
        description="Run a lightweight selector ablation study.",
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="Path to the selector YAML configuration file.")
    parser.add_argument("--dataset", default=None, help="Path to the selection dataset CSV.")
    parser.add_argument("--benchmarks", default=None, help="Path to the benchmark results CSV.")
    parser.add_argument("--summary-output", default=None, help="Output path for the ablation summary CSV.")
    parser.add_argument("--plot-output", default=None, help="Output path for the ablation plot.")
    parser.add_argument("--report-output", default=None, help="Output path for the ablation Markdown report.")
    parser.add_argument("--random-seed", type=int, default=None, help="Random seed used to reproduce validation splits.")
    parser.add_argument("--test-size", type=float, default=None, help="Fraction of labeled rows reserved for testing in holdout-style strategies.")
    parser.add_argument("--model-name", default=None, help="Selector model family. Version 1 supports: random_forest.")
    parser.add_argument("--split-strategy", default=None, help="Data split strategy: holdout, repeated_holdout, or repeated_stratified_kfold.")
    parser.add_argument("--cross-validation-folds", type=int, default=None, help="Number of folds for repeated_stratified_kfold.")
    parser.add_argument("--repeats", type=int, default=None, help="Number of validation repeats for repeated strategies.")
    return parser


def main(argv: list[str] | None = None) -> int:

    # Run selector ablation study from the command line.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = load_yaml_config(args.config)
        split_settings = get_split_settings(config)
        result = run_ablation_study(
            dataset_csv=args.dataset or get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_DATASET_PATH),
            benchmark_csv=args.benchmarks or get_compat_path(config, ["paths.benchmark_results_csv"], DEFAULT_BENCHMARKS_PATH),
            summary_csv=args.summary_output or get_compat_path(config, ["paths.ablation_summary_csv"], DEFAULT_ABLATION_SUMMARY_CSV),
            plot_path=args.plot_output or get_compat_path(config, ["paths.ablation_plot"], DEFAULT_ABLATION_PLOT),
            report_markdown=args.report_output or get_compat_path(config, ["paths.ablation_report_markdown"], DEFAULT_ABLATION_REPORT),
            random_seed=args.random_seed if args.random_seed is not None else get_random_seed(config, 42),
            test_size=args.test_size if args.test_size is not None else split_settings.test_size,
            model_name=args.model_name or get_model_choice(config, "random_forest"),
            split_strategy=args.split_strategy or split_settings.strategy,
            cross_validation_folds=(
                args.cross_validation_folds
                if args.cross_validation_folds is not None
                else split_settings.cross_validation_folds
            ),
            repeats=args.repeats if args.repeats is not None else split_settings.repeats,
            config_path=args.config,
            config=config,
            run_summary_path=get_compat_path(
                config,
                ["paths.ablation_run_summary", "paths.run_summary", "paths.run_summary_path"],
                default_run_summary_path(args.summary_output or get_compat_path(config, ["paths.ablation_summary_csv"], DEFAULT_ABLATION_SUMMARY_CSV)),
            ),
        )
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError) as exc:
        print(f"Failed to run selector ablation study: {exc}", file=sys.stderr)
        return 1

    print(f"Selector ablation summary saved to {result.summary_csv_path}")
    return 0


def _plot_ablation_summary(summary: pd.DataFrame, output_path: Path) -> None:

    # Plot regret vs virtual best for the evaluated feature sets.
    figure, axis = plt.subplots(figsize=(9, 4.5))
    axis.barh(
        summary["feature_set_title"],
        summary["regret_vs_virtual_best_mean"],
        color=["#1f5b92", "#2a9d8f", "#c77d1a"][: len(summary.index)],
    )
    axis.invert_yaxis()
    axis.set_xlabel("Mean regret vs virtual best")
    axis.set_ylabel("Feature set")
    axis.set_title("Selector ablation study")
    for index, row in summary.reset_index(drop=True).iterrows():
        axis.text(
            float(row["regret_vs_virtual_best_mean"]) + 0.02,
            index,
            f"acc={float(row['classification_accuracy_mean']):.3f}",
            va="center",
            fontsize=9,
        )
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def _build_ablation_markdown_report(summary: pd.DataFrame, split_settings: SplitSettings) -> str:

    # Render a concise Markdown ablation report for thesis reuse.
    best_row = summary.iloc[0]
    lines = [
        "# Selector Ablation Summary",
        "",
        f"- Split strategy: `{split_settings.strategy}`",
        f"- Validation repeats: `{split_settings.repeats}`",
        f"- Best feature set by regret vs virtual best: `{best_row['feature_set_name']}`",
        "",
        "| Feature set | Groups | Features | Accuracy | Balanced accuracy | Regret vs VBS | Delta vs SBS |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in summary.to_dict(orient="records"):
        lines.append(
            "| "
            f"{row['feature_set_title']} | "
            f"{row['feature_groups']} | "
            f"{int(row['num_features'])} | "
            f"{_format_metric(row['classification_accuracy_mean'])} | "
            f"{_format_metric(row['balanced_accuracy_mean'])} | "
            f"{_format_metric(row['regret_vs_virtual_best_mean'])} | "
            f"{_format_metric(row['delta_vs_single_best_mean'])} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- `size_only` tests whether instance scale alone is enough for useful algorithm selection.",
            "- `size_plus_constraint_composition` checks whether the basic constraint mix adds predictive value.",
            "- `all_features` is the full thesis feature set currently available in the pipeline.",
        ]
    )
    return "\n".join(lines) + "\n"


def _format_metric(value: object) -> str:

    # Format one numeric metric for ablation reporting.
    numeric = _coerce_float(value)
    if pd.isna(numeric):
        return "NA"
    return f"{numeric:.4f}"


def _coerce_float(value: object) -> float:

    # Convert a scalar to float, returning ``nan`` on failure.
    if value is None or pd.isna(value):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


__all__ = [
    "AblationStudyResult",
    "run_ablation_study",
    "run_ablation_study_from_config",
]


if __name__ == "__main__":
    raise SystemExit(main())
