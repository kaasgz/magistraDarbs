"""Focused tests for the common solver scoring contract."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

pytest.importorskip("ortools")

from src.experiments.run_benchmarks import run_benchmarks


def test_scoring_contract_exports_supported_unsupported_and_not_configured_rows(
    tmp_path: Path,
) -> None:
    """Benchmark rows should expose explicit scoring semantics."""

    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "single.xml").write_text(_single_clean_xml(), encoding="utf-8")
    (input_dir / "double.xml").write_text(_double_clean_xml(), encoding="utf-8")

    output_csv = tmp_path / "benchmark_results.csv"
    run_benchmarks(
        instance_folder=str(input_dir),
        solver_names=["cpsat_solver", "simulated_annealing_solver", "timefold"],
        time_limit_seconds=2,
        random_seed=7,
        output_csv=output_csv,
    )

    rows = _read_rows(output_csv)

    cpsat_single = _row(rows, "SingleClean", "cpsat_solver")
    assert cpsat_single["solver_support_status"] == "supported"
    assert cpsat_single["scoring_status"] == "supported_feasible_run"
    assert cpsat_single["objective_sense"] == "lower_is_better"
    assert cpsat_single["objective_value_valid"] == "True"
    assert cpsat_single["objective_value"] != ""

    annealing_double = _row(rows, "DoubleClean", "simulated_annealing_solver")
    assert annealing_double["solver_support_status"] == "unsupported"
    assert annealing_double["scoring_status"] == "unsupported_instance"
    assert annealing_double["objective_value_valid"] == "False"
    assert annealing_double["objective_value"] == ""
    assert "Unsupported round-robin mode: double" in annealing_double["scoring_notes"]

    timefold_single = _row(rows, "SingleClean", "timefold")
    assert timefold_single["solver_support_status"] == "not_configured"
    assert timefold_single["scoring_status"] == "not_configured"
    assert timefold_single["objective_value_valid"] == "False"
    assert timefold_single["objective_value"] == ""
    assert "Missing external solver executable" in timefold_single["scoring_notes"]


def _read_rows(path: Path) -> list[dict[str, str]]:
    """Read a CSV file into dictionaries."""

    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _row(rows: list[dict[str, str]], instance_name: str, solver_name: str) -> dict[str, str]:
    """Return one benchmark row by instance and solver registry name."""

    return next(
        row
        for row in rows
        if row["instance_name"] == instance_name and row["solver_registry_name"] == solver_name
    )


def _single_clean_xml() -> str:
    """Return a clean single round-robin instance."""

    return "\n".join(
        [
            '<Instance name="SingleClean">',
            "  <MetaData>",
            "    <RoundRobinMode>single</RoundRobinMode>",
            "  </MetaData>",
            "  <Teams>",
            '    <Team id="A" />',
            '    <Team id="B" />',
            '    <Team id="C" />',
            '    <Team id="D" />',
            "  </Teams>",
            "  <Slots>",
            '    <Slot id="R1" />',
            '    <Slot id="R2" />',
            '    <Slot id="R3" />',
            "  </Slots>",
            "</Instance>",
        ]
    )


def _double_clean_xml() -> str:
    """Return a clean double round-robin instance."""

    return "\n".join(
        [
            '<Instance name="DoubleClean">',
            "  <MetaData>",
            "    <RoundRobinMode>double</RoundRobinMode>",
            "  </MetaData>",
            "  <Teams>",
            '    <Team id="A" />',
            '    <Team id="B" />',
            '    <Team id="C" />',
            '    <Team id="D" />',
            "  </Teams>",
            "  <Slots>",
            '    <Slot id="R1" />',
            '    <Slot id="R2" />',
            '    <Slot id="R3" />',
            '    <Slot id="R4" />',
            '    <Slot id="R5" />',
            '    <Slot id="R6" />',
            "  </Slots>",
            "</Instance>",
        ]
    )
