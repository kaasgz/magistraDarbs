"""Tests for the synthetic study dataset experiment generator."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from src.experiments.generate_synthetic_dataset import (
    generate_synthetic_study_dataset,
    main,
)
from src.parsers import load_instance


def test_generate_synthetic_study_dataset_is_deterministic(tmp_path: Path) -> None:
    """Same seeds and timestamp should reproduce XML, metadata, and manifest content."""

    first_root = tmp_path / "first"
    second_root = tmp_path / "second"

    first = generate_synthetic_study_dataset(n=8, seeds=(42, 43), output_root=first_root)
    second = generate_synthetic_study_dataset(n=8, seeds=(42, 43), output_root=second_root)

    first_xml = sorted(path.read_text(encoding="utf-8") for path in first_root.glob("*.xml"))
    second_xml = sorted(path.read_text(encoding="utf-8") for path in second_root.glob("*.xml"))

    assert first.instance_count == second.instance_count == 8
    assert first_xml == second_xml
    assert _metadata_without_paths(first.metadata_csv) == _metadata_without_paths(second.metadata_csv)
    assert _manifest_without_paths(first.manifest_json) == _manifest_without_paths(second.manifest_json)


def test_generate_synthetic_study_dataset_manifest_integrity(tmp_path: Path) -> None:
    """The manifest should describe every generated XML and match metadata rows."""

    output_root = tmp_path / "study"

    exit_code = main(
        [
            "--n",
            "18",
            "--seeds",
            "42,43,44",
            "--output-root",
            str(output_root),
            "--difficulty-profile",
            "mixed",
        ]
    )

    metadata_csv = output_root / "metadata.csv"
    manifest_json = output_root / "manifest.json"
    xml_files = sorted(output_root.glob("*.xml"))
    metadata = _read_metadata(metadata_csv)
    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))

    assert exit_code == 0
    assert len(xml_files) == 18
    assert len(metadata) == 18
    assert manifest["schema"] == "synthetic_study_dataset_v1"
    assert manifest["instance_count"] == 18
    assert manifest["seeds"] == [42, 43, 44]
    assert manifest["difficulty_profile"] == "mixed"
    assert len(manifest["instances"]) == 18

    metadata_names = {row["instance_name"] for row in metadata}
    manifest_names = {row["instance_name"] for row in manifest["instances"]}
    xml_names = {path.stem for path in xml_files}

    assert metadata_names == manifest_names == xml_names
    assert {row["difficulty"] for row in metadata} == {"easy", "medium", "hard"}
    assert {row["round_robin_mode"] for row in metadata} == {"single", "double"}
    assert {int(row["dataset_seed"]) for row in metadata} == {42, 43, 44}
    assert all(int(row["team_count"]) >= 4 for row in metadata)
    assert all(int(row["slot_count"]) > 0 for row in metadata)
    assert all(int(row["hard_constraint_count"]) >= 1 for row in metadata)
    assert all(int(row["soft_constraint_count"]) >= 1 for row in metadata)
    assert sum(int(row["capacity_constraint_count"]) for row in metadata) > 0
    assert sum(int(row["break_constraint_count"]) for row in metadata) > 0
    assert sum(int(row["home_away_constraint_count"]) for row in metadata) > 0

    parsed = load_instance(str(xml_files[0]))
    assert parsed.metadata.synthetic is True
    assert parsed.metadata.name in metadata_names


def _read_metadata(metadata_csv: Path) -> list[dict[str, str]]:
    """Read metadata CSV rows."""

    with metadata_csv.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _metadata_without_paths(metadata_csv: Path) -> list[dict[str, str]]:
    """Return metadata rows after removing output-root-specific paths."""

    rows = _read_metadata(metadata_csv)
    for row in rows:
        row.pop("file_path", None)
    return rows


def _manifest_without_paths(manifest_json: Path) -> dict[str, Any]:
    """Return manifest content after removing output-root-specific paths."""

    manifest = json.loads(manifest_json.read_text(encoding="utf-8"))
    manifest.pop("output_root", None)
    manifest.pop("metadata_csv", None)
    manifest["generation_parameters"].pop("output_root", None)
    for row in manifest["instances"]:
        row.pop("file_path", None)
    return manifest
