"""Tests for the first CP-SAT solver skeleton."""

from __future__ import annotations

import pytest

pytest.importorskip("ortools")

from src.parsers import Constraint, InstanceSummary, Slot, Team, TournamentMetadata
from src.solvers.cpsat_solver import CPSatSolver


def test_cpsat_solver_builds_feasible_round_robin_schedule() -> None:
    """The minimal solver should schedule each pair exactly once."""

    instance = InstanceSummary(
        metadata=TournamentMetadata(name="RoundRobin4"),
        teams=[
            Team(identifier="A"),
            Team(identifier="B"),
            Team(identifier="C"),
            Team(identifier="D"),
        ],
        slots=[
            Slot(identifier="R1"),
            Slot(identifier="R2"),
            Slot(identifier="R3"),
        ],
        team_count=4,
        slot_count=3,
        constraint_count=0,
    )

    result = CPSatSolver().solve(instance, time_limit_seconds=5, random_seed=7)

    assert result.feasible is True
    assert result.status in {"OPTIMAL", "FEASIBLE"}
    assert result.objective_value == pytest.approx(3.0)

    schedule = result.metadata["schedule"]
    assert len(schedule) == 6

    unique_pairs = {
        tuple(sorted((entry["team_1"], entry["team_2"])))
        for entry in schedule
    }
    assert len(unique_pairs) == 6

    teams_by_slot: dict[str, list[str]] = {}
    for entry in schedule:
        teams_by_slot.setdefault(entry["slot"], []).extend([entry["team_1"], entry["team_2"]])

    assert set(teams_by_slot) == {"R1", "R2", "R3"}
    for teams in teams_by_slot.values():
        assert len(teams) == len(set(teams))


def test_cpsat_solver_reports_infeasible_when_slots_are_insufficient() -> None:
    """Too few slots should produce a structured infeasible result."""

    instance = InstanceSummary(
        metadata=TournamentMetadata(name="TooFewSlots"),
        team_count=4,
        slot_count=2,
        constraint_count=0,
    )

    result = CPSatSolver().solve(instance, time_limit_seconds=5, random_seed=7)

    assert result.feasible is False
    assert result.status == "INFEASIBLE"
    assert result.objective_value is None
    assert result.metadata["schedule"] == []
    assert result.metadata["minimum_required_slots"] == 3


def test_cpsat_solver_supports_double_round_robin_with_explicit_legs() -> None:
    """Double round robin mode should schedule both home/away legs for each pair."""

    instance = InstanceSummary(
        metadata=TournamentMetadata(name="DoubleRoundRobin4", round_robin_mode="double"),
        teams=[
            Team(identifier="A"),
            Team(identifier="B"),
            Team(identifier="C"),
            Team(identifier="D"),
        ],
        slots=[
            Slot(identifier="R1"),
            Slot(identifier="R2"),
            Slot(identifier="R3"),
            Slot(identifier="R4"),
            Slot(identifier="R5"),
            Slot(identifier="R6"),
        ],
        team_count=4,
        slot_count=6,
        constraint_count=0,
    )

    result = CPSatSolver().solve(instance, time_limit_seconds=5, random_seed=7)

    assert result.feasible is True
    assert result.status in {"OPTIMAL", "FEASIBLE"}
    assert result.objective_value == pytest.approx(6.0)
    assert result.metadata["round_robin_mode"] == "double"
    assert result.metadata["support_level"] == "supported"
    assert result.metadata["unsupported_constraint_families"] == []

    schedule = result.metadata["schedule"]
    assert len(schedule) == 12

    oriented_pairs = {
        (entry["home_team"], entry["away_team"])
        for entry in schedule
    }
    assert len(oriented_pairs) == 12

    pair_leg_counts: dict[tuple[str, str], set[int]] = {}
    for entry in schedule:
        unordered_pair = tuple(sorted((entry["home_team"], entry["away_team"])))
        pair_leg_counts.setdefault(unordered_pair, set()).add(int(entry["leg"]))

    assert len(pair_leg_counts) == 6
    assert all(legs == {1, 2} for legs in pair_leg_counts.values())


def test_cpsat_solver_reports_partial_support_when_constraints_are_declared() -> None:
    """Declared RobinX constraint families should be recorded as unsupported, not ignored silently."""

    instance = InstanceSummary(
        metadata=TournamentMetadata(name="ConstrainedRoundRobin", round_robin_mode="double"),
        teams=[
            Team(identifier="A"),
            Team(identifier="B"),
            Team(identifier="C"),
            Team(identifier="D"),
        ],
        slots=[
            Slot(identifier="R1"),
            Slot(identifier="R2"),
            Slot(identifier="R3"),
            Slot(identifier="R4"),
            Slot(identifier="R5"),
            Slot(identifier="R6"),
        ],
        constraints=[
            Constraint(category="Capacity", tag="HomeCapacity", type_name="Hard"),
            Constraint(category="Break", tag="HomeAway", type_name="Soft"),
        ],
        team_count=4,
        slot_count=6,
        constraint_count=2,
    )

    result = CPSatSolver().solve(instance, time_limit_seconds=5, random_seed=7)

    assert result.feasible is True
    assert result.metadata["support_level"] == "partially_supported"
    assert result.metadata["declared_constraint_families"] == [
        "Break",
        "Capacity",
        "Hard",
        "HomeAway",
        "HomeCapacity",
        "Soft",
    ]
    assert result.metadata["unsupported_constraint_families"] == [
        "Break",
        "Capacity",
        "Hard",
        "HomeAway",
        "HomeCapacity",
        "Soft",
    ]
    assert any(
        "not yet enforced directly" in note
        for note in result.metadata["support_notes"]
    )


def test_cpsat_solver_double_round_robin_requires_more_slots() -> None:
    """Double round robin should report infeasible when fewer than the required slots are available."""

    instance = InstanceSummary(
        metadata=TournamentMetadata(name="TooFewSlotsDouble", round_robin_mode="double"),
        team_count=4,
        slot_count=5,
        constraint_count=0,
    )

    result = CPSatSolver().solve(instance, time_limit_seconds=5, random_seed=7)

    assert result.feasible is False
    assert result.status == "INFEASIBLE"
    assert result.objective_value is None
    assert result.metadata["minimum_required_slots"] == 6
    assert result.metadata["round_robin_mode"] == "double"
