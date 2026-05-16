# Tests for the Timefold adapter layer.

from __future__ import annotations

from src.parsers.robinx_parser import Constraint, InstanceSummary, Slot, Team, TournamentMetadata
from src.solvers.timefold_adapter import (
    TimefoldInvalidSolutionError,
    build_timefold_problem,
    convert_instance_to_timefold_input,
    convert_timefold_solution,
    describe_timefold_adapter_limitations,
    schedule_to_solver_metadata,
)


def test_convert_instance_to_timefold_input_exports_simple_round_robin_structure() -> None:

    # A parsed instance should convert into the documented Timefold payload shape.
    payload = convert_instance_to_timefold_input(
        _build_four_team_instance(),
        time_limit_seconds=30,
        random_seed=7,
    )

    assert payload["schema"] == "timefold_round_robin_v1"
    assert payload["config"]["run"] == {
        "name": "ExampleLeague",
        "timeLimitSeconds": 30,
        "randomSeed": 7,
    }
    assert len(payload["modelInput"]["teams"]) == 4
    assert len(payload["modelInput"]["slots"]) == 3
    assert len(payload["modelInput"]["matches"]) == 6
    assert len(payload["modelInput"]["meetings"]) == 6
    assert payload["modelInput"]["constraints"] == [{"family": "Capacity"}]
    assert payload["modelInput"]["metadata"]["ignoredConstraintFamilies"] == ["Capacity"]
    assert payload["modelInput"]["metadata"]["adapterLimitations"] == describe_timefold_adapter_limitations()


def test_convert_timefold_solution_builds_internal_schedule_for_simple_instance() -> None:

    # A valid Timefold solution should map back to the internal schedule format.
    problem = build_timefold_problem(_build_four_team_instance())
    solution = convert_timefold_solution(
        problem,
        {
            "status": "SOLVED",
            "feasible": True,
            "objectiveValue": 3.0,
            "runtimeSeconds": 0.5,
            "schedule": [
                {"matchId": "M1", "slotId": "S1"},
                {"matchId": "M6", "slotId": "S1"},
                {"matchId": "M2", "slotId": "S2"},
                {"matchId": "M5", "slotId": "S2"},
                {"matchId": "M3", "slotId": "S3"},
                {"matchId": "M4", "slotId": "S3"},
            ],
            "metadata": {"adapter": "unit-test"},
        },
    )

    assert solution.instance_name == "ExampleLeague"
    assert solution.feasible is True
    assert solution.status == "SOLVED"
    assert solution.objective_value == 3.0
    assert solution.used_slots == 3
    assert solution.metadata["adapter"] == "unit-test"
    assert len(solution.schedule) == 6

    metadata_schedule = schedule_to_solver_metadata(solution.schedule)
    assert metadata_schedule[0] == {
        "meeting_id": "M1",
        "slot_index": 0,
        "slot": "Round 1",
        "slot_id": "S1",
        "leg": 1,
        "home_team": "Team 1",
        "away_team": "Team 2",
        "team_1": "Team 1",
        "team_2": "Team 2",
    }


def test_convert_timefold_solution_rejects_conflicting_slot_assignment() -> None:

    # Conflicting schedules should fail validation in the adapter layer.
    problem = build_timefold_problem(_build_four_team_instance())

    try:
        convert_timefold_solution(
            problem,
            {
                "status": "SOLVED",
                "feasible": True,
                "schedule": [
                    {"matchId": "M1", "slotId": "S1"},
                    {"matchId": "M2", "slotId": "S1"},
                    {"matchId": "M3", "slotId": "S2"},
                    {"matchId": "M4", "slotId": "S2"},
                    {"matchId": "M5", "slotId": "S3"},
                    {"matchId": "M6", "slotId": "S3"},
                ],
            },
        )
    except TimefoldInvalidSolutionError as exc:
        assert "team conflict" in str(exc).lower()
    else:
        raise AssertionError("Expected TimefoldInvalidSolutionError for conflicting schedule.")


def _build_four_team_instance() -> InstanceSummary:

    # Build a simple single round-robin parsed instance for adapter tests.
    return InstanceSummary(
        metadata=TournamentMetadata(
            name="ExampleLeague",
            source_path="tests/fixtures/example_league.xml",
            round_robin_mode="single",
        ),
        teams=[
            Team(identifier="T1", name="Team 1"),
            Team(identifier="T2", name="Team 2"),
            Team(identifier="T3", name="Team 3"),
            Team(identifier="T4", name="Team 4"),
        ],
        slots=[
            Slot(identifier="S1", name="Round 1"),
            Slot(identifier="S2", name="Round 2"),
            Slot(identifier="S3", name="Round 3"),
        ],
        constraints=[
            Constraint(category="Capacity"),
        ],
        team_count=4,
        slot_count=3,
        constraint_count=1,
    )
