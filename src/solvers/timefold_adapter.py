"""Adapter layer between parsed instances and the external Timefold exchange format.

The adapter intentionally models only a small, explicit subset of the parsed
RobinX / ITC2021 instance:

- teams
- slots
- inferred round-robin matches
- declared constraint families as metadata only

Current limitations are deliberate and thesis-baseline oriented:

- instance-specific constraint families such as capacity, break, venue,
  fairness, travel, and richer home/away rules are ignored by the adapter
- the adapter approximates the problem as a compact single or double
  round-robin structure inferred from teams and slots
- slot semantics are preserved only as stable labels and indices, not as full
  calendar or venue models
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Literal, Mapping


RoundRobinMode = Literal["single", "double"]


@dataclass(frozen=True, slots=True)
class TimefoldAdapterLimitations:
    """Explicit statement of the current adapter scope and omissions."""

    supported_scope: tuple[str, ...]
    ignored_constraints: tuple[str, ...]
    approximated_behavior: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TimefoldTeam:
    """Stable team representation used in the Timefold exchange payload."""

    id: str
    name: str
    index: int


@dataclass(frozen=True, slots=True)
class TimefoldSlot:
    """Stable slot representation used in the Timefold exchange payload."""

    id: str
    name: str
    index: int


@dataclass(frozen=True, slots=True)
class TimefoldMatch:
    """One directed round-robin match required by the simplified adapter."""

    id: str
    home_team_index: int
    away_team_index: int
    home_team_id: str
    away_team_id: str
    home_team_name: str
    away_team_name: str
    leg: int


@dataclass(frozen=True, slots=True)
class TimefoldProblem:
    """Compact round-robin problem passed through the adapter layer."""

    instance_name: str
    round_robin_mode: RoundRobinMode
    teams: tuple[TimefoldTeam, ...]
    slots: tuple[TimefoldSlot, ...]
    matches: tuple[TimefoldMatch, ...]
    requested_slot_count: int
    minimum_required_slots: int
    constraint_families: tuple[str, ...]
    parser_notes: tuple[dict[str, str], ...]
    source_path: str | None
    limitations: TimefoldAdapterLimitations


@dataclass(frozen=True, slots=True)
class TimefoldAssignment:
    """Normalized match-to-slot assignment read from a Timefold solution."""

    match_id: str
    slot_index: int


@dataclass(frozen=True, slots=True)
class InternalScheduleEntry:
    """Internal schedule representation returned by the adapter."""

    match_id: str
    slot_index: int
    slot_id: str
    slot_name: str
    leg: int
    home_team: str
    away_team: str


@dataclass(frozen=True, slots=True)
class InternalTimefoldSolution:
    """Normalized solution returned by the adapter before solver wrapping."""

    instance_name: str
    status: str
    feasible: bool
    objective_value: float | None
    runtime_seconds: float | None
    assignments: tuple[TimefoldAssignment, ...]
    schedule: tuple[InternalScheduleEntry, ...]
    used_slots: int
    metadata: dict[str, object]
    error_message: str | None


class TimefoldAdapterError(RuntimeError):
    """Base class for adapter-level conversion and validation failures."""


class TimefoldUnsupportedInstanceError(TimefoldAdapterError):
    """Raised when the external adapter marks an instance unsupported."""


class TimefoldInvalidSolutionError(TimefoldAdapterError):
    """Raised when a Timefold output cannot be normalized safely."""


TIMEFOLD_ADAPTER_LIMITATIONS = TimefoldAdapterLimitations(
    supported_scope=(
        "single_round_robin_structure",
        "double_round_robin_structure",
        "stable_team_slot_and_match_identifiers",
        "round_robin_solution_validation",
    ),
    ignored_constraints=(
        "capacity_constraints",
        "break_constraints",
        "venue_constraints",
        "travel_constraints",
        "fairness_constraints",
        "sequence_constraints",
        "soft_constraint_penalties",
    ),
    approximated_behavior=(
        "matches_are_inferred_from_team_set_and_round_robin_mode",
        "declared_constraint_families_are_exported_as_metadata_only",
        "slots_are_treated_as_simple_ordered_rounds_without_extra_semantics",
    ),
)


def describe_timefold_adapter_limitations() -> dict[str, list[str]]:
    """Return the current adapter limitations as a JSON-friendly mapping."""

    return {
        "supported_scope": list(TIMEFOLD_ADAPTER_LIMITATIONS.supported_scope),
        "ignored_constraints": list(TIMEFOLD_ADAPTER_LIMITATIONS.ignored_constraints),
        "approximated_behavior": list(TIMEFOLD_ADAPTER_LIMITATIONS.approximated_behavior),
    }


def build_timefold_problem(instance: object) -> TimefoldProblem:
    """Build a compact Timefold problem view from one parsed instance."""

    instance_name = _extract_instance_name(instance)
    round_robin_mode = _extract_round_robin_mode(instance)

    explicit_team_count = _safe_nonnegative_int(getattr(instance, "team_count", 0))
    teams = tuple(_build_teams(instance, explicit_team_count))
    minimum_required_slots = _minimum_required_slots(len(teams), round_robin_mode)
    requested_slot_count = _safe_nonnegative_int(getattr(instance, "slot_count", 0))
    slot_count = requested_slot_count if requested_slot_count > 0 else minimum_required_slots
    slots = tuple(_build_slots(instance, slot_count))
    matches = tuple(_build_matches(teams, round_robin_mode))

    constraint_families = tuple(sorted(_extract_constraint_families(instance)))
    parser_notes = tuple(_build_parser_notes(instance))
    source_path = _extract_source_path(instance)

    return TimefoldProblem(
        instance_name=instance_name,
        round_robin_mode=round_robin_mode,
        teams=teams,
        slots=slots,
        matches=matches,
        requested_slot_count=requested_slot_count,
        minimum_required_slots=minimum_required_slots,
        constraint_families=constraint_families,
        parser_notes=parser_notes,
        source_path=source_path,
        limitations=TIMEFOLD_ADAPTER_LIMITATIONS,
    )


def convert_instance_to_timefold_input(
    instance: object,
    *,
    time_limit_seconds: int = 60,
    random_seed: int = 42,
) -> dict[str, object]:
    """Convert one parsed instance directly into the Timefold input payload."""

    return convert_problem_to_timefold_input(
        build_timefold_problem(instance),
        time_limit_seconds=time_limit_seconds,
        random_seed=random_seed,
    )


def convert_problem_to_timefold_input(
    problem: TimefoldProblem,
    *,
    time_limit_seconds: int = 60,
    random_seed: int = 42,
) -> dict[str, object]:
    """Convert one prepared Timefold problem into the external JSON payload."""

    ignored_constraint_families = list(problem.constraint_families)
    limitations = describe_timefold_adapter_limitations()

    return {
        "schema": "timefold_round_robin_v1",
        "config": {
            "run": {
                "name": problem.instance_name,
                "timeLimitSeconds": max(0, int(time_limit_seconds)),
                "randomSeed": int(random_seed),
            }
        },
        "modelInput": {
            "instanceName": problem.instance_name,
            "roundRobinMode": problem.round_robin_mode,
            "teams": [
                {
                    "id": team.id,
                    "name": team.name,
                    "index": team.index,
                }
                for team in problem.teams
            ],
            "slots": [
                {
                    "id": slot.id,
                    "name": slot.name,
                    "index": slot.index,
                }
                for slot in problem.slots
            ],
            "matches": [
                {
                    "id": match.id,
                    "homeTeamId": match.home_team_id,
                    "awayTeamId": match.away_team_id,
                    "homeTeamName": match.home_team_name,
                    "awayTeamName": match.away_team_name,
                    "leg": match.leg,
                }
                for match in problem.matches
            ],
            "meetings": [
                {
                    "id": match.id,
                    "homeTeamId": match.home_team_id,
                    "awayTeamId": match.away_team_id,
                    "homeTeamName": match.home_team_name,
                    "awayTeamName": match.away_team_name,
                    "leg": match.leg,
                }
                for match in problem.matches
            ],
            "constraints": [
                {
                    "family": family,
                }
                for family in problem.constraint_families
            ],
            "metadata": {
                "requestedSlotCount": problem.requested_slot_count,
                "minimumRequiredSlots": problem.minimum_required_slots,
                "sourcePath": problem.source_path,
                "parserNotes": list(problem.parser_notes),
                "ignoredConstraintFamilies": ignored_constraint_families,
                "adapterLimitations": limitations,
            },
        },
    }


def convert_timefold_solution(
    problem: TimefoldProblem,
    payload: str | Mapping[str, object],
) -> InternalTimefoldSolution:
    """Convert a Timefold adapter response into the internal schedule format."""

    raw_payload = _parse_output_payload(payload)
    status = _extract_status(raw_payload)
    error_message = _extract_error_message(raw_payload)

    if status in {"UNSUPPORTED", "UNSUPPORTED_INSTANCE"}:
        raise TimefoldUnsupportedInstanceError(
            error_message or "The external Timefold adapter marked the instance unsupported."
        )

    feasible = _extract_feasible(raw_payload, status)
    runtime_seconds = _extract_optional_float(
        raw_payload,
        "runtime_seconds",
        "runtimeSeconds",
        "solveDurationSeconds",
    )
    metadata = _extract_output_metadata(raw_payload)
    objective_value = _extract_optional_float(raw_payload, "objective_value", "objectiveValue")
    assignments: tuple[TimefoldAssignment, ...] = tuple()
    schedule: tuple[InternalScheduleEntry, ...] = tuple()

    if feasible:
        assignments = _normalize_assignments(
            payload=_extract_schedule_payload(raw_payload),
            problem=problem,
        )
        _validate_assignments(problem, assignments)
        schedule = _build_internal_schedule(problem, assignments)
        if objective_value is None:
            objective_value = float(len({assignment.slot_index for assignment in assignments}))
            metadata["objective_source"] = "derived_used_slots"
    else:
        metadata["reported_infeasible"] = True

    external_score = _extract_text_value(raw_payload, "score", "bestScore")
    if external_score is not None:
        metadata["external_score"] = external_score

    return InternalTimefoldSolution(
        instance_name=problem.instance_name,
        status=status,
        feasible=feasible,
        objective_value=objective_value,
        runtime_seconds=runtime_seconds,
        assignments=assignments,
        schedule=schedule,
        used_slots=len({assignment.slot_index for assignment in assignments}),
        metadata=metadata,
        error_message=error_message,
    )


def schedule_to_solver_metadata(
    schedule: tuple[InternalScheduleEntry, ...],
) -> list[dict[str, object]]:
    """Convert the internal schedule representation into solver metadata rows."""

    return [
        {
            "meeting_id": entry.match_id,
            "slot_index": entry.slot_index,
            "slot": entry.slot_name,
            "slot_id": entry.slot_id,
            "leg": entry.leg,
            "home_team": entry.home_team,
            "away_team": entry.away_team,
            "team_1": entry.home_team,
            "team_2": entry.away_team,
        }
        for entry in schedule
    ]


def _build_teams(instance: object, explicit_team_count: int) -> list[TimefoldTeam]:
    """Build stable team identifiers from parsed teams or fallback labels."""

    teams = list(getattr(instance, "teams", []) or [])
    inferred_count = len(teams)
    team_count = explicit_team_count if explicit_team_count > 0 else inferred_count
    team_count = max(team_count, inferred_count)

    built_teams: list[TimefoldTeam] = []
    for index in range(team_count):
        team = teams[index] if index < inferred_count else None
        candidate_id = _first_non_empty(
            [
                getattr(team, "identifier", None) if team is not None else None,
                getattr(team, "name", None) if team is not None else None,
            ]
        )
        candidate_name = _first_non_empty(
            [
                getattr(team, "name", None) if team is not None else None,
                getattr(team, "identifier", None) if team is not None else None,
            ]
        )
        team_id = candidate_id or f"T{index + 1}"
        team_name = candidate_name or team_id
        built_teams.append(TimefoldTeam(id=team_id, name=team_name, index=index))
    return built_teams


def _build_slots(instance: object, slot_count: int) -> list[TimefoldSlot]:
    """Build stable slot identifiers from parsed slots or fallback labels."""

    slots = list(getattr(instance, "slots", []) or [])
    built_slots: list[TimefoldSlot] = []
    for index in range(slot_count):
        slot = slots[index] if index < len(slots) else None
        candidate_id = _first_non_empty(
            [
                getattr(slot, "identifier", None) if slot is not None else None,
                getattr(slot, "name", None) if slot is not None else None,
            ]
        )
        candidate_name = _first_non_empty(
            [
                getattr(slot, "name", None) if slot is not None else None,
                getattr(slot, "identifier", None) if slot is not None else None,
            ]
        )
        slot_id = candidate_id or f"S{index + 1}"
        slot_name = candidate_name or slot_id
        built_slots.append(TimefoldSlot(id=slot_id, name=slot_name, index=index))
    return built_slots


def _build_matches(
    teams: tuple[TimefoldTeam, ...],
    round_robin_mode: RoundRobinMode,
) -> list[TimefoldMatch]:
    """Build the canonical list of inferred round-robin matches."""

    matches: list[TimefoldMatch] = []
    match_index = 0
    for home_team_index, away_team_index in combinations(range(len(teams)), 2):
        home_team = teams[home_team_index]
        away_team = teams[away_team_index]
        matches.append(
            TimefoldMatch(
                id=f"M{match_index + 1}",
                home_team_index=home_team_index,
                away_team_index=away_team_index,
                home_team_id=home_team.id,
                away_team_id=away_team.id,
                home_team_name=home_team.name,
                away_team_name=away_team.name,
                leg=1,
            )
        )
        match_index += 1

        if round_robin_mode == "double":
            matches.append(
                TimefoldMatch(
                    id=f"M{match_index + 1}",
                    home_team_index=away_team_index,
                    away_team_index=home_team_index,
                    home_team_id=away_team.id,
                    away_team_id=home_team.id,
                    home_team_name=away_team.name,
                    away_team_name=home_team.name,
                    leg=2,
                )
            )
            match_index += 1
    return matches


def _build_parser_notes(instance: object) -> list[dict[str, str]]:
    """Convert structured parser notes into JSON-friendly dictionaries."""

    notes = list(getattr(instance, "parser_notes", []) or [])
    payload: list[dict[str, str]] = []
    for note in notes:
        code = _read_text_field(note, "code")
        message = _read_text_field(note, "message")
        severity = _read_text_field(note, "severity")
        if code is None and message is None and severity is None:
            continue
        payload.append(
            {
                "severity": severity or "info",
                "code": code or "parser_note",
                "message": message or "",
            }
        )
    return payload


def _parse_output_payload(payload: str | Mapping[str, object]) -> dict[str, object]:
    """Parse adapter output from JSON text or reuse an existing mapping."""

    if isinstance(payload, Mapping):
        return {str(key): value for key, value in payload.items()}

    text = payload.strip()
    if not text:
        raise TimefoldInvalidSolutionError("The external adapter produced an empty output payload.")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = _parse_text_output(text)

    if not isinstance(parsed, dict):
        raise TimefoldInvalidSolutionError(
            "The external adapter output must be a JSON object or key-value text."
        )
    return parsed


def _parse_text_output(text: str) -> dict[str, object]:
    """Parse the lightweight line-based Timefold adapter output format."""

    payload: dict[str, object] = {}
    assignments: list[dict[str, object]] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("assignment "):
            assignment: dict[str, object] = {}
            for token in line[len("assignment ") :].split():
                if "=" not in token:
                    continue
                key, value = token.split("=", 1)
                assignment[key.strip()] = value.strip()
            if assignment:
                assignments.append(assignment)
            continue

        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()

    if assignments:
        payload["schedule"] = assignments
    return payload


def _extract_status(payload: Mapping[str, object]) -> str:
    """Extract and normalize one adapter status string."""

    status = _extract_text_value(payload, "status", "solverStatus", "state")
    normalized = status.strip().upper() if status is not None else "UNKNOWN"
    return normalized or "UNKNOWN"


def _extract_feasible(payload: Mapping[str, object], status: str) -> bool:
    """Infer feasibility from explicit flags or the reported status."""

    explicit_flag = _extract_optional_bool(payload, "feasible", "isFeasible")
    if explicit_flag is not None:
        return explicit_flag
    return status in {"SOLVED", "OPTIMAL", "FEASIBLE", "SATISFIED"}


def _extract_schedule_payload(payload: Mapping[str, object]) -> list[object]:
    """Read the schedule list from supported output layouts."""

    for key in ("schedule", "assignments", "matches"):
        value = payload.get(key)
        if isinstance(value, list):
            return value

    model_output = payload.get("modelOutput")
    if isinstance(model_output, Mapping):
        for key in ("schedule", "assignments", "matches"):
            value = model_output.get(key)
            if isinstance(value, list):
                return value
    return []


def _extract_output_metadata(payload: Mapping[str, object]) -> dict[str, object]:
    """Extract adapter metadata while preserving additional output fields lightly."""

    metadata: dict[str, object] = {}
    for key in ("metadata", "solverMetadata"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            metadata.update({str(inner_key): inner_value for inner_key, inner_value in value.items()})
    return metadata


def _extract_error_message(payload: Mapping[str, object]) -> str | None:
    """Extract a readable adapter error message when present."""

    for key in ("error", "message", "detail"):
        value = payload.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _normalize_assignments(
    *,
    payload: list[object],
    problem: TimefoldProblem,
) -> tuple[TimefoldAssignment, ...]:
    """Normalize supported Timefold solution formats into internal assignments."""

    if not payload:
        raise TimefoldInvalidSolutionError("A feasible Timefold result must contain a non-empty schedule.")

    match_by_id = {match.id: match for match in problem.matches}
    match_id_by_key: dict[tuple[str, str, int], str] = {}
    for match in problem.matches:
        match_id_by_key[(match.home_team_id, match.away_team_id, match.leg)] = match.id
        match_id_by_key[(match.home_team_name, match.away_team_name, match.leg)] = match.id

    slot_index_by_text: dict[str, int] = {}
    for slot in problem.slots:
        slot_index_by_text[slot.id] = slot.index
        slot_index_by_text[slot.name] = slot.index
        slot_index_by_text[str(slot.index)] = slot.index
        slot_index_by_text[str(slot.index + 1)] = slot.index

    assignments: list[TimefoldAssignment] = []
    for raw_item in payload:
        if not isinstance(raw_item, Mapping):
            raise TimefoldInvalidSolutionError("Every schedule item must be a mapping.")

        match_id = _extract_text_value(raw_item, "match_id", "matchId", "meeting_id", "meetingId")
        if match_id is None:
            home_team = _extract_text_value(raw_item, "home_team_id", "homeTeamId", "home_team", "homeTeam")
            away_team = _extract_text_value(raw_item, "away_team_id", "awayTeamId", "away_team", "awayTeam")
            leg = _extract_optional_int(raw_item, "leg")
            normalized_leg = leg if leg is not None else 1
            if home_team is None or away_team is None:
                raise TimefoldInvalidSolutionError(
                    "Each schedule item must identify a match by match_id or by home/away teams."
                )
            match_id = match_id_by_key.get((home_team, away_team, normalized_leg))

        if match_id is None or match_id not in match_by_id:
            raise TimefoldInvalidSolutionError("The external adapter returned an unknown match identifier.")

        slot_index = _extract_optional_int(raw_item, "slot_index", "slotIndex")
        if slot_index is None:
            slot_text = _extract_text_value(raw_item, "slot_id", "slotId", "slot", "slotName")
            if slot_text is not None:
                slot_index = slot_index_by_text.get(slot_text)

        if slot_index is None or slot_index < 0 or slot_index >= len(problem.slots):
            raise TimefoldInvalidSolutionError("The external adapter returned an unknown slot reference.")

        assignments.append(TimefoldAssignment(match_id=match_id, slot_index=slot_index))

    return tuple(assignments)


def _validate_assignments(problem: TimefoldProblem, assignments: tuple[TimefoldAssignment, ...]) -> None:
    """Ensure the returned assignments are structurally valid for the simplified model."""

    expected_match_ids = {match.id for match in problem.matches}
    if len(assignments) != len(expected_match_ids):
        raise TimefoldInvalidSolutionError(
            f"The external adapter returned {len(assignments)} assignments for {len(expected_match_ids)} matches."
        )

    match_by_id = {match.id: match for match in problem.matches}
    seen_match_ids: set[str] = set()
    teams_per_slot: dict[int, set[int]] = {}

    for assignment in assignments:
        if assignment.match_id in seen_match_ids:
            raise TimefoldInvalidSolutionError("The external adapter assigned the same match multiple times.")
        seen_match_ids.add(assignment.match_id)

        match = match_by_id[assignment.match_id]
        slot_teams = teams_per_slot.setdefault(assignment.slot_index, set())
        if match.home_team_index in slot_teams or match.away_team_index in slot_teams:
            raise TimefoldInvalidSolutionError("The external adapter returned a team conflict within one slot.")
        slot_teams.add(match.home_team_index)
        slot_teams.add(match.away_team_index)

    if expected_match_ids - seen_match_ids:
        raise TimefoldInvalidSolutionError("The external adapter did not assign all required matches.")


def _build_internal_schedule(
    problem: TimefoldProblem,
    assignments: tuple[TimefoldAssignment, ...],
) -> tuple[InternalScheduleEntry, ...]:
    """Build the internal schedule representation from normalized assignments."""

    match_by_id = {match.id: match for match in problem.matches}
    schedule = [
        InternalScheduleEntry(
            match_id=assignment.match_id,
            slot_index=problem.slots[assignment.slot_index].index,
            slot_id=problem.slots[assignment.slot_index].id,
            slot_name=problem.slots[assignment.slot_index].name,
            leg=match_by_id[assignment.match_id].leg,
            home_team=match_by_id[assignment.match_id].home_team_name,
            away_team=match_by_id[assignment.match_id].away_team_name,
        )
        for assignment in assignments
    ]
    schedule.sort(key=lambda entry: (entry.slot_index, entry.match_id))
    return tuple(schedule)


def _extract_constraint_families(instance: object) -> set[str]:
    """Extract stable constraint-family labels from the parsed instance."""

    constraints = list(getattr(instance, "constraints", []) or [])
    families: set[str] = set()
    for constraint in constraints:
        for value in (
            _read_text_field(constraint, "category"),
            _read_text_field(constraint, "tag"),
            _read_text_field(constraint, "type_name"),
        ):
            if value:
                families.add(value)
    return families


def _extract_instance_name(instance: object) -> str:
    """Extract a readable instance name from common parsed-instance fields."""

    metadata = getattr(instance, "metadata", None)
    for candidate in (
        getattr(metadata, "name", None),
        getattr(instance, "instance_name", None),
        getattr(instance, "name", None),
    ):
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    source_path = _extract_source_path(instance)
    if source_path is not None:
        return Path(source_path).stem
    return instance.__class__.__name__


def _extract_source_path(instance: object) -> str | None:
    """Extract the source XML path when available."""

    metadata = getattr(instance, "metadata", None)
    source_path = getattr(metadata, "source_path", None)
    if isinstance(source_path, str) and source_path.strip():
        return source_path.strip()
    return None


def _extract_round_robin_mode(instance: object) -> RoundRobinMode:
    """Extract a normalized round-robin mode with a conservative fallback."""

    metadata = getattr(instance, "metadata", None)
    raw_value = _first_non_empty(
        [
            _read_text_field(instance, "round_robin_mode"),
            _read_text_field(metadata, "round_robin_mode"),
        ]
    )
    if raw_value is None:
        return "single"
    if "double" in raw_value.casefold():
        return "double"
    return "single"


def _minimum_required_slots(num_teams: int, round_robin_mode: RoundRobinMode) -> int:
    """Return the minimum number of slots implied by the round-robin mode."""

    if num_teams <= 1:
        return 0
    single_round_slots = num_teams if num_teams % 2 == 1 else num_teams - 1
    if round_robin_mode == "double":
        return single_round_slots * 2
    return single_round_slots


def _extract_text_value(source: Mapping[str, object], *keys: str) -> str | None:
    """Extract the first non-empty text value from a mapping."""

    for key in keys:
        value = source.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _extract_optional_bool(source: Mapping[str, object], *keys: str) -> bool | None:
    """Extract one boolean-like value from a mapping."""

    for key in keys:
        value = source.get(key)
        if isinstance(value, bool):
            return value
        if value is None:
            continue
        text = str(value).strip().casefold()
        if text in {"true", "1", "yes"}:
            return True
        if text in {"false", "0", "no"}:
            return False
    return None


def _extract_optional_int(source: Mapping[str, object], *keys: str) -> int | None:
    """Extract one integer-like value from a mapping."""

    for key in keys:
        value = source.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _extract_optional_float(source: Mapping[str, object], *keys: str) -> float | None:
    """Extract one float-like value from a mapping."""

    for key in keys:
        value = source.get(key)
        if value is None or isinstance(value, bool):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _read_text_field(value: object, field_name: str) -> str | None:
    """Read and normalize one text-like field from an object."""

    field_value = getattr(value, field_name, None)
    if isinstance(field_value, str) and field_value.strip():
        return field_value.strip()
    return None


def _first_non_empty(values: list[str | None]) -> str | None:
    """Return the first non-empty string from a list of candidates."""

    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _safe_nonnegative_int(value: object) -> int:
    """Convert a count-like value to a non-negative integer."""

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(0, value)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0
