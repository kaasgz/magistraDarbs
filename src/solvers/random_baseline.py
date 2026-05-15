"""Minimal diagnostic baseline for exercising the experiment pipeline."""

from __future__ import annotations

import random
import time
from pathlib import Path

from src.solvers.base import Solver, SolverResult


class RandomBaselineSolver(Solver):
    """Diagnostic control solver that returns a reproducible synthetic score.

    This solver does not construct an actual schedule. It exists so the parsing,
    experiment, and result-collection pipeline can be checked without implying
    that the result is a real scheduling method.
    """

    def __init__(self, solver_name: str = "random_baseline") -> None:
        """Initialize the baseline solver with a stable public name."""

        self.solver_name = solver_name

    def solve(
        self,
        instance: object,
        time_limit_seconds: int = 60,
        random_seed: int = 42,
    ) -> SolverResult:
        """Return a structured diagnostic result for the given instance.

        Args:
            instance: Parsed instance-like object with optional metadata and counts.
            time_limit_seconds: Included in metadata for pipeline compatibility.
            random_seed: Seed controlling the diagnostic objective value.

        Returns:
            A standardized solver result marked as a diagnostic baseline.
        """

        start_time = time.perf_counter()
        instance_name = _extract_instance_name(instance)

        num_teams = _safe_int(getattr(instance, "team_count", 0))
        num_slots = _safe_int(getattr(instance, "slot_count", 0))
        num_constraints = _safe_int(getattr(instance, "constraint_count", 0))

        rng = random.Random(random_seed)
        scale = max(1, num_teams) * max(1, num_slots)

        # This is intentionally synthetic, not a real optimization result.
        objective_value = round(float(scale + num_constraints + rng.random()), 6)
        runtime_seconds = time.perf_counter() - start_time

        return SolverResult(
            solver_name=self.solver_name,
            instance_name=instance_name,
            objective_value=objective_value,
            runtime_seconds=runtime_seconds,
            feasible=True,
            status="placeholder_feasible",
            solver_support_status="partially_supported",
            scoring_status="partially_modeled_run",
            modeling_scope="deterministic diagnostic score; no schedule construction",
            scoring_notes=(
                "Objective is a synthetic diagnostic score used as a pipeline control.",
                "This solver does not construct or validate a RobinX / ITC2021 schedule.",
            ),
            metadata={
                "is_placeholder": True,
                "notes": "Synthetic diagnostic result; not a scheduling objective.",
                "time_limit_seconds": time_limit_seconds,
                "random_seed": random_seed,
                "num_teams": num_teams,
                "num_slots": num_slots,
                "num_constraints": num_constraints,
            },
        )


def _extract_instance_name(instance: object) -> str:
    """Extract a stable instance name from common parsed-instance attributes."""

    metadata = getattr(instance, "metadata", None)
    name_candidates = [
        getattr(metadata, "name", None),
        getattr(instance, "instance_name", None),
        getattr(instance, "name", None),
    ]
    for candidate in name_candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    source_path = getattr(metadata, "source_path", None)
    if isinstance(source_path, str) and source_path.strip():
        return Path(source_path).stem

    return instance.__class__.__name__


def _safe_int(value: object) -> int:
    """Convert a count-like value to a non-negative integer."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(0, value)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0
