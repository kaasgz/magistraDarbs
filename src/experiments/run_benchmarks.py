"""Run benchmark experiments across multiple instances and solvers."""

from __future__ import annotations

import argparse
import json
import logging
import time
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from src.experiments.benchmark_validation import (
    BenchmarkValidationError,
    validate_benchmark_results,
)
from src.parsers import load_instance
from src.solvers import available_solvers, get_solver
from src.solvers.base import SolverResult
from src.utils import (
    collect_xml_files,
    default_run_summary_path,
    ensure_parent_directory,
    get_compat_path,
    get_random_seed,
    get_selected_solvers,
    get_time_limit_seconds,
    load_yaml_config,
    register_observed_source_kind,
    resolve_instance_source_kind,
    validate_folder_source_hygiene,
    validate_loaded_instance_source,
    write_run_summary,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("configs/benchmark_config.yaml")
DEFAULT_INSTANCE_FOLDER = Path("data/raw/real")
DEFAULT_OUTPUT_PATH = Path("data/results/benchmark_results.csv")


def run_benchmarks(
    instance_folder: str,
    solver_names: list[str],
    time_limit_seconds: int = 60,
    random_seed: int = 42,
    output_csv: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    config_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    run_summary_path: str | Path | None = None,
) -> Path:
    """Run selected solvers on all XML instances in a folder.

    Args:
        instance_folder: Folder containing RobinX / ITC2021 XML files.
        solver_names: Registry names of solvers to run.
        time_limit_seconds: Per-solver time limit.
        random_seed: Random seed passed to each solver.
        output_csv: Output CSV path for structured benchmark results.
        config_path: Optional YAML config path used for the run.
        config: Optional loaded config snapshot to include in metadata.
        run_summary_path: Optional JSON sidecar path for run metadata.

    Returns:
        Path to the written benchmark results CSV.
    """

    input_path = Path(instance_folder)
    if not input_path.exists():
        raise FileNotFoundError(f"Instance folder does not exist: {input_path}")
    if not input_path.is_dir():
        raise NotADirectoryError(f"Instance path is not a folder: {input_path}")
    if not solver_names:
        raise ValueError("At least one solver name must be provided.")

    selected_solver_names = list(solver_names)
    batch_started_at = _timestamp_now()
    output_path = Path(output_csv)
    summary_path = Path(run_summary_path) if run_summary_path is not None else default_run_summary_path(output_path)

    xml_files = collect_xml_files(input_path)
    expected_source = validate_folder_source_hygiene(input_path, xml_files)
    total_runs = len(xml_files) * len(selected_solver_names)
    LOGGER.info(
        "Found %d XML files and %d solvers (%d total runs).",
        len(xml_files),
        len(selected_solver_names),
        total_runs,
    )

    rows: list[dict[str, object]] = []
    run_index = 0
    skipped_instances: list[dict[str, str]] = []
    observed_source_kinds: set[str] = set()

    for xml_file in xml_files:
        LOGGER.info("Loading instance %s", xml_file)
        try:
            instance = load_instance(str(xml_file))
        except Exception as exc:
            LOGGER.warning(
                "Skipping instance %s due to load failure: %s: %s",
                xml_file,
                type(exc).__name__,
                exc,
            )
            skipped_instances.append(
                {
                    "instance_path": xml_file.as_posix(),
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
            continue

        validate_loaded_instance_source(instance, xml_file, expected_source=expected_source)
        source_kind, _ = resolve_instance_source_kind(
            instance,
            xml_file=xml_file,
            input_folder=input_path,
            expected_source=expected_source,
        )
        observed_source_kinds = register_observed_source_kind(
            observed_source_kinds,
            source_kind,
            input_path=input_path,
        )

        instance_name = _extract_instance_name(instance)
        for solver_registry_name in selected_solver_names:
            run_index += 1
            LOGGER.info(
                "[%d/%d] Running solver '%s' on %s",
                run_index,
                total_runs,
                solver_registry_name,
                instance_name,
            )
            rows.append(
                _run_single_solver(
                    instance=instance,
                    solver_registry_name=solver_registry_name,
                    time_limit_seconds=time_limit_seconds,
                    random_seed=random_seed,
                )
            )

    table = pd.DataFrame(rows, columns=_benchmark_columns())
    if not table.empty:
        table = table.sort_values(
            by=["instance_name", "solver_registry_name", "solver_name", "timestamp"],
            ascending=[True, True, True, True],
            kind="mergesort",
        ).reset_index(drop=True)

    validation_issues = validate_benchmark_results(
        table,
        expected_solver_registry_names=selected_solver_names,
    )
    for issue in validation_issues:
        LOGGER.error("Benchmark validation issue [%s]: %s", issue.code, issue.message)

    ensure_parent_directory(output_path)
    table.to_csv(output_path, index=False)

    write_run_summary(
        summary_path,
        stage_name="benchmark_run",
        config_path=config_path,
        config=config,
        settings={
            "random_seed": random_seed,
            "time_limit_seconds": time_limit_seconds,
            "selected_solvers": list(selected_solver_names),
            "batch_started_at": batch_started_at,
            "input_source_kind": expected_source or "unknown",
        },
        inputs={
            "instance_folder": input_path,
        },
        outputs={
            "benchmark_results_csv": output_path,
            "run_summary": summary_path,
        },
        results=_build_batch_results_summary(
            table=table,
            xml_files=xml_files,
            selected_solver_names=selected_solver_names,
            skipped_instances=skipped_instances,
            validation_issues=validation_issues,
        ),
    )
    LOGGER.info("Saved %d benchmark rows to %s", len(table.index), output_path)
    LOGGER.info("Saved benchmark run summary to %s", summary_path)

    if validation_issues:
        joined_messages = "; ".join(issue.message for issue in validation_issues)
        raise BenchmarkValidationError(joined_messages)

    return output_path


def run_benchmarks_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> Path:
    """Run benchmarks using values loaded from a YAML configuration file."""

    config = load_yaml_config(config_path)
    output_path = get_compat_path(config, ["paths.output_csv"], DEFAULT_OUTPUT_PATH)
    summary_path = get_compat_path(
        config,
        ["paths.run_summary", "paths.run_summary_path"],
        default_run_summary_path(output_path),
    )
    return run_benchmarks(
        instance_folder=str(get_compat_path(config, ["paths.instance_folder"], DEFAULT_INSTANCE_FOLDER)),
        solver_names=get_selected_solvers(config, list(available_solvers())),
        time_limit_seconds=get_time_limit_seconds(config, 60),
        random_seed=get_random_seed(config, 42),
        output_csv=output_path,
        config_path=config_path,
        config=config,
        run_summary_path=summary_path,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for benchmark execution."""

    parser = argparse.ArgumentParser(
        description="Run selected solvers on a folder of XML instances.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the benchmark YAML configuration file.",
    )
    parser.add_argument(
        "instance_folder",
        nargs="?",
        help="Folder containing RobinX / ITC2021 XML instance files.",
    )
    parser.add_argument(
        "solver_names",
        nargs="*",
        help=f"Solver names from the registry. Available: {', '.join(available_solvers())}",
    )
    parser.add_argument(
        "--time-limit-seconds",
        type=int,
        default=None,
        help="Per-solver time limit in seconds.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Random seed passed to each solver.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path. Defaults to data/results/benchmark_results.csv.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run benchmarks from the command line."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = load_yaml_config(args.config)
        resolved_output_path = args.output or get_compat_path(config, ["paths.output_csv"], DEFAULT_OUTPUT_PATH)
        output_path = run_benchmarks(
            instance_folder=args.instance_folder
            or str(get_compat_path(config, ["paths.instance_folder"], DEFAULT_INSTANCE_FOLDER)),
            solver_names=list(args.solver_names)
            or get_selected_solvers(config, list(available_solvers())),
            time_limit_seconds=(
                args.time_limit_seconds
                if args.time_limit_seconds is not None
                else get_time_limit_seconds(config, 60)
            ),
            random_seed=(
                args.random_seed
                if args.random_seed is not None
                else get_random_seed(config, 42)
            ),
            output_csv=resolved_output_path,
            config_path=args.config,
            config=config,
            run_summary_path=get_compat_path(
                config,
                ["paths.run_summary", "paths.run_summary_path"],
                default_run_summary_path(resolved_output_path),
            ),
        )
    except (FileNotFoundError, NotADirectoryError, ValueError, KeyError, BenchmarkValidationError) as exc:
        LOGGER.error("Benchmark run failed: %s", exc)
        return 1

    print(f"Benchmark results saved to {output_path}")
    return 0


def _run_single_solver(
    *,
    instance: object,
    solver_registry_name: str,
    time_limit_seconds: int,
    random_seed: int,
) -> dict[str, object]:
    """Run one solver on one instance and return a result row."""

    instance_name = _extract_instance_name(instance)
    started_at = time.perf_counter()

    try:
        solver = get_solver(solver_registry_name)
        result = solver.solve(
            instance,
            time_limit_seconds=time_limit_seconds,
            random_seed=random_seed,
        )
        error_message = _extract_error_message(result.metadata)
    except Exception as exc:
        runtime_seconds = time.perf_counter() - started_at
        LOGGER.warning(
            "Solver '%s' failed on instance '%s': %s: %s",
            solver_registry_name,
            instance_name,
            type(exc).__name__,
            exc,
        )
        result = SolverResult(
            solver_name=solver_registry_name,
            instance_name=instance_name,
            objective_value=None,
            runtime_seconds=runtime_seconds,
            feasible=False,
            status=f"FAILED:{type(exc).__name__}",
            metadata={"error": str(exc)},
        )
        error_message = str(exc)

    return _result_to_row(
        result=result,
        solver_registry_name=solver_registry_name,
        random_seed=random_seed,
        time_limit_seconds=time_limit_seconds,
        instance=instance,
        timestamp=_timestamp_now(),
        error_message=error_message,
    )


def _result_to_row(
    *,
    result: SolverResult,
    solver_registry_name: str,
    random_seed: int,
    time_limit_seconds: int,
    instance: object,
    timestamp: str,
    error_message: str | None,
) -> dict[str, object]:
    """Convert a solver result into one benchmark table row."""

    return {
        "instance_name": result.instance_name,
        "solver_name": result.solver_name,
        "solver_registry_name": solver_registry_name,
        "objective_value": result.objective_value,
        "runtime_seconds": result.runtime_seconds,
        "feasible": result.feasible,
        "status": result.status,
        "random_seed": random_seed,
        "configured_time_limit_seconds": time_limit_seconds,
        "timestamp": timestamp,
        "is_synthetic": _extract_is_synthetic(instance),
        "instance_source_path": _extract_instance_source_path(instance),
        "solver_metadata_json": _serialize_metadata(result.metadata),
        "error_message": error_message,
    }


def _build_batch_results_summary(
    *,
    table: pd.DataFrame,
    xml_files: list[Path],
    selected_solver_names: list[str],
    skipped_instances: list[dict[str, str]],
    validation_issues: list[object],
) -> dict[str, object]:
    """Build benchmark batch summary metrics for the run summary artifact."""

    status_counts: dict[str, int] = {}
    failed_run_count = 0
    feasible_run_count = 0
    aggregate_runtime_seconds = 0.0
    rows_per_solver: dict[str, int] = {}

    if not table.empty:
        status_counts = {
            str(key): int(value)
            for key, value in table["status"].astype("string").value_counts().to_dict().items()
        }
        failed_run_count = int(table["status"].astype("string").str.startswith("FAILED", na=False).sum())
        feasible_run_count = int(table["feasible"].astype(bool).sum())
        aggregate_runtime_seconds = round(
            float(pd.to_numeric(table["runtime_seconds"], errors="coerce").fillna(0.0).sum()),
            6,
        )
        rows_per_solver = {
            str(key): int(value)
            for key, value in table["solver_registry_name"].astype("string").value_counts().to_dict().items()
        }

    return {
        "num_input_xml_files": len(xml_files),
        "num_instances_loaded": len(xml_files) - len(skipped_instances),
        "num_instances_skipped": len(skipped_instances),
        "num_solvers": len(selected_solver_names),
        "selected_solvers": list(selected_solver_names),
        "num_requested_runs": len(xml_files) * len(selected_solver_names),
        "num_benchmark_rows": len(table.index),
        "num_completed_solver_runs": len(table.index) - failed_run_count,
        "num_failed_solver_runs": failed_run_count,
        "num_feasible_runs": feasible_run_count,
        "num_non_feasible_runs": len(table.index) - feasible_run_count,
        "aggregate_runtime_seconds": aggregate_runtime_seconds,
        "rows_per_solver": rows_per_solver,
        "status_counts": status_counts,
        "instance_load_failures": skipped_instances,
        "validation_issue_count": len(validation_issues),
        "validation_issues": [
            {
                "code": getattr(issue, "code", "validation_issue"),
                "message": getattr(issue, "message", str(issue)),
            }
            for issue in validation_issues
        ],
    }


def _benchmark_columns() -> list[str]:
    """Return the stable benchmark CSV column order."""

    return [
        "instance_name",
        "solver_name",
        "solver_registry_name",
        "objective_value",
        "runtime_seconds",
        "feasible",
        "status",
        "random_seed",
        "configured_time_limit_seconds",
        "timestamp",
        "is_synthetic",
        "instance_source_path",
        "solver_metadata_json",
        "error_message",
    ]


def _extract_instance_name(instance: object) -> str:
    """Extract a readable instance name from a parsed instance-like object."""

    metadata = getattr(instance, "metadata", None)
    name = getattr(metadata, "name", None)
    if isinstance(name, str) and name.strip():
        return name.strip()
    return instance.__class__.__name__


def _extract_is_synthetic(instance: object) -> bool:
    """Extract whether the instance is marked as synthetic."""

    metadata = getattr(instance, "metadata", None)
    synthetic = getattr(metadata, "synthetic", None)
    return bool(synthetic) if isinstance(synthetic, bool) else False


def _extract_instance_source_path(instance: object) -> str | None:
    """Extract the original XML path when available."""

    metadata = getattr(instance, "metadata", None)
    source_path = getattr(metadata, "source_path", None)
    if isinstance(source_path, str) and source_path.strip():
        return source_path.strip()
    return None


def _extract_error_message(metadata: dict[str, Any]) -> str | None:
    """Extract a readable error string from solver metadata when present."""

    value = metadata.get("error")
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _serialize_metadata(metadata: dict[str, Any]) -> str:
    """Serialize solver metadata into one compact JSON string."""

    if not metadata:
        return "{}"
    return json.dumps(metadata, ensure_ascii=True, sort_keys=True, default=str)


def _timestamp_now() -> str:
    """Return the current timestamp as an ISO string."""

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


if __name__ == "__main__":
    raise SystemExit(main())
