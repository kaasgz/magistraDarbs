# Tests for the placeholder random baseline solver.

from src.parsers import InstanceSummary, TournamentMetadata
from src.solvers import RandomBaselineSolver


def test_random_baseline_returns_structured_placeholder_result() -> None:

    # The baseline solver should return the shared result structure.
    instance = InstanceSummary(
        metadata=TournamentMetadata(name="SampleInstance", source_path="data/raw/sample.xml"),
        team_count=4,
        slot_count=6,
        constraint_count=10,
    )
    solver = RandomBaselineSolver()

    result = solver.solve(instance, time_limit_seconds=30, random_seed=7)

    assert result.solver_name == "random_baseline"
    assert result.instance_name == "SampleInstance"
    assert result.objective_value is not None
    assert result.runtime_seconds >= 0.0
    assert result.feasible is True
    assert result.status == "placeholder_feasible"
    assert result.metadata["is_placeholder"] is True
    assert result.metadata["time_limit_seconds"] == 30
    assert result.metadata["random_seed"] == 7


def test_random_baseline_is_reproducible_for_same_seed() -> None:

    # The synthetic objective should be stable for a fixed seed and instance.
    instance = InstanceSummary(
        metadata=TournamentMetadata(name="ReproducibleInstance"),
        team_count=3,
        slot_count=5,
        constraint_count=8,
    )
    solver = RandomBaselineSolver()

    first = solver.solve(instance, random_seed=11)
    second = solver.solve(instance, random_seed=11)

    assert first.objective_value == second.objective_value
    assert first.instance_name == second.instance_name
