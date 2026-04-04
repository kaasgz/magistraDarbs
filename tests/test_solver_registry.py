"""Tests for the solver registry."""

import pytest

from src.solvers import available_solvers, get_solver
from src.solvers.cpsat_solver import CPSatSolver
from src.solvers.random_baseline import RandomBaselineSolver
from src.solvers.simulated_annealing_solver import SimulatedAnnealingSolver


def test_available_solvers_lists_registered_names() -> None:
    """The registry should expose the configured solver names."""

    assert available_solvers() == [
        "cpsat_solver",
        "random_baseline",
        "simulated_annealing_solver",
    ]


def test_get_solver_returns_requested_solver_instances() -> None:
    """Registered names should construct the matching solver classes."""

    assert isinstance(get_solver("random_baseline"), RandomBaselineSolver)
    assert isinstance(get_solver("cpsat_solver"), CPSatSolver)
    assert isinstance(
        get_solver("simulated_annealing_solver"),
        SimulatedAnnealingSolver,
    )


def test_get_solver_forwards_constructor_kwargs() -> None:
    """Registry lookup should pass keyword arguments to solver constructors."""

    solver = get_solver("simulated_annealing_solver", max_iterations=123)

    assert isinstance(solver, SimulatedAnnealingSolver)
    assert solver.max_iterations == 123


def test_get_solver_raises_clear_error_for_unknown_name() -> None:
    """Unknown registry names should raise a helpful error."""

    with pytest.raises(KeyError, match="Unknown solver 'missing_solver'"):
        get_solver("missing_solver")
