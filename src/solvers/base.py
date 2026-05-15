"""Shared interfaces for scheduling solvers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal


SolverSupportStatus = Literal[
    "supported",
    "partially_supported",
    "unsupported",
    "not_configured",
    "failed",
]
ScoringStatus = Literal[
    "supported_feasible_run",
    "supported_infeasible_run",
    "partially_modeled_run",
    "unsupported_instance",
    "failed_run",
    "not_configured",
]
ObjectiveSense = Literal["lower_is_better"]


@dataclass(slots=True)
class SolverResult:
    """Standardized result returned by all solver implementations.

    ``objective_value`` is minimized throughout this repository. The scoring
    fields make clear whether that value is a fully comparable result,
    a simplified-model score, or not a valid score for selector/evaluation use.
    """

    solver_name: str
    instance_name: str
    objective_value: float | None
    runtime_seconds: float
    feasible: bool
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)
    solver_support_status: SolverSupportStatus | str = "supported"
    scoring_status: ScoringStatus | str | None = None
    modeling_scope: str = "not_specified"
    scoring_notes: tuple[str, ...] = field(default_factory=tuple)
    objective_sense: ObjectiveSense = "lower_is_better"

    def __post_init__(self) -> None:
        """Normalize optional scoring fields for older constructor call sites."""

        if self.scoring_status is None:
            self.scoring_status = (
                "supported_feasible_run" if self.feasible else "supported_infeasible_run"
            )
        if isinstance(self.scoring_notes, str):
            self.scoring_notes = (self.scoring_notes,)
        else:
            self.scoring_notes = tuple(str(note) for note in self.scoring_notes)


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
