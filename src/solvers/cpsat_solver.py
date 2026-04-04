"""First CP-SAT round-robin solver skeleton for sports scheduling."""

from __future__ import annotations

import time
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

from ortools.sat.python import cp_model

from src.solvers.base import Solver, SolverResult


@dataclass(slots=True)
class _RoundRobinProblemData:
    """Internal round-robin data prepared from a parsed instance."""

    instance_name: str
    team_labels: list[str]
    slot_labels: list[str]
    matches: list[tuple[int, int]]
    num_slots: int
    requested_slot_count: int
    minimum_required_slots: int


class CPSatSolver(Solver):
    """Minimal CP-SAT baseline for single round-robin scheduling.

    This first version only models a compact baseline schedule:

    - each unordered team pair is played exactly once
    - a team cannot play more than once per slot

    Advanced ITC2021-style constraints are intentionally left out for now so
    the solver can act as a clean foundation for incremental extension.
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
        """Build and solve a minimal round-robin CP-SAT model."""

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
                metadata={
                    "model_type": "cp_sat_round_robin_baseline",
                    "schedule": [],
                    "num_teams": len(problem.team_labels),
                    "num_matches": 0,
                    "num_slots": problem.num_slots,
                    "minimum_required_slots": problem.minimum_required_slots,
                },
            )

        model = cp_model.CpModel()
        match_vars = _create_match_assignment_variables(model, problem)

        _add_match_assignment_constraints(model, problem, match_vars)
        _add_team_availability_constraints(model, problem, match_vars)
        slot_used = _add_compact_schedule_objective(model, problem, match_vars)

        # Placeholder for future extension:
        # - add home/away decision variables
        # - add venue, break, fairness, and travel constraints
        # - add soft-constraint penalties from richer ITC2021 formulations

        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = max(0.0, float(time_limit_seconds))
        solver.parameters.random_seed = random_seed
        solver.parameters.num_search_workers = 1

        status_code = solver.Solve(model)
        status_name = solver.StatusName(status_code)
        runtime_seconds = time.perf_counter() - start_time
        feasible = status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE)

        schedule = _extract_schedule(problem, match_vars, solver) if feasible else []
        objective_value = float(solver.ObjectiveValue()) if feasible else None

        return SolverResult(
            solver_name=self.solver_name,
            instance_name=problem.instance_name,
            objective_value=objective_value,
            runtime_seconds=runtime_seconds,
            feasible=feasible,
            status=status_name,
            metadata={
                "model_type": "cp_sat_round_robin_baseline",
                "schedule": schedule,
                "num_teams": len(problem.team_labels),
                "num_matches": len(problem.matches),
                "num_slots": problem.num_slots,
                "requested_slot_count": problem.requested_slot_count,
                "minimum_required_slots": problem.minimum_required_slots,
                "slot_labels": problem.slot_labels,
                "team_labels": problem.team_labels,
                "used_slots": _count_used_slots(slot_used, solver) if feasible else 0,
                "future_extensions": [
                    "home_away_assignment",
                    "advanced_itc2021_constraints",
                    "soft_constraint_objectives",
                ],
            },
        )


def _prepare_problem_data(instance: object) -> _RoundRobinProblemData:
    """Prepare round-robin inputs from a parsed instance-like object."""

    instance_name = _extract_instance_name(instance)
    explicit_team_count = _safe_nonnegative_int(getattr(instance, "team_count", 0))
    team_labels = _build_team_labels(instance, explicit_team_count)
    num_teams = len(team_labels)

    minimum_required_slots = _minimum_required_slots(num_teams)
    requested_slot_count = _safe_nonnegative_int(getattr(instance, "slot_count", 0))
    num_slots = requested_slot_count if requested_slot_count > 0 else minimum_required_slots
    slot_labels = _build_slot_labels(instance, num_slots)
    matches = list(combinations(range(num_teams), 2))

    return _RoundRobinProblemData(
        instance_name=instance_name,
        team_labels=team_labels,
        slot_labels=slot_labels,
        matches=matches,
        num_slots=num_slots,
        requested_slot_count=requested_slot_count,
        minimum_required_slots=minimum_required_slots,
    )


def _create_match_assignment_variables(
    model: cp_model.CpModel,
    problem: _RoundRobinProblemData,
) -> dict[tuple[int, int, int], cp_model.IntVar]:
    """Create one binary variable per match-slot assignment."""

    match_vars: dict[tuple[int, int, int], cp_model.IntVar] = {}
    for team_a, team_b in problem.matches:
        for slot in range(problem.num_slots):
            match_vars[(team_a, team_b, slot)] = model.NewBoolVar(
                f"match_t{team_a}_t{team_b}_s{slot}",
            )
    return match_vars


def _add_match_assignment_constraints(
    model: cp_model.CpModel,
    problem: _RoundRobinProblemData,
    match_vars: dict[tuple[int, int, int], cp_model.IntVar],
) -> None:
    """Ensure each pair of teams is scheduled exactly once."""

    for team_a, team_b in problem.matches:
        model.Add(
            sum(match_vars[(team_a, team_b, slot)] for slot in range(problem.num_slots)) == 1,
        )


def _add_team_availability_constraints(
    model: cp_model.CpModel,
    problem: _RoundRobinProblemData,
    match_vars: dict[tuple[int, int, int], cp_model.IntVar],
) -> None:
    """Prevent teams from playing more than once in the same slot."""

    for slot in range(problem.num_slots):
        for team in range(len(problem.team_labels)):
            incident_matches = [
                match_vars[(team_a, team_b, slot)]
                for team_a, team_b in problem.matches
                if team in (team_a, team_b)
            ]
            if incident_matches:
                model.Add(sum(incident_matches) <= 1)


def _add_compact_schedule_objective(
    model: cp_model.CpModel,
    problem: _RoundRobinProblemData,
    match_vars: dict[tuple[int, int, int], cp_model.IntVar],
) -> list[cp_model.IntVar]:
    """Minimize the number of used slots in the baseline formulation."""

    slot_used: list[cp_model.IntVar] = []
    for slot in range(problem.num_slots):
        used = model.NewBoolVar(f"slot_used_{slot}")
        slot_used.append(used)
        slot_matches = [
            match_vars[(team_a, team_b, slot)]
            for team_a, team_b in problem.matches
        ]
        if slot_matches:
            for var in slot_matches:
                model.Add(var <= used)
            model.Add(sum(slot_matches) >= used)
        else:
            model.Add(used == 0)

    model.Minimize(sum(slot_used))
    return slot_used


def _extract_schedule(
    problem: _RoundRobinProblemData,
    match_vars: dict[tuple[int, int, int], cp_model.IntVar],
    solver: cp_model.CpSolver,
) -> list[dict[str, object]]:
    """Extract a readable slot-by-slot schedule from a solved model."""

    schedule: list[dict[str, object]] = []
    for slot in range(problem.num_slots):
        for team_a, team_b in problem.matches:
            if solver.BooleanValue(match_vars[(team_a, team_b, slot)]):
                schedule.append(
                    {
                        "slot_index": slot,
                        "slot": problem.slot_labels[slot],
                        "team_1": problem.team_labels[team_a],
                        "team_2": problem.team_labels[team_b],
                    },
                )
    return schedule


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


def _minimum_required_slots(num_teams: int) -> int:
    """Return the minimum slot count for a single round-robin tournament."""

    if num_teams <= 1:
        return 0
    return num_teams if num_teams % 2 == 1 else num_teams - 1


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
