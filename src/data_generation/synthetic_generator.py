# Generate larger synthetic instance datasets for algorithm selection experiments.

from __future__ import annotations

import argparse
import csv
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree as ET

from src.demo.generate_demo_instances import (
    DemoInstanceSpec,
    DifficultyLevel,
    RoundRobinMode,
    generate_demo_instances,
)
from src.parsers import load_instance


DEFAULT_OUTPUT_FOLDER = Path("data/raw/synthetic/generated")
DEFAULT_METADATA_CSV_NAME = "metadata.csv"
_DIFFICULTY_SEQUENCE: tuple[DifficultyLevel, ...] = ("easy", "medium", "hard")


@dataclass(frozen=True, slots=True)
class SyntheticDatasetPreset:

    # Difficulty-specific parameter ranges for the dataset generator.
    difficulty: DifficultyLevel
    team_range: tuple[int, int]
    extra_slot_range: tuple[int, int]
    round_robin_modes: tuple[RoundRobinMode, ...]
    total_constraint_range: tuple[int, int]
    hard_ratio_range: tuple[float, float]
    density_range: tuple[float, float]
    penalty_weight_range: tuple[int, int]


DATASET_PRESETS: dict[DifficultyLevel, SyntheticDatasetPreset] = {
    "easy": SyntheticDatasetPreset(
        difficulty="easy",
        team_range=(4, 8),
        extra_slot_range=(0, 2),
        round_robin_modes=("single", "single", "double"),
        total_constraint_range=(3, 7),
        hard_ratio_range=(0.35, 0.50),
        density_range=(0.15, 0.35),
        penalty_weight_range=(5, 18),
    ),
    "medium": SyntheticDatasetPreset(
        difficulty="medium",
        team_range=(8, 14),
        extra_slot_range=(1, 4),
        round_robin_modes=("single", "double"),
        total_constraint_range=(6, 12),
        hard_ratio_range=(0.45, 0.65),
        density_range=(0.30, 0.60),
        penalty_weight_range=(10, 35),
    ),
    "hard": SyntheticDatasetPreset(
        difficulty="hard",
        team_range=(12, 20),
        extra_slot_range=(2, 6),
        round_robin_modes=("single", "double", "double"),
        total_constraint_range=(10, 18),
        hard_ratio_range=(0.55, 0.80),
        density_range=(0.55, 0.85),
        penalty_weight_range=(20, 70),
    ),
}


@dataclass(frozen=True, slots=True)
class SyntheticDatasetRequest:

    # One concrete generation request for a single synthetic instance.
    difficulty: DifficultyLevel
    team_count: int
    slot_count: int
    round_robin_mode: RoundRobinMode
    hard_constraint_count: int
    soft_constraint_count: int
    constraint_density: float
    penalty_weight_range: tuple[int, int]


@dataclass(frozen=True, slots=True)
class GeneratedSyntheticDatasetRow:

    # Metadata row describing one generated synthetic instance.
    instance_name: str
    file_name: str
    file_path: str
    difficulty: DifficultyLevel
    random_seed: int
    team_count: int
    slot_count: int
    round_robin_mode: RoundRobinMode
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
class SyntheticDatasetGenerationResult:

    # Summary of one larger synthetic dataset generation run.
    output_folder: Path
    metadata_csv: Path
    instance_count: int
    random_seed: int
    generation_timestamp: str
    instances: tuple[GeneratedSyntheticDatasetRow, ...]


DifficultySelection = Literal["mixed", "easy", "medium", "hard"]


def generate_synthetic_dataset(
    output_folder: str | Path = DEFAULT_OUTPUT_FOLDER,
    metadata_csv: str | Path | None = None,
    *,
    instance_count: int = 100,
    random_seed: int = 42,
    difficulty: DifficultySelection = "mixed",
    generation_timestamp: str | None = None,
) -> SyntheticDatasetGenerationResult:

    # Generate a larger, diverse synthetic dataset for selector experiments.
    if instance_count <= 0:
        raise ValueError("instance_count must be positive.")

    resolved_difficulty = _normalize_difficulty_selection(difficulty)
    resolved_timestamp = _resolve_generation_timestamp(generation_timestamp)

    output_path = Path(output_folder)
    output_path.mkdir(parents=True, exist_ok=True)
    metadata_path = Path(metadata_csv) if metadata_csv is not None else output_path / DEFAULT_METADATA_CSV_NAME
    metadata_path.parent.mkdir(parents=True, exist_ok=True)

    _clear_existing_generated_dataset(output_path, metadata_path)

    rows: list[GeneratedSyntheticDatasetRow] = []
    difficulty_counts: dict[DifficultyLevel, int] = {key: 0 for key in DATASET_PRESETS}

    with tempfile.TemporaryDirectory(prefix="synthetic_dataset_generation_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)

        for global_index in range(instance_count):
            instance_seed = random_seed + (global_index * 7_919)
            difficulty_level = _resolve_difficulty_for_index(global_index, resolved_difficulty)
            difficulty_index = difficulty_counts[difficulty_level]
            difficulty_counts[difficulty_level] += 1

            request = _build_generation_request(
                difficulty_level=difficulty_level,
                difficulty_index=difficulty_index,
                instance_seed=instance_seed,
            )
            generated_file = _generate_one_instance(
                temp_dir=temp_dir,
                output_folder=output_path,
                global_index=global_index,
                request=request,
                instance_seed=instance_seed,
                generation_timestamp=resolved_timestamp,
            )
            spec = generated_file["spec"]
            final_xml = generated_file["path"]

            family_counts = _count_constraint_families(final_xml)
            row = GeneratedSyntheticDatasetRow(
                instance_name=spec.instance_name,
                file_name=final_xml.name,
                file_path=final_xml.as_posix(),
                difficulty=spec.difficulty_level,
                random_seed=spec.random_seed,
                team_count=spec.team_count,
                slot_count=spec.slot_count,
                round_robin_mode=spec.round_robin_mode,
                meeting_count=spec.meeting_count,
                constraint_count=spec.constraint_count,
                hard_constraint_count=spec.hard_constraint_count,
                soft_constraint_count=spec.soft_constraint_count,
                hard_constraint_ratio=round(
                    spec.hard_constraint_count / max(1, spec.constraint_count),
                    4,
                ),
                constraint_density=spec.constraint_density,
                penalty_weight_min=spec.penalty_weight_range[0],
                penalty_weight_max=spec.penalty_weight_range[1],
                constraint_families=";".join(sorted(family_counts["families"])),
                num_constraint_families=len(family_counts["families"]),
                capacity_constraint_count=family_counts["counts"].get("Capacity", 0),
                break_constraint_count=family_counts["counts"].get("Break", 0),
                home_away_constraint_count=family_counts["counts"].get("HomeAway", 0),
                availability_constraint_count=family_counts["counts"].get("Availability", 0),
                venue_constraint_count=family_counts["counts"].get("Venue", 0),
                separation_constraint_count=family_counts["counts"].get("Separation", 0),
                fairness_constraint_count=family_counts["counts"].get("Fairness", 0),
                travel_constraint_count=family_counts["counts"].get("Travel", 0),
            )
            rows.append(row)

    _write_metadata_csv(metadata_path, rows)

    return SyntheticDatasetGenerationResult(
        output_folder=output_path,
        metadata_csv=metadata_path,
        instance_count=instance_count,
        random_seed=random_seed,
        generation_timestamp=resolved_timestamp,
        instances=tuple(rows),
    )


def build_argument_parser() -> argparse.ArgumentParser:

    # Create the CLI parser for the larger synthetic dataset generator.
    parser = argparse.ArgumentParser(
        description="Generate a larger synthetic dataset for selector experiments.",
    )
    parser.add_argument(
        "--instance-count",
        type=int,
        default=100,
        help="Number of synthetic XML instances to generate.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=42,
        help="Random seed for reproducible generation.",
    )
    parser.add_argument(
        "--difficulty",
        choices=("mixed", "easy", "medium", "hard"),
        default="mixed",
        help="Difficulty profile to generate. Use 'mixed' for a diverse dataset.",
    )
    parser.add_argument(
        "--output-folder",
        default=str(DEFAULT_OUTPUT_FOLDER),
        help="Folder where generated XML instances are written.",
    )
    parser.add_argument(
        "--metadata-csv",
        default=None,
        help="Optional metadata CSV path. Defaults to <output-folder>/metadata.csv.",
    )
    parser.add_argument(
        "--generation-timestamp",
        default=None,
        help="Optional fixed ISO timestamp for reproducible metadata.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:

    # Run the synthetic dataset generator from the command line.
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        result = generate_synthetic_dataset(
            output_folder=args.output_folder,
            metadata_csv=args.metadata_csv,
            instance_count=args.instance_count,
            random_seed=args.random_seed,
            difficulty=args.difficulty,
            generation_timestamp=args.generation_timestamp,
        )
    except ValueError as exc:
        print(f"Failed to generate synthetic dataset: {exc}")
        return 1

    print(
        f"Generated {result.instance_count} synthetic instances in {result.output_folder} "
        f"with metadata at {result.metadata_csv}",
    )
    return 0


def _build_generation_request(
    *,
    difficulty_level: DifficultyLevel,
    difficulty_index: int,
    instance_seed: int,
) -> SyntheticDatasetRequest:

    # Build one concrete generation request with deterministic diversity.
    preset = DATASET_PRESETS[difficulty_level]
    span_seed = instance_seed + (difficulty_index * 313)

    team_count = _cycled_int(
        preset.team_range,
        index=difficulty_index,
        seed=span_seed,
    )
    round_robin_mode = _cycled_mode(
        preset.round_robin_modes,
        index=difficulty_index,
    )
    minimum_slot_count = _minimum_required_slots(team_count, round_robin_mode)
    extra_slots = _cycled_int(
        preset.extra_slot_range,
        index=difficulty_index,
        seed=span_seed + 11,
    )
    slot_count = minimum_slot_count + extra_slots

    total_constraints = _cycled_int(
        preset.total_constraint_range,
        index=difficulty_index,
        seed=span_seed + 23,
    )
    if round_robin_mode == "double":
        total_constraints += 1
    if team_count >= 14:
        total_constraints += 1
    if team_count >= 18:
        total_constraints += 1

    hard_ratio = _cycled_float(
        preset.hard_ratio_range,
        index=difficulty_index,
        seed=span_seed + 41,
    )
    hard_constraint_count = max(1, min(total_constraints - 1, round(total_constraints * hard_ratio)))
    soft_constraint_count = max(1, total_constraints - hard_constraint_count)

    constraint_density = round(
        _cycled_float(
            preset.density_range,
            index=difficulty_index,
            seed=span_seed + 59,
        ),
        2,
    )

    penalty_lower = preset.penalty_weight_range[0] + (difficulty_index % 4)
    penalty_upper = preset.penalty_weight_range[1] + (difficulty_index % 7)

    return SyntheticDatasetRequest(
        difficulty=difficulty_level,
        team_count=team_count,
        slot_count=slot_count,
        round_robin_mode=round_robin_mode,
        hard_constraint_count=hard_constraint_count,
        soft_constraint_count=soft_constraint_count,
        constraint_density=constraint_density,
        penalty_weight_range=(penalty_lower, penalty_upper),
    )


def _generate_one_instance(
    *,
    temp_dir: Path,
    output_folder: Path,
    global_index: int,
    request: SyntheticDatasetRequest,
    instance_seed: int,
    generation_timestamp: str,
) -> dict[str, Path | DemoInstanceSpec]:

    # Generate one synthetic instance through the existing XML builder.
    instance_output = temp_dir / f"instance_{global_index:04d}"
    manifest_path = temp_dir / f"manifest_{global_index:04d}.json"
    instance_output.mkdir(parents=True, exist_ok=True)

    generation = generate_demo_instances(
        output_folder=instance_output,
        manifest_path=manifest_path,
        instance_count=1,
        random_seed=instance_seed,
        difficulty_level=request.difficulty,
        team_count=request.team_count,
        slot_count=request.slot_count,
        round_robin_mode=request.round_robin_mode,
        hard_constraint_count=request.hard_constraint_count,
        soft_constraint_count=request.soft_constraint_count,
        constraint_density=request.constraint_density,
        penalty_weight_range=request.penalty_weight_range,
        generation_timestamp=generation_timestamp,
    )

    source_xml = next(instance_output.glob("*.xml"))
    original_spec = generation.instances[0]
    unique_instance_name = _build_unique_instance_name(original_spec, global_index)
    final_xml = output_folder / f"{unique_instance_name}.xml"

    _rewrite_instance_identity(source_xml, unique_instance_name)
    _ensure_home_away_category(source_xml)
    source_xml.replace(final_xml)

    final_spec = DemoInstanceSpec(
        instance_name=unique_instance_name,
        file_name=final_xml.name,
        profile_name=original_spec.profile_name,
        difficulty_level=original_spec.difficulty_level,
        round_robin_mode=original_spec.round_robin_mode,
        team_count=original_spec.team_count,
        slot_count=original_spec.slot_count,
        meeting_count=original_spec.meeting_count,
        hard_constraint_count=original_spec.hard_constraint_count,
        soft_constraint_count=original_spec.soft_constraint_count,
        constraint_count=original_spec.constraint_count,
        constraint_density=original_spec.constraint_density,
        penalty_weight_range=original_spec.penalty_weight_range,
        random_seed=original_spec.random_seed,
        generation_timestamp=original_spec.generation_timestamp,
        synthetic=original_spec.synthetic,
    )

    return {"path": final_xml, "spec": final_spec}


def _count_constraint_families(xml_path: Path) -> dict[str, object]:

    # Count constraint categories present in one generated XML instance.
    summary = load_instance(str(xml_path))
    counts: dict[str, int] = {}
    families: set[str] = set()
    for constraint in summary.constraints:
        category = getattr(constraint, "category", None)
        if not isinstance(category, str) or not category.strip():
            continue
        normalized = category.strip()
        families.add(normalized)
        counts[normalized] = counts.get(normalized, 0) + 1
    return {"counts": counts, "families": families}


def _write_metadata_csv(metadata_path: Path, rows: list[GeneratedSyntheticDatasetRow]) -> None:

    # Write the metadata CSV with a stable column order.
    with metadata_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(asdict(rows[0]).keys()) if rows else _metadata_columns())
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))


def _metadata_columns() -> list[str]:

    # Return the stable metadata CSV column order.
    return [
        "instance_name",
        "file_name",
        "file_path",
        "difficulty",
        "random_seed",
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


def _build_unique_instance_name(spec: DemoInstanceSpec, global_index: int) -> str:

    # Build a unique dataset instance name derived from the underlying spec.
    return (
        f"synthetic_dataset_{spec.difficulty_level}_{spec.team_count:02d}t_"
        f"{spec.round_robin_mode}_{global_index + 1:03d}"
    )


def _rewrite_instance_identity(xml_path: Path, instance_name: str) -> None:

    # Rewrite the XML root and metadata name to the final unique instance name.
    tree = ET.parse(xml_path)
    root = tree.getroot()
    root.attrib["name"] = instance_name
    metadata_name = root.find("./MetaData/Name")
    if metadata_name is not None:
        metadata_name.text = instance_name
    tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def _ensure_home_away_category(xml_path: Path) -> None:

    # Normalize home-away semantics into an explicit HomeAway constraint category.
    tree = ET.parse(xml_path)
    root = tree.getroot()
    changed = False
    for constraint in root.findall(".//Constraint"):
        tag_value = (constraint.get("tag") or constraint.get("Tag") or "").casefold()
        pattern_value = (constraint.get("pattern") or constraint.get("Pattern") or "").casefold()
        if "homeaway" in tag_value or pattern_value == "home_away":
            if constraint.get("category") != "HomeAway":
                constraint.set("category", "HomeAway")
                changed = True

    if changed:
        tree.write(xml_path, encoding="utf-8", xml_declaration=True)


def _clear_existing_generated_dataset(output_folder: Path, metadata_path: Path) -> None:

    # Remove previously generated XML files and the previous metadata CSV.
    for xml_file in output_folder.glob("*.xml"):
        xml_file.unlink()

    if metadata_path.exists():
        metadata_path.unlink()


def _resolve_difficulty_for_index(index: int, selection: DifficultySelection) -> DifficultyLevel:

    # Resolve the difficulty level for one generated instance.
    if selection == "mixed":
        return _DIFFICULTY_SEQUENCE[index % len(_DIFFICULTY_SEQUENCE)]
    return selection


def _normalize_difficulty_selection(value: str) -> DifficultySelection:

    # Normalize the requested dataset difficulty setting.
    normalized = value.strip().casefold()
    if normalized not in {"mixed", "easy", "medium", "hard"}:
        raise ValueError("difficulty must be one of: mixed, easy, medium, hard.")
    return normalized  # type: ignore[return-value]


def _resolve_generation_timestamp(generation_timestamp: str | None) -> str:

    # Resolve one stable ISO timestamp for the generation run.
    if generation_timestamp is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    parsed = datetime.fromisoformat(generation_timestamp)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat(timespec="seconds")


def _cycled_int(value_range: tuple[int, int], *, index: int, seed: int) -> int:

    # Cycle across an integer range with a small deterministic perturbation.
    lower, upper = value_range
    span = upper - lower + 1
    if span <= 0:
        return lower
    base_value = lower + (index % span)
    offset = ((seed // 17) % 3) - 1
    return min(upper, max(lower, base_value + offset))


def _cycled_float(value_range: tuple[float, float], *, index: int, seed: int) -> float:

    # Cycle across a float range with deterministic coverage.
    lower, upper = value_range
    if upper <= lower:
        return lower

    step_count = 7
    position = (index + (seed % step_count)) % step_count
    ratio = position / max(1, step_count - 1)
    return lower + ((upper - lower) * ratio)


def _cycled_mode(modes: tuple[RoundRobinMode, ...], *, index: int) -> RoundRobinMode:

    # Cycle through allowed round-robin modes to encourage diversity.
    return modes[index % len(modes)]


def _minimum_required_slots(team_count: int, round_robin_mode: RoundRobinMode) -> int:

    # Return the minimum slot count implied by the chosen round-robin mode.
    if team_count <= 1:
        return 0
    single_round_slots = team_count if team_count % 2 == 1 else team_count - 1
    if round_robin_mode == "double":
        return single_round_slots * 2
    return single_round_slots


if __name__ == "__main__":
    raise SystemExit(main())
