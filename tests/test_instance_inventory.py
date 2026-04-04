"""Tests for XML instance inventory generation and reporting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.parsers import build_instance_inventory, instance_inventory_report


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_build_instance_inventory_writes_summary_for_real_folder(tmp_path: Path) -> None:
    """The inventory helper should summarize parseable XML files in a real-data folder."""

    input_dir = tmp_path / "data" / "raw" / "real"
    input_dir.mkdir(parents=True)
    (input_dir / "sample.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    output_csv = tmp_path / "data" / "processed" / "instance_inventory.csv"
    written_path = build_instance_inventory(input_dir, output_csv)
    frame = pd.read_csv(written_path)
    report = instance_inventory_report(written_path)

    assert written_path == output_csv
    assert list(frame.columns) == [
        "filename",
        "relative_path",
        "parseable",
        "instance_name",
        "teams",
        "slots",
        "number_of_constraints",
        "data_source",
        "source_inference",
        "parser_note_count",
        "parse_error",
    ]
    assert len(frame.index) == 1
    assert frame.loc[0, "filename"] == "sample.xml"
    assert bool(frame.loc[0, "parseable"]) is True
    assert frame.loc[0, "instance_name"] == "SampleRobinX"
    assert int(frame.loc[0, "teams"]) == 3
    assert int(frame.loc[0, "slots"]) == 2
    assert int(frame.loc[0, "number_of_constraints"]) == 2
    assert frame.loc[0, "data_source"] == "real"
    assert "Parseable: 1" in report
    assert "SampleRobinX" in report


def test_build_instance_inventory_marks_unparseable_files(tmp_path: Path) -> None:
    """Malformed or unusable XML files should stay visible in the inventory."""

    input_dir = tmp_path / "data" / "raw" / "real"
    input_dir.mkdir(parents=True)
    (input_dir / "broken.xml").write_text("<Instance><Teams>", encoding="utf-8")

    output_csv = tmp_path / "data" / "processed" / "instance_inventory.csv"
    frame = pd.read_csv(build_instance_inventory(input_dir, output_csv))

    assert len(frame.index) == 1
    assert bool(frame.loc[0, "parseable"]) is False
    assert frame.loc[0, "filename"] == "broken.xml"
    assert frame.loc[0, "data_source"] == "real"
    assert "teams" in str(frame.loc[0, "parse_error"]).casefold()
