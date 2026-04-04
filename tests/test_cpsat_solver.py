"""Tests for the first CP-SAT solver skeleton."""

from __future__ import annotations

import pytest

pytest.importorskip("ortools")

from src.parsers import InstanceSummary, Slot, Team, TournamentMetadata
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
