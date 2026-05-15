"""Registry of available solver implementations."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from src.solvers.base import Solver
from src.solvers.random_baseline import RandomBaselineSolver
from src.solvers.simulated_annealing_solver import SimulatedAnnealingSolver
from src.solvers.timefold_solver import TimefoldSolver


SolverFactory = Callable[..., Solver]


@dataclass(frozen=True, slots=True)
class SolverPortfolioMetadata:
    """Thesis-facing interpretation metadata for one registered solver."""

    registry_name: str
    display_name: str
    role: str
    maturity: str
    thesis_scope: str
    objective_interpretation: str
    is_external: bool = False


def get_solver(name: str, **kwargs: object) -> Solver:
    """Create a solver instance by registry name.

    Args:
        name: Registered solver name.
        **kwargs: Keyword arguments forwarded to the solver constructor.

    Returns:
        A configured solver instance.

    Raises:
        KeyError: If the solver name is not registered.
    """

    try:
        factory = SOLVER_REGISTRY[name]
    except KeyError as exc:
        available = ", ".join(available_solvers())
        raise KeyError(f"Unknown solver '{name}'. Available solvers: {available}") from exc
    return factory(**kwargs)


def available_solvers() -> list[str]:
    """Return the registered solver names in a stable order."""

    return sorted(SOLVER_REGISTRY)


def get_solver_metadata(name: str) -> SolverPortfolioMetadata:
    """Return conservative thesis-facing metadata for a registered solver."""

    try:
        return SOLVER_PORTFOLIO_METADATA[name]
    except KeyError as exc:
        available = ", ".join(available_solvers())
        raise KeyError(f"Unknown solver '{name}'. Available solvers: {available}") from exc


def solver_portfolio_metadata() -> list[SolverPortfolioMetadata]:
    """Return interpretation metadata for all registered solvers."""

    return [get_solver_metadata(name) for name in available_solvers()]


def _create_random_baseline(**kwargs: object) -> Solver:
    """Create the random baseline solver."""

    return RandomBaselineSolver(**kwargs)


def _create_cpsat_solver(**kwargs: object) -> Solver:
    """Create the CP-SAT solver lazily to keep the registry easy to extend."""

    from src.solvers.cpsat_solver import CPSatSolver

    return CPSatSolver(**kwargs)


def _create_simulated_annealing_solver(**kwargs: object) -> Solver:
    """Create the simulated annealing baseline solver."""

    return SimulatedAnnealingSolver(**kwargs)


def _create_timefold_solver(**kwargs: object) -> Solver:
    """Create the external Timefold solver wrapper."""

    return TimefoldSolver(**kwargs)


SOLVER_REGISTRY: dict[str, SolverFactory] = {
    "random_baseline": _create_random_baseline,
    "cpsat_solver": _create_cpsat_solver,
    "simulated_annealing_solver": _create_simulated_annealing_solver,
    "timefold": _create_timefold_solver,
}


SOLVER_PORTFOLIO_METADATA: dict[str, SolverPortfolioMetadata] = {
    "random_baseline": SolverPortfolioMetadata(
        registry_name="random_baseline",
        display_name="Random baseline",
        role="diagnostic_baseline",
        maturity="diagnostic_only",
        thesis_scope="Reproducible pipeline baseline; does not construct a timetable.",
        objective_interpretation="Deterministic diagnostic score; not a scheduling objective.",
    ),
    "cpsat_solver": SolverPortfolioMetadata(
        registry_name="cpsat_solver",
        display_name="CP-SAT compact baseline",
        role="compact_optimization_baseline",
        maturity="partial_round_robin_model",
        thesis_scope=(
            "Compact single/double round-robin model with meeting assignment "
            "and at-most-one-match-per-team-per-slot constraints."
        ),
        objective_interpretation=(
            "Comparable only inside the modeled compact CP-SAT scope; parsed "
            "RobinX / ITC2021 constraint families are recorded but not fully enforced."
        ),
    ),
    "simulated_annealing_solver": SolverPortfolioMetadata(
        registry_name="simulated_annealing_solver",
        display_name="Simulated annealing baseline",
        role="simplified_heuristic_baseline",
        maturity="simplified_single_round_robin_heuristic",
        thesis_scope="Lightweight heuristic over inferred single-round-robin slot assignments.",
        objective_interpretation=(
            "Penalty score for the simplified heuristic model; not a full "
            "ITC2021 objective."
        ),
    ),
    "timefold": SolverPortfolioMetadata(
        registry_name="timefold",
        display_name="Timefold external adapter",
        role="external_integration",
        maturity="configuration_dependent_external_model",
        thesis_scope=(
            "Python-side adapter that exports round-robin data to a configured "
            "external Timefold executable."
        ),
        objective_interpretation=(
            "Objective semantics depend on the external model; without an "
            "executable the solver is intentionally marked not_configured."
        ),
        is_external=True,
    ),
}
