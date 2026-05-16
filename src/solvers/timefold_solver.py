# External Timefold solver integration built on the adapter layer.

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Sequence

from src.solvers.base import Solver, SolverResult
from src.solvers.timefold_adapter import (
    TimefoldProblem,
    TimefoldUnsupportedInstanceError,
    TimefoldInvalidSolutionError,
    build_timefold_problem,
    convert_problem_to_timefold_input,
    convert_timefold_solution,
    describe_timefold_adapter_limitations,
    schedule_to_solver_metadata,
)


class TimefoldSolver(Solver):

    # Call a Timefold-based external executable through the adapter layer.
    def __init__(
        self,
        solver_name: str = "timefold",
        executable_path: str | Path | None = None,
        time_limit_seconds: int | None = None,
        command_arguments: Sequence[str] | None = None,
        working_directory: str | Path | None = None,
        timeout_buffer_seconds: int = 5,
    ) -> None:

        # Initialize the external solver wrapper.
        self.solver_name = solver_name
        self.executable_path = str(executable_path).strip() if executable_path is not None else None
        self.configured_time_limit_seconds = (
            max(0, int(time_limit_seconds)) if time_limit_seconds is not None else None
        )
        self.command_arguments = tuple(str(argument) for argument in (command_arguments or ()))
        self.working_directory = Path(working_directory) if working_directory is not None else None
        self.timeout_buffer_seconds = max(0, int(timeout_buffer_seconds))

    def solve(
        self,
        instance: object,
        time_limit_seconds: int = 60,
        random_seed: int = 42,
    ) -> SolverResult:

        # Export the instance, run the external adapter, and normalize output.
        start_time = time.perf_counter()
        problem = build_timefold_problem(instance)
        effective_time_limit_seconds = self._effective_time_limit_seconds(time_limit_seconds)

        if len(problem.teams) <= 1:
            runtime_seconds = time.perf_counter() - start_time
            support_status = _timefold_support_status(problem)
            return SolverResult(
                solver_name=self.solver_name,
                instance_name=problem.instance_name,
                objective_value=0.0,
                runtime_seconds=runtime_seconds,
                feasible=True,
                status="TRIVIAL",
                solver_support_status=support_status,
                scoring_status=_timefold_scoring_status(problem, feasible=True),
                modeling_scope=_timefold_modeling_scope(),
                scoring_notes=_timefold_scoring_notes(problem),
                metadata={
                    **self._base_metadata(
                        problem=problem,
                        effective_time_limit_seconds=effective_time_limit_seconds,
                        random_seed=random_seed,
                    ),
                    "schedule": [],
                    "used_slots": 0,
                },
            )

        if not self.executable_path:
            runtime_seconds = time.perf_counter() - start_time
            return _failure_result(
                solver_name=self.solver_name,
                instance_name=problem.instance_name,
                runtime_seconds=runtime_seconds,
                status="NOT_CONFIGURED",
                message="Timefold executable path is not configured.",
                metadata=self._base_metadata(
                    problem=problem,
                    effective_time_limit_seconds=effective_time_limit_seconds,
                    random_seed=random_seed,
                ),
                solver_support_status="not_configured",
                scoring_status="not_configured",
                modeling_scope=_timefold_modeling_scope(),
                scoring_notes=(
                    "Missing external solver executable.",
                    "No objective value is valid for scoring.",
                ),
            )

        adapter_payload = convert_problem_to_timefold_input(
            problem,
            time_limit_seconds=effective_time_limit_seconds,
            random_seed=random_seed,
        )

        with tempfile.TemporaryDirectory(prefix="timefold_solver_") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            input_path = temp_dir / "timefold_input.json"
            output_path = temp_dir / "timefold_output.json"
            input_path.write_text(
                json.dumps(adapter_payload, indent=2, ensure_ascii=True, sort_keys=True),
                encoding="utf-8",
            )
            command = self._build_command(
                input_path=input_path,
                output_path=output_path,
                time_limit_seconds=effective_time_limit_seconds,
                random_seed=random_seed,
            )

            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    cwd=str(self.working_directory) if self.working_directory is not None else None,
                    text=True,
                    timeout=max(1, effective_time_limit_seconds) + self.timeout_buffer_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                runtime_seconds = time.perf_counter() - start_time
                metadata = self._base_metadata(
                    problem=problem,
                    effective_time_limit_seconds=effective_time_limit_seconds,
                    random_seed=random_seed,
                )
                metadata.update(
                    {
                        "command": command,
                        "stdout": _truncate_text(exc.stdout),
                        "stderr": _truncate_text(exc.stderr),
                    }
                )
                return _failure_result(
                    solver_name=self.solver_name,
                    instance_name=problem.instance_name,
                    runtime_seconds=runtime_seconds,
                    status="TIMEOUT",
                    message=(
                        "The external Timefold process exceeded the configured timeout "
                        f"of {effective_time_limit_seconds} seconds."
                    ),
                    metadata=metadata,
                    solver_support_status="failed",
                    scoring_status="failed_run",
                    modeling_scope=_timefold_modeling_scope(),
                    scoring_notes=("External Timefold process timed out; no valid objective is available.",),
                )
            except OSError as exc:
                runtime_seconds = time.perf_counter() - start_time
                metadata = self._base_metadata(
                    problem=problem,
                    effective_time_limit_seconds=effective_time_limit_seconds,
                    random_seed=random_seed,
                )
                metadata["command"] = command
                return _failure_result(
                    solver_name=self.solver_name,
                    instance_name=problem.instance_name,
                    runtime_seconds=runtime_seconds,
                    status="EXECUTION_ERROR",
                    message=str(exc),
                    metadata=metadata,
                    solver_support_status="failed",
                    scoring_status="failed_run",
                    modeling_scope=_timefold_modeling_scope(),
                    scoring_notes=("External Timefold process could not be launched.",),
                )

            runtime_seconds = time.perf_counter() - start_time
            stdout_text = completed.stdout or ""
            stderr_text = completed.stderr or ""
            raw_output = _read_adapter_output(output_path=output_path, stdout_text=stdout_text)
            base_metadata = self._base_metadata(
                problem=problem,
                effective_time_limit_seconds=effective_time_limit_seconds,
                random_seed=random_seed,
            )
            base_metadata.update(
                {
                    "command": command,
                    "process_returncode": completed.returncode,
                    "stdout": _truncate_text(stdout_text),
                    "stderr": _truncate_text(stderr_text),
                }
            )

            if raw_output is None:
                return _failure_result(
                    solver_name=self.solver_name,
                    instance_name=problem.instance_name,
                    runtime_seconds=runtime_seconds,
                    status="INVALID_OUTPUT",
                    message=(
                        "The external Timefold process finished without writing an output file "
                        "or emitting parseable stdout."
                    ),
                    metadata=base_metadata,
                    solver_support_status="failed",
                    scoring_status="failed_run",
                    modeling_scope=_timefold_modeling_scope(),
                    scoring_notes=("External Timefold process did not return a parseable solution.",),
                )

            try:
                adapter_result = convert_timefold_solution(problem, raw_output)
            except TimefoldUnsupportedInstanceError as exc:
                return _failure_result(
                    solver_name=self.solver_name,
                    instance_name=problem.instance_name,
                    runtime_seconds=runtime_seconds,
                    status="UNSUPPORTED_INSTANCE",
                    message=str(exc),
                    metadata=base_metadata,
                    solver_support_status="unsupported",
                    scoring_status="unsupported_instance",
                    modeling_scope=_timefold_modeling_scope(),
                    scoring_notes=("External Timefold adapter reported the instance as unsupported.",),
                )
            except TimefoldInvalidSolutionError as exc:
                return _failure_result(
                    solver_name=self.solver_name,
                    instance_name=problem.instance_name,
                    runtime_seconds=runtime_seconds,
                    status="INVALID_SOLUTION",
                    message=str(exc),
                    metadata=base_metadata,
                    solver_support_status="failed",
                    scoring_status="failed_run",
                    modeling_scope=_timefold_modeling_scope(),
                    scoring_notes=("External Timefold adapter returned an invalid solution.",),
                )

            result_metadata = dict(base_metadata)
            result_metadata.update(adapter_result.metadata)
            result_metadata["schedule"] = schedule_to_solver_metadata(adapter_result.schedule)
            result_metadata["used_slots"] = adapter_result.used_slots
            if adapter_result.error_message:
                result_metadata["error"] = adapter_result.error_message

            support_status = _timefold_support_status(problem)
            return SolverResult(
                solver_name=self.solver_name,
                instance_name=problem.instance_name,
                objective_value=adapter_result.objective_value,
                runtime_seconds=adapter_result.runtime_seconds
                if adapter_result.runtime_seconds is not None
                else runtime_seconds,
                feasible=adapter_result.feasible,
                status=adapter_result.status,
                solver_support_status=support_status,
                scoring_status=_timefold_scoring_status(problem, feasible=adapter_result.feasible),
                modeling_scope=_timefold_modeling_scope(),
                scoring_notes=_timefold_scoring_notes(problem),
                metadata=result_metadata,
            )

    def _effective_time_limit_seconds(self, requested_time_limit_seconds: int) -> int:

        # Resolve the effective time limit passed to the external executable.
        if self.configured_time_limit_seconds is not None:
            return self.configured_time_limit_seconds
        return max(0, int(requested_time_limit_seconds))

    def _build_command(
        self,
        *,
        input_path: Path,
        output_path: Path,
        time_limit_seconds: int,
        random_seed: int,
    ) -> list[str]:

        # Build the external adapter command line.
        return [
            self.executable_path or "",
            *self.command_arguments,
            "--input",
            str(input_path),
            "--output",
            str(output_path),
            "--time-limit-seconds",
            str(time_limit_seconds),
            "--random-seed",
            str(random_seed),
        ]

    def _base_metadata(
        self,
        *,
        problem: TimefoldProblem,
        effective_time_limit_seconds: int,
        random_seed: int,
    ) -> dict[str, object]:

        # Build stable solver metadata shared across all outcomes.
        return {
            "exchange_format": "timefold_round_robin_v1",
            "round_robin_mode": problem.round_robin_mode,
            "num_teams": len(problem.teams),
            "num_slots": len(problem.slots),
            "num_matches": len(problem.matches),
            "num_meetings": len(problem.matches),
            "requested_slot_count": problem.requested_slot_count,
            "minimum_required_slots": problem.minimum_required_slots,
            "constraint_families": list(problem.constraint_families),
            "adapter_limitations": describe_timefold_adapter_limitations(),
            "effective_time_limit_seconds": effective_time_limit_seconds,
            "random_seed": random_seed,
            "executable_path": self.executable_path,
            "command_arguments": list(self.command_arguments),
            "source_path": problem.source_path,
        }


def _read_adapter_output(output_path: Path, stdout_text: str) -> str | None:

    # Read adapter output from file first, then fall back to stdout.
    if output_path.exists():
        text = output_path.read_text(encoding="utf-8").strip()
        if text:
            return text

    if stdout_text.strip():
        return stdout_text
    return None


def _failure_result(
    *,
    solver_name: str,
    instance_name: str,
    runtime_seconds: float,
    status: str,
    message: str,
    metadata: dict[str, object],
    solver_support_status: str,
    scoring_status: str,
    modeling_scope: str,
    scoring_notes: tuple[str, ...],
) -> SolverResult:

    # Build one standardized non-feasible solver result.
    failure_metadata = dict(metadata)
    failure_metadata["error"] = message
    return SolverResult(
        solver_name=solver_name,
        instance_name=instance_name,
        objective_value=None,
        runtime_seconds=runtime_seconds,
        feasible=False,
        status=status,
        solver_support_status=solver_support_status,
        scoring_status=scoring_status,
        modeling_scope=modeling_scope,
        scoring_notes=scoring_notes,
        metadata=failure_metadata,
    )


def _timefold_support_status(problem: TimefoldProblem) -> str:

    # Return support status for a configured Timefold adapter run.
    return "partially_supported" if problem.constraint_families else "supported"


def _timefold_scoring_status(problem: TimefoldProblem, *, feasible: bool) -> str:

    # Return the common scoring status for a configured Timefold adapter run.
    if problem.constraint_families:
        return "partially_modeled_run"
    return "supported_feasible_run" if feasible else "supported_infeasible_run"


def _timefold_modeling_scope() -> str:

    # Describe Python-side Timefold integration scope.
    return (
        "external Timefold subprocess adapter; Python exports round-robin data "
        "and declared constraints; exact modeling scope depends on the external executable"
    )


def _timefold_scoring_notes(problem: TimefoldProblem) -> tuple[str, ...]:

    # Return scoring notes for Timefold results.
    notes = [
        "Objective is produced by the external adapter and interpreted as lower-is-better.",
    ]
    if problem.constraint_families:
        notes.append(
            "Declared RobinX / ITC2021 constraint families are exported; enforcement depends on the external model."
        )
    return tuple(notes)


def _truncate_text(value: str | bytes | None, limit: int = 4_000) -> str | None:

    # Trim large stdout or stderr payloads to keep metadata readable.
    if value is None:
        return None
    text = value.decode("utf-8", errors="replace") if isinstance(value, bytes) else str(value)
    stripped = text.strip()
    if not stripped:
        return None
    if len(stripped) <= limit:
        return stripped
    return f"{stripped[:limit]}...[truncated]"
