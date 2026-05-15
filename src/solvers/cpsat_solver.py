"""CP-SAT round-robin baseline with explicit single/double-leg support."""

from __future__ import annotations

import time
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Literal

from ortools.sat.python import cp_model

from src.solvers.base import Solver, SolverResult


RoundRobinMode = Literal["single", "double"]
SupportLevel = Literal["supported", "partially_supported"]


@dataclass(frozen=True, slots=True)
class _MeetingDefinition:
    """One directed meeting that must be scheduled exactly once."""

    home_team_index: int
    away_team_index: int
    home_team_label: str
    away_team_label: str
    leg: int


@dataclass(frozen=True, slots=True)
class _ConstraintSupportSummary:
    """Audit-friendly summary of what the current baseline actually supports."""

    support_level: SupportLevel
    supported_capabilities: tuple[str, ...]
    declared_constraint_families: tuple[str, ...]
    unsupported_constraint_families: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _RoundRobinProblemData:
    """Internal round-robin data prepared from a parsed instance."""

    instance_name: str
    round_robin_mode: RoundRobinMode
    team_labels: tuple[str, ...]
    slot_labels: tuple[str, ...]
    meetings: tuple[_MeetingDefinition, ...]
    num_slots: int
    requested_slot_count: int
    minimum_required_slots: int
    constraint_support: _ConstraintSupportSummary


class CPSatSolver(Solver):
    """CP-SAT baseline for compact single and double round-robin schedules.

    The solver now supports two structural formats:

    - single round robin: one directed meeting per unordered pair
    - double round robin: two directed meetings per pair with opposite
      home/away orientation

    The modeled hard structure is still intentionally narrow:

    - every required meeting must be assigned exactly once
    - a team cannot play more than once in the same slot
    - the objective minimizes the number of used slots

    Parsed RobinX / ITC2021 constraint families are recorded for auditability
    but are not yet enforced directly in the model. When such constraints are
    present, the returned metadata marks the support level as partial rather
    than pretending full compliance.
    """

    def __init__(self, solver_name: str = "cpsat_round_robin") -> None:
        """Initialize the solver with a stable public name."""

        self.solver_name = solver_name

    def solve(
        self,
        instance: object,
        time_limit_seconds: int = 60,
        random_seed: int = 42,
    ) -> SolverResult:
        """Build and solve a compact round-robin CP-SAT model."""

        start_time = time.perf_counter()
        problem = _prepare_problem_data(instance)

        if len(problem.team_labels) <= 1:
            runtime_seconds = time.perf_counter() - start_time
            return SolverResult(
                solver_name=self.solver_name,
                instance_name=problem.instance_name,
                objective_value=0.0,
                runtime_seconds=runtime_seconds,
                feasible=True,
                status="TRIVIAL",
                solver_support_status=problem.constraint_support.support_level,
                scoring_status=_scoring_status(problem, feasible=True),
                modeling_scope=_modeling_scope(problem),
                scoring_notes=problem.constraint_support.notes,
                metadata=_result_metadata(
                    problem=problem,
                    schedule=[],
                    used_slots=0,
                    future_extensions=[
                        "instance_specific_constraint_modeling",
                        "soft_constraint_objectives",
                        "venue_and_travel_constraints",
                    ],
                ),
            )

        model = cp_model.CpModel()
        meeting_vars = _create_meeting_assignment_variables(model, problem)

        _add_meeting_assignment_constraints(model, problem, meeting_vars)
        _add_team_availability_constraints(model, problem, meeting_vars)
        slot_used = _add_compact_schedule_objective(model, problem, meeting_vars)

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(0.0, float(time_limit_seconds))
        solver.parameters.random_seed = random_seed
        solver.parameters.num_search_workers = 1

        status_code = solver.Solve(model)
        status_name = solver.StatusName(status_code)
        runtime_seconds = time.perf_counter() - start_time
        feasible = status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE)

        schedule = _extract_schedule(problem, meeting_vars, solver) if feasible else []
        objective_value = float(solver.ObjectiveValue()) if feasible else None

        return SolverResult(
            solver_name=self.solver_name,
            instance_name=problem.instance_name,
            objective_value=objective_value,
            runtime_seconds=runtime_seconds,
            feasible=feasible,
            status=status_name,
            solver_support_status=problem.constraint_support.support_level,
            scoring_status=_scoring_status(problem, feasible=feasible),
            modeling_scope=_modeling_scope(problem),
            scoring_notes=problem.constraint_support.notes,
            metadata=_result_metadata(
                problem=problem,
                schedule=schedule,
                used_slots=_count_used_slots(slot_used, solver) if feasible else 0,
                future_extensions=[
                    "instance_specific_capacity_constraints",
                    "break_and_home_away_pattern_constraints",
                    "soft_constraint_penalty_modeling",
                ],
            ),
        )


def _prepare_problem_data(instance: object) -> _RoundRobinProblemData:
    """Prepare round-robin inputs from a parsed instance-like object."""

    instance_name = _extract_instance_name(instance)
    round_robin_mode = _extract_round_robin_mode(instance)
    explicit_team_count = _safe_nonnegative_int(getattr(instance, "team_count", 0))
    team_labels = tuple(_build_team_labels(instance, explicit_team_count))
    num_teams = len(team_labels)

    minimum_required_slots = _minimum_required_slots(num_teams, round_robin_mode)
    requested_slot_count = _safe_nonnegative_int(getattr(instance, "slot_count", 0))
    num_slots = requested_slot_count if requested_slot_count > 0 else minimum_required_slots
    slot_labels = tuple(_build_slot_labels(instance, num_slots))
    meetings = _build_meetings(team_labels, round_robin_mode)
    constraint_support = _summarize_constraint_support(instance, round_robin_mode)

    return _RoundRobinProblemData(
        instance_name=instance_name,
        round_robin_mode=round_robin_mode,
        team_labels=team_labels,
        slot_labels=slot_labels,
        meetings=meetings,
        num_slots=num_slots,
        requested_slot_count=requested_slot_count,
        minimum_required_slots=minimum_required_slots,
        constraint_support=constraint_support,
    )


def _create_meeting_assignment_variables(
    model: cp_model.CpModel,
    problem: _RoundRobinProblemData,
) -> dict[tuple[int, int], cp_model.IntVar]:
    """Create one binary variable per meeting-slot assignment."""

    meeting_vars: dict[tuple[int, int], cp_model.IntVar] = {}
    for meeting_index, meeting in enumerate(problem.meetings):
        for slot in range(problem.num_slots):
            meeting_vars[(meeting_index, slot)] = model.NewBoolVar(
                f"meeting_{meeting_index}_leg{meeting.leg}_h{meeting.home_team_index}_a{meeting.away_team_index}_s{slot}",
            )
    return meeting_vars


def _add_meeting_assignment_constraints(
    model: cp_model.CpModel,
    problem: _RoundRobinProblemData,
    meeting_vars: dict[tuple[int, int], cp_model.IntVar],
) -> None:
    """Ensure each required meeting is scheduled exactly once."""

    for meeting_index in range(len(problem.meetings)):
        model.Add(
            sum(meeting_vars[(meeting_index, slot)] for slot in range(problem.num_slots)) == 1,
        )


def _add_team_availability_constraints(
    model: cp_model.CpModel,
    problem: _RoundRobinProblemData,
    meeting_vars: dict[tuple[int, int], cp_model.IntVar],
) -> None:
    """Prevent teams from playing more than once in the same slot."""

    for slot in range(problem.num_slots):
        for team_index in range(len(problem.team_labels)):
            incident_meetings = [
                meeting_vars[(meeting_index, slot)]
                for meeting_index, meeting in enumerate(problem.meetings)
                if team_index in {meeting.home_team_index, meeting.away_team_index}
            ]
            if incident_meetings:
                model.Add(sum(incident_meetings) <= 1)


def _add_compact_schedule_objective(
    model: cp_model.CpModel,
    problem: _RoundRobinProblemData,
    meeting_vars: dict[tuple[int, int], cp_model.IntVar],
) -> list[cp_model.IntVar]:
    """Minimize the number of used slots in the baseline formulation."""

    slot_used: list[cp_model.IntVar] = []
    for slot in range(problem.num_slots):
        used = model.NewBoolVar(f"slot_used_{slot}")
        slot_used.append(used)
        slot_meetings = [
            meeting_vars[(meeting_index, slot)]
            for meeting_index in range(len(problem.meetings))
        ]
        if slot_meetings:
            for var in slot_meetings:
                model.Add(var <= used)
            model.Add(sum(slot_meetings) >= used)
        else:
            model.Add(used == 0)

    model.Minimize(sum(slot_used))
    return slot_used


def _extract_schedule(
    problem: _RoundRobinProblemData,
    meeting_vars: dict[tuple[int, int], cp_model.IntVar],
    solver: cp_model.CpSolver,
) -> list[dict[str, object]]:
    """Extract a readable slot-by-slot schedule from a solved model."""

    schedule: list[dict[str, object]] = []
    for slot in range(problem.num_slots):
        for meeting_index, meeting in enumerate(problem.meetings):
            if not solver.BooleanValue(meeting_vars[(meeting_index, slot)]):
                continue
            schedule.append(
                {
                    "slot_index": slot,
                    "slot": problem.slot_labels[slot],
                    "meeting_index": meeting_index,
                    "leg": meeting.leg,
                    "home_team": meeting.home_team_label,
                    "away_team": meeting.away_team_label,
                    "team_1": meeting.home_team_label,
                    "team_2": meeting.away_team_label,
                }
            )
    return schedule


def _result_metadata(
    *,
    problem: _RoundRobinProblemData,
    schedule: list[dict[str, object]],
    used_slots: int,
    future_extensions: list[str],
) -> dict[str, object]:
    """Build one audit-friendly metadata payload for solver results."""

    return {
        "model_type": "cp_sat_round_robin_baseline",
        "round_robin_mode": problem.round_robin_mode,
        "schedule": schedule,
        "num_teams": len(problem.team_labels),
        "num_meetings": len(problem.meetings),
        "num_slots": problem.num_slots,
        "requested_slot_count": problem.requested_slot_count,
        "minimum_required_slots": problem.minimum_required_slots,
        "slot_labels": list(problem.slot_labels),
        "team_labels": list(problem.team_labels),
        "used_slots": used_slots,
        "support_level": problem.constraint_support.support_level,
        "supported_capabilities": list(problem.constraint_support.supported_capabilities),
        "declared_constraint_families": list(problem.constraint_support.declared_constraint_families),
        "unsupported_constraint_families": list(problem.constraint_support.unsupported_constraint_families),
        "support_notes": list(problem.constraint_support.notes),
        "future_extensions": future_extensions,
    }


def _scoring_status(problem: _RoundRobinProblemData, *, feasible: bool) -> str:
    """Return the common scoring-contract status for a CP-SAT result."""

    if problem.constraint_support.support_level == "partially_supported":
        return "partially_modeled_run"
    return "supported_feasible_run" if feasible else "supported_infeasible_run"


def _modeling_scope(problem: _RoundRobinProblemData) -> str:
    """Describe the implemented CP-SAT model scope for benchmark exports."""

    return (
        f"compact {problem.round_robin_mode} round-robin CP-SAT model; "
        "one meeting per required leg; at most one match per team per slot; "
        "minimizes used slots; parsed RobinX constraint families are not enforced"
    )


def _count_used_slots(slot_used: list[cp_model.IntVar], solver: cp_model.CpSolver) -> int:
    """Count the slots that are active in the solved schedule."""

    return sum(1 for used in slot_used if solver.BooleanValue(used))


def _build_team_labels(instance: object, explicit_team_count: int) -> list[str]:
    """Build stable team labels from parsed teams or fallback names."""

    teams = list(getattr(instance, "teams", []) or [])
    inferred_count = len(teams)
    num_teams = explicit_team_count if explicit_team_count > 0 else inferred_count
    num_teams = max(num_teams, inferred_count)

    labels: list[str] = []
    for index in range(num_teams):
        team = teams[index] if index < inferred_count else None
        label = _first_non_empty(
            [
                getattr(team, "identifier", None) if team is not None else None,
                getattr(team, "name", None) if team is not None else None,
            ],
        )
        labels.append(label or f"T{index + 1}")
    return labels


def _build_slot_labels(instance: object, num_slots: int) -> list[str]:
    """Build stable slot labels from parsed slots or fallback names."""

    slots = list(getattr(instance, "slots", []) or [])
    labels: list[str] = []
    for index in range(num_slots):
        slot = slots[index] if index < len(slots) else None
        label = _first_non_empty(
            [
                getattr(slot, "identifier", None) if slot is not None else None,
                getattr(slot, "name", None) if slot is not None else None,
            ],
        )
        labels.append(label or f"S{index + 1}")
    return labels


def _build_meetings(
    team_labels: tuple[str, ...],
    round_robin_mode: RoundRobinMode,
) -> tuple[_MeetingDefinition, ...]:
    """Build the directed meetings implied by the requested round-robin mode."""

    meetings: list[_MeetingDefinition] = []
    for home_team_index, away_team_index in combinations(range(len(team_labels)), 2):
        meetings.append(
            _MeetingDefinition(
                home_team_index=home_team_index,
                away_team_index=away_team_index,
                home_team_label=team_labels[home_team_index],
                away_team_label=team_labels[away_team_index],
                leg=1,
            )
        )
        if round_robin_mode == "double":
            meetings.append(
                _MeetingDefinition(
                    home_team_index=away_team_index,
                    away_team_index=home_team_index,
                    home_team_label=team_labels[away_team_index],
                    away_team_label=team_labels[home_team_index],
                    leg=2,
                )
            )
    return tuple(meetings)


def _minimum_required_slots(num_teams: int, round_robin_mode: RoundRobinMode = "single") -> int:
    """Return the minimum slot count implied by the round-robin mode."""

    if num_teams <= 1:
        return 0
    single_round_slots = num_teams if num_teams % 2 == 1 else num_teams - 1
    if round_robin_mode == "double":
        return single_round_slots * 2
    return single_round_slots


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


def _summarize_constraint_support(
    instance: object,
    round_robin_mode: RoundRobinMode,
) -> _ConstraintSupportSummary:
    """Describe what the current baseline does and does not support."""

    declared_constraint_families = _extract_constraint_families(instance)
    unsupported_constraint_families = declared_constraint_families
    notes = [
        (
            "Supports compact "
            f"{round_robin_mode} round-robin scheduling with at most one match per team per slot."
        ),
    ]
    if round_robin_mode == "single":
        notes.append(
            "Single round robin uses one canonical home/away orientation per pair for schedule reporting.",
        )
    else:
        notes.append(
            "Double round robin schedules both home/away legs for every team pair.",
        )
    if unsupported_constraint_families:
        notes.append(
            "Parsed RobinX / ITC2021 constraint families are recorded but not yet enforced directly by this baseline.",
        )

    return _ConstraintSupportSummary(
        support_level="supported" if not unsupported_constraint_families else "partially_supported",
        supported_capabilities=(
            "single_round_robin" if round_robin_mode == "single" else "double_round_robin",
            "one_meeting_per_required_leg",
            "at_most_one_match_per_team_per_slot",
            "compact_slot_minimization",
        ),
        declared_constraint_families=declared_constraint_families,
        unsupported_constraint_families=unsupported_constraint_families,
        notes=tuple(notes),
    )


def _extract_constraint_families(instance: object) -> tuple[str, ...]:
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
    return tuple(sorted(families))


def _extract_instance_name(instance: object) -> str:
    """Extract a readable instance name from common instance fields."""

    metadata = getattr(instance, "metadata", None)
    candidates = [
        getattr(metadata, "name", None),
        getattr(instance, "instance_name", None),
        getattr(instance, "name", None),
    ]
    for candidate in candidates:
        if isinstance(candidate, str) and candidate.strip():
            return candidate.strip()

    source_path = getattr(metadata, "source_path", None)
    if isinstance(source_path, str) and source_path.strip():
        return Path(source_path).stem

    return instance.__class__.__name__


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


def _first_non_empty(values: list[str | None]) -> str | None:
    """Return the first non-empty string from a list of candidates."""

    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _read_text_field(value: object, field_name: str) -> str | None:
    """Read and normalize one text-like field from an object."""

    field_value = getattr(value, field_name, None)
    if isinstance(field_value, str) and field_value.strip():
        return field_value.strip()
    return None
