"""Evaluation helpers for solver and selector experiments.

These helpers operate on benchmark tables with the same schema as
``benchmark_results.csv`` produced by ``src.experiments.run_benchmarks``.

Assumptions in this first version:

- Lower objective values are better.
- Only rows with ``feasible == True`` and a numeric ``objective_value`` are
  eligible for "best solver" comparisons.
- Runtime averages are computed over all recorded runs, including failed ones,
  because benchmark time still matters when a solver does not succeed.
- When an instance has no feasible solver result, ``best_solver_per_instance``
  returns a placeholder row with ``status == 'NO_FEASIBLE_SOLVER'``.
- ``single_best_solver`` prioritizes solver coverage first, then lower average
  objective, then lower average runtime.
"""

from __future__ import annotations

from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {
    "instance_name",
    "solver_name",
    "objective_value",
    "runtime_seconds",
    "feasible",
    "status",
}


def best_solver_per_instance(results: pd.DataFrame) -> pd.DataFrame:
    """Return the best feasible solver result for each instance.

    Args:
        results: Benchmark results in ``benchmark_results.csv`` style format.

    Returns:
        A table with one row per instance. If no feasible solver result exists
        for an instance, a placeholder row is returned instead.
    """

    frame = _prepare_results_frame(results)
    all_instances = sorted(frame["instance_name"].dropna().unique())
    eligible = _eligible_results(frame)

    best_rows = (
        eligible.sort_values(
            by=["instance_name", "objective_value", "runtime_seconds", "solver_name"],
            ascending=[True, True, True, True],
            kind="mergesort",
        )
        .groupby("instance_name", sort=True, as_index=False)
        .head(1)
        .loc[:, _benchmark_columns()]
    )

    selected_instances = set(best_rows["instance_name"])
    missing_instances = [instance for instance in all_instances if instance not in selected_instances]
    if missing_instances:
        best_rows = pd.concat(
            [best_rows, _no_feasible_rows(missing_instances)],
            ignore_index=True,
        )

    return best_rows.sort_values("instance_name", kind="mergesort").reset_index(drop=True)


def single_best_solver(results: pd.DataFrame) -> pd.Series:
    """Return the best fixed solver under simple benchmark assumptions.

    The current definition prioritizes:

    1. More solved instances.
    2. Lower average feasible objective.
    3. Lower average runtime across all runs.

    Args:
        results: Benchmark results in ``benchmark_results.csv`` style format.

    Returns:
        A pandas series summarizing the selected single best solver. If no
        solver has a feasible result, the returned series contains safe
        placeholder values.
    """

    objective_summary = average_objective_by_solver(results)
    if objective_summary.empty:
        return pd.Series(
            {
                "solver_name": pd.NA,
                "num_instances_solved": 0,
                "average_objective": float("nan"),
                "average_runtime": float("nan"),
            }
        )

    runtime_summary = average_runtime_by_solver(results).loc[:, ["solver_name", "average_runtime"]]
    summary = objective_summary.merge(runtime_summary, on="solver_name", how="left")
    best_row = (
        summary.sort_values(
            by=["num_instances_solved", "average_objective", "average_runtime", "solver_name"],
            ascending=[False, True, True, True],
            kind="mergesort",
        )
        .iloc[0]
    )
    return best_row.loc[
        ["solver_name", "num_instances_solved", "average_objective", "average_runtime"]
    ]


def virtual_best_solver(results: pd.DataFrame) -> pd.Series:
    """Return an aggregate summary of the virtual best solver.

    The virtual best solver is the oracle that picks the best feasible solver
    independently for each instance.

    Args:
        results: Benchmark results in ``benchmark_results.csv`` style format.

    Returns:
        A pandas series with aggregate virtual-best metrics.
    """

    best_rows = best_solver_per_instance(results)
    feasible_rows = best_rows[best_rows["feasible"]].copy()

    return pd.Series(
        {
            "solver_name": "virtual_best_solver",
            "num_instances": int(best_rows["instance_name"].nunique()),
            "num_instances_solved": int(feasible_rows["instance_name"].nunique()),
            "average_objective": feasible_rows["objective_value"].mean(),
            "average_runtime": feasible_rows["runtime_seconds"].mean(),
        }
    )


def average_objective_by_solver(results: pd.DataFrame) -> pd.DataFrame:
    """Compute average feasible objective values by solver.

    Args:
        results: Benchmark results in ``benchmark_results.csv`` style format.

    Returns:
        A table with one row per solver, using only feasible runs with numeric
        objectives.
    """

    eligible = _eligible_results(_prepare_results_frame(results))
    if eligible.empty:
        return pd.DataFrame(columns=["solver_name", "average_objective", "num_instances_solved"])

    summary = (
        eligible.groupby("solver_name", as_index=False)
        .agg(
            average_objective=("objective_value", "mean"),
            num_instances_solved=("instance_name", "nunique"),
        )
        .sort_values(by=["average_objective", "solver_name"], ascending=[True, True], kind="mergesort")
        .reset_index(drop=True)
    )
    return summary


def average_runtime_by_solver(results: pd.DataFrame) -> pd.DataFrame:
    """Compute average runtime by solver across all recorded runs.

    Args:
        results: Benchmark results in ``benchmark_results.csv`` style format.

    Returns:
        A table with one row per solver.
    """

    frame = _prepare_results_frame(results)
    summary = (
        frame.groupby("solver_name", as_index=False)
        .agg(
            average_runtime=("runtime_seconds", "mean"),
            num_runs=("solver_name", "size"),
            num_feasible_runs=("feasible", "sum"),
        )
        .sort_values(by=["average_runtime", "solver_name"], ascending=[True, True], kind="mergesort")
        .reset_index(drop=True)
    )
    return summary


def _prepare_results_frame(results: pd.DataFrame) -> pd.DataFrame:
    """Validate and normalize benchmark results for metric computation."""

    missing_columns = sorted(REQUIRED_COLUMNS.difference(results.columns))
    if missing_columns:
        missing = ", ".join(missing_columns)
        raise ValueError(f"Benchmark results are missing required columns: {missing}")

    frame = results.copy()
    frame["instance_name"] = frame["instance_name"].astype("string")
    frame["solver_name"] = frame["solver_name"].astype("string")
    frame["status"] = frame["status"].astype("string")
    frame["objective_value"] = pd.to_numeric(frame["objective_value"], errors="coerce")
    frame["runtime_seconds"] = pd.to_numeric(frame["runtime_seconds"], errors="coerce")
    frame["feasible"] = frame["feasible"].map(_coerce_feasible).astype(bool)
    return frame


def _eligible_results(frame: pd.DataFrame) -> pd.DataFrame:
    """Return results eligible for objective-based comparison."""

    return frame[frame["feasible"] & frame["objective_value"].notna()].copy()


def _no_feasible_rows(instance_names: list[str]) -> pd.DataFrame:
    """Create placeholder rows for instances with no feasible solver result."""

    rows: list[dict[str, Any]] = []
    for instance_name in instance_names:
        rows.append(
            {
                "instance_name": instance_name,
                "solver_name": pd.NA,
                "objective_value": float("nan"),
                "runtime_seconds": float("nan"),
                "feasible": False,
                "status": "NO_FEASIBLE_SOLVER",
            }
        )
    return pd.DataFrame(rows, columns=_benchmark_columns())


def _benchmark_columns() -> list[str]:
    """Return the stable benchmark column order used by the metrics helpers."""

    return [
        "instance_name",
        "solver_name",
        "objective_value",
        "runtime_seconds",
        "feasible",
        "status",
    ]


def _coerce_feasible(value: object) -> bool:
    """Normalize a CSV-style feasibility value to a Python boolean."""

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
