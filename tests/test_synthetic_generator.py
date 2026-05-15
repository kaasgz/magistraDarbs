"""Tests for the larger synthetic dataset generator."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.data_generation.synthetic_generator import generate_synthetic_dataset, main
from src.features.build_feature_table import build_feature_table
from src.parsers import load_instance


FIXED_TIMESTAMP = "2026-04-19T12:00:00+00:00"


def test_generate_synthetic_dataset_writes_diverse_xml_batch_and_metadata_csv(tmp_path: Path) -> None:
    """The generator should produce a diverse mixed-difficulty batch and a metadata CSV."""

    output_folder = tmp_path / "generated"
    metadata_csv = output_folder / "metadata.csv"

    result = generate_synthetic_dataset(
        output_folder=output_folder,
        metadata_csv=metadata_csv,
        instance_count=12,
        random_seed=17,
        difficulty="mixed",
        generation_timestamp=FIXED_TIMESTAMP,
    )

    xml_files = sorted(output_folder.glob("*.xml"))
    metadata = pd.read_csv(metadata_csv)
    first_instance = load_instance(str(xml_files[0]))

    assert result.instance_count == 12
    assert len(xml_files) == 12
    assert len(metadata.index) == 12
    assert set(metadata["difficulty"]) == {"easy", "medium", "hard"}
    assert set(metadata["round_robin_mode"]) == {"single", "double"}
    assert metadata["team_count"].between(4, 20).all()
    assert metadata["constraint_count"].ge(3).all()
    assert metadata["hard_constraint_ratio"].between(0.3, 0.85).all()
    assert metadata["home_away_constraint_count"].sum() > 0
    assert metadata["capacity_constraint_count"].sum() > 0
    assert metadata["break_constraint_count"].sum() > 0
    assert first_instance.metadata.synthetic is True
    assert first_instance.metadata.generated_at == FIXED_TIMESTAMP


def test_generate_synthetic_dataset_is_reproducible_for_same_seed(tmp_path: Path) -> None:
    """The same seed and timestamp should reproduce identical XML and metadata outputs."""

    first_output = tmp_path / "first"
    second_output = tmp_path / "second"

    first_result = generate_synthetic_dataset(
        output_folder=first_output,
        instance_count=9,
        random_seed=23,
        difficulty="mixed",
        generation_timestamp=FIXED_TIMESTAMP,
    )
    second_result = generate_synthetic_dataset(
        output_folder=second_output,
        instance_count=9,
        random_seed=23,
        difficulty="mixed",
        generation_timestamp=FIXED_TIMESTAMP,
    )

    first_metadata = pd.read_csv(first_result.metadata_csv)
    second_metadata = pd.read_csv(second_result.metadata_csv)
    first_files = sorted(first_output.glob("*.xml"))
    second_files = sorted(second_output.glob("*.xml"))

    comparable_first = first_metadata.drop(columns=["file_path"])
    comparable_second = second_metadata.drop(columns=["file_path"])

    assert comparable_first.to_dict(orient="records") == comparable_second.to_dict(orient="records")
    assert [path.name for path in first_files] == [path.name for path in second_files]
    assert [path.read_text(encoding="utf-8") for path in first_files] == [
        path.read_text(encoding="utf-8") for path in second_files
    ]


def test_generated_synthetic_dataset_works_with_feature_pipeline(tmp_path: Path) -> None:
    """Generated experiment-scale XML should be consumable by the feature builder."""

    output_folder = tmp_path / "generated"
    features_csv = tmp_path / "features.csv"

    generation = generate_synthetic_dataset(
        output_folder=output_folder,
        instance_count=6,
        random_seed=31,
        difficulty="mixed",
        generation_timestamp=FIXED_TIMESTAMP,
    )
    build_feature_table(input_folder=generation.output_folder, output_csv=features_csv, random_seed=31)

    features = pd.read_csv(features_csv)

    assert len(features.index) == 6
    assert {"instance_name", "num_teams", "num_slots", "num_constraints"} <= set(features.columns)


def test_synthetic_generator_cli_supports_instance_count_argument(tmp_path: Path) -> None:
    """The CLI should honor the requested instance count and write the metadata CSV."""

    output_folder = tmp_path / "generated"
    metadata_csv = tmp_path / "synthetic_metadata.csv"

    exit_code = main(
        [
            "--instance-count",
            "5",
            "--random-seed",
            "13",
            "--difficulty",
            "mixed",
            "--output-folder",
            str(output_folder),
            "--metadata-csv",
            str(metadata_csv),
            "--generation-timestamp",
            FIXED_TIMESTAMP,
        ]
    )

    assert exit_code == 0
    assert len(list(output_folder.glob("*.xml"))) == 5
    metadata = pd.read_csv(metadata_csv)
    assert len(metadata.index) == 5
