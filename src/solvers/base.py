"""Shared interfaces for scheduling solvers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SolverResult:
    """Standardized result returned by all solver implementations."""

    solver_name: str
    instance_name: str
    objective_value: float | None
    runtime_seconds: float
    feasible: bool
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)


class Solver(ABC):
    """Abstract base class for all thesis solver implementations."""

    @abstractmethod
    def solve(
        self,
        instance: object,
        time_limit_seconds: int = 60,
        random_seed: int = 42,
    ) -> SolverResult:
        """Solve one instance and return a standardized solver result.

        Args:
            instance: Parsed instance representation consumed by the solver.
            time_limit_seconds: Solver time limit in seconds.
            random_seed: Random seed used for reproducibility.

        Returns:
            A standardized solver result describing the outcome.
        """

        raise NotImplementedError
