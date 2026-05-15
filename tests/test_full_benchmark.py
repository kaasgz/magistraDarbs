"""Tests for the full solver portfolio benchmark runner."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from src.data_generation.synthetic_generator import generate_synthetic_dataset
from src.experiments.full_benchmark import DEFAULT_FULL_SOLVER_PORTFOLIO, main, run_full_benchmark


FIXED_TIMESTAMP = "2026-04-19T12:00:00+00:00"


def test_run_full_benchmark_runs_all_solvers_and_adds_support_status(tmp_path: Path) -> None:
    """The full benchmark should run the standard portfolio and write support status."""

    input_dir = tmp_path / "generated"
    generate_synthetic_dataset(
        output_folder=input_dir,
        instance_count=1,
        random_seed=3,
        difficulty="easy",
        generation_timestamp=FIXED_TIMESTAMP,
    )

    adapter_path = _write_fake_timefold_adapter(tmp_path)
    output_csv = tmp_path / "full_benchmark_results.csv"
    summary_json = tmp_path / "full_benchmark_summary.json"

    written_path = run_full_benchmark(
        instance_folder=input_dir,
        output_csv=output_csv,
        time_limit_seconds=1,
        random_seed=3,
        timefold_executable_path=sys.executable,
        timefold_command_arguments=[str(adapter_path)],
        timefold_time_limit_seconds=1,
        run_summary_path=summary_json,
    )

    results = pd.read_csv(written_path)

    assert written_path == output_csv
    assert len(results.index) == len(DEFAULT_FULL_SOLVER_PORTFOLIO)
    assert set(results["solver_registry_name"]) == set(DEFAULT_FULL_SOLVER_PORTFOLIO)
    assert {
        "objective_value",
        "runtime_seconds",
        "feasible",
        "solver_support_status",
        "scoring_status",
        "objective_value_valid",
    } <= set(results.columns)
    assert results["solver_support_status"].notna().all()
    assert set(results.loc[results["solver_registry_name"] == "timefold", "solver_support_status"]) == {
        "partially_supported"
    }
    assert summary_json.exists()


def test_run_full_benchmark_handles_unconfigured_timefold_cleanly(tmp_path: Path) -> None:
    """Timefold should produce a clean non-fatal row when no executable is configured."""

    input_dir = tmp_path / "generated"
    generate_synthetic_dataset(
        output_folder=input_dir,
        instance_count=1,
        random_seed=5,
        difficulty="easy",
        generation_timestamp=FIXED_TIMESTAMP,
    )

    output_csv = tmp_path / "full_benchmark_results.csv"
    run_full_benchmark(
        instance_folder=input_dir,
        output_csv=output_csv,
        time_limit_seconds=1,
        random_seed=5,
    )

    results = pd.read_csv(output_csv)
    timefold_row = results.loc[results["solver_registry_name"] == "timefold"].iloc[0]

    assert timefold_row["feasible"] in {False, "False"}
    assert timefold_row["status"] == "NOT_CONFIGURED"
    assert timefold_row["solver_support_status"] == "not_configured"
    assert timefold_row["scoring_status"] == "not_configured"
    assert timefold_row["objective_value_valid"] in {False, "False"}
    assert isinstance(timefold_row["error_message"], str)


def test_full_benchmark_cli_runs_one_command(tmp_path: Path) -> None:
    """The CLI entry point should run the full benchmark with one command."""

    input_dir = tmp_path / "generated"
    generate_synthetic_dataset(
        output_folder=input_dir,
        instance_count=1,
        random_seed=7,
        difficulty="easy",
        generation_timestamp=FIXED_TIMESTAMP,
    )
    output_csv = tmp_path / "full_benchmark_results.csv"

    exit_code = main(
        [
            str(input_dir),
            "--output",
            str(output_csv),
            "--time-limit-seconds",
            "1",
            "--random-seed",
            "7",
        ]
    )

    assert exit_code == 0
    results = pd.read_csv(output_csv)
    assert len(results.index) == len(DEFAULT_FULL_SOLVER_PORTFOLIO)


def _write_fake_timefold_adapter(tmp_path: Path) -> Path:
    """Write a tiny adapter that returns a deterministic greedy schedule."""

    adapter_path = tmp_path / "fake_timefold_adapter.py"
    adapter_path.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "import json",
                "from pathlib import Path",
                "",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--output', required=True)",
                "parser.add_argument('--time-limit-seconds', dest='time_limit_seconds', required=True)",
                "parser.add_argument('--random-seed', dest='random_seed', required=True)",
                "args = parser.parse_args()",
                "",
                "payload = json.loads(Path(args.input).read_text(encoding='utf-8'))",
                "matches = payload['modelInput']['matches']",
                "slots = payload['modelInput']['slots']",
                "teams_by_match = {",
                "    match['id']: {match['homeTeamId'], match['awayTeamId']}",
                "    for match in matches",
                "}",
                "teams_per_slot = {slot['id']: set() for slot in slots}",
                "schedule = []",
                "for match in matches:",
                "    for slot in slots:",
                "        slot_id = slot['id']",
                "        if teams_by_match[match['id']].isdisjoint(teams_per_slot[slot_id]):",
                "            schedule.append({'matchId': match['id'], 'slotId': slot_id})",
                "            teams_per_slot[slot_id].update(teams_by_match[match['id']])",
                "            break",
                "result = {",
                "    'status': 'SOLVED',",
                "    'feasible': len(schedule) == len(matches),",
                "    'objectiveValue': float(len({item['slotId'] for item in schedule})),",
                "    'runtimeSeconds': 0.1,",
                "    'schedule': schedule,",
                "}",
                "Path(args.output).write_text(json.dumps(result), encoding='utf-8')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return adapter_path
