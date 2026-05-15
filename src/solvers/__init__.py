"""Scheduling solver implementations."""

from src.solvers.base import Solver, SolverResult
from src.solvers.random_baseline import RandomBaselineSolver
from src.solvers.registry import (
    SolverPortfolioMetadata,
    available_solvers,
    get_solver,
    get_solver_metadata,
    solver_portfolio_metadata,
)
from src.solvers.simulated_annealing_solver import SimulatedAnnealingSolver
from src.solvers.timefold_solver import TimefoldSolver

__all__ = [
    "RandomBaselineSolver",
    "SimulatedAnnealingSolver",
    "Solver",
    "SolverPortfolioMetadata",
    "SolverResult",
    "TimefoldSolver",
    "available_solvers",
    "get_solver",
    "get_solver_metadata",
    "solver_portfolio_metadata",
]

try:
    from src.solvers.cpsat_solver import CPSatSolver
except ModuleNotFoundError as exc:
    if not exc.name or not exc.name.startswith("ortools"):
        raise
else:
    __all__.append("CPSatSolver")
