"""Tests for XML instance inventory generation and reporting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.parsers import (
    build_instance_inventory,
    build_real_dataset_inventory,
    instance_inventory_report,
    real_dataset_inventory_report,
)


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
        "parser_warnings",
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
    assert pd.isna(frame.loc[0, "parser_warnings"])
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


def test_build_real_dataset_inventory_scans_recursively_and_reports_totals(tmp_path: Path) -> None:
    """The real-data wrapper should recurse under data/raw/real and print concise totals."""

    input_dir = tmp_path / "data" / "raw" / "real"
    nested_dir = input_dir / "league_a"
    nested_dir.mkdir(parents=True)
    (nested_dir / "sample.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (input_dir / "broken.xml").write_text("<Instance><Teams>", encoding="utf-8")

    output_csv = tmp_path / "data" / "processed" / "real_dataset_inventory.csv"
    written_path = build_real_dataset_inventory(input_dir, output_csv)
    frame = pd.read_csv(written_path)
    report = real_dataset_inventory_report(written_path)

    assert written_path == output_csv
    assert len(frame.index) == 2
    assert set(frame["filename"]) == {"sample.xml", "broken.xml"}
    assert set(frame["relative_path"]) == {"league_a/sample.xml", "broken.xml"}
    assert frame["parseable"].map(bool).sum() == 1
    assert "Total files: 2" in report
    assert "Parseable files: 1" in report
    assert "Failed files: 1" in report


def test_build_real_dataset_inventory_records_parser_warning_messages(tmp_path: Path) -> None:
    """Recoverable XML warnings should stay visible in the real-data inventory CSV."""

    input_dir = tmp_path / "data" / "raw" / "real"
    input_dir.mkdir(parents=True)
    xml_path = input_dir / "recoverable.xml"
    xml_path.write_text(
        "\n".join(
            [
                '<Instance name="RecoverableFixture">',
                "  <Teams>",
                '    <Team id="T1" name="Team A" />',
                '    <Team id="T2" name="Team B" />',
                "  </Teams>",
                "  <Slots>",
                '    <Slot id="S1" name="Round 1">',
                "  </Slots>",
                "</Instance>",
            ]
        ),
        encoding="utf-8",
    )

    output_csv = tmp_path / "data" / "processed" / "real_dataset_inventory.csv"
    frame = pd.read_csv(build_real_dataset_inventory(input_dir, output_csv))

    assert len(frame.index) == 1
    assert bool(frame.loc[0, "parseable"]) is True
    assert frame.loc[0, "instance_name"] == "RecoverableFixture"
    assert "xml_recovery_applied" in str(frame.loc[0, "parser_warnings"])


def test_build_real_dataset_inventory_marks_itc2021_style_xml_as_parseable(tmp_path: Path) -> None:
    """Official-style ITC2021 XML structure should appear as parseable in the inventory."""

    input_dir = tmp_path / "data" / "raw" / "real"
    input_dir.mkdir(parents=True)
    (input_dir / "itc2021_style.xml").write_text(
        "\n".join(
            [
                "<Instance>",
                "  <MetaData>",
                "    <InstanceName>Inventory ITC2021 Style</InstanceName>",
                "  </MetaData>",
                "  <Structure>",
                "    <Format>",
                "      <numberRoundRobin>2</numberRoundRobin>",
                "    </Format>",
                "  </Structure>",
                "  <Resources>",
                "    <Teams>",
                '      <team id="0" name="Team 0" />',
                '      <team id="1" name="Team 1" />',
                '      <team id="2" name="Team 2" />',
                '      <team id="3" name="Team 3" />',
                "    </Teams>",
                "    <Slots>",
                '      <slot id="0" name="Slot 0" />',
                '      <slot id="1" name="Slot 1" />',
                '      <slot id="2" name="Slot 2" />',
                '      <slot id="3" name="Slot 3" />',
                '      <slot id="4" name="Slot 4" />',
                '      <slot id="5" name="Slot 5" />',
                "    </Slots>",
                "  </Resources>",
                "  <Constraints>",
                "    <GameConstraints>",
                '      <GA1 meetings="0,1;" slots="0;1" max="1" min="0" type="HARD" />',
                "    </GameConstraints>",
                "  </Constraints>",
                "</Instance>",
            ]
        ),
        encoding="utf-8",
    )

    output_csv = tmp_path / "data" / "processed" / "real_dataset_inventory.csv"
    frame = pd.read_csv(build_real_dataset_inventory(input_dir, output_csv))

    assert len(frame.index) == 1
    assert bool(frame.loc[0, "parseable"]) is True
    assert frame.loc[0, "instance_name"] == "Inventory ITC2021 Style"
    assert int(frame.loc[0, "teams"]) == 4
    assert int(frame.loc[0, "slots"]) == 6
    assert int(frame.loc[0, "number_of_constraints"]) == 1
