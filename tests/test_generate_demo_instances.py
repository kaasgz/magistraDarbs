"""Tests for synthetic demo instance generation."""

from __future__ import annotations

import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pandas as pd

from src.demo.generate_demo_instances import generate_demo_instances
from src.features.build_feature_table import build_feature_table
from src.parsers import load_instance


FIXED_TIMESTAMP = "2026-04-04T12:00:00+00:00"


def test_generate_demo_instances_writes_manifest_and_structured_metadata(tmp_path: Path) -> None:
    """Generated instances should carry synthetic metadata and parser-friendly structure."""

    output_folder = tmp_path / "raw"
    manifest_path = tmp_path / "processed" / "manifest.json"

    result = generate_demo_instances(
        output_folder=output_folder,
        manifest_path=manifest_path,
        instance_count=2,
        random_seed=11,
        difficulty_level="medium",
        generation_timestamp=FIXED_TIMESTAMP,
    )

    xml_files = sorted(output_folder.glob("*.xml"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    first_xml = xml_files[0]
    first_root = ET.parse(first_xml).getroot()
    first_summary = load_instance(str(first_xml))

    assert result.instance_count == 2
    assert len(xml_files) == 2
    assert manifest["instance_count"] == 2
    assert manifest["generation_timestamp"] == FIXED_TIMESTAMP
    assert manifest["generation_parameters"]["difficulty_level"] == "medium"

    assert first_root.attrib["synthetic"] == "true"
    assert first_root.findtext("./MetaData/Synthetic") == "true"
    assert first_root.findtext("./MetaData/GeneratedAt") == FIXED_TIMESTAMP
    assert first_root.findtext("./MetaData/Difficulty") == "medium"
    assert first_root.findtext("./MetaData/ObjectiveName") == "weighted_soft_penalty"
    assert first_root.find("./Meetings") is not None

    assert first_summary.metadata.synthetic is True
    assert first_summary.metadata.generated_at == FIXED_TIMESTAMP
    assert first_summary.metadata.difficulty_level == "medium"
    assert first_summary.metadata.objective_name == "weighted_soft_penalty"
    assert first_summary.metadata.objective_sense == "minimize"


def test_generate_demo_instances_is_reproducible_for_same_seed(tmp_path: Path) -> None:
    """The same seed and fixed timestamp should produce identical outputs."""

    first_output = tmp_path / "first"
    second_output = tmp_path / "second"
    first_manifest = tmp_path / "first_manifest.json"
    second_manifest = tmp_path / "second_manifest.json"

    generate_demo_instances(
        output_folder=first_output,
        manifest_path=first_manifest,
        instance_count=3,
        random_seed=7,
        difficulty_level="hard",
        generation_timestamp=FIXED_TIMESTAMP,
    )
    generate_demo_instances(
        output_folder=second_output,
        manifest_path=second_manifest,
        instance_count=3,
        random_seed=7,
        difficulty_level="hard",
        generation_timestamp=FIXED_TIMESTAMP,
    )

    first_payload = json.loads(first_manifest.read_text(encoding="utf-8"))
    second_payload = json.loads(second_manifest.read_text(encoding="utf-8"))
    first_files = sorted(first_output.glob("*.xml"))
    second_files = sorted(second_output.glob("*.xml"))

    assert {key: value for key, value in first_payload.items() if key != "output_folder"} == {
        key: value for key, value in second_payload.items() if key != "output_folder"
    }
    assert [path.name for path in first_files] == [path.name for path in second_files]
    assert [path.read_text(encoding="utf-8") for path in first_files] == [
        path.read_text(encoding="utf-8") for path in second_files
    ]


def test_generate_demo_instances_respect_explicit_team_slot_and_constraint_counts(tmp_path: Path) -> None:
    """Explicit generation parameters should be reflected in the parsed instance."""

    output_folder = tmp_path / "raw"
    manifest_path = tmp_path / "manifest.json"

    generate_demo_instances(
        output_folder=output_folder,
        manifest_path=manifest_path,
        instance_count=1,
        random_seed=21,
        difficulty_level="hard",
        team_count=8,
        slot_count=16,
        round_robin_mode="double",
        hard_constraint_count=5,
        soft_constraint_count=4,
        constraint_density=0.60,
        penalty_weight_range=(7, 21),
        generation_timestamp=FIXED_TIMESTAMP,
    )

    xml_file = next(output_folder.glob("*.xml"))
    summary = load_instance(str(xml_file))
    root = ET.parse(xml_file).getroot()
    constraint_types = [constraint.type_name for constraint in summary.constraints]
    soft_weights = [
        int(element.attrib["weight"])
        for element in root.findall("./Constraints/Constraint")
        if element.attrib.get("type") == "Soft"
    ]

    assert summary.team_count == 8
    assert summary.slot_count == 16
    assert summary.constraint_count == 9
    assert constraint_types.count("Hard") == 5
    assert constraint_types.count("Soft") == 4
    assert all(7 <= weight <= 21 for weight in soft_weights)


def test_generated_instances_work_with_feature_pipeline(tmp_path: Path) -> None:
    """Generated XML files should be consumable by the current feature pipeline."""

    output_folder = tmp_path / "raw"
    manifest_path = tmp_path / "manifest.json"
    features_csv = tmp_path / "features.csv"

    generate_demo_instances(
        output_folder=output_folder,
        manifest_path=manifest_path,
        instance_count=3,
        random_seed=5,
        generation_timestamp=FIXED_TIMESTAMP,
    )
    build_feature_table(input_folder=output_folder, output_csv=features_csv, random_seed=5)

    frame = pd.read_csv(features_csv)

    assert len(frame.index) == 3
    assert {"instance_name", "num_teams", "num_slots", "num_constraints", "objective_present"} <= set(
        frame.columns
    )
    assert frame["objective_present"].all()
