# Tests for the shared solver interface.

from src.solvers import Solver, SolverResult


class DummySolver(Solver):

    # Minimal solver used to test the abstract interface.
    def solve(
        self,
        instance: object,
        time_limit_seconds: int = 60,
        random_seed: int = 42,
    ) -> SolverResult:
        return SolverResult(
            solver_name="dummy",
            instance_name=str(instance),
            objective_value=1.0,
            runtime_seconds=0.01,
            feasible=True,
            status="ok",
            metadata={
                "time_limit_seconds": time_limit_seconds,
                "random_seed": random_seed,
            },
        )


def test_solver_result_uses_independent_metadata_dicts() -> None:

    # Solver results should not share mutable metadata by default.
    first = SolverResult(
        solver_name="solver-a",
        instance_name="instance-a",
        objective_value=None,
        runtime_seconds=0.0,
        feasible=False,
        status="not_run",
    )
    second = SolverResult(
        solver_name="solver-b",
        instance_name="instance-b",
        objective_value=None,
        runtime_seconds=0.0,
        feasible=False,
        status="not_run",
    )

    first.metadata["note"] = "first"

    assert first.metadata == {"note": "first"}
    assert second.metadata == {}


def test_solver_interface_returns_standardized_result() -> None:

    # Concrete solvers should return the shared result format.
    solver = DummySolver()

    result = solver.solve("sample-instance", time_limit_seconds=30, random_seed=7)

    assert result.solver_name == "dummy"
    assert result.instance_name == "sample-instance"
    assert result.objective_value == 1.0
    assert result.runtime_seconds == 0.01
    assert result.feasible is True
    assert result.status == "ok"
    assert result.metadata == {"time_limit_seconds": 30, "random_seed": 7}
