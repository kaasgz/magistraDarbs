# First simulated annealing baseline for sports tournament scheduling.

from __future__ import annotations

import math
import random
import time
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from src.solvers.base import Solver, SolverResult


@dataclass(frozen=True, slots=True)
class _ProblemData:

    # Prepared round-robin data used by the simulated annealing solver.
    instance_name: str
    round_robin_mode: str | None
    team_labels: tuple[str, ...]
    slot_labels: tuple[str, ...]
    matches: tuple[tuple[int, int], ...]
    num_slots: int
    requested_slot_count: int
    minimum_required_slots: int
    constraint_families: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _ScheduleState:

    # Schedule representation mapping each inferred match to one slot index.
    #
    # Version 1 simplification:
    # Every unordered team pair is always assigned to exactly one slot. The state
    # does not model home/away orientation, venues, or rich ITC2021 constraints.
    #
    assignments: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class _StateEvaluation:

    # Objective breakdown for one schedule state.
    objective: float
    team_conflict_penalty: int
    duplicate_match_penalty: int
    used_slots: int


class SimulatedAnnealingSolver(Solver):

    # Simulated annealing baseline for simplified round-robin scheduling.
    #
    # Version 1 intentionally uses a simplified schedule model and penalty
    # function:
    #
    # - matches are inferred from the team set as one single round-robin
    # - each match is always scheduled exactly once by representation
    # - hard structure is approximated through penalties instead of exact repair
    # - only team-per-slot conflicts and slot usage are scored
    #
    # This keeps the baseline small and auditable while leaving clear extension
    # points for richer constraint handling.
    #
    def __init__(
        self,
        solver_name: str = "simulated_annealing_baseline",
        max_iterations: int = 20_000,
        initial_temperature: float = 10.0,
        cooling_rate: float = 0.995,
    ) -> None:

        # Initialize annealing hyperparameters for the baseline solver.
        self.solver_name = solver_name
        self.max_iterations = max_iterations
        self.initial_temperature = initial_temperature
        self.cooling_rate = cooling_rate

    def solve(
        self,
        instance: object,
        time_limit_seconds: int = 60,
        random_seed: int = 42,
    ) -> SolverResult:

        # Search for a low-penalty schedule with simulated annealing.
        start_time = time.perf_counter()
        rng = random.Random(random_seed)
        problem = _prepare_problem_data(instance)

        if problem.round_robin_mode == "double":
            runtime_seconds = time.perf_counter() - start_time
            notes = (
                "Unsupported round-robin mode: double.",
                "The current simulated annealing baseline infers one unordered match per team pair.",
            )
            return SolverResult(
                solver_name=self.solver_name,
                instance_name=problem.instance_name,
                objective_value=None,
                runtime_seconds=runtime_seconds,
                feasible=False,
                status="UNSUPPORTED_INSTANCE",
                solver_support_status="unsupported",
                scoring_status="unsupported_instance",
                modeling_scope=_modeling_scope(problem),
                scoring_notes=notes,
                metadata={
                    "algorithm": "simulated_annealing",
                    "error": "Double round-robin instances are outside the current simulated annealing model.",
                    "round_robin_mode": problem.round_robin_mode,
                    "unsupported_constraint_families": list(problem.constraint_families),
                    "simplifications": _simplifications(),
                },
            )

        if len(problem.team_labels) <= 1:
            runtime_seconds = time.perf_counter() - start_time
            support_status = _support_status(problem)
            return SolverResult(
                solver_name=self.solver_name,
                instance_name=problem.instance_name,
                objective_value=0.0,
                runtime_seconds=runtime_seconds,
                feasible=True,
                status="TRIVIAL",
                solver_support_status=support_status,
                scoring_status=_scoring_status(problem, feasible=True),
                modeling_scope=_modeling_scope(problem),
                scoring_notes=_scoring_notes(problem),
                metadata={
                    "algorithm": "simulated_annealing",
                    "is_placeholder": True,
                    "schedule": [],
                    "iterations": 0,
                    "temperature": 0.0,
                    "round_robin_mode": problem.round_robin_mode,
                    "support_level": support_status,
                    "unsupported_constraint_families": list(problem.constraint_families),
                    "num_teams": len(problem.team_labels),
                    "num_matches": 0,
                    "num_slots": problem.num_slots,
                    "minimum_required_slots": problem.minimum_required_slots,
                },
            )

        current_state = _initialize_state(problem, rng)
        current_eval = _evaluate_state(problem, current_state)
        best_state = current_state
        best_eval = current_eval

        iteration = 0
        accepted_moves = 0
        deadline = start_time + max(0.0, float(time_limit_seconds))

        while iteration < self.max_iterations and time.perf_counter() < deadline:
            iteration += 1
            temperature = _temperature_at_iteration(
                initial_temperature=self.initial_temperature,
                cooling_rate=self.cooling_rate,
                iteration=iteration,
            )
            neighbor_state = _propose_neighbor(problem, current_state, rng)
            neighbor_eval = _evaluate_state(problem, neighbor_state)

            if _should_accept(current_eval.objective, neighbor_eval.objective, temperature, rng):
                current_state = neighbor_state
                current_eval = neighbor_eval
                accepted_moves += 1

                if neighbor_eval.objective < best_eval.objective:
                    best_state = neighbor_state
                    best_eval = neighbor_eval

            if best_eval.objective <= 0.0:
                break

        runtime_seconds = time.perf_counter() - start_time
        feasible = best_eval.team_conflict_penalty == 0 and best_eval.duplicate_match_penalty == 0
        status = "FEASIBLE" if feasible else "APPROXIMATE"
        support_status = _support_status(problem)

        return SolverResult(
            solver_name=self.solver_name,
            instance_name=problem.instance_name,
            objective_value=best_eval.objective,
            runtime_seconds=runtime_seconds,
            feasible=feasible,
            status=status,
            solver_support_status=support_status,
            scoring_status=_scoring_status(problem, feasible=feasible),
            modeling_scope=_modeling_scope(problem),
            scoring_notes=_scoring_notes(problem),
            metadata={
                "algorithm": "simulated_annealing",
                "is_placeholder": True,
                "schedule": _build_schedule(problem, best_state),
                "iterations": iteration,
                "accepted_moves": accepted_moves,
                "final_temperature": _temperature_at_iteration(
                    initial_temperature=self.initial_temperature,
                    cooling_rate=self.cooling_rate,
                    iteration=iteration,
                ),
                "team_conflict_penalty": best_eval.team_conflict_penalty,
                "duplicate_match_penalty": best_eval.duplicate_match_penalty,
                "used_slots": best_eval.used_slots,
                "num_teams": len(problem.team_labels),
                "num_matches": len(problem.matches),
                "num_slots": problem.num_slots,
                "round_robin_mode": problem.round_robin_mode,
                "support_level": support_status,
                "unsupported_constraint_families": list(problem.constraint_families),
                "requested_slot_count": problem.requested_slot_count,
                "minimum_required_slots": problem.minimum_required_slots,
                "team_labels": list(problem.team_labels),
                "slot_labels": list(problem.slot_labels),
                "future_extensions": [
                    "home_away_orientation",
                    "itc2021_soft_constraint_penalties",
                    "repair_moves_and_hybrid_local_search",
                ],
                "simplifications": _simplifications(),
            },
        )


def _prepare_problem_data(instance: object) -> _ProblemData:

    # Prepare team, slot, and inferred match data from an instance-like object.
    instance_name = _extract_instance_name(instance)
    round_robin_mode = _extract_round_robin_mode(instance)
    explicit_team_count = _safe_nonnegative_int(getattr(instance, "team_count", 0))
    team_labels = tuple(_build_team_labels(instance, explicit_team_count))
    num_teams = len(team_labels)

    minimum_required_slots = _minimum_required_slots(num_teams)
    requested_slot_count = _safe_nonnegative_int(getattr(instance, "slot_count", 0))
    num_slots = requested_slot_count if requested_slot_count > 0 else max(1, minimum_required_slots)
    slot_labels = tuple(_build_slot_labels(instance, num_slots))
    matches = tuple(combinations(range(num_teams), 2))

    return _ProblemData(
        instance_name=instance_name,
        round_robin_mode=round_robin_mode,
        team_labels=team_labels,
        slot_labels=slot_labels,
        matches=matches,
        num_slots=num_slots,
        requested_slot_count=requested_slot_count,
        minimum_required_slots=minimum_required_slots,
        constraint_families=_extract_constraint_families(instance),
    )


def _initialize_state(problem: _ProblemData, rng: random.Random) -> _ScheduleState:

    # Create an initial randomized state.
    #
    # Version 1 simplification:
    # The initial state is purely randomized over slots. Feasibility is improved
    # by optimization rather than by a dedicated constructive heuristic.
    #
    if problem.num_slots <= 0:
        return _ScheduleState(assignments=tuple())

    assignments = tuple(rng.randrange(problem.num_slots) for _ in problem.matches)
    return _ScheduleState(assignments=assignments)


def _evaluate_state(problem: _ProblemData, state: _ScheduleState) -> _StateEvaluation:

    # Compute the simplified annealing objective for one schedule state.
    if not problem.matches:
        return _StateEvaluation(
            objective=0.0,
            team_conflict_penalty=0,
            duplicate_match_penalty=0,
            used_slots=0,
        )

    teams_per_slot: list[dict[int, int]] = [dict() for _ in range(problem.num_slots)]
    used_slots: set[int] = set()

    for match_index, slot_index in enumerate(state.assignments):
        if slot_index < 0 or slot_index >= problem.num_slots:
            continue
        used_slots.add(slot_index)
        team_a, team_b = problem.matches[match_index]
        teams_per_slot[slot_index][team_a] = teams_per_slot[slot_index].get(team_a, 0) + 1
        teams_per_slot[slot_index][team_b] = teams_per_slot[slot_index].get(team_b, 0) + 1

    team_conflict_penalty = 0
    for slot_team_counts in teams_per_slot:
        for appearances in slot_team_counts.values():
            if appearances > 1:
                team_conflict_penalty += appearances - 1

    duplicate_match_penalty = max(0, len(problem.matches) - len(state.assignments))
    objective = float(1_000 * team_conflict_penalty + len(used_slots))

    return _StateEvaluation(
        objective=objective,
        team_conflict_penalty=team_conflict_penalty,
        duplicate_match_penalty=duplicate_match_penalty,
        used_slots=len(used_slots),
    )


def _propose_neighbor(
    problem: _ProblemData,
    state: _ScheduleState,
    rng: random.Random,
) -> _ScheduleState:

    # Generate a neighboring state using a small schedule perturbation.
    if problem.num_slots <= 1 or not state.assignments:
        return state

    assignments = list(state.assignments)
    move_type = "reassign" if len(assignments) == 1 else rng.choice(["reassign", "swap"])

    if move_type == "swap":
        first_index, second_index = rng.sample(range(len(assignments)), 2)
        assignments[first_index], assignments[second_index] = (
            assignments[second_index],
            assignments[first_index],
        )
    else:
        match_index = rng.randrange(len(assignments))
        current_slot = assignments[match_index]
        candidate_slots = [slot for slot in range(problem.num_slots) if slot != current_slot]
        assignments[match_index] = rng.choice(candidate_slots) if candidate_slots else current_slot

    return _ScheduleState(assignments=tuple(assignments))


def _temperature_at_iteration(
    initial_temperature: float,
    cooling_rate: float,
    iteration: int,
) -> float:

    # Compute the geometric cooling schedule temperature.
    if iteration <= 0:
        return max(1e-6, initial_temperature)
    return max(1e-6, initial_temperature * (cooling_rate ** iteration))


def _should_accept(
    current_objective: float,
    candidate_objective: float,
    temperature: float,
    rng: random.Random,
) -> bool:

    # Apply the standard simulated annealing acceptance rule.
    if candidate_objective <= current_objective:
        return True

    delta = candidate_objective - current_objective
    probability = math.exp(-delta / max(temperature, 1e-6))
    return rng.random() < probability


def _build_schedule(problem: _ProblemData, state: _ScheduleState) -> list[dict[str, object]]:

    # Convert a schedule state to a readable list of scheduled matches.
    schedule: list[dict[str, object]] = []
    for match_index, slot_index in enumerate(state.assignments):
        if slot_index < 0 or slot_index >= problem.num_slots:
            continue
        team_a, team_b = problem.matches[match_index]
        schedule.append(
            {
                "slot_index": slot_index,
                "slot": problem.slot_labels[slot_index],
                "team_1": problem.team_labels[team_a],
                "team_2": problem.team_labels[team_b],
            },
        )

    schedule.sort(key=lambda item: (int(item["slot_index"]), str(item["team_1"]), str(item["team_2"])))
    return schedule


def _build_team_labels(instance: object, explicit_team_count: int) -> list[str]:

    # Build stable team labels from parsed teams or fallback names.
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

    # Build stable slot labels from parsed slots or fallback names.
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


def _minimum_required_slots(num_teams: int) -> int:

    # Return the minimum slot count for single round-robin play.
    if num_teams <= 1:
        return 0
    return num_teams if num_teams % 2 == 1 else num_teams - 1


def _support_status(problem: _ProblemData) -> str:

    # Return the modeling support level for the annealing baseline.
    if problem.round_robin_mode not in {"single", None}:
        return "unsupported"
    if problem.round_robin_mode is None or problem.constraint_families:
        return "partially_supported"
    return "supported"


def _scoring_status(problem: _ProblemData, *, feasible: bool) -> str:

    # Return the common scoring-contract status for annealing results.
    support_status = _support_status(problem)
    if support_status == "unsupported":
        return "unsupported_instance"
    if support_status == "partially_supported":
        return "partially_modeled_run"
    return "supported_feasible_run" if feasible else "supported_infeasible_run"


def _modeling_scope(problem: _ProblemData) -> str:

    # Describe the implemented annealing model scope.
    return (
        "simplified single round-robin simulated annealing model; one unordered "
        "match per team pair; no home/away, venue, travel, or direct RobinX "
        "constraint modeling"
    )


def _scoring_notes(problem: _ProblemData) -> tuple[str, ...]:

    # Return concise scoring notes for benchmark exports.
    notes = [
        "Objective is a penalty score: lower is better.",
        "Team-per-slot conflicts dominate the objective; used slots are secondary.",
    ]
    if problem.round_robin_mode is None:
        notes.append("Round-robin mode missing or ambiguous; solver assumes single round robin.")
    if problem.constraint_families:
        notes.append("Parsed RobinX / ITC2021 constraint families are not directly modeled.")
    return tuple(notes)


def _simplifications() -> list[str]:

    # Return the stable list of annealing baseline simplifications.
    return [
        "single_round_robin_inferred_from_team_set",
        "no_home_away_decisions",
        "no_venue_or_travel_modeling",
        "penalty_based_objective_with_team_slot_conflicts_only",
    ]


def _extract_round_robin_mode(instance: object) -> str | None:

    # Extract a normalized round-robin mode when available.
    metadata = getattr(instance, "metadata", None)
    raw_value = _first_non_empty(
        [
            _read_text_field(instance, "round_robin_mode"),
            _read_text_field(metadata, "round_robin_mode"),
        ]
    )
    if raw_value is None:
        return None
    normalized = raw_value.casefold()
    if "double" in normalized:
        return "double"
    if "single" in normalized:
        return "single"
    return None


def _extract_constraint_families(instance: object) -> tuple[str, ...]:

    # Extract stable constraint-family labels from the parsed instance.
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

    # Extract a readable instance name from common instance fields.
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

    # Convert a count-like value to a non-negative integer.
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(0, value)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _first_non_empty(values: list[str | None]) -> str | None:

    # Return the first non-empty string from a list of candidates.
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _read_text_field(value: object, field_name: str) -> str | None:

    # Read and normalize one text-like field from an object.
    field_value = getattr(value, field_name, None)
    if isinstance(field_value, str) and field_value.strip():
        return field_value.strip()
    return None
