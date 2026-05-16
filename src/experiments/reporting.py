# Thesis-friendly reporting utilities for benchmark and selector artifacts.

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd


matplotlib.use("Agg")
import matplotlib.pyplot as plt

from src.experiments.metrics import (
    average_objective_by_solver,
    average_runtime_by_solver,
    best_solver_per_instance,
)
from src.selection.feature_groups import feature_group_for_column
from src.utils import default_run_summary_path, ensure_directory, write_run_summary


DEFAULT_BENCHMARKS_PATH = Path("data/results/benchmark_results.csv")
DEFAULT_SUMMARY_CSV_PATH = Path("data/results/selector_evaluation_summary.csv")
DEFAULT_IMPORTANCE_PATH = Path("data/results/random_forest_feature_importance.csv")
DEFAULT_OUTPUT_DIR = Path("data/results/thesis_artifacts")


@dataclass(slots=True)
class ThesisArtifactResult:

    # Summary of exported thesis-friendly experiment artifacts.
    output_dir: Path
    solver_comparison_csv: Path
    selector_summary_csv: Path
    feature_importance_csv: Path
    runtime_plot_png: Path
    objective_plot_png: Path
    summary_markdown: Path


def generate_thesis_artifacts(
    benchmark_csv: str | Path = DEFAULT_BENCHMARKS_PATH,
    evaluation_summary_csv: str | Path = DEFAULT_SUMMARY_CSV_PATH,
    feature_importance_csv: str | Path = DEFAULT_IMPORTANCE_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    run_summary_path: str | Path | None = None,
) -> ThesisArtifactResult:

    # Generate thesis-facing tables, figures, and Markdown summaries.
    benchmark_path = Path(benchmark_csv)
    evaluation_summary_path = Path(evaluation_summary_csv)
    importance_path = Path(feature_importance_csv)
    output_path = ensure_directory(output_dir)

    benchmark_frame = pd.read_csv(benchmark_path)
    evaluation_summary = pd.read_csv(evaluation_summary_path)
    feature_importance = pd.read_csv(importance_path)

    solver_comparison = _build_solver_comparison_table(benchmark_frame)
    selector_summary = _build_selector_summary_table(evaluation_summary)
    importance_table = _build_feature_importance_table(feature_importance)

    solver_comparison_csv = output_path / "solver_comparison_table.csv"
    selector_summary_csv = output_path / "selector_vs_baselines_summary.csv"
    importance_table_csv = output_path / "feature_importance_table.csv"
    runtime_plot_png = output_path / "solver_runtime_comparison.png"
    objective_plot_png = output_path / "selector_objective_comparison.png"
    summary_markdown = output_path / "thesis_artifact_summary.md"

    solver_comparison.to_csv(solver_comparison_csv, index=False)
    selector_summary.to_csv(selector_summary_csv, index=False)
    importance_table.to_csv(importance_table_csv, index=False)

    _plot_solver_runtime_comparison(solver_comparison, runtime_plot_png)
    _plot_selector_objective_comparison(selector_summary, objective_plot_png)
    summary_markdown.write_text(
        _build_summary_markdown(
            benchmark_path=benchmark_path,
            evaluation_summary_path=evaluation_summary_path,
            importance_path=importance_path,
            solver_comparison=solver_comparison,
            selector_summary=selector_summary,
            importance_table=importance_table,
        ),
        encoding="utf-8",
    )

    result = ThesisArtifactResult(
        output_dir=output_path,
        solver_comparison_csv=solver_comparison_csv,
        selector_summary_csv=selector_summary_csv,
        feature_importance_csv=importance_table_csv,
        runtime_plot_png=runtime_plot_png,
        objective_plot_png=objective_plot_png,
        summary_markdown=summary_markdown,
    )

    summary_path = (
        Path(run_summary_path)
        if run_summary_path is not None
        else default_run_summary_path(output_path)
    )
    write_run_summary(
        summary_path,
        stage_name="thesis_artifact_export",
        config_path=None,
        config=None,
        settings={},
        inputs={
            "benchmark_results_csv": benchmark_path,
            "selector_evaluation_summary_csv": evaluation_summary_path,
            "feature_importance_csv": importance_path,
        },
        outputs={
            "output_dir": output_path,
            "solver_comparison_csv": result.solver_comparison_csv,
            "selector_summary_csv": result.selector_summary_csv,
            "feature_importance_table_csv": result.feature_importance_csv,
            "runtime_plot_png": result.runtime_plot_png,
            "objective_plot_png": result.objective_plot_png,
            "summary_markdown": result.summary_markdown,
            "run_summary": summary_path,
        },
        results={
            "num_solvers": int(len(solver_comparison.index)),
            "num_selector_summary_rows": int(len(selector_summary.index)),
            "num_feature_importance_rows": int(len(importance_table.index)),
        },
    )
    return result


def build_argument_parser() -> argparse.ArgumentParser:

    # Create the command-line parser for thesis artifact export.
    parser = argparse.ArgumentParser(
        description="Generate thesis-friendly tables and plots from experiment artifacts.",
    )
    parser.add_argument(
        "--benchmark-csv",
        default=str(DEFAULT_BENCHMARKS_PATH),
        help="Path to the benchmark results CSV.",
    )
    parser.add_argument(
        "--evaluation-summary-csv",
        default=str(DEFAULT_SUMMARY_CSV_PATH),
        help="Path to the selector evaluation summary CSV.",
    )
    parser.add_argument(
        "--feature-importance-csv",
        default=str(DEFAULT_IMPORTANCE_PATH),
        help="Path to the feature importance CSV.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where thesis artifact exports will be written.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:

    # Run thesis artifact export from the command line.
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        result = generate_thesis_artifacts(
            benchmark_csv=args.benchmark_csv,
            evaluation_summary_csv=args.evaluation_summary_csv,
            feature_importance_csv=args.feature_importance_csv,
            output_dir=args.output_dir,
        )
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError) as exc:
        print(f"Failed to export thesis artifacts: {exc}")
        return 1

    print(f"Thesis artifacts saved to {result.output_dir}")
    return 0


def _build_solver_comparison_table(benchmark_frame: pd.DataFrame) -> pd.DataFrame:

    # Build one thesis-friendly solver comparison table from benchmark results.
    objective_summary = average_objective_by_solver(benchmark_frame)
    runtime_summary = average_runtime_by_solver(benchmark_frame)
    virtual_best_rows = best_solver_per_instance(benchmark_frame)

    wins = (
        virtual_best_rows[virtual_best_rows["solver_name"].notna()]
        .groupby("solver_name", as_index=False)
        .size()
        .rename(columns={"size": "win_count"})
    )

    summary = runtime_summary.merge(objective_summary, on="solver_name", how="outer")
    summary = summary.merge(wins, on="solver_name", how="left")
    summary["win_count"] = pd.to_numeric(summary["win_count"], errors="coerce").fillna(0).astype(int)

    num_instances = int(benchmark_frame["instance_name"].astype("string").nunique())
    solved = pd.to_numeric(summary["num_instances_solved"], errors="coerce").fillna(0)
    summary["coverage_ratio"] = solved / max(1, num_instances)
    summary = summary.fillna(
        {
            "num_runs": 0,
            "num_feasible_runs": 0,
            "num_instances_solved": 0,
        }
    )

    ordered = summary.loc[
        :,
        [
            "solver_name",
            "num_runs",
            "num_feasible_runs",
            "num_instances_solved",
            "coverage_ratio",
            "win_count",
            "average_objective",
            "average_runtime",
        ],
    ].copy()
    ordered = ordered.sort_values(
        by=["num_instances_solved", "average_objective", "average_runtime", "solver_name"],
        ascending=[False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    return ordered


def _build_selector_summary_table(evaluation_summary: pd.DataFrame) -> pd.DataFrame:

    # Build a concise selector vs SBS vs VBS comparison table.
    mean_row = _select_summary_row(evaluation_summary, "aggregate_mean")
    std_row = _select_summary_row(evaluation_summary, "aggregate_std")
    split_count = int(
        evaluation_summary["summary_row_type"].astype("string").eq("split").sum()
    ) if "summary_row_type" in evaluation_summary.columns else len(evaluation_summary.index)
    split_count = max(1, split_count)

    selected_objective = _to_float(mean_row.get("average_selected_objective"))
    virtual_best_objective = _to_float(mean_row.get("average_virtual_best_objective"))
    single_best_objective = _to_float(mean_row.get("average_single_best_objective"))

    rows = [
        {
            "method": "selector",
            "reference_solver_name": None,
            "split_strategy": mean_row.get("split_strategy"),
            "num_validation_splits": split_count,
            "average_objective": selected_objective,
            "objective_gap_vs_virtual_best": _to_float(mean_row.get("regret_vs_virtual_best")),
            "objective_gap_vs_single_best": _to_float(mean_row.get("delta_vs_single_best")),
            "classification_accuracy": _to_float(mean_row.get("classification_accuracy")),
            "classification_accuracy_std": _to_float(std_row.get("classification_accuracy")),
            "balanced_accuracy": _to_float(mean_row.get("balanced_accuracy")),
            "balanced_accuracy_std": _to_float(std_row.get("balanced_accuracy")),
        },
        {
            "method": "single_best_solver",
            "reference_solver_name": mean_row.get("single_best_solver_name"),
            "split_strategy": mean_row.get("split_strategy"),
            "num_validation_splits": split_count,
            "average_objective": single_best_objective,
            "objective_gap_vs_virtual_best": single_best_objective - virtual_best_objective,
            "objective_gap_vs_single_best": 0.0,
            "classification_accuracy": float("nan"),
            "classification_accuracy_std": float("nan"),
            "balanced_accuracy": float("nan"),
            "balanced_accuracy_std": float("nan"),
        },
        {
            "method": "virtual_best_solver",
            "reference_solver_name": "oracle",
            "split_strategy": mean_row.get("split_strategy"),
            "num_validation_splits": split_count,
            "average_objective": virtual_best_objective,
            "objective_gap_vs_virtual_best": 0.0,
            "objective_gap_vs_single_best": virtual_best_objective - single_best_objective,
            "classification_accuracy": float("nan"),
            "classification_accuracy_std": float("nan"),
            "balanced_accuracy": float("nan"),
            "balanced_accuracy_std": float("nan"),
        },
    ]
    return pd.DataFrame(rows)


def _build_feature_importance_table(feature_importance: pd.DataFrame) -> pd.DataFrame:

    # Build a cleaned feature importance export for thesis reuse.
    required_columns = {"feature", "importance"}
    missing_columns = sorted(required_columns.difference(feature_importance.columns))
    if missing_columns:
        joined = ", ".join(missing_columns)
        raise ValueError(f"Feature importance input is missing required columns: {joined}")

    table = feature_importance.copy()
    table["source_feature"] = table.get("source_feature", table["feature"]).astype(str)
    table["feature_group"] = table.get("feature_group", table["source_feature"].map(feature_group_for_column))
    table["importance"] = pd.to_numeric(table["importance"], errors="coerce")
    table = table.dropna(subset=["importance"]).copy()
    table = table.sort_values(
        by=["importance", "source_feature", "feature"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    table.insert(0, "importance_rank", range(1, len(table.index) + 1))

    total_importance = float(table["importance"].sum())
    if total_importance > 0.0:
        table["importance_share"] = table["importance"] / total_importance
        table["cumulative_importance_share"] = table["importance_share"].cumsum()
    else:
        table["importance_share"] = 0.0
        table["cumulative_importance_share"] = 0.0

    return table.loc[
        :,
        [
            "importance_rank",
            "feature",
            "source_feature",
            "feature_group",
            "importance",
            "importance_share",
            "cumulative_importance_share",
        ],
    ]


def _plot_solver_runtime_comparison(summary: pd.DataFrame, output_path: Path) -> None:

    # Plot average runtime per solver with a clean thesis-friendly style.
    figure, axis = plt.subplots(figsize=(8.5, 4.5))
    available = summary.dropna(subset=["average_runtime"]).copy()
    if available.empty:
        axis.text(0.5, 0.5, "No runtime data available", ha="center", va="center")
        axis.set_axis_off()
    else:
        available = available.sort_values(
            by=["average_runtime", "solver_name"],
            ascending=[True, True],
            kind="mergesort",
        )
        axis.barh(
            available["solver_name"],
            available["average_runtime"],
            color="#1f5b92",
        )
        axis.invert_yaxis()
        axis.set_xlabel("Average runtime (s)")
        axis.set_ylabel("Solver")
        axis.set_title("Average solver runtime")
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def _plot_selector_objective_comparison(summary: pd.DataFrame, output_path: Path) -> None:

    # Plot selector, SBS, and VBS objective comparison.
    figure, axis = plt.subplots(figsize=(8.5, 4.5))
    available = summary.dropna(subset=["average_objective"]).copy()
    if available.empty:
        axis.text(0.5, 0.5, "No objective comparison available", ha="center", va="center")
        axis.set_axis_off()
    else:
        colors = {
            "selector": "#2a9d8f",
            "single_best_solver": "#c77d1a",
            "virtual_best_solver": "#1f5b92",
        }
        axis.bar(
            available["method"],
            available["average_objective"],
            color=[colors.get(method, "#4c566a") for method in available["method"]],
        )
        axis.set_ylabel("Average objective")
        axis.set_xlabel("Method")
        axis.set_title("Selector vs SBS vs VBS objective comparison")
        for index, row in available.reset_index(drop=True).iterrows():
            axis.text(
                index,
                float(row["average_objective"]),
                f"{float(row['average_objective']):.3f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
    figure.tight_layout()
    figure.savefig(output_path, dpi=200, bbox_inches="tight")
    plt.close(figure)


def _build_summary_markdown(
    *,
    benchmark_path: Path,
    evaluation_summary_path: Path,
    importance_path: Path,
    solver_comparison: pd.DataFrame,
    selector_summary: pd.DataFrame,
    importance_table: pd.DataFrame,
) -> str:

    # Render a concise Markdown summary for thesis writing.
    lines = [
        "# Thesis Artifact Summary",
        "",
        "## Inputs",
        "",
        f"- Benchmark results: `{benchmark_path.as_posix()}`",
        f"- Selector evaluation summary: `{evaluation_summary_path.as_posix()}`",
        f"- Feature importance: `{importance_path.as_posix()}`",
        "",
        "## Solver Comparison",
        "",
        _markdown_table(
            solver_comparison.head(10),
            columns=[
                "solver_name",
                "num_instances_solved",
                "win_count",
                "average_objective",
                "average_runtime",
            ],
        ),
        "",
        "## Selector vs SBS vs VBS",
        "",
        _markdown_table(
            selector_summary,
            columns=[
                "method",
                "reference_solver_name",
                "average_objective",
                "objective_gap_vs_virtual_best",
                "objective_gap_vs_single_best",
                "classification_accuracy",
                "balanced_accuracy",
            ],
        ),
        "",
        "## Top Feature Importance",
        "",
        _markdown_table(
            importance_table.head(10),
            columns=[
                "importance_rank",
                "source_feature",
                "feature_group",
                "importance",
                "importance_share",
            ],
        ),
        "",
        "## Notes",
        "",
        "- Solver comparison uses the benchmark CSV produced by the main experiment pipeline.",
        "- Selector baseline comparison uses the aggregate evaluation summary rows.",
        "- These exports are thesis-friendly presentation artifacts, not a replacement for the raw experiment outputs.",
        "",
    ]
    return "\n".join(lines)


def _select_summary_row(summary: pd.DataFrame, row_type: str) -> pd.Series:

    # Return one evaluation summary row by type with a stable fallback.
    if "summary_row_type" not in summary.columns:
        raise ValueError("Evaluation summary CSV must contain a 'summary_row_type' column.")
    matches = summary[summary["summary_row_type"] == row_type]
    if not matches.empty:
        return matches.iloc[0]
    if not summary.empty:
        return summary.iloc[0]
    raise ValueError("Evaluation summary CSV is empty.")


def _markdown_table(frame: pd.DataFrame, *, columns: list[str]) -> str:

    # Render a small dataframe as a simple Markdown table.
    available_columns = [column for column in columns if column in frame.columns]
    if frame.empty or not available_columns:
        return "_No rows available._"

    lines = [
        "| " + " | ".join(_labelize(column) for column in available_columns) + " |",
        "| " + " | ".join("---" for _ in available_columns) + " |",
    ]
    for row in frame.loc[:, available_columns].to_dict(orient="records"):
        lines.append(
            "| " + " | ".join(_format_markdown_value(row.get(column)) for column in available_columns) + " |"
        )
    return "\n".join(lines)


def _format_markdown_value(value: object) -> str:

    # Format one scalar value for Markdown output.
    if value is None:
        return "NA"
    numeric = _to_float(value)
    if pd.notna(numeric):
        if float(numeric).is_integer():
            return str(int(numeric))
        return f"{float(numeric):.4f}"
    text = str(value).strip()
    return text or "NA"


def _labelize(value: str) -> str:

    # Convert one identifier-like string into a readable label.
    return value.replace("_", " ").strip().title()


def _to_float(value: object) -> float:

    # Convert a scalar value to float with NaN fallback.
    if value is None:
        return float("nan")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return float("nan")
    return numeric


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "ThesisArtifactResult",
    "generate_thesis_artifacts",
]


if __name__ == "__main__":
    raise SystemExit(main())
