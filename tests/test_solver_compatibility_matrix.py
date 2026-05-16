# Tests for the real-instance solver compatibility matrix.

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.experiments.build_solver_compatibility_matrix import (
    build_solver_compatibility_matrix,
    main,
)
from src.experiments.full_benchmark import DEFAULT_FULL_SOLVER_PORTFOLIO


def test_build_solver_compatibility_matrix_classifies_core_solver_scope(tmp_path: Path) -> None:

    # The matrix should report conservative per-solver support decisions.
    input_dir = tmp_path / "data" / "raw" / "real"
    input_dir.mkdir(parents=True)
    (input_dir / "single_clean.xml").write_text(_single_clean_xml(), encoding="utf-8")
    (input_dir / "double_constrained.xml").write_text(_double_constrained_xml(), encoding="utf-8")

    output_csv = tmp_path / "data" / "processed" / "real_pipeline_current" / "solver_compatibility_matrix.csv"
    summary_markdown = (
        tmp_path / "data" / "results" / "real_pipeline_current" / "solver_compatibility_summary.md"
    )

    result = build_solver_compatibility_matrix(
        input_folder=input_dir,
        output_csv=output_csv,
        summary_markdown=summary_markdown,
    )
    matrix = pd.read_csv(result.matrix_csv)

    assert result.num_rows == 2 * len(DEFAULT_FULL_SOLVER_PORTFOLIO)
    assert list(matrix.columns) == [
        "instance_name",
        "solver_name",
        "support_status",
        "unsupported_constraint_families",
        "notes",
    ]

    assert _status(matrix, "SingleClean", "cpsat_solver") == "supported"
    assert _status(matrix, "SingleClean", "simulated_annealing_solver") == "supported"
    assert _status(matrix, "SingleClean", "random_baseline") == "partially_supported"
    assert _status(matrix, "SingleClean", "timefold") == "not_configured"

    assert _status(matrix, "DoubleConstrained", "cpsat_solver") == "partially_supported"
    assert _status(matrix, "DoubleConstrained", "simulated_annealing_solver") == "unsupported"
    assert "Capacity" in _field(matrix, "DoubleConstrained", "cpsat_solver", "unsupported_constraint_families")
    assert "unsupported round-robin mode: double" in _field(
        matrix,
        "DoubleConstrained",
        "simulated_annealing_solver",
        "notes",
    )

    summary_text = summary_markdown.read_text(encoding="utf-8")
    assert "Solver Compatibility Summary" in summary_text
    assert "| `timefold` | `not_configured` | 2 |" in summary_text
    assert "| `simulated_annealing_solver` | `unsupported` | 1 |" in summary_text


def test_solver_compatibility_matrix_records_parser_failures(tmp_path: Path) -> None:

    # Unparseable XML files should produce explicit unsupported rows.
    input_dir = tmp_path / "real"
    input_dir.mkdir()
    (input_dir / "broken.xml").write_text("", encoding="utf-8")
    output_csv = tmp_path / "solver_compatibility_matrix.csv"
    summary_markdown = tmp_path / "solver_compatibility_summary.md"

    exit_code = main(
        [
            "--input-folder",
            str(input_dir),
            "--output-csv",
            str(output_csv),
            "--summary-markdown",
            str(summary_markdown),
        ]
    )
    matrix = pd.read_csv(output_csv)

    assert exit_code == 0
    assert len(matrix.index) == len(DEFAULT_FULL_SOLVER_PORTFOLIO)
    assert set(matrix["support_status"]) == {"unsupported"}
    assert matrix["notes"].str.contains("parser limitation").all()
    assert summary_markdown.exists()


def _status(matrix: pd.DataFrame, instance_name: str, solver_name: str) -> str:

    # Return the support status for one matrix row.
    return _field(matrix, instance_name, solver_name, "support_status")


def _field(matrix: pd.DataFrame, instance_name: str, solver_name: str, column: str) -> str:

    # Return one field from the compatibility matrix.
    row = matrix[
        (matrix["instance_name"] == instance_name)
        & (matrix["solver_name"] == solver_name)
    ].iloc[0]
    return str(row[column])


def _single_clean_xml() -> str:

    # Return a small single round-robin instance without declared constraints.
    return "\n".join(
        [
            '<Instance name="SingleClean">',
            "  <MetaData>",
            "    <RoundRobinMode>single</RoundRobinMode>",
            "  </MetaData>",
            "  <Teams>",
            '    <Team id="T1" />',
            '    <Team id="T2" />',
            '    <Team id="T3" />',
            '    <Team id="T4" />',
            "  </Teams>",
            "  <Slots>",
            '    <Slot id="S1" />',
            '    <Slot id="S2" />',
            '    <Slot id="S3" />',
            "  </Slots>",
            "</Instance>",
        ]
    )


def _double_constrained_xml() -> str:

    # Return a double round-robin instance with one parsed constraint family.
    return "\n".join(
        [
            '<Instance name="DoubleConstrained">',
            "  <MetaData>",
            "    <RoundRobinMode>double</RoundRobinMode>",
            "  </MetaData>",
            "  <Teams>",
            '    <Team id="T1" />',
            '    <Team id="T2" />',
            '    <Team id="T3" />',
            '    <Team id="T4" />',
            "  </Teams>",
            "  <Slots>",
            '    <Slot id="S1" />',
            '    <Slot id="S2" />',
            '    <Slot id="S3" />',
            '    <Slot id="S4" />',
            '    <Slot id="S5" />',
            '    <Slot id="S6" />',
            "  </Slots>",
            "  <Constraints>",
            "    <CapacityConstraints>",
            '      <CA1 type="Hard" />',
            "    </CapacityConstraints>",
            "  </Constraints>",
            "</Instance>",
        ]
    )
