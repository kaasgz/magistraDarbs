"""Generate thesis-facing benchmark and selector summary reports."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from src.selection.feature_groups import feature_group_for_column
from src.utils import default_run_summary_path, ensure_directory, write_run_summary


DEFAULT_BENCHMARK_CSV = Path("data/results/full_selection/combined_benchmark_results.csv")
DEFAULT_EVALUATION_SUMMARY_CSV = Path("data/results/full_selection/selector_evaluation_summary.csv")
DEFAULT_FEATURE_IMPORTANCE_CSV = Path("data/results/full_selection/feature_importance.csv")
DEFAULT_SYNTHETIC_BENCHMARK_CSV = Path("data/results/synthetic_study/benchmark_results.csv")
DEFAULT_REAL_BENCHMARK_CSV = Path("data/results/real_pipeline_current/benchmark_results.csv")
DEFAULT_SYNTHETIC_EVALUATION_SUMMARY_CSV = Path("data/results/synthetic_study/aggregate_selector_summary.csv")
DEFAULT_REAL_EVALUATION_SUMMARY_CSV = Path("data/results/real_pipeline_current/selector_evaluation_summary.csv")
DEFAULT_COMPATIBILITY_MATRIX_CSV = Path(
    "data/processed/real_pipeline_current/solver_compatibility_matrix.csv"
)
DEFAULT_OUTPUT_DIR = Path("data/results/reports")
DEFAULT_TOP_FEATURE_COUNT = 15

ResultScope = Literal["auto", "synthetic", "real", "mixed", "unknown"]
_REQUIRED_BENCHMARK_COLUMNS = {
    "instance_name",
    "solver_name",
    "objective_value",
    "runtime_seconds",
    "feasible",
    "status",
}


@dataclass(frozen=True, slots=True)
class ThesisBenchmarkReportResult:
    """Paths written by the thesis-facing benchmark report generator."""

    output_dir: Path
    solver_comparison_csv: Path
    solver_comparison_markdown: Path
    solver_support_summary_csv: Path
    solver_support_summary_markdown: Path
    win_counts_csv: Path
    win_counts_markdown: Path
    average_objective_csv: Path
    average_objective_markdown: Path
    average_runtime_csv: Path
    average_runtime_markdown: Path
    selector_vs_baselines_csv: Path
    selector_vs_baselines_markdown: Path
    feature_importance_summary_csv: Path
    feature_importance_summary_markdown: Path
    summary_markdown: Path
    run_summary_json: Path


def generate_thesis_benchmark_report(
    benchmark_csv: str | Path | None = None,
    evaluation_summary_csv: str | Path | None = None,
    feature_importance_csv: str | Path | None = None,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    result_scope: ResultScope = "auto",
    top_feature_count: int = DEFAULT_TOP_FEATURE_COUNT,
    run_summary_path: str | Path | None = None,
    synthetic_benchmark_csv: str | Path = DEFAULT_SYNTHETIC_BENCHMARK_CSV,
    real_benchmark_csv: str | Path = DEFAULT_REAL_BENCHMARK_CSV,
    synthetic_evaluation_summary_csv: str | Path = DEFAULT_SYNTHETIC_EVALUATION_SUMMARY_CSV,
    real_evaluation_summary_csv: str | Path = DEFAULT_REAL_EVALUATION_SUMMARY_CSV,
    compatibility_matrix_csv: str | Path | None = DEFAULT_COMPATIBILITY_MATRIX_CSV,
) -> ThesisBenchmarkReportResult:
    """Generate CSV and Markdown summaries suitable for thesis writing."""

    output_path = ensure_directory(output_dir)

    benchmark_frame, benchmark_inputs = _load_benchmark_inputs(
        benchmark_csv=benchmark_csv,
        synthetic_benchmark_csv=synthetic_benchmark_csv,
        real_benchmark_csv=real_benchmark_csv,
    )

    prepared_benchmarks = _prepare_benchmark_frame(
        benchmark_frame,
        result_scope=result_scope,
    )
    report_scope = _summarize_report_scope(prepared_benchmarks)
    top_feature_count = max(1, int(top_feature_count))
    evaluation_summary, evaluation_inputs = _load_evaluation_inputs(
        evaluation_summary_csv=evaluation_summary_csv,
        synthetic_evaluation_summary_csv=synthetic_evaluation_summary_csv,
        real_evaluation_summary_csv=real_evaluation_summary_csv,
        report_scope=report_scope,
    )
    feature_importance, feature_importance_input = _load_feature_importance(feature_importance_csv)
    compatibility_summary = _load_compatibility_summary(compatibility_matrix_csv)

    solver_comparison = _build_solver_comparison_table(
        prepared_benchmarks,
        compatibility_summary=compatibility_summary,
    )
    solver_support_summary = _build_solver_support_summary(
        prepared_benchmarks,
        compatibility_summary=compatibility_summary,
    )
    win_counts = _build_win_counts_table(solver_comparison)
    average_objective = _build_average_objective_table(solver_comparison)
    average_runtime = _build_average_runtime_table(solver_comparison)
    selector_vs_baselines = _build_selector_vs_baselines_table(
        evaluation_summary,
        result_scope=report_scope,
    )
    feature_importance_summary = _build_feature_importance_summary(
        feature_importance,
        result_scope=report_scope,
        top_feature_count=top_feature_count,
    )

    paths = _report_output_paths(output_path)
    solver_comparison.to_csv(paths["solver_comparison_csv"], index=False)
    solver_support_summary.to_csv(paths["solver_support_summary_csv"], index=False)
    win_counts.to_csv(paths["win_counts_csv"], index=False)
    average_objective.to_csv(paths["average_objective_csv"], index=False)
    average_runtime.to_csv(paths["average_runtime_csv"], index=False)
    selector_vs_baselines.to_csv(paths["selector_vs_baselines_csv"], index=False)
    feature_importance_summary.to_csv(paths["feature_importance_summary_csv"], index=False)

    _write_table_markdown(
        paths["solver_comparison_markdown"],
        title="Solver Comparison Table",
        description="Aggregated solver coverage, objective, runtime, and win-count metrics.",
        table=solver_comparison,
        columns=[
            "result_scope",
            "solver_registry_name",
            "solver_name",
            "num_instances_total",
            "feasible_coverage_ratio",
            "valid_feasible_coverage_ratio",
            "win_count",
            "average_objective_valid_feasible",
            "average_runtime_seconds",
        ],
    )
    _write_table_markdown(
        paths["solver_support_summary_markdown"],
        title="Solver Support Summary",
        description=(
            "Support and scoring-status rows. Feasible rows describe coverage; "
            "valid feasible rows describe objective-comparable quality."
        ),
        table=solver_support_summary,
        columns=[
            "result_scope",
            "solver_registry_name",
            "solver_support_status",
            "scoring_status",
            "num_rows",
            "num_feasible_runs",
            "num_valid_feasible_runs",
            "average_runtime_seconds",
        ],
    )
    _write_table_markdown(
        paths["win_counts_markdown"],
        title="Win Counts Per Solver",
        description="Number of instances where each solver achieved the best feasible objective.",
        table=win_counts,
        columns=["result_scope", "solver_registry_name", "solver_name", "win_count"],
    )
    _write_table_markdown(
        paths["average_objective_markdown"],
        title="Average Objective Per Solver",
        description="Average objective over feasible solver runs. Lower is better.",
        table=average_objective,
        columns=[
            "result_scope",
            "solver_registry_name",
            "solver_name",
            "average_objective_valid_feasible",
            "num_instances_solved",
        ],
    )
    _write_table_markdown(
        paths["average_runtime_markdown"],
        title="Average Runtime Per Solver",
        description="Average runtime over all recorded solver runs.",
        table=average_runtime,
        columns=[
            "result_scope",
            "solver_registry_name",
            "solver_name",
            "average_runtime_seconds",
            "num_runs",
        ],
    )
    _write_table_markdown(
        paths["selector_vs_baselines_markdown"],
        title="Selector Vs Single Best Vs Virtual Best",
        description="Selector performance compared with the single-best and virtual-best baselines.",
        table=selector_vs_baselines,
        columns=[
            "result_scope",
            "method",
            "reference_solver_name",
            "average_objective",
            "objective_gap_vs_virtual_best",
            "objective_gap_vs_single_best",
            "classification_accuracy",
            "balanced_accuracy",
        ],
    )
    _write_table_markdown(
        paths["feature_importance_summary_markdown"],
        title="Feature Importance Summary",
        description=f"Top {top_feature_count} selector features by random-forest importance.",
        table=feature_importance_summary,
        columns=[
            "result_scope",
            "importance_rank",
            "source_feature",
            "feature_group",
            "importance",
            "importance_share",
            "cumulative_importance_share",
        ],
    )

    paths["summary_markdown"].write_text(
        _build_summary_markdown(
            benchmark_inputs=benchmark_inputs,
            evaluation_inputs=evaluation_inputs,
            feature_importance_input=feature_importance_input,
            report_scope=report_scope,
            solver_comparison=solver_comparison,
            solver_support_summary=solver_support_summary,
            win_counts=win_counts,
            average_objective=average_objective,
            average_runtime=average_runtime,
            selector_vs_baselines=selector_vs_baselines,
            feature_importance_summary=feature_importance_summary,
        ),
        encoding="utf-8",
    )

    run_summary = (
        Path(run_summary_path)
        if run_summary_path is not None
        else default_run_summary_path(paths["summary_markdown"])
    )
    write_run_summary(
        run_summary,
        stage_name="thesis_benchmark_report",
        config_path=None,
        config=None,
        settings={
            "result_scope": result_scope,
            "resolved_report_scope": report_scope,
            "top_feature_count": top_feature_count,
        },
        inputs={
            **benchmark_inputs,
            **evaluation_inputs,
            "feature_importance_csv": feature_importance_input,
            "compatibility_matrix_csv": Path(compatibility_matrix_csv)
            if compatibility_matrix_csv is not None
            else None,
        },
        outputs={**paths, "run_summary": run_summary},
        results={
            "num_solver_rows": len(solver_comparison.index),
            "num_solver_support_rows": len(solver_support_summary.index),
            "num_selector_rows": len(selector_vs_baselines.index),
            "num_feature_importance_rows": len(feature_importance_summary.index),
            "result_scopes": sorted(prepared_benchmarks["result_scope"].unique().tolist()),
        },
    )

    return ThesisBenchmarkReportResult(
        output_dir=output_path,
        solver_comparison_csv=paths["solver_comparison_csv"],
        solver_comparison_markdown=paths["solver_comparison_markdown"],
        solver_support_summary_csv=paths["solver_support_summary_csv"],
        solver_support_summary_markdown=paths["solver_support_summary_markdown"],
        win_counts_csv=paths["win_counts_csv"],
        win_counts_markdown=paths["win_counts_markdown"],
        average_objective_csv=paths["average_objective_csv"],
        average_objective_markdown=paths["average_objective_markdown"],
        average_runtime_csv=paths["average_runtime_csv"],
        average_runtime_markdown=paths["average_runtime_markdown"],
        selector_vs_baselines_csv=paths["selector_vs_baselines_csv"],
        selector_vs_baselines_markdown=paths["selector_vs_baselines_markdown"],
        feature_importance_summary_csv=paths["feature_importance_summary_csv"],
        feature_importance_summary_markdown=paths["feature_importance_summary_markdown"],
        summary_markdown=paths["summary_markdown"],
        run_summary_json=run_summary,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for thesis benchmark report generation."""

    parser = argparse.ArgumentParser(
        description="Generate thesis-facing CSV and Markdown benchmark reports.",
    )
    parser.add_argument(
        "--benchmark-csv",
        default=None,
        help=(
            "Optional single benchmark results CSV. When omitted, the refreshed "
            "synthetic-study and real-current benchmark CSVs are combined."
        ),
    )
    parser.add_argument(
        "--evaluation-summary-csv",
        default=None,
        help=(
            "Optional single selector evaluation summary CSV. When omitted, the "
            "refreshed synthetic-study and real-current summaries are combined."
        ),
    )
    parser.add_argument(
        "--feature-importance-csv",
        default=None,
        help="Optional selector feature importance CSV for the top-feature table.",
    )
    parser.add_argument(
        "--synthetic-benchmark-csv",
        default=str(DEFAULT_SYNTHETIC_BENCHMARK_CSV),
        help="Synthetic-study aggregate benchmark CSV used when --benchmark-csv is omitted.",
    )
    parser.add_argument(
        "--real-benchmark-csv",
        default=str(DEFAULT_REAL_BENCHMARK_CSV),
        help="Current real-data benchmark CSV used when --benchmark-csv is omitted.",
    )
    parser.add_argument(
        "--synthetic-evaluation-summary-csv",
        default=str(DEFAULT_SYNTHETIC_EVALUATION_SUMMARY_CSV),
        help="Synthetic-study selector summary used when --evaluation-summary-csv is omitted.",
    )
    parser.add_argument(
        "--real-evaluation-summary-csv",
        default=str(DEFAULT_REAL_EVALUATION_SUMMARY_CSV),
        help="Current real-data selector summary used when --evaluation-summary-csv is omitted.",
    )
    parser.add_argument(
        "--compatibility-matrix-csv",
        default=str(DEFAULT_COMPATIBILITY_MATRIX_CSV),
        help="Optional real solver compatibility matrix for support context.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where report CSV and Markdown files are written.",
    )
    parser.add_argument(
        "--result-scope",
        choices=("auto", "synthetic", "real", "mixed", "unknown"),
        default="auto",
        help="Explicitly label the report as synthetic or real, or infer from benchmark metadata.",
    )
    parser.add_argument(
        "--top-feature-count",
        type=int,
        default=DEFAULT_TOP_FEATURE_COUNT,
        help="Number of feature-importance rows to include in the summary.",
    )
    parser.add_argument(
        "--run-summary",
        default=None,
        help="Optional JSON run summary path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the thesis benchmark report generator from the command line."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        result = generate_thesis_benchmark_report(
            benchmark_csv=args.benchmark_csv,
            evaluation_summary_csv=args.evaluation_summary_csv,
            feature_importance_csv=args.feature_importance_csv,
            output_dir=args.output_dir,
            result_scope=args.result_scope,
            top_feature_count=args.top_feature_count,
            run_summary_path=args.run_summary,
            synthetic_benchmark_csv=args.synthetic_benchmark_csv,
            real_benchmark_csv=args.real_benchmark_csv,
            synthetic_evaluation_summary_csv=args.synthetic_evaluation_summary_csv,
            real_evaluation_summary_csv=args.real_evaluation_summary_csv,
            compatibility_matrix_csv=args.compatibility_matrix_csv,
        )
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError) as exc:
        print(f"Failed to generate thesis benchmark report: {exc}")
        return 1

    print(f"Thesis benchmark reports saved to {result.output_dir}")
    return 0


def _report_output_paths(output_dir: Path) -> dict[str, Path]:
    """Return stable output file paths for report artifacts."""

    return {
        "solver_comparison_csv": output_dir / "solver_comparison.csv",
        "solver_comparison_markdown": output_dir / "solver_comparison.md",
        "solver_support_summary_csv": output_dir / "solver_support_summary.csv",
        "solver_support_summary_markdown": output_dir / "solver_support_summary.md",
        "win_counts_csv": output_dir / "solver_win_counts.csv",
        "win_counts_markdown": output_dir / "solver_win_counts.md",
        "average_objective_csv": output_dir / "average_objective_per_solver.csv",
        "average_objective_markdown": output_dir / "average_objective_per_solver.md",
        "average_runtime_csv": output_dir / "average_runtime_per_solver.csv",
        "average_runtime_markdown": output_dir / "average_runtime_per_solver.md",
        "selector_vs_baselines_csv": output_dir / "selector_vs_baselines.csv",
        "selector_vs_baselines_markdown": output_dir / "selector_vs_baselines.md",
        "feature_importance_summary_csv": output_dir / "feature_importance_summary.csv",
        "feature_importance_summary_markdown": output_dir / "feature_importance_summary.md",
        "summary_markdown": output_dir / "thesis_benchmark_report.md",
    }


def _load_benchmark_inputs(
    *,
    benchmark_csv: str | Path | None,
    synthetic_benchmark_csv: str | Path,
    real_benchmark_csv: str | Path,
) -> tuple[pd.DataFrame, dict[str, Path]]:
    """Load either one benchmark file or the refreshed synthetic/real pair."""

    if benchmark_csv is not None:
        path = Path(benchmark_csv)
        return pd.read_csv(path), {"benchmark_csv": path}

    synthetic_path = Path(synthetic_benchmark_csv)
    real_path = Path(real_benchmark_csv)
    synthetic = pd.read_csv(synthetic_path)
    real = pd.read_csv(real_path)
    synthetic["result_scope"] = "synthetic"
    real["result_scope"] = "real"
    if "is_synthetic" not in synthetic.columns:
        synthetic["is_synthetic"] = True
    if "is_synthetic" not in real.columns:
        real["is_synthetic"] = False
    return (
        pd.concat([synthetic, real], ignore_index=True, sort=False),
        {
            "synthetic_benchmark_csv": synthetic_path,
            "real_benchmark_csv": real_path,
        },
    )


def _load_evaluation_inputs(
    *,
    evaluation_summary_csv: str | Path | None,
    synthetic_evaluation_summary_csv: str | Path,
    real_evaluation_summary_csv: str | Path,
    report_scope: str,
) -> tuple[pd.DataFrame, dict[str, Path]]:
    """Load selector evaluation summaries with explicit result scopes."""

    if evaluation_summary_csv is not None:
        path = Path(evaluation_summary_csv)
        summary = pd.read_csv(path)
        if "result_scope" not in summary.columns:
            summary["result_scope"] = report_scope
        return summary, {"evaluation_summary_csv": path}

    synthetic_path = Path(synthetic_evaluation_summary_csv)
    real_path = Path(real_evaluation_summary_csv)
    synthetic = pd.read_csv(synthetic_path)
    real = pd.read_csv(real_path)
    synthetic["result_scope"] = "synthetic"
    real["result_scope"] = "real"
    return (
        pd.concat([synthetic, real], ignore_index=True, sort=False),
        {
            "synthetic_evaluation_summary_csv": synthetic_path,
            "real_evaluation_summary_csv": real_path,
        },
    )


def _load_feature_importance(feature_importance_csv: str | Path | None) -> tuple[pd.DataFrame, Path | None]:
    """Load optional feature-importance data."""

    if feature_importance_csv is None:
        return pd.DataFrame(), None
    path = Path(feature_importance_csv)
    return pd.read_csv(path), path


def _load_compatibility_summary(compatibility_matrix_csv: str | Path | None) -> pd.DataFrame:
    """Summarize the real compatibility matrix when available."""

    columns = [
        "result_scope",
        "solver_registry_name",
        "compatibility_total_instances",
        "compatibility_supported_instances",
        "compatibility_partially_supported_instances",
        "compatibility_unsupported_instances",
        "compatibility_not_configured_instances",
    ]
    if compatibility_matrix_csv is None:
        return pd.DataFrame(columns=columns)

    path = Path(compatibility_matrix_csv)
    if not path.exists():
        return pd.DataFrame(columns=columns)

    matrix = pd.read_csv(path)
    if not {"solver_name", "support_status"}.issubset(matrix.columns):
        return pd.DataFrame(columns=columns)

    frame = matrix.copy()
    frame["support_status"] = frame["support_status"].fillna("unknown").astype("string")
    grouped = (
        frame.groupby("solver_name", as_index=False)
        .agg(
            compatibility_total_instances=("instance_name", "nunique"),
            compatibility_supported_instances=(
                "support_status",
                lambda values: int((values.astype("string") == "supported").sum()),
            ),
            compatibility_partially_supported_instances=(
                "support_status",
                lambda values: int((values.astype("string") == "partially_supported").sum()),
            ),
            compatibility_unsupported_instances=(
                "support_status",
                lambda values: int((values.astype("string") == "unsupported").sum()),
            ),
            compatibility_not_configured_instances=(
                "support_status",
                lambda values: int((values.astype("string") == "not_configured").sum()),
            ),
        )
        .rename(columns={"solver_name": "solver_registry_name"})
    )
    grouped.insert(0, "result_scope", "real")
    return grouped.loc[:, columns]


def _prepare_benchmark_frame(benchmark_frame: pd.DataFrame, *, result_scope: ResultScope) -> pd.DataFrame:
    """Validate and normalize benchmark rows for thesis reports."""

    missing_columns = sorted(_REQUIRED_BENCHMARK_COLUMNS.difference(benchmark_frame.columns))
    if missing_columns:
        joined = ", ".join(missing_columns)
        raise ValueError(f"Benchmark CSV is missing required columns: {joined}")

    frame = benchmark_frame.copy()
    frame["instance_name"] = frame["instance_name"].astype("string")
    frame["solver_name"] = frame["solver_name"].astype("string")
    if "solver_registry_name" not in frame.columns:
        frame["solver_registry_name"] = frame["solver_name"]
    else:
        frame["solver_registry_name"] = frame["solver_registry_name"].fillna(frame["solver_name"]).astype("string")
    frame["status"] = frame["status"].astype("string")
    frame["objective_value"] = pd.to_numeric(frame["objective_value"], errors="coerce")
    frame["runtime_seconds"] = pd.to_numeric(frame["runtime_seconds"], errors="coerce")
    frame["feasible"] = frame["feasible"].map(_coerce_bool).astype(bool)
    if "solver_support_status" not in frame.columns:
        frame["solver_support_status"] = "unknown"
    frame["solver_support_status"] = frame["solver_support_status"].fillna("unknown").astype("string")
    if "scoring_status" not in frame.columns:
        frame["scoring_status"] = frame.apply(_derive_scoring_status, axis=1)
    else:
        missing_scoring_status = _missing_string_mask(frame["scoring_status"])
        frame.loc[missing_scoring_status, "scoring_status"] = frame[missing_scoring_status].apply(
            _derive_scoring_status,
            axis=1,
        )
    frame["scoring_status"] = frame["scoring_status"].fillna("unknown").astype("string")

    fallback_objective_valid = (
        frame["feasible"]
        & frame["objective_value"].notna()
        & ~frame.apply(_is_unsupported_or_not_configured_row, axis=1)
    )
    if "objective_value_valid" in frame.columns:
        missing_objective_valid = _missing_string_mask(frame["objective_value_valid"])
        frame["objective_value_valid_bool"] = frame["objective_value_valid"].map(_coerce_bool).astype(bool)
        frame.loc[missing_objective_valid, "objective_value_valid_bool"] = fallback_objective_valid[
            missing_objective_valid
        ]
    else:
        frame["objective_value_valid_bool"] = fallback_objective_valid
    frame["valid_feasible_result"] = (
        frame["feasible"]
        & frame["objective_value"].notna()
        & frame["objective_value_valid_bool"]
        & ~frame.apply(_is_unsupported_or_not_configured_row, axis=1)
    )
    frame["result_scope"] = _resolve_result_scopes(frame, result_scope=result_scope)
    return frame


def _resolve_result_scopes(frame: pd.DataFrame, *, result_scope: ResultScope) -> pd.Series:
    """Resolve explicit synthetic/real result scopes for benchmark rows."""

    if result_scope != "auto":
        return pd.Series([result_scope] * len(frame.index), index=frame.index, dtype="string")
    if "result_scope" in frame.columns:
        return frame["result_scope"].fillna("unknown").astype("string")
    if "is_synthetic" not in frame.columns:
        return pd.Series(["unknown"] * len(frame.index), index=frame.index, dtype="string")
    return frame["is_synthetic"].map(lambda value: "synthetic" if _coerce_bool(value) else "real").astype("string")


def _build_solver_comparison_table(
    frame: pd.DataFrame,
    *,
    compatibility_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Build the main solver comparison report table."""

    group_columns = ["result_scope", "solver_registry_name", "solver_name"]
    runtime_summary = (
        frame.groupby(group_columns, as_index=False)
        .agg(
            num_runs=("solver_name", "size"),
            num_feasible_runs=("feasible", "sum"),
            num_valid_feasible_runs=("valid_feasible_result", "sum"),
            average_runtime_seconds=("runtime_seconds", "mean"),
        )
    )

    feasible_instances = (
        frame[frame["feasible"]]
        .groupby(group_columns, as_index=False)
        .agg(num_instances_feasible=("instance_name", "nunique"))
    )
    eligible = frame[frame["valid_feasible_result"]].copy()
    if eligible.empty:
        objective_summary = pd.DataFrame(
            columns=[
                *group_columns,
                "num_instances_solved",
                "num_instances_valid_feasible",
                "average_objective_valid_feasible",
            ]
        )
        win_counts = pd.DataFrame(columns=[*group_columns, "win_count"])
    else:
        objective_summary = (
            eligible.groupby(group_columns, as_index=False)
            .agg(
                num_instances_solved=("instance_name", "nunique"),
                num_instances_valid_feasible=("instance_name", "nunique"),
                average_objective_valid_feasible=("objective_value", "mean"),
            )
        )
        best_rows = (
            eligible.sort_values(
                by=[
                    "result_scope",
                    "instance_name",
                    "objective_value",
                    "runtime_seconds",
                    "solver_registry_name",
                    "solver_name",
                ],
                ascending=[True, True, True, True, True, True],
                kind="mergesort",
            )
            .groupby(["result_scope", "instance_name"], as_index=False)
            .head(1)
        )
        win_counts = (
            best_rows.groupby(group_columns, as_index=False)
            .size()
            .rename(columns={"size": "win_count"})
        )

    summary = runtime_summary.merge(objective_summary, on=group_columns, how="left")
    summary = summary.merge(feasible_instances, on=group_columns, how="left")
    summary = summary.merge(win_counts, on=group_columns, how="left")
    summary["num_instances_solved"] = pd.to_numeric(
        summary["num_instances_solved"],
        errors="coerce",
    ).fillna(0).astype(int)
    summary["num_instances_valid_feasible"] = pd.to_numeric(
        summary["num_instances_valid_feasible"],
        errors="coerce",
    ).fillna(0).astype(int)
    summary["num_instances_feasible"] = pd.to_numeric(
        summary["num_instances_feasible"],
        errors="coerce",
    ).fillna(0).astype(int)
    summary["win_count"] = pd.to_numeric(summary["win_count"], errors="coerce").fillna(0).astype(int)

    instance_counts = frame.groupby("result_scope")["instance_name"].nunique().to_dict()
    summary["num_instances_total"] = summary["result_scope"].map(lambda scope: int(instance_counts.get(scope, 0)))
    summary["feasible_coverage_ratio"] = summary.apply(
        lambda row: _safe_divide(row["num_instances_feasible"], row["num_instances_total"]),
        axis=1,
    )
    summary["valid_feasible_coverage_ratio"] = summary.apply(
        lambda row: _safe_divide(row["num_instances_valid_feasible"], row["num_instances_total"]),
        axis=1,
    )
    summary["coverage_ratio"] = summary["valid_feasible_coverage_ratio"]
    summary["average_objective"] = summary["average_objective_valid_feasible"]
    summary["num_runs"] = pd.to_numeric(summary["num_runs"], errors="coerce").fillna(0).astype(int)
    summary["num_feasible_runs"] = pd.to_numeric(
        summary["num_feasible_runs"],
        errors="coerce",
    ).fillna(0).astype(int)
    summary["num_valid_feasible_runs"] = pd.to_numeric(
        summary["num_valid_feasible_runs"],
        errors="coerce",
    ).fillna(0).astype(int)
    summary = _merge_compatibility_summary(summary, compatibility_summary)

    return summary.loc[
        :,
        [
            "result_scope",
            "solver_registry_name",
            "solver_name",
            "num_runs",
            "num_feasible_runs",
            "num_valid_feasible_runs",
            "num_instances_total",
            "num_instances_feasible",
            "num_instances_solved",
            "num_instances_valid_feasible",
            "feasible_coverage_ratio",
            "valid_feasible_coverage_ratio",
            "coverage_ratio",
            "win_count",
            "average_objective_valid_feasible",
            "average_objective",
            "average_runtime_seconds",
            "compatibility_total_instances",
            "compatibility_supported_instances",
            "compatibility_partially_supported_instances",
            "compatibility_unsupported_instances",
            "compatibility_not_configured_instances",
        ],
    ].sort_values(
        by=[
            "result_scope",
            "num_instances_valid_feasible",
            "num_instances_feasible",
            "win_count",
            "average_objective_valid_feasible",
            "average_runtime_seconds",
            "solver_registry_name",
        ],
        ascending=[True, False, False, False, True, True, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _build_win_counts_table(solver_comparison: pd.DataFrame) -> pd.DataFrame:
    """Extract the thesis win-count table."""

    return solver_comparison.loc[
        :,
        ["result_scope", "solver_registry_name", "solver_name", "win_count"],
    ].sort_values(
        by=["result_scope", "win_count", "solver_registry_name"],
        ascending=[True, False, True],
        kind="mergesort",
    ).reset_index(drop=True)


def _build_solver_support_summary(
    frame: pd.DataFrame,
    *,
    compatibility_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Build support-status and scoring-status breakdown rows."""

    group_columns = [
        "result_scope",
        "solver_registry_name",
        "solver_name",
        "solver_support_status",
        "scoring_status",
    ]
    summary = (
        frame.groupby(group_columns, as_index=False, dropna=False)
        .agg(
            num_rows=("solver_name", "size"),
            num_feasible_runs=("feasible", "sum"),
            num_valid_feasible_runs=("valid_feasible_result", "sum"),
            num_instances=("instance_name", "nunique"),
            average_runtime_seconds=("runtime_seconds", "mean"),
        )
        .sort_values(
            by=["result_scope", "solver_registry_name", "solver_support_status", "scoring_status"],
            kind="mergesort",
        )
        .reset_index(drop=True)
    )
    run_counts = (
        frame.groupby(["result_scope", "solver_registry_name"], as_index=False)
        .agg(total_solver_rows=("solver_name", "size"))
    )
    summary = summary.merge(run_counts, on=["result_scope", "solver_registry_name"], how="left")
    summary["row_ratio_within_solver"] = summary.apply(
        lambda row: _safe_divide(row["num_rows"], row["total_solver_rows"]),
        axis=1,
    )
    summary = _merge_compatibility_summary(summary, compatibility_summary)
    return summary


def _merge_compatibility_summary(
    table: pd.DataFrame,
    compatibility_summary: pd.DataFrame,
) -> pd.DataFrame:
    """Attach real compatibility counts when a matrix is available."""

    compatibility_columns = [
        "compatibility_total_instances",
        "compatibility_supported_instances",
        "compatibility_partially_supported_instances",
        "compatibility_unsupported_instances",
        "compatibility_not_configured_instances",
    ]
    if compatibility_summary.empty:
        for column in compatibility_columns:
            table[column] = 0
        return table

    merged = table.merge(
        compatibility_summary,
        on=["result_scope", "solver_registry_name"],
        how="left",
    )
    for column in compatibility_columns:
        merged[column] = pd.to_numeric(merged[column], errors="coerce").fillna(0).astype(int)
    return merged


def _build_average_objective_table(solver_comparison: pd.DataFrame) -> pd.DataFrame:
    """Extract average objective values by solver."""

    return solver_comparison.loc[
        :,
        [
            "result_scope",
            "solver_registry_name",
            "solver_name",
            "average_objective_valid_feasible",
            "average_objective",
            "num_instances_solved",
            "num_valid_feasible_runs",
            "valid_feasible_coverage_ratio",
            "coverage_ratio",
        ],
    ].sort_values(
        by=["result_scope", "average_objective_valid_feasible", "solver_registry_name"],
        ascending=[True, True, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)


def _build_average_runtime_table(solver_comparison: pd.DataFrame) -> pd.DataFrame:
    """Extract average runtime values by solver."""

    return solver_comparison.loc[
        :,
        [
            "result_scope",
            "solver_registry_name",
            "solver_name",
            "average_runtime_seconds",
            "num_runs",
            "num_feasible_runs",
            "num_valid_feasible_runs",
        ],
    ].sort_values(
        by=["result_scope", "average_runtime_seconds", "solver_registry_name"],
        ascending=[True, True, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)


def _build_selector_vs_baselines_table(
    evaluation_summary: pd.DataFrame,
    *,
    result_scope: str,
) -> pd.DataFrame:
    """Build selector vs single-best and virtual-best comparison rows."""

    if "result_scope" in evaluation_summary.columns:
        rows: list[dict[str, object]] = []
        for scope, scope_summary in evaluation_summary.groupby("result_scope", sort=True):
            rows.extend(
                _selector_vs_baselines_rows(
                    scope_summary,
                    result_scope=str(scope),
                )
            )
        return pd.DataFrame(rows)

    return pd.DataFrame(_selector_vs_baselines_rows(evaluation_summary, result_scope=result_scope))


def _selector_vs_baselines_rows(
    evaluation_summary: pd.DataFrame,
    *,
    result_scope: str,
) -> list[dict[str, object]]:
    """Build selector and baseline rows for one result scope."""

    mean_row = _select_summary_row(evaluation_summary, "aggregate_mean")
    std_row = _select_summary_row(evaluation_summary, "aggregate_std")
    split_count = _count_validation_splits(evaluation_summary)

    selector_objective = _to_float(mean_row.get("average_selected_objective"))
    virtual_best_objective = _to_float(mean_row.get("average_virtual_best_objective"))
    single_best_objective = _to_float(mean_row.get("average_single_best_objective"))

    return [
        {
            "result_scope": result_scope,
            "method": "selector",
            "reference_solver_name": None,
            "split_strategy": _clean_optional_string(mean_row.get("split_strategy")),
            "num_validation_splits": split_count,
            "average_objective": selector_objective,
            "objective_gap_vs_virtual_best": _to_float(mean_row.get("regret_vs_virtual_best")),
            "objective_gap_vs_single_best": _to_float(mean_row.get("delta_vs_single_best")),
            "classification_accuracy": _to_float(mean_row.get("classification_accuracy")),
            "classification_accuracy_std": _to_float(std_row.get("classification_accuracy")),
            "balanced_accuracy": _to_float(mean_row.get("balanced_accuracy")),
            "balanced_accuracy_std": _to_float(std_row.get("balanced_accuracy")),
        },
        {
            "result_scope": result_scope,
            "method": "single_best_solver",
            "reference_solver_name": _clean_optional_string(mean_row.get("single_best_solver_name")),
            "split_strategy": _clean_optional_string(mean_row.get("split_strategy")),
            "num_validation_splits": split_count,
            "average_objective": single_best_objective,
            "objective_gap_vs_virtual_best": _safe_subtract(
                single_best_objective,
                virtual_best_objective,
            ),
            "objective_gap_vs_single_best": 0.0,
            "classification_accuracy": float("nan"),
            "classification_accuracy_std": float("nan"),
            "balanced_accuracy": float("nan"),
            "balanced_accuracy_std": float("nan"),
        },
        {
            "result_scope": result_scope,
            "method": "virtual_best_solver",
            "reference_solver_name": "oracle",
            "split_strategy": _clean_optional_string(mean_row.get("split_strategy")),
            "num_validation_splits": split_count,
            "average_objective": virtual_best_objective,
            "objective_gap_vs_virtual_best": 0.0,
            "objective_gap_vs_single_best": _safe_subtract(
                virtual_best_objective,
                single_best_objective,
            ),
            "classification_accuracy": float("nan"),
            "classification_accuracy_std": float("nan"),
            "balanced_accuracy": float("nan"),
            "balanced_accuracy_std": float("nan"),
        },
    ]


def _build_feature_importance_summary(
    feature_importance: pd.DataFrame,
    *,
    result_scope: str,
    top_feature_count: int,
) -> pd.DataFrame:
    """Build a cleaned top-feature table for thesis reuse."""

    output_columns = [
        "result_scope",
        "importance_rank",
        "feature",
        "source_feature",
        "feature_group",
        "importance",
        "importance_share",
        "cumulative_importance_share",
    ]
    if feature_importance.empty:
        return pd.DataFrame(columns=output_columns)

    if "importance" not in feature_importance.columns:
        raise ValueError("Feature importance CSV must contain an 'importance' column.")
    if "feature" not in feature_importance.columns and "source_feature" not in feature_importance.columns:
        raise ValueError("Feature importance CSV must contain 'feature' or 'source_feature'.")

    table = feature_importance.copy()
    if "feature" not in table.columns:
        table["feature"] = table["source_feature"]
    if "source_feature" not in table.columns:
        table["source_feature"] = table["feature"].map(_source_feature_name)
    if "feature_group" not in table.columns:
        table["feature_group"] = table["source_feature"].map(feature_group_for_column)

    table["importance"] = pd.to_numeric(table["importance"], errors="coerce")
    table = table.dropna(subset=["importance"]).copy()
    table = table.drop(columns=["importance_rank"], errors="ignore")
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

    table.insert(0, "result_scope", result_scope)
    table = table.head(top_feature_count)
    return table.loc[:, output_columns]


def _write_table_markdown(
    output_path: Path,
    *,
    title: str,
    description: str,
    table: pd.DataFrame,
    columns: list[str],
) -> None:
    """Write one Markdown file containing a reusable report table."""

    output_path.write_text(
        "\n".join(
            [
                f"# {title}",
                "",
                description,
                "",
                _markdown_table(table, columns=columns),
                "",
            ]
        ),
        encoding="utf-8",
    )


def _build_summary_markdown(
    *,
    benchmark_inputs: dict[str, Path],
    evaluation_inputs: dict[str, Path],
    feature_importance_input: Path | None,
    report_scope: str,
    solver_comparison: pd.DataFrame,
    solver_support_summary: pd.DataFrame,
    win_counts: pd.DataFrame,
    average_objective: pd.DataFrame,
    average_runtime: pd.DataFrame,
    selector_vs_baselines: pd.DataFrame,
    feature_importance_summary: pd.DataFrame,
) -> str:
    """Render the combined thesis benchmark report."""

    lines = [
        "# Thesis Benchmark And Selector Report",
        "",
        "## Synthetic/Real Separation",
        "",
        f"- Report scope: `{report_scope}`",
        "- Every generated CSV includes a `result_scope` column.",
        "- When the input benchmark contains both synthetic and real rows, solver metrics are grouped separately by `result_scope`.",
        "",
        "## Inputs",
        "",
        *_render_input_lines("Benchmark results", benchmark_inputs),
        *_render_input_lines("Selector evaluation summaries", evaluation_inputs),
        f"- Feature importance: `{feature_importance_input.as_posix() if feature_importance_input is not None else 'not provided'}`",
        "",
        "## Solver Comparison Table",
        "",
        _markdown_table(
            solver_comparison,
            columns=[
                "result_scope",
                "solver_registry_name",
                "solver_name",
                "num_instances_total",
                "feasible_coverage_ratio",
                "valid_feasible_coverage_ratio",
                "win_count",
                "average_objective_valid_feasible",
                "average_runtime_seconds",
            ],
        ),
        "",
        "## Solver Support Summary",
        "",
        _markdown_table(
            solver_support_summary,
            columns=[
                "result_scope",
                "solver_registry_name",
                "solver_support_status",
                "scoring_status",
                "num_rows",
                "num_feasible_runs",
                "num_valid_feasible_runs",
                "row_ratio_within_solver",
            ],
        ),
        "",
        "## Win Counts Per Solver",
        "",
        _markdown_table(
            win_counts,
            columns=["result_scope", "solver_registry_name", "solver_name", "win_count"],
        ),
        "",
        "## Average Objective Per Solver",
        "",
        _markdown_table(
            average_objective,
            columns=[
                "result_scope",
                "solver_registry_name",
                "solver_name",
                "average_objective_valid_feasible",
                "num_instances_solved",
            ],
        ),
        "",
        "## Average Runtime Per Solver",
        "",
        _markdown_table(
            average_runtime,
            columns=[
                "result_scope",
                "solver_registry_name",
                "solver_name",
                "average_runtime_seconds",
                "num_runs",
            ],
        ),
        "",
        "## Selector Vs Single Best Vs Virtual Best",
        "",
        _markdown_table(
            selector_vs_baselines,
            columns=[
                "result_scope",
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
        "## Feature Importance Summary",
        "",
        _markdown_table(
            feature_importance_summary,
            columns=[
                "result_scope",
                "importance_rank",
                "source_feature",
                "feature_group",
                "importance",
                "importance_share",
            ],
        ),
        "",
        "## Interpretation Notes",
        "",
        "- Lower objective values are treated as better.",
        "- Feasible coverage counts whether a solver returned a feasible result for an instance.",
        "- Valid feasible coverage counts whether the row is objective-comparable under the scoring contract.",
        "- Average objective uses only valid feasible rows; unsupported, failed, and not-configured rows cannot improve objective quality.",
        "- Average runtime uses all recorded solver rows, including unsupported, failed, and not-configured rows.",
        "- Support-status tables report `solver_support_status` and `scoring_status` separately from performance quality.",
        "- The virtual best solver is an oracle baseline and should be interpreted as a lower bound.",
        "- The single best solver is the best fixed solver baseline from selector evaluation.",
        "",
    ]
    return "\n".join(lines)


def _markdown_table(frame: pd.DataFrame, *, columns: list[str]) -> str:
    """Render a dataframe as a compact Markdown table."""

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


def _select_summary_row(summary: pd.DataFrame, row_type: str) -> pd.Series:
    """Return one evaluation summary row by type with a stable fallback."""

    if summary.empty:
        raise ValueError("Evaluation summary CSV is empty.")
    if "summary_scope" in summary.columns:
        scope_aliases = {
            "aggregate_mean": ("aggregate_mean", "all_seeds_mean"),
            "aggregate_std": ("aggregate_std", "all_seeds_std"),
        }
        matches = summary[
            summary["summary_scope"].astype("string").isin(scope_aliases.get(row_type, (row_type,)))
        ]
        if not matches.empty:
            return matches.iloc[0]
        if row_type == "aggregate_std":
            return pd.Series(dtype="object")
    if "summary_row_type" not in summary.columns:
        return summary.iloc[0]
    matches = summary[summary["summary_row_type"].astype("string") == row_type]
    if not matches.empty:
        return matches.iloc[0]
    if row_type == "aggregate_std":
        return pd.Series(dtype="object")
    return summary.iloc[0]


def _count_validation_splits(evaluation_summary: pd.DataFrame) -> int:
    """Count validation split rows in an evaluation summary table."""

    if "summary_scope" in evaluation_summary.columns:
        per_seed_count = int(evaluation_summary["summary_scope"].astype("string").eq("per_seed").sum())
        return max(1, per_seed_count)
    if "summary_row_type" not in evaluation_summary.columns:
        return max(1, len(evaluation_summary.index))
    split_count = int(evaluation_summary["summary_row_type"].astype("string").eq("split").sum())
    return max(1, split_count)


def _summarize_report_scope(frame: pd.DataFrame) -> str:
    """Return one compact scope label for selector-level report rows."""

    scopes = sorted(str(value) for value in frame["result_scope"].dropna().unique().tolist())
    if not scopes:
        return "unknown"
    if len(scopes) == 1:
        return scopes[0]
    return "mixed"


def _derive_scoring_status(row: pd.Series) -> str:
    """Derive a conservative scoring status for older benchmark outputs."""

    support_status = str(row.get("solver_support_status", "")).strip().casefold()
    status = str(row.get("status", "")).strip().casefold()
    if "not_configured" in support_status or "not configured" in status or "not_configured" in status:
        return "not_configured"
    if "unsupported" in support_status or "unsupported" in status:
        return "unsupported_instance"
    if "failed" in status:
        return "failed_run"
    if bool(row.get("feasible")) and pd.notna(row.get("objective_value")):
        return "legacy_feasible_run"
    return "legacy_infeasible_run"


def _is_unsupported_or_not_configured_row(row: pd.Series) -> bool:
    """Return whether a row should be excluded from objective quality metrics."""

    support_status = str(row.get("solver_support_status", "")).strip().casefold()
    scoring_status = str(row.get("scoring_status", "")).strip().casefold()
    status = str(row.get("status", "")).strip().casefold()
    combined = " ".join([support_status, scoring_status, status]).replace("-", "_")
    markers = (
        "unsupported",
        "not_configured",
        "not configured",
        "failed",
        "execution_error",
        "invalid_output",
        "invalid_solution",
        "timeout",
    )
    return any(marker in combined for marker in markers)


def _render_input_lines(label: str, inputs: dict[str, Path]) -> list[str]:
    """Render run input paths for the summary Markdown."""

    if not inputs:
        return [f"- {label}: `not provided`"]
    return [
        f"- {label} ({name}): `{path.as_posix()}`"
        for name, path in sorted(inputs.items())
    ]


def _coerce_bool(value: object) -> bool:
    """Normalize bool-like CSV values."""

    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def _missing_string_mask(values: pd.Series) -> pd.Series:
    """Return True for null or blank string values in a series."""

    return values.isna() | values.astype("string").str.strip().fillna("").eq("")


def _safe_divide(numerator: object, denominator: object) -> float:
    """Divide two scalar values with NaN protection."""

    top = _to_float(numerator)
    bottom = _to_float(denominator)
    if pd.isna(top) or pd.isna(bottom) or bottom == 0.0:
        return 0.0
    return float(top / bottom)


def _safe_subtract(left: object, right: object) -> float:
    """Subtract two scalar values with NaN fallback."""

    left_value = _to_float(left)
    right_value = _to_float(right)
    if pd.isna(left_value) or pd.isna(right_value):
        return float("nan")
    return float(left_value - right_value)


def _to_float(value: object) -> float:
    """Convert a scalar value to float with NaN fallback."""

    if value is None or pd.isna(value):
        return float("nan")
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _clean_optional_string(value: object) -> str | None:
    """Return a non-empty string or None."""

    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    return text or None


def _source_feature_name(feature_name: object) -> str:
    """Map a transformed feature name to a readable source feature name."""

    text = str(feature_name)
    if "__" in text:
        text = text.split("__", maxsplit=1)[1]
    return text


def _format_markdown_value(value: object) -> str:
    """Format one scalar value for Markdown output."""

    if value is None or pd.isna(value):
        return "NA"
    numeric = _to_float(value)
    if pd.notna(numeric):
        if float(numeric).is_integer():
            return str(int(numeric))
        return f"{float(numeric):.4f}"
    text = str(value).strip().replace("|", "\\|")
    return text or "NA"


def _labelize(value: str) -> str:
    """Convert one identifier-like string into a readable label."""

    return value.replace("_", " ").strip().title()


__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "ThesisBenchmarkReportResult",
    "generate_thesis_benchmark_report",
]


if __name__ == "__main__":
    raise SystemExit(main())
