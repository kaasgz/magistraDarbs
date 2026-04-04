"""Scheduling solver implementations."""

from src.solvers.base import Solver, SolverResult
from src.solvers.random_baseline import RandomBaselineSolver
from src.solvers.registry import available_solvers, get_solver
from src.solvers.simulated_annealing_solver import SimulatedAnnealingSolver

__all__ = [
    "RandomBaselineSolver",
    "SimulatedAnnealingSolver",
    "Solver",
    "SolverResult",
    "available_solvers",
    "get_solver",
]

try:
    from src.solvers.cpsat_solver import CPSatSolver
except ModuleNotFoundError as exc:
    if not exc.name or not exc.name.startswith("ortools"):
        raise
else:
    __all__.append("CPSatSolver")
