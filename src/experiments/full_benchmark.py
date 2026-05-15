"""Run the full solver portfolio on one dataset of XML instances."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from src.experiments.benchmark_validation import (
    BenchmarkValidationError,
    validate_benchmark_results,
)
from src.experiments.run_benchmarks import run_benchmarks


LOGGER = logging.getLogger(__name__)

DEFAULT_INSTANCE_FOLDER = Path("data/raw/synthetic/generated")
DEFAULT_OUTPUT_PATH = Path("data/results/full_benchmark_results.csv")
DEFAULT_FULL_SOLVER_PORTFOLIO = [
    "random_baseline",
    "cpsat_solver",
    "simulated_annealing_solver",
    "timefold",
]


def run_full_benchmark(
    instance_folder: str | Path = DEFAULT_INSTANCE_FOLDER,
    output_csv: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    time_limit_seconds: int = 60,
    random_seed: int = 42,
    timefold_executable_path: str | Path | None = None,
    timefold_time_limit_seconds: int | None = None,
    timefold_command_arguments: Sequence[str] | None = None,
    run_summary_path: str | Path | None = None,
) -> Path:
    """Run all configured portfolio solvers on every XML instance in a folder.

    The function keeps the existing benchmark runner as the source of truth for
    solver execution and failure handling, then adds a normalized
    ``solver_support_status`` column required by the full benchmark artifact.
    """

    input_path = Path(instance_folder)
    output_path = Path(output_csv)
    LOGGER.info(
        "Starting full benchmark on %s with %d solvers.",
        input_path,
        len(DEFAULT_FULL_SOLVER_PORTFOLIO),
    )
    LOGGER.info(
        "Full solver portfolio: %s",
        ", ".join(DEFAULT_FULL_SOLVER_PORTFOLIO),
    )

    solver_settings_by_name = _build_solver_settings(
        timefold_executable_path=timefold_executable_path,
        timefold_time_limit_seconds=timefold_time_limit_seconds,
        timefold_command_arguments=timefold_command_arguments,
    )

    benchmark_path = run_benchmarks(
        instance_folder=str(input_path),
        solver_names=list(DEFAULT_FULL_SOLVER_PORTFOLIO),
        time_limit_seconds=time_limit_seconds,
        random_seed=random_seed,
        output_csv=output_path,
        run_summary_path=run_summary_path,
        solver_settings_by_name=solver_settings_by_name,
    )

    table = pd.read_csv(benchmark_path)
    table = _add_solver_support_status(table)
    table = _order_full_benchmark_columns(table)

    validation_issues = validate_benchmark_results(
        table,
        expected_solver_registry_names=DEFAULT_FULL_SOLVER_PORTFOLIO,
    )
    if validation_issues:
        joined_messages = "; ".join(issue.message for issue in validation_issues)
        raise BenchmarkValidationError(joined_messages)

    table.to_csv(benchmark_path, index=False)
    LOGGER.info("Saved full benchmark results with %d rows to %s.", len(table.index), benchmark_path)
    return benchmark_path


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for the full benchmark runner."""

    parser = argparse.ArgumentParser(
        description="Run the full solver portfolio on a dataset of XML instances.",
    )
    parser.add_argument(
        "instance_folder",
        nargs="?",
        default=str(DEFAULT_INSTANCE_FOLDER),
        help="Folder containing XML instances. Defaults to data/raw/synthetic/generated.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output CSV path. Defaults to data/results/full_benchmark_results.csv.",
    )
    parser.add_argument(
        "--time-limit-seconds",
        type=int,
        default=60,
        help="Default per-solver time limit in seconds.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed passed to all solvers.",
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
        help="Additional argument passed to the Timefold executable. Repeat for multiple arguments.",
    )
    parser.add_argument(
        "--run-summary",
        default=None,
        help="Optional run summary JSON path.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the full benchmark from the command line."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        output_path = run_full_benchmark(
            instance_folder=args.instance_folder,
            output_csv=args.output,
            time_limit_seconds=args.time_limit_seconds,
            random_seed=args.random_seed,
            timefold_executable_path=args.timefold_executable,
            timefold_time_limit_seconds=args.timefold_time_limit_seconds,
            timefold_command_arguments=args.timefold_command_arg,
            run_summary_path=args.run_summary,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError, BenchmarkValidationError) as exc:
        LOGGER.error("Full benchmark failed: %s", exc)
        return 1

    print(f"Full benchmark results saved to {output_path}")
    return 0


def _build_solver_settings(
    *,
    timefold_executable_path: str | Path | None,
    timefold_time_limit_seconds: int | None,
    timefold_command_arguments: Sequence[str] | None,
) -> dict[str, dict[str, object]]:
    """Build constructor kwargs for solvers that need external configuration."""

    timefold_settings: dict[str, object] = {
        "executable_path": str(timefold_executable_path) if timefold_executable_path else None,
    }
    if timefold_time_limit_seconds is not None:
        timefold_settings["time_limit_seconds"] = timefold_time_limit_seconds
    if timefold_command_arguments is not None:
        timefold_settings["command_arguments"] = list(timefold_command_arguments)

    return {
        "timefold": timefold_settings,
    }


def _add_solver_support_status(table: pd.DataFrame) -> pd.DataFrame:
    """Add a normalized solver support status column."""

    frame = table.copy()
    if "solver_support_status" in frame.columns:
        frame["solver_support_status"] = frame["solver_support_status"].fillna("").astype(str)
        missing_mask = frame["solver_support_status"].str.strip() == ""
        if not missing_mask.any():
            return frame
        frame.loc[missing_mask, "solver_support_status"] = [
            _derive_solver_support_status(row)
            for row in frame.loc[missing_mask].to_dict(orient="records")
        ]
        return frame

    frame["solver_support_status"] = [_derive_solver_support_status(row) for row in frame.to_dict(orient="records")]
    return frame


def _derive_solver_support_status(row: dict[str, Any]) -> str:
    """Derive a compact support status from solver status and metadata."""

    status = str(row.get("status", "")).strip()
    normalized_status = status.casefold()
    metadata = _parse_metadata(row.get("solver_metadata_json"))

    contract_status = str(row.get("solver_support_status", "")).strip()
    if contract_status:
        return contract_status

    if normalized_status == "not_configured":
        return "not_configured"
    if normalized_status == "unsupported_instance":
        return "unsupported"
    if normalized_status == "timeout":
        return "timeout"
    if normalized_status.startswith("failed"):
        return "failed"
    if normalized_status in {"execution_error", "invalid_output", "invalid_solution"}:
        return "failed"

    support_level = metadata.get("support_level")
    if isinstance(support_level, str) and support_level.strip():
        return support_level.strip()

    if bool(metadata.get("is_placeholder")):
        return "partially_supported"

    if "adapter_limitations" in metadata:
        return "partially_supported" if metadata.get("constraint_families") else "supported"

    feasible = row.get("feasible")
    if isinstance(feasible, bool):
        return "supported" if feasible else "completed_non_feasible"
    if str(feasible).strip().casefold() in {"true", "1", "yes"}:
        return "supported"
    return "completed_non_feasible"


def _parse_metadata(value: object) -> dict[str, Any]:
    """Parse serialized solver metadata from a benchmark row."""

    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _order_full_benchmark_columns(table: pd.DataFrame) -> pd.DataFrame:
    """Keep the most important full benchmark fields near the front."""

    preferred_columns = [
        "instance_name",
        "solver_name",
        "solver_registry_name",
        "objective_value",
        "objective_sense",
        "objective_value_valid",
        "runtime_seconds",
        "feasible",
        "solver_support_status",
        "scoring_status",
        "modeling_scope",
        "scoring_notes",
        "status",
        "random_seed",
        "configured_time_limit_seconds",
    ]
    remaining_columns = [column for column in table.columns if column not in preferred_columns]
    return table.loc[:, [column for column in preferred_columns if column in table.columns] + remaining_columns]


if __name__ == "__main__":
    raise SystemExit(main())
