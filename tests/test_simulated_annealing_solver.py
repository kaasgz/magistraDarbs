# Tests for the simulated annealing baseline solver.

from dataclasses import dataclass, field

from src.solvers.simulated_annealing_solver import SimulatedAnnealingSolver


@dataclass(slots=True)
class _Metadata:
    name: str | None = None
    source_path: str | None = None


@dataclass(slots=True)
class _Team:
    identifier: str | None = None
    name: str | None = None


@dataclass(slots=True)
class _Slot:
    identifier: str | None = None
    name: str | None = None


@dataclass(slots=True)
class _Instance:
    metadata: _Metadata
    teams: list[_Team] = field(default_factory=list)
    slots: list[_Slot] = field(default_factory=list)
    team_count: int = 0
    slot_count: int = 0
    constraint_count: int = 0


def test_simulated_annealing_solver_returns_structured_result() -> None:

    # The annealing solver should return a standardized solver result.
    instance = _Instance(
        metadata=_Metadata(name="Annealing4"),
        teams=[
            _Team(identifier="A"),
            _Team(identifier="B"),
            _Team(identifier="C"),
            _Team(identifier="D"),
        ],
        slots=[
            _Slot(identifier="R1"),
            _Slot(identifier="R2"),
            _Slot(identifier="R3"),
        ],
        team_count=4,
        slot_count=3,
        constraint_count=0,
    )
    solver = SimulatedAnnealingSolver(max_iterations=500)

    result = solver.solve(instance, time_limit_seconds=1, random_seed=7)

    assert result.solver_name == "simulated_annealing_baseline"
    assert result.instance_name == "Annealing4"
    assert result.objective_value is not None
    assert result.runtime_seconds >= 0.0
    assert result.status in {"FEASIBLE", "APPROXIMATE"}
    assert result.metadata["algorithm"] == "simulated_annealing"
    assert result.metadata["num_matches"] == 6
    assert len(result.metadata["schedule"]) == 6


def test_simulated_annealing_solver_is_reproducible_for_fixed_seed() -> None:

    # The best objective should be stable for a fixed seed and instance.
    instance = _Instance(
        metadata=_Metadata(name="ReproducibleAnnealing"),
        team_count=4,
        slot_count=3,
        constraint_count=0,
    )
    solver = SimulatedAnnealingSolver(max_iterations=500)

    first = solver.solve(instance, time_limit_seconds=1, random_seed=11)
    second = solver.solve(instance, time_limit_seconds=1, random_seed=11)

    assert first.objective_value == second.objective_value
    assert first.metadata["team_conflict_penalty"] == second.metadata["team_conflict_penalty"]
    assert first.metadata["used_slots"] == second.metadata["used_slots"]


def test_simulated_annealing_solver_marks_conflicted_small_slot_case_as_approximate() -> None:

    # Too few slots should typically retain conflict penalties in version 1.
    instance = _Instance(
        metadata=_Metadata(name="TooFewSlotsAnnealing"),
        team_count=4,
        slot_count=2,
        constraint_count=0,
    )
    solver = SimulatedAnnealingSolver(max_iterations=500)

    result = solver.solve(instance, time_limit_seconds=1, random_seed=5)

    assert result.feasible is False
    assert result.status == "APPROXIMATE"
    assert result.metadata["team_conflict_penalty"] > 0
