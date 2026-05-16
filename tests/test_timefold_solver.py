# Tests for the external Timefold solver wrapper.

from __future__ import annotations

import sys
from pathlib import Path

from src.parsers.robinx_parser import InstanceSummary, Slot, Team, TournamentMetadata
from src.solvers.timefold_solver import TimefoldSolver


def test_timefold_solver_reads_json_output_from_adapter(tmp_path: Path) -> None:

    # A valid JSON payload should be normalized into the shared solver result.
    adapter_path = _write_fake_adapter(
        tmp_path,
        "\n".join(
            [
                "result = {",
                '    "status": "SOLVED",',
                '    "feasible": True,',
                '    "objectiveValue": 1.0,',
                '    "runtimeSeconds": 0.25,',
                '    "schedule": [{"meetingId": meetings[0]["id"], "slotId": slots[0]["id"]}],',
                '    "metadata": {"adapter": "fake-json"},',
                "}",
                'output_path.write_text(json.dumps(result), encoding="utf-8")',
            ]
        ),
    )
    solver = TimefoldSolver(
        executable_path=sys.executable,
        command_arguments=[str(adapter_path)],
        timeout_buffer_seconds=0,
    )

    result = solver.solve(_build_single_match_instance(), time_limit_seconds=3, random_seed=7)

    assert result.solver_name == "timefold"
    assert result.feasible is True
    assert result.status == "SOLVED"
    assert result.objective_value == 1.0
    assert result.metadata["adapter"] == "fake-json"
    assert result.metadata["used_slots"] == 1
    assert result.metadata["effective_time_limit_seconds"] == 3
    assert result.metadata["schedule"] == [
        {
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
    ]


def test_timefold_solver_reads_text_output_and_derives_objective(tmp_path: Path) -> None:

    # A line-based adapter output should also be accepted.
    adapter_path = _write_fake_adapter(
        tmp_path,
        "\n".join(
            [
                "output_path.write_text(",
                '    "\\n".join(',
                "        [",
                '            "status=SOLVED",',
                '            "feasible=true",',
                '            "runtime_seconds=0.2",',
                '            f"assignment meeting_id={meetings[0][\'id\']} slot_id={slots[0][\'id\']}",',
                "        ]",
                "    ),",
                '    encoding="utf-8",',
                ")",
            ]
        ),
    )
    solver = TimefoldSolver(
        executable_path=sys.executable,
        command_arguments=[str(adapter_path)],
        timeout_buffer_seconds=0,
    )

    result = solver.solve(_build_single_match_instance(), time_limit_seconds=2, random_seed=11)

    assert result.feasible is True
    assert result.status == "SOLVED"
    assert result.objective_value == 1.0
    assert result.metadata["objective_source"] == "derived_used_slots"


def test_timefold_solver_handles_timeout_cleanly(tmp_path: Path) -> None:

    # A hanging adapter should be reported as a timeout instead of crashing.
    adapter_path = _write_fake_adapter(
        tmp_path,
        "time.sleep(int(args.time_limit_seconds) + 2)",
    )
    solver = TimefoldSolver(
        executable_path=sys.executable,
        command_arguments=[str(adapter_path)],
        timeout_buffer_seconds=0,
    )

    result = solver.solve(_build_single_match_instance(), time_limit_seconds=1, random_seed=5)

    assert result.feasible is False
    assert result.status == "TIMEOUT"
    assert result.objective_value is None
    assert "timeout" in str(result.metadata["error"]).lower()


def test_timefold_solver_marks_invalid_schedule_output(tmp_path: Path) -> None:

    # A feasible-looking but invalid schedule should be rejected cleanly.
    adapter_path = _write_fake_adapter(
        tmp_path,
        "\n".join(
            [
                "result = {",
                '    "status": "SOLVED",',
                '    "feasible": True,',
                '    "schedule": [],',
                "}",
                'output_path.write_text(json.dumps(result), encoding="utf-8")',
            ]
        ),
    )
    solver = TimefoldSolver(
        executable_path=sys.executable,
        command_arguments=[str(adapter_path)],
        timeout_buffer_seconds=0,
    )

    result = solver.solve(_build_single_match_instance(), time_limit_seconds=2, random_seed=13)

    assert result.feasible is False
    assert result.status == "INVALID_SOLUTION"
    assert "schedule" in str(result.metadata["error"]).lower()


def test_timefold_solver_reports_unsupported_instance(tmp_path: Path) -> None:

    # An adapter-level unsupported-instance response should map cleanly.
    adapter_path = _write_fake_adapter(
        tmp_path,
        "\n".join(
            [
                "result = {",
                '    "status": "UNSUPPORTED_INSTANCE",',
                '    "feasible": False,',
                '    "error": "adapter does not support this instance",',
                "}",
                'output_path.write_text(json.dumps(result), encoding="utf-8")',
            ]
        ),
    )
    solver = TimefoldSolver(
        executable_path=sys.executable,
        command_arguments=[str(adapter_path)],
        timeout_buffer_seconds=0,
    )

    result = solver.solve(_build_single_match_instance(), time_limit_seconds=2, random_seed=17)

    assert result.feasible is False
    assert result.status == "UNSUPPORTED_INSTANCE"
    assert result.metadata["error"] == "adapter does not support this instance"


def _build_single_match_instance() -> InstanceSummary:

    # Build a tiny parsed instance with exactly one required meeting.
    return InstanceSummary(
        metadata=TournamentMetadata(
            name="TinyInstance",
            source_path="tests/fixtures/tiny_instance.xml",
            round_robin_mode="single",
        ),
        teams=[
            Team(identifier="T1", name="Team 1"),
            Team(identifier="T2", name="Team 2"),
        ],
        slots=[
            Slot(identifier="S1", name="Round 1"),
        ],
        team_count=2,
        slot_count=1,
        constraint_count=0,
    )


def _write_fake_adapter(tmp_path: Path, body: str) -> Path:

    # Write one tiny Python adapter script and return its path.
    adapter_path = tmp_path / "fake_timefold_adapter.py"
    adapter_path.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "import json",
                "import time",
                "from pathlib import Path",
                "",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--output', required=True)",
                "parser.add_argument('--time-limit-seconds', dest='time_limit_seconds', required=True)",
                "parser.add_argument('--random-seed', dest='random_seed', required=True)",
                "args = parser.parse_args()",
                "",
                "input_path = Path(args.input)",
                "output_path = Path(args.output)",
                "payload = json.loads(input_path.read_text(encoding='utf-8'))",
                "meetings = payload['modelInput']['meetings']",
                "slots = payload['modelInput']['slots']",
                "",
                body,
                "",
            ]
        ),
        encoding="utf-8",
    )
    return adapter_path
