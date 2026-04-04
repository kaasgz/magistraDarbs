"""Print a concise readable summary from one benchmark CSV artifact."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from src.experiments.benchmark_validation import validate_benchmark_results
from src.experiments.metrics import average_objective_by_solver, average_runtime_by_solver


def benchmark_report(benchmark_csv: str | Path) -> str:
    """Build a short human-readable report for one benchmark CSV."""

    path = Path(benchmark_csv)
    frame = pd.read_csv(path)
    validation_issues = validate_benchmark_results(frame)

    num_rows = len(frame.index)
    num_instances = int(frame["instance_name"].astype("string").nunique()) if "instance_name" in frame.columns else 0
    num_solvers = (
        int(frame["solver_registry_name"].astype("string").nunique())
        if "solver_registry_name" in frame.columns
        else int(frame["solver_name"].astype("string").nunique())
        if "solver_name" in frame.columns
        else 0
    )
    aggregate_runtime = (
        float(pd.to_numeric(frame["runtime_seconds"], errors="coerce").fillna(0.0).sum())
        if "runtime_seconds" in frame.columns
        else 0.0
    )
    feasible_runs = (
        int(frame["feasible"].map(_coerce_bool).sum())
        if "feasible" in frame.columns
        else 0
    )
    failed_runs = (
        int(frame["status"].astype("string").str.startswith("FAILED", na=False).sum())
        if "status" in frame.columns
        else 0
    )

    objective_summary = average_objective_by_solver(frame)
    runtime_summary = average_runtime_by_solver(frame)
    merged = objective_summary.merge(
        runtime_summary.loc[:, ["solver_name", "average_runtime", "num_runs", "num_feasible_runs"]],
        on="solver_name",
        how="outer",
    ).fillna({"num_runs": 0, "num_feasible_runs": 0})

    lines = [
        f"Benchmark file: {path.as_posix()}",
        f"Rows: {num_rows}",
        f"Instances: {num_instances}",
        f"Solvers: {num_solvers}",
        f"Feasible runs: {feasible_runs}",
        f"Failed runs: {failed_runs}",
        f"Aggregate runtime (s): {aggregate_runtime:.6f}",
    ]

    if validation_issues:
        lines.append(f"Validation issues: {len(validation_issues)}")
        lines.extend(f"- [{issue.code}] {issue.message}" for issue in validation_issues)
    else:
        lines.append("Validation issues: 0")

    if merged.empty:
        lines.append("Solver summary: no benchmark rows available")
    else:
        lines.append("Solver summary:")
        for row in merged.sort_values("solver_name", kind="mergesort").to_dict(orient="records"):
            lines.append(
                "- "
                f"{row['solver_name']}: runs={int(row.get('num_runs', 0))}, "
                f"feasible={int(row.get('num_feasible_runs', 0))}, "
                f"avg_runtime={_format_float(row.get('average_runtime'))}, "
                f"avg_objective={_format_float(row.get('average_objective'))}"
            )

    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the benchmark report helper."""

    parser = argparse.ArgumentParser(description="Print a short report for one benchmark CSV.")
    parser.add_argument("benchmark_csv", help="Path to the benchmark results CSV.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the benchmark report helper from the command line."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)
    print(benchmark_report(args.benchmark_csv))
    return 0


def _coerce_bool(value: object) -> bool:
    """Convert CSV-style feasibility values into booleans."""

    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def _format_float(value: object) -> str:
    """Format one possibly missing float value for display."""

    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return "n/a"
    if pd.isna(numeric):
        return "n/a"
    return f"{numeric:.6f}"


if __name__ == "__main__":
    raise SystemExit(main())
