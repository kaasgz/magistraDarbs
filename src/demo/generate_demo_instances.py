# Generate reproducible RobinX-like synthetic instances for local experiments.

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree as ET


DEFAULT_OUTPUT_FOLDER = Path("data/raw/synthetic/demo_instances")
DEFAULT_MANIFEST_PATH = Path("data/processed/demo_manifest.json")

RoundRobinMode = Literal["single", "double"]
DifficultyLevel = Literal["easy", "medium", "hard"]

_DEFAULT_DIFFICULTY_SEQUENCE: tuple[DifficultyLevel, ...] = ("easy", "medium", "hard")
_OBJECTIVE_NAME = "weighted_soft_penalty"
_OBJECTIVE_SENSE = "minimize"

_TEAM_MARKETS: tuple[str, ...] = (
    "Northport",
    "Eastvale",
    "Southridge",
    "Westhaven",
    "Rivergate",
    "Hillcrest",
    "Lakewood",
    "Brookfield",
    "Stonebridge",
    "Fairview",
    "Kingsport",
    "Redwood",
    "Silverton",
    "Cedarfield",
    "Mapleton",
    "Oakridge",
)
_TEAM_SUFFIXES: tuple[str, ...] = (
    "United",
    "City",
    "Athletic",
    "Rovers",
    "Sporting",
    "Town",
    "Olympic",
    "FC",
)
_REGIONS: tuple[str, ...] = ("North", "South", "East", "West", "Central")


@dataclass(frozen=True, slots=True)
class DifficultyPreset:

    # Parameter ranges used to create one family of synthetic instances.
    difficulty_level: DifficultyLevel
    team_range: tuple[int, int]
    extra_slot_range: tuple[int, int]
    round_robin_modes: tuple[RoundRobinMode, ...]
    hard_constraint_range: tuple[int, int]
    soft_constraint_range: tuple[int, int]
    density_range: tuple[float, float]
    penalty_weight_range: tuple[int, int]


DIFFICULTY_PRESETS: dict[DifficultyLevel, DifficultyPreset] = {
    "easy": DifficultyPreset(
        difficulty_level="easy",
        team_range=(4, 6),
        extra_slot_range=(0, 1),
        round_robin_modes=("single",),
        hard_constraint_range=(2, 4),
        soft_constraint_range=(1, 3),
        density_range=(0.20, 0.35),
        penalty_weight_range=(5, 15),
    ),
    "medium": DifficultyPreset(
        difficulty_level="medium",
        team_range=(6, 8),
        extra_slot_range=(1, 2),
        round_robin_modes=("single", "double"),
        hard_constraint_range=(4, 7),
        soft_constraint_range=(3, 5),
        density_range=(0.35, 0.55),
        penalty_weight_range=(10, 30),
    ),
    "hard": DifficultyPreset(
        difficulty_level="hard",
        team_range=(8, 12),
        extra_slot_range=(1, 3),
        round_robin_modes=("double",),
        hard_constraint_range=(7, 11),
        soft_constraint_range=(5, 8),
        density_range=(0.55, 0.80),
        penalty_weight_range=(20, 60),
    ),
}


@dataclass(frozen=True, slots=True)
class SyntheticTeam:

    # One synthetic team participating in the generated instance.
    identifier: str
    name: str
    region: str
    venue_id: str
    venue_name: str
    venue_group: str


@dataclass(frozen=True, slots=True)
class SyntheticSlot:

    # One generated calendar slot.
    identifier: str
    name: str
    sequence: int
    phase: str
    slot_kind: str


@dataclass(frozen=True, slots=True)
class SyntheticMeeting:

    # One scheduled round-robin meeting description.
    identifier: str
    home_team: str
    away_team: str
    slot_id: str
    round_number: int
    leg: int


@dataclass(frozen=True, slots=True)
class SyntheticConstraint:

    # One structured synthetic constraint.
    identifier: str
    category: str
    tag: str
    type_name: str
    weight: int
    description: str
    team_ids: tuple[str, ...] = ()
    slot_ids: tuple[str, ...] = ()
    parameters: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True)
class GenerationContext:

    # All structural ingredients used to build one XML instance.
    spec: "DemoInstanceSpec"
    teams: tuple[SyntheticTeam, ...]
    slots: tuple[SyntheticSlot, ...]
    meetings: tuple[SyntheticMeeting, ...]
    constraints: tuple[SyntheticConstraint, ...]


@dataclass(slots=True)
class DemoInstanceSpec:

    # Specification and metadata for one generated synthetic instance.
    instance_name: str
    file_name: str
    profile_name: str
    difficulty_level: DifficultyLevel
    round_robin_mode: RoundRobinMode
    team_count: int
    slot_count: int
    meeting_count: int
    hard_constraint_count: int
    soft_constraint_count: int
    constraint_count: int
    constraint_density: float
    penalty_weight_range: tuple[int, int]
    random_seed: int
    generation_timestamp: str
    synthetic: bool = True


@dataclass(slots=True)
class DemoGenerationResult:

    # Summary of one synthetic generation run.
    output_folder: Path
    manifest_path: Path
    instance_count: int
    random_seed: int
    generation_timestamp: str
    instances: list[DemoInstanceSpec]


def generate_demo_instances(
    output_folder: str | Path = DEFAULT_OUTPUT_FOLDER,
    manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
    instance_count: int = 12,
    random_seed: int = 42,
    *,
    difficulty_level: DifficultyLevel | str | None = None,
    team_count: int | None = None,
    slot_count: int | None = None,
    round_robin_mode: RoundRobinMode | str | None = None,
    hard_constraint_count: int | None = None,
    soft_constraint_count: int | None = None,
    constraint_density: float | None = None,
    penalty_weight_range: tuple[int, int] | None = None,
    generation_timestamp: str | None = None,
) -> DemoGenerationResult:

    # Generate reproducible, structurally plausible RobinX-like XML instances.
    if instance_count <= 0:
        raise ValueError("instance_count must be positive.")

    requested_difficulty = _normalize_difficulty_level(difficulty_level) if difficulty_level is not None else None
    requested_mode = _normalize_round_robin_mode(round_robin_mode) if round_robin_mode is not None else None

    if team_count is not None and team_count < 4:
        raise ValueError("team_count must be at least 4 for a meaningful tournament instance.")
    if hard_constraint_count is not None and hard_constraint_count < 0:
        raise ValueError("hard_constraint_count must be non-negative.")
    if soft_constraint_count is not None and soft_constraint_count < 0:
        raise ValueError("soft_constraint_count must be non-negative.")

    validated_density = _validate_constraint_density(constraint_density)
    validated_penalty_range = _validate_penalty_weight_range(penalty_weight_range)
    resolved_timestamp = _resolve_generation_timestamp(generation_timestamp)

    output_path = Path(output_folder)
    manifest_output_path = Path(manifest_path)
    output_path.mkdir(parents=True, exist_ok=True)
    manifest_output_path.parent.mkdir(parents=True, exist_ok=True)
    _clear_existing_demo_instances(output_path)

    instances: list[DemoInstanceSpec] = []
    for index in range(instance_count):
        instance_seed = random_seed + (index * 9_973)
        rng = random.Random(instance_seed)
        preset = DIFFICULTY_PRESETS[_resolve_difficulty_for_index(index, requested_difficulty)]
        spec = _build_instance_spec(
            index=index,
            preset=preset,
            rng=rng,
            instance_seed=instance_seed,
            generation_timestamp=resolved_timestamp,
            team_count=team_count,
            slot_count=slot_count,
            round_robin_mode=requested_mode,
            hard_constraint_count=hard_constraint_count,
            soft_constraint_count=soft_constraint_count,
            constraint_density=validated_density,
            penalty_weight_range=validated_penalty_range,
        )
        context = _build_generation_context(spec, rng)
        tree = _build_instance_tree(context)
        tree.write(output_path / spec.file_name, encoding="utf-8", xml_declaration=True)
        instances.append(spec)

    payload = {
        "instance_count": instance_count,
        "random_seed": random_seed,
        "generation_timestamp": resolved_timestamp,
        "output_folder": output_path.as_posix(),
        "generation_parameters": {
            "difficulty_level": requested_difficulty or "mixed",
            "team_count": team_count,
            "slot_count": slot_count,
            "round_robin_mode": requested_mode,
            "hard_constraint_count": hard_constraint_count,
            "soft_constraint_count": soft_constraint_count,
            "constraint_density": validated_density,
            "penalty_weight_range": list(validated_penalty_range) if validated_penalty_range else None,
        },
        "instances": [asdict(instance) for instance in instances],
    }
    manifest_output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return DemoGenerationResult(
        output_folder=output_path,
        manifest_path=manifest_output_path,
        instance_count=instance_count,
        random_seed=random_seed,
        generation_timestamp=resolved_timestamp,
        instances=instances,
    )


def _build_instance_spec(
    *,
    index: int,
    preset: DifficultyPreset,
    rng: random.Random,
    instance_seed: int,
    generation_timestamp: str,
    team_count: int | None,
    slot_count: int | None,
    round_robin_mode: RoundRobinMode | None,
    hard_constraint_count: int | None,
    soft_constraint_count: int | None,
    constraint_density: float | None,
    penalty_weight_range: tuple[int, int] | None,
) -> DemoInstanceSpec:

    # Build one deterministic instance specification.
    resolved_team_count = team_count or rng.randint(*preset.team_range)
    resolved_mode = round_robin_mode or rng.choice(preset.round_robin_modes)
    minimum_slot_count = _minimum_required_slots(resolved_team_count, resolved_mode)
    if slot_count is not None and slot_count < minimum_slot_count:
        raise ValueError(
            "slot_count must be at least the minimum required for the chosen round-robin mode.",
        )

    extra_slots = rng.randint(*preset.extra_slot_range)
    resolved_slot_count = slot_count if slot_count is not None else minimum_slot_count + extra_slots
    resolved_hard_constraints = (
        hard_constraint_count
        if hard_constraint_count is not None
        else rng.randint(*preset.hard_constraint_range)
    )
    resolved_soft_constraints = (
        soft_constraint_count
        if soft_constraint_count is not None
        else rng.randint(*preset.soft_constraint_range)
    )
    resolved_density = (
        round(constraint_density, 2)
        if constraint_density is not None
        else round(rng.uniform(*preset.density_range), 2)
    )
    resolved_penalty_range = penalty_weight_range or preset.penalty_weight_range
    meeting_count = _meeting_count(resolved_team_count, resolved_mode)

    instance_number = index + 1
    instance_name = (
        f"synthetic_{preset.difficulty_level}_{resolved_team_count:02d}t_"
        f"{resolved_mode}_{instance_number:02d}"
    )
    return DemoInstanceSpec(
        instance_name=instance_name,
        file_name=f"{instance_name}.xml",
        profile_name=preset.difficulty_level,
        difficulty_level=preset.difficulty_level,
        round_robin_mode=resolved_mode,
        team_count=resolved_team_count,
        slot_count=resolved_slot_count,
        meeting_count=meeting_count,
        hard_constraint_count=resolved_hard_constraints,
        soft_constraint_count=resolved_soft_constraints,
        constraint_count=resolved_hard_constraints + resolved_soft_constraints,
        constraint_density=resolved_density,
        penalty_weight_range=resolved_penalty_range,
        random_seed=instance_seed,
        generation_timestamp=generation_timestamp,
    )


def _build_generation_context(spec: DemoInstanceSpec, rng: random.Random) -> GenerationContext:

    # Build the structural data used to serialize one synthetic instance.
    teams = _build_teams(spec.team_count, spec.difficulty_level, spec.constraint_density, rng)
    rounds = _generate_round_robin_rounds([team.identifier for team in teams], spec.round_robin_mode)
    round_slot_indices = _distribute_round_slots(len(rounds), spec.slot_count)
    slots = _build_slots(spec.slot_count, round_slot_indices)
    meetings = _build_meetings(rounds, slots, round_slot_indices, spec.round_robin_mode)
    constraints = _build_constraints(spec, teams, slots, meetings, rng)
    return GenerationContext(
        spec=spec,
        teams=teams,
        slots=slots,
        meetings=meetings,
        constraints=constraints,
    )


def _build_instance_tree(context: GenerationContext) -> ET.ElementTree:

    # Serialize one synthetic generation context into RobinX-like XML.
    spec = context.spec
    root = ET.Element(
        "Instance",
        attrib={
            "name": spec.instance_name,
            "synthetic": "true",
            "difficulty": spec.difficulty_level,
        },
    )

    metadata = ET.SubElement(root, "MetaData")
    ET.SubElement(metadata, "Name").text = spec.instance_name
    ET.SubElement(metadata, "Description").text = (
        "Synthetic RobinX-like sports scheduling instance for development, smoke tests, "
        "controlled experiments, and the local dashboard. It is not equivalent to ITC2021 "
        "benchmark data."
    )
    ET.SubElement(metadata, "Synthetic").text = "true"
    ET.SubElement(metadata, "GeneratedAt").text = spec.generation_timestamp
    ET.SubElement(metadata, "GenerationSeed").text = str(spec.random_seed)
    ET.SubElement(metadata, "Difficulty").text = spec.difficulty_level
    ET.SubElement(metadata, "RoundRobinMode").text = spec.round_robin_mode
    ET.SubElement(metadata, "ObjectiveName").text = _OBJECTIVE_NAME
    ET.SubElement(metadata, "ObjectiveSense").text = _OBJECTIVE_SENSE

    major_parameters = ET.SubElement(metadata, "GenerationParameters")
    ET.SubElement(major_parameters, "TeamCount").text = str(spec.team_count)
    ET.SubElement(major_parameters, "SlotCount").text = str(spec.slot_count)
    ET.SubElement(major_parameters, "HardConstraintCount").text = str(spec.hard_constraint_count)
    ET.SubElement(major_parameters, "SoftConstraintCount").text = str(spec.soft_constraint_count)
    ET.SubElement(major_parameters, "ConstraintDensity").text = f"{spec.constraint_density:.2f}"
    ET.SubElement(major_parameters, "PenaltyWeightMin").text = str(spec.penalty_weight_range[0])
    ET.SubElement(major_parameters, "PenaltyWeightMax").text = str(spec.penalty_weight_range[1])

    ET.SubElement(
        root,
        "Objective",
        attrib={
            "name": _OBJECTIVE_NAME,
            "sense": _OBJECTIVE_SENSE,
        },
    )
    ET.SubElement(
        root,
        "Format",
        attrib={
            "competition": "round_robin",
            "mode": spec.round_robin_mode,
            "requiredMeetings": str(spec.meeting_count),
            "minimumSlots": str(_minimum_required_slots(spec.team_count, spec.round_robin_mode)),
        },
    )

    venues = _unique_venues(context.teams)
    resources = ET.SubElement(root, "Resources")
    venue_section = ET.SubElement(resources, "Venues", attrib={"count": str(len(venues))})
    for venue_id, venue_name, venue_group in venues:
        ET.SubElement(
            venue_section,
            "Venue",
            attrib={
                "id": venue_id,
                "name": venue_name,
                "group": venue_group,
            },
        )

    teams_element = ET.SubElement(root, "Teams", attrib={"count": str(spec.team_count)})
    for team in context.teams:
        ET.SubElement(
            teams_element,
            "Team",
            attrib={
                "id": team.identifier,
                "name": team.name,
                "region": team.region,
                "venue": team.venue_id,
            },
        )

    slots_element = ET.SubElement(root, "Slots", attrib={"count": str(spec.slot_count)})
    for slot in context.slots:
        ET.SubElement(
            slots_element,
            "Slot",
            attrib={
                "id": slot.identifier,
                "name": slot.name,
                "sequence": str(slot.sequence),
                "phase": slot.phase,
                "kind": slot.slot_kind,
            },
        )

    meetings_element = ET.SubElement(root, "Meetings", attrib={"count": str(spec.meeting_count)})
    for meeting in context.meetings:
        ET.SubElement(
            meetings_element,
            "Meeting",
            attrib={
                "id": meeting.identifier,
                "home": meeting.home_team,
                "away": meeting.away_team,
                "slot": meeting.slot_id,
                "round": str(meeting.round_number),
                "leg": str(meeting.leg),
            },
        )

    constraints_element = ET.SubElement(root, "Constraints", attrib={"count": str(spec.constraint_count)})
    for constraint in context.constraints:
        attributes = {
            "id": constraint.identifier,
            "category": constraint.category,
            "tag": constraint.tag,
            "type": constraint.type_name,
            "weight": str(constraint.weight),
        }
        for key, value in constraint.parameters:
            attributes[key] = value

        constraint_element = ET.SubElement(constraints_element, "Constraint", attrib=attributes)
        ET.SubElement(constraint_element, "Description").text = constraint.description

        if constraint.team_ids:
            team_refs = ET.SubElement(constraint_element, "TeamRefs")
            for team_id in constraint.team_ids:
                ET.SubElement(team_refs, "TeamRef", attrib={"ref": team_id})

        if constraint.slot_ids:
            slot_refs = ET.SubElement(constraint_element, "SlotRefs")
            for slot_id in constraint.slot_ids:
                ET.SubElement(slot_refs, "SlotRef", attrib={"ref": slot_id})

    return ET.ElementTree(root)


def _build_teams(
    team_count: int,
    difficulty_level: DifficultyLevel,
    constraint_density: float,
    rng: random.Random,
) -> tuple[SyntheticTeam, ...]:

    # Build teams with regions and venue assignments.
    markets = list(_TEAM_MARKETS)
    suffixes = list(_TEAM_SUFFIXES)
    rng.shuffle(markets)
    rng.shuffle(suffixes)

    team_rows: list[dict[str, str]] = []
    for index in range(team_count):
        market = markets[index % len(markets)]
        suffix = suffixes[index % len(suffixes)]
        if index >= len(markets):
            market = f"{market} {index + 1}"
        team_rows.append(
            {
                "identifier": f"T{index + 1}",
                "name": f"{market} {suffix}",
                "region": _REGIONS[index % len(_REGIONS)],
                "venue_id": f"V{index + 1}",
                "venue_name": f"{market} Stadium",
                "venue_group": f"VG{index + 1}",
            }
        )

    shared_pair_count = _shared_venue_pair_count(team_count, difficulty_level, constraint_density)
    available_indices = list(range(team_count))
    rng.shuffle(available_indices)
    for pair_index in range(shared_pair_count):
        if len(available_indices) < 2:
            break
        first_index = available_indices.pop()
        second_index = available_indices.pop()
        shared_venue_id = f"VS{pair_index + 1}"
        shared_venue_name = f"Shared Municipal Arena {pair_index + 1}"
        shared_group = f"VGS{pair_index + 1}"
        for team_index in (first_index, second_index):
            team_rows[team_index]["venue_id"] = shared_venue_id
            team_rows[team_index]["venue_name"] = shared_venue_name
            team_rows[team_index]["venue_group"] = shared_group

    return tuple(SyntheticTeam(**team_row) for team_row in team_rows)


def _build_slots(
    slot_count: int,
    round_slot_indices: list[int],
) -> tuple[SyntheticSlot, ...]:

    # Build calendar slots and mark which ones host round-robin rounds.
    match_slot_indices = set(round_slot_indices)
    match_counter = 0
    buffer_counter = 0
    slots: list[SyntheticSlot] = []
    for index in range(slot_count):
        is_match_slot = index in match_slot_indices
        if is_match_slot:
            match_counter += 1
            name = f"Round {match_counter}"
        else:
            buffer_counter += 1
            name = f"Buffer Window {buffer_counter}"

        slots.append(
            SyntheticSlot(
                identifier=f"S{index + 1}",
                name=name,
                sequence=index + 1,
                phase=_slot_phase(index, slot_count),
                slot_kind="match" if is_match_slot else "buffer",
            )
        )
    return tuple(slots)


def _build_meetings(
    rounds: list[list[tuple[str, str]]],
    slots: tuple[SyntheticSlot, ...],
    round_slot_indices: list[int],
    round_robin_mode: RoundRobinMode,
) -> tuple[SyntheticMeeting, ...]:

    # Build meeting records from generated round-robin rounds.
    meetings: list[SyntheticMeeting] = []
    slot_lookup = {index: slots[index].identifier for index in round_slot_indices}
    base_round_count = len(rounds) if round_robin_mode == "single" else len(rounds) // 2

    meeting_index = 0
    for round_number, pairings in enumerate(rounds, start=1):
        slot_id = slot_lookup[round_slot_indices[round_number - 1]]
        leg = 1 if round_number <= base_round_count else 2
        for home_team, away_team in pairings:
            meeting_index += 1
            meetings.append(
                SyntheticMeeting(
                    identifier=f"M{meeting_index}",
                    home_team=home_team,
                    away_team=away_team,
                    slot_id=slot_id,
                    round_number=round_number,
                    leg=leg,
                )
            )

    return tuple(meetings)


def _build_constraints(
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
) -> tuple[SyntheticConstraint, ...]:

    # Build plausible hard and soft constraint sets.
    constraints: list[SyntheticConstraint] = []
    next_identifier = 1
    for index in range(spec.hard_constraint_count):
        builder = _HARD_CONSTRAINT_BUILDERS[index % len(_HARD_CONSTRAINT_BUILDERS)]
        constraints.append(builder(next_identifier, spec, teams, slots, meetings, rng, True))
        next_identifier += 1

    for index in range(spec.soft_constraint_count):
        builder = _SOFT_CONSTRAINT_BUILDERS[index % len(_SOFT_CONSTRAINT_BUILDERS)]
        constraints.append(builder(next_identifier, spec, teams, slots, meetings, rng, False))
        next_identifier += 1

    return tuple(constraints)


def _build_capacity_constraint(
    identifier: int,
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
    is_hard: bool,
) -> SyntheticConstraint:

    # Limit home hosting load over a slot window.
    selected_teams = _pick_team_subset(
        [team.identifier for team in teams],
        spec.constraint_density,
        rng,
        min_size=1,
        max_size=min(3, len(teams)),
    )
    selected_slots = _pick_slot_window(
        [slot.identifier for slot in slots if slot.slot_kind == "match"],
        spec.constraint_density,
        rng,
        min_size=2,
        max_size=min(6, len(slots)),
    )
    max_home_games = max(1, len(selected_slots) // 2)
    return SyntheticConstraint(
        identifier=f"C{identifier}",
        category="Capacity",
        tag="HomeCapacity",
        type_name="Hard" if is_hard else "Soft",
        weight=_constraint_weight(spec.penalty_weight_range, rng, is_hard),
        description=(
            "Selected clubs have a capped number of home matches in the referenced slot window."
        ),
        team_ids=selected_teams,
        slot_ids=selected_slots,
        parameters=(
            ("scope", "home"),
            ("max_home_games", str(max_home_games)),
            ("density", f"{spec.constraint_density:.2f}"),
        ),
    )


def _build_availability_constraint(
    identifier: int,
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
    is_hard: bool,
) -> SyntheticConstraint:

    # Represent team or venue unavailability across a small slot set.
    selected_teams = _pick_team_subset(
        [team.identifier for team in teams],
        spec.constraint_density,
        rng,
        min_size=1,
        max_size=min(2, len(teams)),
    )
    selected_slots = _pick_slot_window(
        [slot.identifier for slot in slots],
        spec.constraint_density,
        rng,
        min_size=1,
        max_size=min(4, len(slots)),
    )
    return SyntheticConstraint(
        identifier=f"C{identifier}",
        category="Availability",
        tag="TeamUnavailable",
        type_name="Hard" if is_hard else "Soft",
        weight=_constraint_weight(spec.penalty_weight_range, rng, is_hard),
        description="Selected clubs are unavailable in the referenced calendar slots.",
        team_ids=selected_teams,
        slot_ids=selected_slots,
        parameters=(
            ("availability", "unavailable"),
            ("resource", "team"),
        ),
    )


def _build_shared_venue_constraint(
    identifier: int,
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
    is_hard: bool,
) -> SyntheticConstraint:

    # Avoid simultaneous home matches for teams sharing a venue.
    selected_teams = _shared_venue_teams(teams) or _pick_team_subset(
        [team.identifier for team in teams],
        spec.constraint_density,
        rng,
        min_size=2,
        max_size=2,
    )
    selected_slots = _pick_slot_window(
        [slot.identifier for slot in slots if slot.slot_kind == "match"],
        spec.constraint_density,
        rng,
        min_size=2,
        max_size=min(6, len(slots)),
    )
    return SyntheticConstraint(
        identifier=f"C{identifier}",
        category="Venue",
        tag="SharedVenue",
        type_name="Hard" if is_hard else "Soft",
        weight=_constraint_weight(spec.penalty_weight_range, rng, is_hard),
        description="Teams that share a venue should not host simultaneously in the same slot.",
        team_ids=selected_teams,
        slot_ids=selected_slots,
        parameters=(
            ("scope", "home_conflict"),
            ("venue_dependency", "shared"),
        ),
    )


def _build_separation_constraint(
    identifier: int,
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
    is_hard: bool,
) -> SyntheticConstraint:

    # Require a minimum separation between repeated meetings.
    selected_pair = _pick_meeting_pair(meetings, rng)
    min_gap = max(1, min(4, round(spec.constraint_density * 4)))
    return SyntheticConstraint(
        identifier=f"C{identifier}",
        category="Separation",
        tag="RematchGap",
        type_name="Hard" if is_hard else "Soft",
        weight=_constraint_weight(spec.penalty_weight_range, rng, is_hard),
        description="Repeated meetings between the referenced teams should be separated in time.",
        team_ids=selected_pair,
        parameters=(
            ("min_gap_slots", str(min_gap)),
            ("scope", "head_to_head"),
        ),
    )


def _build_break_constraint(
    identifier: int,
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
    is_hard: bool,
) -> SyntheticConstraint:

    # Cap home/away streak lengths.
    selected_teams = _pick_team_subset(
        [team.identifier for team in teams],
        spec.constraint_density,
        rng,
        min_size=1,
        max_size=min(2, len(teams)),
    )
    max_streak = 2 if is_hard else 3
    return SyntheticConstraint(
        identifier=f"C{identifier}",
        category="Break",
        tag="MaxConsecutiveHomeAway",
        type_name="Hard" if is_hard else "Soft",
        weight=_constraint_weight(spec.penalty_weight_range, rng, is_hard),
        description="Selected clubs should avoid long consecutive home or away streaks.",
        team_ids=selected_teams,
        parameters=(
            ("max_streak", str(max_streak)),
            ("pattern", "home_away"),
        ),
    )


def _build_fairness_constraint(
    identifier: int,
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
    is_hard: bool,
) -> SyntheticConstraint:

    # Promote balanced home-away exposure in the early season.
    match_slot_ids = [slot.identifier for slot in slots if slot.slot_kind == "match"]
    early_window = tuple(match_slot_ids[: max(2, len(match_slot_ids) // 2)]) if match_slot_ids else ()
    return SyntheticConstraint(
        identifier=f"C{identifier}",
        category="Fairness",
        tag="OpeningBalance",
        type_name="Hard" if is_hard else "Soft",
        weight=_constraint_weight(spec.penalty_weight_range, rng, is_hard),
        description="Home-away balance should stay controlled during the opening phase.",
        team_ids=tuple(team.identifier for team in teams),
        slot_ids=early_window,
        parameters=(
            ("balance_tolerance", "1" if is_hard else "2"),
            ("phase", "opening"),
        ),
    )


def _build_travel_constraint(
    identifier: int,
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
    is_hard: bool,
) -> SyntheticConstraint:

    # Penalize concentrated away travel for the same clubs.
    region = rng.choice(_REGIONS)
    region_team_ids = tuple(team.identifier for team in teams if team.region == region)
    if len(region_team_ids) < 2:
        region_team_ids = _pick_team_subset(
            [team.identifier for team in teams],
            spec.constraint_density,
            rng,
            min_size=2,
            max_size=min(4, len(teams)),
        )
    return SyntheticConstraint(
        identifier=f"C{identifier}",
        category="Travel",
        tag="AwayTripCompression",
        type_name="Hard" if is_hard else "Soft",
        weight=_constraint_weight(spec.penalty_weight_range, rng, is_hard),
        description="Regional clubs should avoid compressed clusters of away travel.",
        team_ids=region_team_ids,
        parameters=(
            ("target_region", region),
            ("preferred_gap", "2"),
        ),
    )


def _build_derby_constraint(
    identifier: int,
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
    is_hard: bool,
) -> SyntheticConstraint:

    # Shape derby placement toward later showcase slots.
    derby_pair = _pick_regional_pair(teams, rng)
    late_slots = _pick_late_slot_window(
        [slot.identifier for slot in slots if slot.slot_kind == "match"],
        spec.constraint_density,
    )
    return SyntheticConstraint(
        identifier=f"C{identifier}",
        category="Fairness",
        tag="DerbyWindow",
        type_name="Hard" if is_hard else "Soft",
        weight=_constraint_weight(spec.penalty_weight_range, rng, is_hard),
        description="Derby meetings are preferred in later showcase slots.",
        team_ids=derby_pair,
        slot_ids=late_slots,
        parameters=(
            ("preference", "late_window"),
            ("derby", "true"),
        ),
    )


def _build_rest_spacing_constraint(
    identifier: int,
    spec: DemoInstanceSpec,
    teams: tuple[SyntheticTeam, ...],
    slots: tuple[SyntheticSlot, ...],
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
    is_hard: bool,
) -> SyntheticConstraint:

    # Prefer extra rest between demanding fixtures.
    selected_teams = _pick_team_subset(
        [team.identifier for team in teams],
        spec.constraint_density,
        rng,
        min_size=2,
        max_size=min(3, len(teams)),
    )
    selected_slots = _pick_slot_window(
        [slot.identifier for slot in slots if slot.slot_kind == "match"],
        spec.constraint_density,
        rng,
        min_size=2,
        max_size=min(5, len(slots)),
    )
    return SyntheticConstraint(
        identifier=f"C{identifier}",
        category="Break",
        tag="RestSpacing",
        type_name="Hard" if is_hard else "Soft",
        weight=_constraint_weight(spec.penalty_weight_range, rng, is_hard),
        description="Selected clubs should receive spacing between demanding fixtures.",
        team_ids=selected_teams,
        slot_ids=selected_slots,
        parameters=(
            ("min_rest_slots", "1" if is_hard else "2"),
            ("scope", "fixture_spacing"),
        ),
    )


_HARD_CONSTRAINT_BUILDERS = (
    _build_capacity_constraint,
    _build_availability_constraint,
    _build_shared_venue_constraint,
    _build_separation_constraint,
    _build_break_constraint,
    _build_fairness_constraint,
)

_SOFT_CONSTRAINT_BUILDERS = (
    _build_break_constraint,
    _build_fairness_constraint,
    _build_travel_constraint,
    _build_derby_constraint,
    _build_rest_spacing_constraint,
    _build_capacity_constraint,
)


def _generate_round_robin_rounds(
    team_ids: list[str],
    round_robin_mode: RoundRobinMode,
) -> list[list[tuple[str, str]]]:

    # Generate round-robin pairings using a simple circle-method variant.
    rotation: list[str | None] = list(team_ids)
    if len(rotation) % 2 == 1:
        rotation.append(None)

    base_rounds: list[list[tuple[str, str]]] = []
    round_count = len(rotation) - 1
    for round_index in range(round_count):
        pairings: list[tuple[str, str]] = []
        for pair_index in range(len(rotation) // 2):
            left = rotation[pair_index]
            right = rotation[-(pair_index + 1)]
            if left is None or right is None:
                continue

            if (round_index + pair_index) % 2 == 0:
                home_team, away_team = left, right
            else:
                home_team, away_team = right, left

            if pair_index == 0 and round_index % 2 == 1:
                home_team, away_team = away_team, home_team

            pairings.append((home_team, away_team))

        base_rounds.append(pairings)
        rotation = [rotation[0], rotation[-1], *rotation[1:-1]]

    if round_robin_mode == "single":
        return base_rounds

    mirrored_rounds = [[(away_team, home_team) for home_team, away_team in pairings] for pairings in base_rounds]
    return base_rounds + mirrored_rounds


def _distribute_round_slots(required_rounds: int, slot_count: int) -> list[int]:

    # Spread required rounds across the available slot horizon.
    extra_slots = slot_count - required_rounds
    gaps_after_round = [0] * required_rounds
    for extra_index in range(extra_slots):
        target_index = ((extra_index + 1) * required_rounds) // (extra_slots + 1) - 1
        gaps_after_round[max(0, target_index)] += 1

    slot_indices: list[int] = []
    current_slot = 0
    for round_index in range(required_rounds):
        slot_indices.append(current_slot)
        current_slot += 1 + gaps_after_round[round_index]
    return slot_indices


def _minimum_required_slots(team_count: int, round_robin_mode: RoundRobinMode = "single") -> int:

    # Return the minimum slot count for the requested round-robin structure.
    if team_count <= 1:
        return 0

    single_round_slots = team_count if team_count % 2 == 1 else team_count - 1
    if round_robin_mode == "single":
        return single_round_slots
    return single_round_slots * 2


def _meeting_count(team_count: int, round_robin_mode: RoundRobinMode) -> int:

    # Return the number of meetings implied by the round-robin mode.
    pair_count = team_count * (team_count - 1) // 2
    return pair_count if round_robin_mode == "single" else pair_count * 2


def _resolve_difficulty_for_index(
    index: int,
    requested_difficulty: DifficultyLevel | None,
) -> DifficultyLevel:

    # Resolve the preset used for a given generated instance.
    if requested_difficulty is not None:
        return requested_difficulty
    return _DEFAULT_DIFFICULTY_SEQUENCE[index % len(_DEFAULT_DIFFICULTY_SEQUENCE)]


def _normalize_difficulty_level(value: str) -> DifficultyLevel:

    # Normalize a difficulty label.
    normalized = value.strip().casefold()
    if normalized not in DIFFICULTY_PRESETS:
        raise ValueError("difficulty_level must be one of: easy, medium, hard.")
    return normalized  # type: ignore[return-value]


def _normalize_round_robin_mode(value: str) -> RoundRobinMode:

    # Normalize the requested round-robin mode.
    normalized = value.strip().casefold()
    if normalized not in {"single", "double"}:
        raise ValueError("round_robin_mode must be either 'single' or 'double'.")
    return normalized  # type: ignore[return-value]


def _validate_constraint_density(value: float | None) -> float | None:

    # Validate a constraint density parameter.
    if value is None:
        return None
    if not 0.0 < value <= 1.0:
        raise ValueError("constraint_density must be in the interval (0.0, 1.0].")
    return value


def _validate_penalty_weight_range(
    value: tuple[int, int] | None,
) -> tuple[int, int] | None:

    # Validate a penalty weight range override.
    if value is None:
        return None
    lower, upper = value
    if lower <= 0 or upper <= 0 or lower > upper:
        raise ValueError("penalty_weight_range must contain two positive integers in ascending order.")
    return (lower, upper)


def _resolve_generation_timestamp(generation_timestamp: str | None) -> str:

    # Resolve one stable ISO timestamp for the generation run.
    if generation_timestamp is None:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    parsed = datetime.fromisoformat(generation_timestamp)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.isoformat(timespec="seconds")


def _pick_team_subset(
    team_ids: list[str],
    density: float,
    rng: random.Random,
    *,
    min_size: int,
    max_size: int,
) -> tuple[str, ...]:

    # Pick a reproducible team subset with density-driven scope size.
    target_size = max(min_size, round(len(team_ids) * density))
    target_size = min(max_size, max(min_size, target_size))
    shuffled = list(team_ids)
    rng.shuffle(shuffled)
    selected = sorted(shuffled[:target_size], key=_numeric_identifier_key)
    return tuple(selected)


def _pick_slot_window(
    slot_ids: list[str],
    density: float,
    rng: random.Random,
    *,
    min_size: int,
    max_size: int,
) -> tuple[str, ...]:

    # Pick a contiguous slot window with density-driven width.
    if not slot_ids:
        return ()

    target_size = max(min_size, round(len(slot_ids) * density))
    target_size = min(max_size, max(min_size, target_size))
    target_size = min(target_size, len(slot_ids))
    if target_size == len(slot_ids):
        return tuple(slot_ids)

    start_index = rng.randint(0, len(slot_ids) - target_size)
    return tuple(slot_ids[start_index : start_index + target_size])


def _pick_late_slot_window(slot_ids: list[str], density: float) -> tuple[str, ...]:

    # Pick a late-season slot window for showcase constraints.
    if not slot_ids:
        return ()

    target_size = max(2, round(len(slot_ids) * max(0.25, density / 2)))
    target_size = min(target_size, len(slot_ids))
    return tuple(slot_ids[-target_size:])


def _pick_meeting_pair(
    meetings: tuple[SyntheticMeeting, ...],
    rng: random.Random,
) -> tuple[str, str]:

    # Pick one unordered team pair that appears in the meeting list.
    unique_pairs = sorted(
        {
            tuple(sorted((meeting.home_team, meeting.away_team), key=_numeric_identifier_key))
            for meeting in meetings
        },
        key=lambda pair: (_numeric_identifier_key(pair[0]), _numeric_identifier_key(pair[1])),
    )
    return unique_pairs[rng.randrange(len(unique_pairs))]


def _pick_regional_pair(
    teams: tuple[SyntheticTeam, ...],
    rng: random.Random,
) -> tuple[str, str]:

    # Pick a derby-style pair, preferring teams from the same region.
    regional_pairs: list[tuple[str, str]] = []
    for index, first_team in enumerate(teams):
        for second_team in teams[index + 1 :]:
            if first_team.region == second_team.region:
                regional_pairs.append((first_team.identifier, second_team.identifier))

    if regional_pairs:
        return regional_pairs[rng.randrange(len(regional_pairs))]

    return (teams[0].identifier, teams[1].identifier)


def _shared_venue_pair_count(
    team_count: int,
    difficulty_level: DifficultyLevel,
    density: float,
) -> int:

    # Estimate how many shared venue pairs should exist.
    if team_count < 6:
        return 0
    baseline = 0 if difficulty_level == "easy" else 1
    return min(team_count // 4, baseline + int(round(density * 2)))


def _shared_venue_teams(teams: tuple[SyntheticTeam, ...]) -> tuple[str, ...]:

    # Return one pair of teams that share a venue, when available.
    by_venue: dict[str, list[str]] = {}
    for team in teams:
        by_venue.setdefault(team.venue_id, []).append(team.identifier)

    shared_groups = [identifiers for identifiers in by_venue.values() if len(identifiers) >= 2]
    if not shared_groups:
        return ()

    selected = sorted(shared_groups[0][:2], key=_numeric_identifier_key)
    return tuple(selected)


def _unique_venues(teams: tuple[SyntheticTeam, ...]) -> tuple[tuple[str, str, str], ...]:

    # Return unique venue rows for XML serialization.
    seen: set[str] = set()
    venues: list[tuple[str, str, str]] = []
    for team in teams:
        if team.venue_id in seen:
            continue
        seen.add(team.venue_id)
        venues.append((team.venue_id, team.venue_name, team.venue_group))
    return tuple(venues)


def _constraint_weight(
    penalty_weight_range: tuple[int, int],
    rng: random.Random,
    is_hard: bool,
) -> int:

    # Return a deterministic constraint weight.
    if is_hard:
        return 0
    lower, upper = penalty_weight_range
    return rng.randint(lower, upper)


def _slot_phase(index: int, slot_count: int) -> str:

    # Assign a coarse calendar phase to each slot.
    ratio = (index + 1) / max(1, slot_count)
    if ratio <= 0.34:
        return "opening"
    if ratio <= 0.67:
        return "midseason"
    return "run_in"


def _numeric_identifier_key(value: str) -> int:

    # Sort identifiers such as ``T10`` and ``S2`` numerically.
    digits = "".join(character for character in value if character.isdigit())
    return int(digits) if digits else 0


def _clear_existing_demo_instances(output_folder: Path) -> None:

    # Remove previously generated XML files from the target folder.
    for xml_file in output_folder.glob("*.xml"):
        xml_file.unlink()
