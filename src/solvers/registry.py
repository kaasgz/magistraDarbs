"""Registry of available solver implementations."""

from __future__ import annotations

from collections.abc import Callable

from src.solvers.base import Solver
from src.solvers.random_baseline import RandomBaselineSolver
from src.solvers.simulated_annealing_solver import SimulatedAnnealingSolver


SolverFactory = Callable[..., Solver]


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


SOLVER_REGISTRY: dict[str, SolverFactory] = {
    "random_baseline": _create_random_baseline,
    "cpsat_solver": _create_cpsat_solver,
    "simulated_annealing_solver": _create_simulated_annealing_solver,
}
