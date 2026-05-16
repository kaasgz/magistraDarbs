# Generate the configured synthetic study dataset with explicit seeds.

from __future__ import annotations

import argparse
import csv
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from src.data_generation.synthetic_generator import (
    DifficultySelection,
    GeneratedSyntheticDatasetRow,
    generate_synthetic_dataset,
)
from src.utils import ensure_parent_directory


DEFAULT_OUTPUT_ROOT = Path("data/raw/synthetic/study")
DEFAULT_METADATA_NAME = "metadata.csv"
DEFAULT_MANIFEST_NAME = "manifest.json"
DEFAULT_GENERATION_TIMESTAMP = "2026-01-01T00:00:00+00:00"
STUDY_XML_PREFIX = "synthetic_study_"


@dataclass(frozen=True, slots=True)
class SyntheticStudyRow:

    # Metadata for one generated study instance.
    instance_name: str
    file_name: str
    file_path: str
    dataset_seed: int
    source_random_seed: int
    seed_batch_index: int
    instance_index: int
    difficulty: str
    team_count: int
    slot_count: int
    round_robin_mode: str
    meeting_count: int
    constraint_count: int
    hard_constraint_count: int
    soft_constraint_count: int
    hard_constraint_ratio: float
    constraint_density: float
    penalty_weight_min: int
    penalty_weight_max: int
    constraint_families: str
    num_constraint_families: int
    capacity_constraint_count: int
    break_constraint_count: int
    home_away_constraint_count: int
    availability_constraint_count: int
    venue_constraint_count: int
    separation_constraint_count: int
    fairness_constraint_count: int
    travel_constraint_count: int


@dataclass(frozen=True, slots=True)
class SyntheticStudyGenerationResult:

    # Summary of one synthetic study generation run.
    output_root: Path
    metadata_csv: Path
    manifest_json: Path
    instance_count: int
    seeds: tuple[int, ...]
    difficulty_profile: DifficultySelection
    generation_timestamp: str
    instances: tuple[SyntheticStudyRow, ...]


def generate_synthetic_study_dataset(
    *,
    n: int = 100,
    seeds: tuple[int, ...] = (42,),
    output_root: str | Path = DEFAULT_OUTPUT_ROOT,
    difficulty_profile: DifficultySelection = "mixed",
    generation_timestamp: str = DEFAULT_GENERATION_TIMESTAMP,
) -> SyntheticStudyGenerationResult:

    # Generate a multi-seed synthetic dataset for thesis experiments.
    if n <= 0:
        raise ValueError("n must be positive.")
    if not seeds:
        raise ValueError("At least one dataset seed is required.")

    normalized_profile = _normalize_difficulty_profile(difficulty_profile)
    output_path = Path(output_root)
    metadata_csv = output_path / DEFAULT_METADATA_NAME
    manifest_json = output_path / DEFAULT_MANIFEST_NAME

    _prepare_output_root(output_path)

    rows: list[SyntheticStudyRow] = []
    allocation = _allocate_instances(n=n, seed_count=len(seeds))
    global_index = 0

    with tempfile.TemporaryDirectory(prefix="synthetic_study_generation_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        for seed_batch_index, (dataset_seed, batch_size) in enumerate(zip(seeds, allocation, strict=True)):
            if batch_size <= 0:
                continue

            batch_root = temp_dir / f"seed_{dataset_seed}"
            batch_result = generate_synthetic_dataset(
                output_folder=batch_root,
                metadata_csv=batch_root / DEFAULT_METADATA_NAME,
                instance_count=batch_size,
                random_seed=dataset_seed,
                difficulty=normalized_profile,
                generation_timestamp=generation_timestamp,
            )

            for batch_row in batch_result.instances:
                global_index += 1
                rows.append(
                    _materialize_study_instance(
                        source_row=batch_row,
                        output_root=output_path,
                        dataset_seed=dataset_seed,
                        seed_batch_index=seed_batch_index,
                        instance_index=global_index,
                    )
                )

    _write_metadata_csv(metadata_csv, rows)
    _write_manifest(
        manifest_json=manifest_json,
        metadata_csv=metadata_csv,
        output_root=output_path,
        n=n,
        seeds=seeds,
        difficulty_profile=normalized_profile,
        generation_timestamp=generation_timestamp,
        rows=rows,
    )

    return SyntheticStudyGenerationResult(
        output_root=output_path,
        metadata_csv=metadata_csv,
        manifest_json=manifest_json,
        instance_count=n,
        seeds=seeds,
        difficulty_profile=normalized_profile,
        generation_timestamp=generation_timestamp,
        instances=tuple(rows),
    )


def build_argument_parser() -> argparse.ArgumentParser:

    # Create the CLI parser for synthetic study generation.
    parser = argparse.ArgumentParser(
        description="Generate a larger synthetic study dataset for algorithm-selection experiments.",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=100,
        help="Total number of synthetic XML instances to generate.",
    )
    parser.add_argument(
        "--seeds",
        default="42",
        help="Comma-separated dataset seeds, for example 42,43,44.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Output folder for study XMLs, metadata.csv, and manifest.json.",
    )
    parser.add_argument(
        "--difficulty-profile",
        choices=("mixed", "easy", "medium", "hard"),
        default="mixed",
        help="Difficulty profile to generate.",
    )
    parser.add_argument(
        "--generation-timestamp",
        default=DEFAULT_GENERATION_TIMESTAMP,
        help="Fixed ISO timestamp embedded in generated XML for reproducibility.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:

    # Run synthetic study generation from the command line.
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        result = generate_synthetic_study_dataset(
            n=args.n,
            seeds=_parse_seeds(args.seeds),
            output_root=args.output_root,
            difficulty_profile=args.difficulty_profile,
            generation_timestamp=args.generation_timestamp,
        )
    except ValueError as exc:
        print(f"Failed to generate synthetic study dataset: {exc}")
        return 1

    print(f"Generated {result.instance_count} synthetic study instances in {result.output_root}")
    print(f"Metadata CSV: {result.metadata_csv}")
    print(f"Manifest JSON: {result.manifest_json}")
    return 0


def _materialize_study_instance(
    *,
    source_row: GeneratedSyntheticDatasetRow,
    output_root: Path,
    dataset_seed: int,
    seed_batch_index: int,
    instance_index: int,
) -> SyntheticStudyRow:

    # Move one generated XML into the study namespace and build metadata.
    instance_name = _study_instance_name(source_row, dataset_seed=dataset_seed, instance_index=instance_index)
    destination_xml = output_root / f"{instance_name}.xml"
    source_xml = Path(source_row.file_path)
    _rewrite_instance_identity(source_xml, instance_name)
    source_xml.replace(destination_xml)

    return SyntheticStudyRow(
        instance_name=instance_name,
        file_name=destination_xml.name,
        file_path=destination_xml.as_posix(),
        dataset_seed=dataset_seed,
        source_random_seed=source_row.random_seed,
        seed_batch_index=seed_batch_index,
        instance_index=instance_index,
        difficulty=source_row.difficulty,
        team_count=source_row.team_count,
        slot_count=source_row.slot_count,
        round_robin_mode=source_row.round_robin_mode,
        meeting_count=source_row.meeting_count,
        constraint_count=source_row.constraint_count,
        hard_constraint_count=source_row.hard_constraint_count,
        soft_constraint_count=source_row.soft_constraint_count,
        hard_constraint_ratio=source_row.hard_constraint_ratio,
        constraint_density=source_row.constraint_density,
        penalty_weight_min=source_row.penalty_weight_min,
        penalty_weight_max=source_row.penalty_weight_max,
        constraint_families=source_row.constraint_families,
        num_constraint_families=source_row.num_constraint_families,
        capacity_constraint_count=source_row.capacity_constraint_count,
        break_constraint_count=source_row.break_constraint_count,
        home_away_constraint_count=source_row.home_away_constraint_count,
        availability_constraint_count=source_row.availability_constraint_count,
        venue_constraint_count=source_row.venue_constraint_count,
        separation_constraint_count=source_row.separation_constraint_count,
        fairness_constraint_count=source_row.fairness_constraint_count,
        travel_constraint_count=source_row.travel_constraint_count,
    )


def _write_metadata_csv(metadata_csv: Path, rows: list[SyntheticStudyRow]) -> None:

    # Write study metadata with a stable schema.
    ensure_parent_directory(metadata_csv)
    fieldnames = list(asdict(rows[0]).keys()) if rows else _metadata_columns()
    with metadata_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _write_manifest(
    *,
    manifest_json: Path,
    metadata_csv: Path,
    output_root: Path,
    n: int,
    seeds: tuple[int, ...],
    difficulty_profile: DifficultySelection,
    generation_timestamp: str,
    rows: list[SyntheticStudyRow],
) -> None:

    # Write a JSON manifest for reproducible study generation.
    ensure_parent_directory(manifest_json)
    payload: dict[str, Any] = {
        "schema": "synthetic_study_dataset_v1",
        "instance_count": n,
        "seeds": list(seeds),
        "difficulty_profile": difficulty_profile,
        "generation_timestamp": generation_timestamp,
        "output_root": output_root.as_posix(),
        "metadata_csv": metadata_csv.as_posix(),
        "generation_parameters": {
            "n": n,
            "seeds": list(seeds),
            "difficulty_profile": difficulty_profile,
            "output_root": output_root.as_posix(),
        },
        "instances": [asdict(row) for row in rows],
    }
    manifest_json.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _prepare_output_root(output_root: Path) -> None:

    # Create the output root and refresh only study-generator artifacts.
    output_root.mkdir(parents=True, exist_ok=True)
    foreign_xml = [
        path
        for path in output_root.glob("*.xml")
        if not path.name.startswith(STUDY_XML_PREFIX)
    ]
    if foreign_xml:
        names = ", ".join(path.name for path in foreign_xml[:5])
        raise ValueError(
            "Output root contains XML files not owned by the study generator: "
            f"{names}. Use a dedicated output root."
        )

    for xml_file in output_root.glob(f"{STUDY_XML_PREFIX}*.xml"):
        xml_file.unlink()
    for artifact_name in (DEFAULT_METADATA_NAME, DEFAULT_MANIFEST_NAME):
        artifact_path = output_root / artifact_name
        if artifact_path.exists():
            artifact_path.unlink()


def _allocate_instances(*, n: int, seed_count: int) -> tuple[int, ...]:

    # Allocate total instances across seed batches deterministically.
    base_count = n // seed_count
    remainder = n % seed_count
    return tuple(base_count + (1 if index < remainder else 0) for index in range(seed_count))


def _study_instance_name(
    source_row: GeneratedSyntheticDatasetRow,
    *,
    dataset_seed: int,
    instance_index: int,
) -> str:

    # Build one globally unique study instance name.
    return (
        f"{STUDY_XML_PREFIX}{source_row.difficulty}_{source_row.team_count:02d}t_"
        f"{source_row.round_robin_mode}_seed{dataset_seed}_{instance_index:04d}"
    )


def _rewrite_instance_identity(xml_path: Path, instance_name: str) -> None:

    # Rewrite XML root and metadata name to the final study instance name.
    tree = ET.parse(xml_path)
    root = tree.getroot()
    root.attrib["name"] = instance_name
    metadata_name = root.find("./MetaData/Name")
    if metadata_name is not None:
        metadata_name.text = instance_name
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def _parse_seeds(value: str) -> tuple[int, ...]:

    # Parse a comma-separated seed list.
    parts = [part.strip() for part in value.split(",") if part.strip()]
    if not parts:
        raise ValueError("seeds must contain at least one integer.")
    try:
        return tuple(int(part) for part in parts)
    except ValueError as exc:
        raise ValueError("seeds must be a comma-separated list of integers.") from exc


def _normalize_difficulty_profile(value: str) -> DifficultySelection:

    # Normalize the requested difficulty profile.
    normalized = value.strip().casefold()
    if normalized not in {"mixed", "easy", "medium", "hard"}:
        raise ValueError("difficulty_profile must be one of: mixed, easy, medium, hard.")
    return normalized  # type: ignore[return-value]


def _metadata_columns() -> list[str]:

    # Return the stable metadata CSV column order.
    return [
        "instance_name",
        "file_name",
        "file_path",
        "dataset_seed",
        "source_random_seed",
        "seed_batch_index",
        "instance_index",
        "difficulty",
        "team_count",
        "slot_count",
        "round_robin_mode",
        "meeting_count",
        "constraint_count",
        "hard_constraint_count",
        "soft_constraint_count",
        "hard_constraint_ratio",
        "constraint_density",
        "penalty_weight_min",
        "penalty_weight_max",
        "constraint_families",
        "num_constraint_families",
        "capacity_constraint_count",
        "break_constraint_count",
        "home_away_constraint_count",
        "availability_constraint_count",
        "venue_constraint_count",
        "separation_constraint_count",
        "fairness_constraint_count",
        "travel_constraint_count",
    ]


__all__ = [
    "DEFAULT_OUTPUT_ROOT",
    "SyntheticStudyGenerationResult",
    "SyntheticStudyRow",
    "generate_synthetic_study_dataset",
]


if __name__ == "__main__":
    raise SystemExit(main())
