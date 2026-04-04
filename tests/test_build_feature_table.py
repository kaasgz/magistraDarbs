"""Tests for batch feature table generation."""

from __future__ import annotations

import csv
from pathlib import Path

import pytest

from src.demo.generate_demo_instances import generate_demo_instances
from src.features.build_feature_table import build_feature_table


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXED_TIMESTAMP = "2026-04-04T12:00:00+00:00"


def test_build_feature_table_writes_one_row_per_valid_instance(tmp_path: Path) -> None:
    """The builder should write one CSV row for each valid XML file."""

    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "valid.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (input_dir / "missing_sections.xml").write_text(
        (FIXTURES_DIR / "sample_robinx_missing_sections.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    output_csv = tmp_path / "features.csv"
    build_feature_table(str(input_dir), output_csv)

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert reader.fieldnames is not None
    assert reader.fieldnames[0] == "instance_name"
    assert len(rows) == 2
    assert {row["instance_name"] for row in rows} == {"SampleRobinX", "missing_sections"}


def test_build_feature_table_skips_broken_files_and_logs_it(
    tmp_path: Path,
    caplog,
) -> None:
    """Broken XML files should be skipped with a clear warning message."""

    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "valid.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (input_dir / "broken.xml").write_text("<Instance><Teams>", encoding="utf-8")

    output_csv = tmp_path / "features.csv"
    caplog.set_level("INFO")

    build_feature_table(str(input_dir), output_csv)

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert "Skipping broken file" in caplog.text
    assert "broken.xml" in caplog.text


def test_build_feature_table_accepts_recoverable_xml_and_logs_parser_notes(
    tmp_path: Path,
    caplog,
) -> None:
    """Recoverable XML should stay in the pipeline and emit parser-note logs."""

    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "recoverable.xml").write_text(
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

    output_csv = tmp_path / "features.csv"
    caplog.set_level("INFO")

    build_feature_table(str(input_dir), output_csv)

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["instance_name"] == "RecoverableFixture"
    assert "[xml_recovery_applied]" in caplog.text


def test_build_feature_table_writes_empty_csv_for_empty_folder(tmp_path: Path) -> None:
    """An empty input folder should still produce a valid empty CSV file."""

    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    output_csv = tmp_path / "features.csv"

    build_feature_table(str(input_dir), output_csv)

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)

    assert rows == [["instance_name"]]


def test_build_feature_table_rejects_synthetic_instances_in_real_folder(tmp_path: Path) -> None:
    """Synthetic XML should not be accepted silently in a real-data folder."""

    input_dir = tmp_path / "data" / "raw" / "real"
    input_dir.mkdir(parents=True)
    manifest_path = tmp_path / "data" / "processed" / "demo_manifest.json"

    generate_demo_instances(
        output_folder=input_dir,
        manifest_path=manifest_path,
        instance_count=1,
        random_seed=11,
        generation_timestamp=FIXED_TIMESTAMP,
    )

    with pytest.raises(ValueError, match="Real-data folder contains a synthetic instance"):
        build_feature_table(str(input_dir), tmp_path / "features.csv")
