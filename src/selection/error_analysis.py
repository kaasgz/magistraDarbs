# Error analysis for selector decisions.
#
# This module analyzes selector evaluation outputs with a focus on algorithm
# selection quality rather than only classifier accuracy.
#
# Version 1 workflow:
#
# - Load the detailed selector evaluation report.
# - Merge it with the selection dataset to recover instance features.
# - Mark "hard instances" as the upper quartile of positive regret values.
# - Summarize the most common solver confusions.
# - Compare simple numeric feature averages for hard vs non-hard instances.
#
# Saved artefacts are intended to be compact and thesis-friendly:
#
# - ``hard_instances.csv`` for close qualitative inspection.
# - ``hard_instance_regret.png`` for the worst underperforming instances.
# - ``confused_solver_pairs.png`` for the most frequent mis-selections.
# - ``hard_instance_feature_patterns.png`` for simple feature differences.

from __future__ import annotations

import argparse
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd


matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.selection.feature_groups import feature_group_for_column
from src.utils import (
    default_run_summary_path,
    ensure_directory,
    get_compat_path,
    load_yaml_config,
    write_run_summary,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("configs/selector_config.yaml")
DEFAULT_EVALUATION_REPORT = Path("data/results/selector_evaluation.csv")
DEFAULT_SELECTION_DATASET = Path("data/processed/selection_dataset.csv")
DEFAULT_OUTPUT_DIR = Path("data/results/error_analysis")
REQUIRED_EVALUATION_COLUMNS = {
    "instance_name",
    "selected_solver",
    "true_best_solver",
    "selected_solver_objective",
    "best_possible_objective",
    "regret_vs_virtual_best",
    "improvement_vs_single_best",
}


@dataclass(slots=True)
class ErrorAnalysisResult:

    # Summary of generated error-analysis artefacts.
    output_dir: Path
    hard_instances_csv: Path
    confusion_pairs_csv: Path
    cluster_summary_csv: Path
    summary_markdown: Path
    hard_instance_plot: Path
    confusion_plot: Path
    feature_pattern_plot: Path
    num_hard_instances: int
    num_confusion_pairs: int


def analyze_selector_errors(
    evaluation_report_csv: str | Path = DEFAULT_EVALUATION_REPORT,
    selection_dataset_csv: str | Path = DEFAULT_SELECTION_DATASET,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    config_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    run_summary_path: str | Path | None = None,
) -> ErrorAnalysisResult:

    # Analyze selector errors and save thesis-friendly artefacts.
    evaluation_path = Path(evaluation_report_csv)
    dataset_path = Path(selection_dataset_csv)
    output_path = Path(output_dir)

    evaluation_report = pd.read_csv(evaluation_path)
    selection_dataset = pd.read_csv(dataset_path)

    _validate_evaluation_report(evaluation_report)
    _validate_selection_dataset(selection_dataset)

    merged = evaluation_report.merge(
        selection_dataset,
        on="instance_name",
        how="left",
        suffixes=("", "_dataset"),
    )
    merged["analysis_case_id"] = _analysis_case_id(merged)
    merged["regret_vs_virtual_best"] = pd.to_numeric(
        merged["regret_vs_virtual_best"],
        errors="coerce",
    )
    merged["improvement_vs_single_best"] = pd.to_numeric(
        merged["improvement_vs_single_best"],
        errors="coerce",
    )
    if "prediction_correct" not in merged.columns:
        merged["prediction_correct"] = (
            merged["selected_solver"].astype("string") == merged["true_best_solver"].astype("string")
        )

    hard_instances = _identify_hard_instances(merged)
    confusion_pairs = _most_confused_solver_pairs(merged)
    feature_pattern_frame = _feature_pattern_summary(merged, hard_instances)
    cluster_summary = _error_cluster_summary(merged, feature_pattern_frame)

    ensure_directory(output_path)
    hard_instances_csv = output_path / "hard_instances.csv"
    confusion_pairs_csv = output_path / "confused_solver_pairs.csv"
    cluster_summary_csv = output_path / "error_cluster_summary.csv"
    summary_markdown = output_path / "error_analysis_summary.md"
    hard_instance_plot = output_path / "hard_instance_regret.png"
    confusion_plot = output_path / "confused_solver_pairs.png"
    feature_pattern_plot = output_path / "hard_instance_feature_patterns.png"

    hard_instances.to_csv(hard_instances_csv, index=False)
    confusion_pairs.to_csv(confusion_pairs_csv, index=False)
    cluster_summary.to_csv(cluster_summary_csv, index=False)
    _plot_hard_instances(hard_instances, hard_instance_plot)
    _plot_confusion_pairs(confusion_pairs, confusion_plot)
    _plot_feature_patterns(feature_pattern_frame, feature_pattern_plot)
    summary_markdown.write_text(
        _build_error_analysis_markdown(
            hard_instances=hard_instances,
            confusion_pairs=confusion_pairs,
            cluster_summary=cluster_summary,
        ),
        encoding="utf-8",
    )

    LOGGER.info("Saved hard instances to %s", hard_instances_csv)
    LOGGER.info("Saved confused solver pairs to %s", confusion_pairs_csv)
    LOGGER.info("Saved error cluster summary to %s", cluster_summary_csv)
    LOGGER.info("Saved error analysis summary to %s", summary_markdown)
    LOGGER.info("Saved hard-instance plot to %s", hard_instance_plot)
    LOGGER.info("Saved confusion plot to %s", confusion_plot)
    LOGGER.info("Saved feature-pattern plot to %s", feature_pattern_plot)

    result = ErrorAnalysisResult(
        output_dir=output_path,
        hard_instances_csv=hard_instances_csv,
        confusion_pairs_csv=confusion_pairs_csv,
        cluster_summary_csv=cluster_summary_csv,
        summary_markdown=summary_markdown,
        hard_instance_plot=hard_instance_plot,
        confusion_plot=confusion_plot,
        feature_pattern_plot=feature_pattern_plot,
        num_hard_instances=len(hard_instances.index),
        num_confusion_pairs=len(confusion_pairs.index),
    )
    summary_path = Path(run_summary_path) if run_summary_path is not None else default_run_summary_path(output_path)
    write_run_summary(
        summary_path,
        stage_name="selector_error_analysis",
        config_path=config_path,
        config=config,
        settings={},
        inputs={
            "evaluation_report_csv": evaluation_path,
            "selection_dataset_csv": dataset_path,
        },
        outputs={
            "output_dir": output_path,
            "hard_instances_csv": hard_instances_csv,
            "confusion_pairs_csv": confusion_pairs_csv,
            "cluster_summary_csv": cluster_summary_csv,
            "summary_markdown": summary_markdown,
            "hard_instance_plot": hard_instance_plot,
            "confusion_plot": confusion_plot,
            "feature_pattern_plot": feature_pattern_plot,
            "run_summary": summary_path,
        },
        results={
            "num_hard_instances": result.num_hard_instances,
            "num_confusion_pairs": result.num_confusion_pairs,
            "num_cluster_rows": int(len(cluster_summary.index)),
        },
    )
    LOGGER.info("Saved selector-error-analysis run summary to %s", summary_path)
    return result


def analyze_selector_errors_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> ErrorAnalysisResult:

    # Analyze selector errors using values loaded from a YAML configuration file.
    config = load_yaml_config(config_path)
    output_dir = get_compat_path(
        config,
        ["paths.error_analysis_output_dir"],
        DEFAULT_OUTPUT_DIR,
    )
    summary_path = get_compat_path(
        config,
        ["paths.error_analysis_run_summary", "paths.run_summary", "paths.run_summary_path"],
        default_run_summary_path(output_dir),
    )
    return analyze_selector_errors(
        evaluation_report_csv=get_compat_path(config, ["paths.evaluation_report_csv"], DEFAULT_EVALUATION_REPORT),
        selection_dataset_csv=get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_SELECTION_DATASET),
        output_dir=output_dir,
        config_path=config_path,
        config=config,
        run_summary_path=summary_path,
    )


def build_argument_parser() -> argparse.ArgumentParser:

    # Create the command-line parser for selector error analysis.
    parser = argparse.ArgumentParser(
        description="Analyze selector errors from evaluation outputs.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the selector YAML configuration file.",
    )
    parser.add_argument(
        "--evaluation-report",
        default=None,
        help="Path to the selector evaluation report CSV.",
    )
    parser.add_argument(
        "--selection-dataset",
        default=None,
        help="Path to the selection dataset CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=None,
        help="Directory where error-analysis artefacts will be written.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:

    # Run selector error analysis from the command line.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = load_yaml_config(args.config)
        resolved_output_dir = args.output_dir or get_compat_path(
            config,
            ["paths.error_analysis_output_dir"],
            DEFAULT_OUTPUT_DIR,
        )
        result = analyze_selector_errors(
            evaluation_report_csv=args.evaluation_report
            or get_compat_path(config, ["paths.evaluation_report_csv"], DEFAULT_EVALUATION_REPORT),
            selection_dataset_csv=args.selection_dataset
            or get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_SELECTION_DATASET),
            output_dir=resolved_output_dir,
            config_path=args.config,
            config=config,
            run_summary_path=get_compat_path(
                config,
                ["paths.error_analysis_run_summary", "paths.run_summary", "paths.run_summary_path"],
                default_run_summary_path(resolved_output_dir),
            ),
        )
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError) as exc:
        print(f"Failed to analyze selector errors: {exc}", file=sys.stderr)
        return 1

    print(f"Selector error analysis saved to {result.output_dir}")
    return 0


def _validate_evaluation_report(report: pd.DataFrame) -> None:

    # Validate the expected selector evaluation report schema.
    missing_columns = sorted(REQUIRED_EVALUATION_COLUMNS.difference(report.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Evaluation report is missing required columns: {missing}")


def _validate_selection_dataset(dataset: pd.DataFrame) -> None:

    # Validate that the selection dataset can be joined by instance name.
    if "instance_name" not in dataset.columns:
        raise ValueError("Selection dataset must contain an 'instance_name' column.")
    if dataset["instance_name"].duplicated().any():
        raise ValueError("Selection dataset must contain unique instance_name values.")


def _identify_hard_instances(merged: pd.DataFrame) -> pd.DataFrame:

    # Return the most severe underperforming instances.
    #
    # Version 1 definition:
    # Hard instances are those with positive regret that are at or above the
    # 75th percentile of positive regrets. This yields a deterministic subset
    # that focuses on the most costly selector mistakes.
    #
    positive_regret = merged["regret_vs_virtual_best"].dropna()
    positive_regret = positive_regret[positive_regret > 0.0]

    if positive_regret.empty:
        return merged.iloc[0:0].copy()

    threshold = float(positive_regret.quantile(0.75))
    hard_instances = merged[merged["regret_vs_virtual_best"] >= threshold].copy()
    return hard_instances.sort_values(
        by=["regret_vs_virtual_best", "instance_name"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _most_confused_solver_pairs(merged: pd.DataFrame) -> pd.DataFrame:

    # Count the most frequent selected-vs-true solver confusions.
    confusions = merged[
        merged["selected_solver"].notna()
        & merged["true_best_solver"].notna()
        & (merged["selected_solver"] != merged["true_best_solver"])
    ].copy()

    if confusions.empty:
        return pd.DataFrame(columns=["true_best_solver", "selected_solver", "count", "pair_label"])

    summary = (
        confusions.groupby(["true_best_solver", "selected_solver"], as_index=False)
        .size()
        .rename(columns={"size": "count"})
        .sort_values(
            by=["count", "true_best_solver", "selected_solver"],
            ascending=[False, True, True],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )
    summary["pair_label"] = summary["true_best_solver"] + " -> " + summary["selected_solver"]
    return summary


def _feature_pattern_summary(merged: pd.DataFrame, hard_instances: pd.DataFrame) -> pd.DataFrame:

    # Summarize standardized numeric feature differences for hard predictions.
    numeric_feature_columns = [
        column
        for column in merged.columns
        if column not in _non_feature_columns()
        and pd.api.types.is_numeric_dtype(merged[column])
    ]

    if not numeric_feature_columns or hard_instances.empty:
        return pd.DataFrame(
            columns=[
                "feature",
                "feature_group",
                "hard_mean_zscore",
                "other_mean_zscore",
                "abs_standardized_gap",
            ]
        )

    hard_case_ids = set(hard_instances["analysis_case_id"].astype(str))
    hard_mask = merged["analysis_case_id"].astype(str).isin(hard_case_ids)
    other_instances = merged[~hard_mask]
    if other_instances.empty:
        return pd.DataFrame(
            columns=[
                "feature",
                "feature_group",
                "hard_mean_zscore",
                "other_mean_zscore",
                "abs_standardized_gap",
            ]
        )

    rows: list[dict[str, float | str]] = []
    for column in numeric_feature_columns:
        numeric_values = pd.to_numeric(merged[column], errors="coerce")
        standard_deviation = float(numeric_values.std(ddof=0))
        if pd.isna(standard_deviation) or standard_deviation == 0.0:
            continue
        standardized = (numeric_values - float(numeric_values.mean())) / standard_deviation
        hard_mean = float(pd.to_numeric(standardized.loc[hard_mask], errors="coerce").mean())
        other_mean = float(pd.to_numeric(standardized.loc[~hard_mask], errors="coerce").mean())
        rows.append(
            {
                "feature": column,
                "feature_group": feature_group_for_column(column),
                "hard_mean_zscore": hard_mean,
                "other_mean_zscore": other_mean,
                "abs_standardized_gap": abs(hard_mean - other_mean),
            }
        )

    summary = pd.DataFrame(rows)
    if summary.empty:
        return pd.DataFrame(
            columns=[
                "feature",
                "feature_group",
                "hard_mean_zscore",
                "other_mean_zscore",
                "abs_standardized_gap",
            ]
        )
    return summary.sort_values(
        by=["abs_standardized_gap", "feature_group", "feature"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _error_cluster_summary(merged: pd.DataFrame, feature_summary: pd.DataFrame) -> pd.DataFrame:

    # Summarize whether errors cluster by difficulty or feature group.
    difficulty_summary = _difficulty_cluster_summary(merged)
    feature_group_summary = _feature_group_cluster_summary(feature_summary)
    summaries = [frame for frame in [difficulty_summary, feature_group_summary] if not frame.empty]
    if not summaries:
        return pd.DataFrame(
            columns=[
                "cluster_type",
                "cluster_scope",
                "cluster_label",
                "num_cases",
                "num_errors",
                "error_rate",
                "mean_regret",
                "num_features",
                "mean_abs_standardized_gap",
                "top_feature",
            ]
        )
    return pd.concat(summaries, ignore_index=True)


def _difficulty_cluster_summary(merged: pd.DataFrame) -> pd.DataFrame:

    # Summarize error concentration by difficulty-like categorical columns.
    candidate_columns = [
        column
        for column in merged.columns
        if column not in _non_feature_columns()
        and (
            "difficulty" in column.casefold()
            or column in {"profile_name"}
        )
    ]
    if not candidate_columns:
        return pd.DataFrame()

    error_mask = _error_mask(merged)
    rows: list[dict[str, object]] = []
    for column in candidate_columns:
        available = merged[column].dropna()
        if available.empty:
            continue
        for cluster_label, group in merged.groupby(column, dropna=True, sort=True):
            if pd.isna(cluster_label):
                continue
            rows.append(
                {
                    "cluster_type": "difficulty",
                    "cluster_scope": column,
                    "cluster_label": str(cluster_label),
                    "num_cases": int(len(group.index)),
                    "num_errors": int(error_mask.loc[group.index].sum()),
                    "error_rate": float(error_mask.loc[group.index].mean()),
                    "mean_regret": float(pd.to_numeric(group["regret_vs_virtual_best"], errors="coerce").mean()),
                    "num_features": pd.NA,
                    "mean_abs_standardized_gap": pd.NA,
                    "top_feature": pd.NA,
                }
            )

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(
        by=["error_rate", "mean_regret", "cluster_scope", "cluster_label"],
        ascending=[False, False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _feature_group_cluster_summary(feature_summary: pd.DataFrame) -> pd.DataFrame:

    # Aggregate feature-pattern gaps to the feature-group level.
    if feature_summary.empty:
        return pd.DataFrame()

    rows: list[dict[str, object]] = []
    for feature_group, group in feature_summary.groupby("feature_group", sort=True):
        best_row = group.sort_values(
            by=["abs_standardized_gap", "feature"],
            ascending=[False, True],
            kind="mergesort",
        ).iloc[0]
        rows.append(
            {
                "cluster_type": "feature_group",
                "cluster_scope": "feature_group",
                "cluster_label": str(feature_group),
                "num_cases": pd.NA,
                "num_errors": pd.NA,
                "error_rate": pd.NA,
                "mean_regret": pd.NA,
                "num_features": int(len(group.index)),
                "mean_abs_standardized_gap": float(group["abs_standardized_gap"].mean()),
                "top_feature": str(best_row["feature"]),
            }
        )

    return pd.DataFrame(rows).sort_values(
        by=["mean_abs_standardized_gap", "cluster_label"],
        ascending=[False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _plot_hard_instances(hard_instances: pd.DataFrame, output_path: Path) -> None:

    # Plot selector regret for the hardest instances.
    figure, axis = plt.subplots(figsize=(10, 5))
    if hard_instances.empty:
        axis.text(0.5, 0.5, "No hard instances identified", ha="center", va="center")
        axis.set_axis_off()
    else:
        top_rows = hard_instances.head(10)
        axis.barh(
            top_rows["instance_name"],
            top_rows["regret_vs_virtual_best"],
            color="#8b1e3f",
        )
        axis.invert_yaxis()
        axis.set_xlabel("Regret vs virtual best")
        axis.set_ylabel("Instance")
        axis.set_title("Hardest selector underperformance cases")
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def _plot_confusion_pairs(confusion_pairs: pd.DataFrame, output_path: Path) -> None:

    # Plot the most frequent solver confusions.
    figure, axis = plt.subplots(figsize=(10, 5))
    if confusion_pairs.empty:
        axis.text(0.5, 0.5, "No solver confusions observed", ha="center", va="center")
        axis.set_axis_off()
    else:
        top_pairs = confusion_pairs.head(10)
        axis.barh(top_pairs["pair_label"], top_pairs["count"], color="#1f5b92")
        axis.invert_yaxis()
        axis.set_xlabel("Count")
        axis.set_ylabel("True best -> selected")
        axis.set_title("Most frequent confused solver pairs")
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def _plot_feature_patterns(feature_summary: pd.DataFrame, output_path: Path) -> None:

    # Plot standardized numeric feature differences for hard predictions.
    figure, axis = plt.subplots(figsize=(10, 5))
    if feature_summary.empty:
        axis.text(0.5, 0.5, "Not enough data for feature-pattern analysis", ha="center", va="center")
        axis.set_axis_off()
    else:
        top_features = feature_summary.head(5)
        x_positions = range(len(top_features.index))
        axis.bar(
            [position - 0.2 for position in x_positions],
            top_features["hard_mean_zscore"],
            width=0.4,
            label="Hard instances",
            color="#c77d1a",
        )
        axis.bar(
            [position + 0.2 for position in x_positions],
            top_features["other_mean_zscore"],
            width=0.4,
            label="Other test instances",
            color="#2a9d8f",
        )
        axis.set_xticks(list(x_positions))
        axis.set_xticklabels(
            top_features["feature"] + " (" + top_features["feature_group"] + ")",
            rotation=25,
            ha="right",
        )
        axis.set_ylabel("Mean standardized feature value")
        axis.set_title("Feature signals in poor selector choices")
        axis.legend()
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def _build_error_analysis_markdown(
    *,
    hard_instances: pd.DataFrame,
    confusion_pairs: pd.DataFrame,
    cluster_summary: pd.DataFrame,
) -> str:

    # Render a concise error-analysis summary for thesis writing.
    lines = [
        "# Selector Error Analysis Summary",
        "",
        f"- Hard regret cases identified: `{len(hard_instances.index)}`",
        f"- Confused solver pairs observed: `{len(confusion_pairs.index)}`",
        "",
    ]

    lines.extend(
        [
            "## Worst Regret Cases",
            "",
        ]
    )
    if hard_instances.empty:
        lines.append("- No positive-regret hard cases were identified.")
    else:
        for row in hard_instances.head(5).to_dict(orient="records"):
            lines.append(
                "- "
                f"`{row['instance_name']}` selected `{row['selected_solver']}` instead of "
                f"`{row['true_best_solver']}` with regret `{_format_metric(row['regret_vs_virtual_best'])}`."
            )

    lines.extend(
        [
            "",
            "## Frequent Confusions",
            "",
        ]
    )
    if confusion_pairs.empty:
        lines.append("- No repeated solver confusions were observed.")
    else:
        for row in confusion_pairs.head(5).to_dict(orient="records"):
            lines.append(
                "- "
                f"`{row['pair_label']}` occurred `{int(row['count'])}` times."
            )

    lines.extend(
        [
            "",
            "## Error Clustering",
            "",
        ]
    )
    difficulty_rows = cluster_summary[cluster_summary["cluster_type"] == "difficulty"].head(5)
    if difficulty_rows.empty:
        lines.append("- No explicit difficulty column was available in the selection dataset.")
    else:
        for row in difficulty_rows.to_dict(orient="records"):
            lines.append(
                "- "
                f"Difficulty `{row['cluster_label']}` in `{row['cluster_scope']}` had error rate "
                f"`{_format_metric(row['error_rate'])}` and mean regret `{_format_metric(row['mean_regret'])}`."
            )

    feature_group_rows = cluster_summary[cluster_summary["cluster_type"] == "feature_group"].head(5)
    if feature_group_rows.empty:
        lines.append("- No feature-group clustering signal could be estimated.")
    else:
        for row in feature_group_rows.to_dict(orient="records"):
            lines.append(
                "- "
                f"Feature group `{row['cluster_label']}` showed mean standardized gap "
                f"`{_format_metric(row['mean_abs_standardized_gap'])}`; strongest feature was `{row['top_feature']}`."
            )

    return "\n".join(lines) + "\n"


def _non_feature_columns() -> set[str]:

    # Return columns that should not be treated as structural features.
    return {
        "split_id",
        "split_strategy",
        "repeat_index",
        "fold_index",
        "stratified_split",
        "analysis_case_id",
        "instance_name",
        "selected_solver",
        "true_best_solver",
        "prediction_correct",
        "selected_solver_objective",
        "best_possible_objective",
        "single_best_solver",
        "single_best_solver_objective",
        "selected_objective_for_scoring",
        "single_best_objective_for_scoring",
        "regret_vs_virtual_best",
        "delta_vs_single_best",
        "improvement_vs_single_best",
        "best_solver",
    }


def _error_mask(merged: pd.DataFrame) -> pd.Series:

    # Return a stable boolean mask for selector mistakes.
    prediction_correct = merged.get("prediction_correct")
    if prediction_correct is not None:
        normalized = (
            prediction_correct.astype("string")
            .str.strip()
            .str.casefold()
            .map({"true": True, "1": True, "yes": True, "false": False, "0": False, "no": False})
            .fillna(False)
            .astype(bool)
        )
        return ~normalized
    return merged["selected_solver"].astype("string") != merged["true_best_solver"].astype("string")


def _format_metric(value: object) -> str:

    # Format one metric value for Markdown summaries.
    numeric = pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]
    if pd.isna(numeric):
        return "NA"
    return f"{float(numeric):.4f}"


def _analysis_case_id(merged: pd.DataFrame) -> pd.Series:

    # Return one stable identifier for an evaluated split-instance case.
    if "split_id" in merged.columns:
        return (
            merged["split_id"].astype("string").fillna("split")
            + "::"
            + merged["instance_name"].astype("string").fillna("instance")
        )
    return merged["instance_name"].astype("string").fillna("instance")


if __name__ == "__main__":
    raise SystemExit(main())
