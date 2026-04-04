"""Structural feature extraction for parsed sports timetabling instances."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypeAlias

from src.features.validation import FeatureValidationError, ensure_valid_features, validate_feature_names
from src.parsers import InstanceSummary


FeatureValue: TypeAlias = int | float | bool | str
_ConstraintClass = Literal["hard", "soft", "unclassified"]


@dataclass(frozen=True, slots=True)
class ConstraintStatistics:
    """Aggregated statistics about parsed constraint entries."""

    num_hard_constraints: int
    num_soft_constraints: int
    num_unclassified_constraints: int
    num_constraints_missing_category: int
    num_constraints_missing_tag: int
    num_constraints_missing_type: int
    number_of_constraint_categories: int
    number_of_constraint_tags: int
    number_of_constraint_types: int


def extract_features(instance: InstanceSummary) -> dict[str, FeatureValue]:
    """Extract an interpretable flat feature mapping from one parsed instance.

    The feature set is grouped conceptually into:

    - size features
    - constraint composition features
    - density features
    - diversity features
    - objective-related features

    Missing information is handled conservatively through explicit fallback
    defaults so that downstream experiments remain reproducible.
    """

    constraints = list(getattr(instance, "constraints", []) or [])
    num_teams = _safe_count(getattr(instance, "team_count", None), getattr(instance, "teams", []))
    num_slots = _safe_count(getattr(instance, "slot_count", None), getattr(instance, "slots", []))
    num_constraints = _safe_count(getattr(instance, "constraint_count", None), constraints)

    constraint_statistics = _summarize_constraints(constraints)
    objective_name = _extract_objective_name(instance)
    objective_sense = _extract_objective_sense(instance)
    objective_present = bool(objective_name or objective_sense)
    estimated_minimum_slots = _estimate_minimum_slots(num_teams, _extract_round_robin_mode(instance))
    slot_surplus = max(0, num_slots - estimated_minimum_slots)

    feature_items = [
        *_size_feature_items(
            num_teams=num_teams,
            num_slots=num_slots,
            num_constraints=num_constraints,
            estimated_minimum_slots=estimated_minimum_slots,
            slot_surplus=slot_surplus,
        ),
        *_constraint_composition_feature_items(constraint_statistics),
        *_density_feature_items(
            num_teams=num_teams,
            num_slots=num_slots,
            num_constraints=num_constraints,
            constraint_statistics=constraint_statistics,
        ),
        *_diversity_feature_items(num_constraints=num_constraints, constraint_statistics=constraint_statistics),
        *_objective_feature_items(
            objective_present=objective_present,
            objective_name=objective_name,
            objective_sense=objective_sense,
        ),
    ]
    duplicate_name_issues = validate_feature_names([name for name, _ in feature_items])
    if duplicate_name_issues:
        message = "; ".join(issue.message for issue in duplicate_name_issues)
        raise FeatureValidationError(message)

    features = {name: value for name, value in feature_items}
    ensure_valid_features(features)
    return features


def _size_feature_items(
    *,
    num_teams: int,
    num_slots: int,
    num_constraints: int,
    estimated_minimum_slots: int,
    slot_surplus: int,
) -> list[tuple[str, FeatureValue]]:
    """Return size-oriented structural features."""

    return [
        ("num_teams", num_teams),
        ("num_slots", num_slots),
        ("num_constraints", num_constraints),
        ("teams_is_even", bool(num_teams > 0 and num_teams % 2 == 0)),
        ("estimated_minimum_slots", estimated_minimum_slots),
        ("slot_pressure", _safe_ratio(estimated_minimum_slots, num_slots)),
        ("slot_surplus", slot_surplus),
    ]


def _constraint_composition_feature_items(
    constraint_statistics: ConstraintStatistics,
) -> list[tuple[str, FeatureValue]]:
    """Return features describing the composition of the constraint set."""

    return [
        ("num_hard_constraints", constraint_statistics.num_hard_constraints),
        ("num_soft_constraints", constraint_statistics.num_soft_constraints),
        ("num_unclassified_constraints", constraint_statistics.num_unclassified_constraints),
        ("num_constraints_missing_category", constraint_statistics.num_constraints_missing_category),
        ("num_constraints_missing_tag", constraint_statistics.num_constraints_missing_tag),
        ("num_constraints_missing_type", constraint_statistics.num_constraints_missing_type),
    ]


def _density_feature_items(
    *,
    num_teams: int,
    num_slots: int,
    num_constraints: int,
    constraint_statistics: ConstraintStatistics,
) -> list[tuple[str, FeatureValue]]:
    """Return density-style structural features."""

    return [
        ("ratio_hard_to_all", _safe_ratio(constraint_statistics.num_hard_constraints, num_constraints)),
        ("ratio_soft_to_all", _safe_ratio(constraint_statistics.num_soft_constraints, num_constraints)),
        (
            "ratio_unclassified_to_all",
            _safe_ratio(constraint_statistics.num_unclassified_constraints, num_constraints),
        ),
        ("constraints_per_team", _safe_ratio(num_constraints, num_teams)),
        ("constraints_per_slot", _safe_ratio(num_constraints, num_slots)),
        ("constraints_per_team_slot", _safe_grid_ratio(num_constraints, num_teams, num_slots)),
    ]


def _diversity_feature_items(
    *,
    num_constraints: int,
    constraint_statistics: ConstraintStatistics,
) -> list[tuple[str, FeatureValue]]:
    """Return diversity-style structural features."""

    return [
        ("number_of_constraint_categories", constraint_statistics.number_of_constraint_categories),
        ("number_of_constraint_tags", constraint_statistics.number_of_constraint_tags),
        ("number_of_constraint_types", constraint_statistics.number_of_constraint_types),
        (
            "ratio_constraint_categories_to_constraints",
            _safe_ratio(constraint_statistics.number_of_constraint_categories, num_constraints),
        ),
        (
            "ratio_constraint_tags_to_constraints",
            _safe_ratio(constraint_statistics.number_of_constraint_tags, num_constraints),
        ),
        (
            "ratio_constraint_types_to_constraints",
            _safe_ratio(constraint_statistics.number_of_constraint_types, num_constraints),
        ),
    ]


def _objective_feature_items(
    *,
    objective_present: bool,
    objective_name: str,
    objective_sense: str,
) -> list[tuple[str, FeatureValue]]:
    """Return objective-related features."""

    return [
        ("objective_present", objective_present),
        ("objective_name", objective_name),
        ("objective_sense", objective_sense),
        ("objective_is_minimization", _is_minimization(objective_sense)),
        ("objective_is_maximization", _is_maximization(objective_sense)),
    ]


def _summarize_constraints(constraints: list[object]) -> ConstraintStatistics:
    """Return aggregate statistics about the parsed constraint list."""

    num_hard_constraints = 0
    num_soft_constraints = 0
    num_unclassified_constraints = 0
    num_constraints_missing_category = 0
    num_constraints_missing_tag = 0
    num_constraints_missing_type = 0

    unique_categories: set[str] = set()
    unique_tags: set[str] = set()
    unique_types: set[str] = set()

    for constraint in constraints:
        category = _read_text_field(constraint, "category")
        tag = _read_text_field(constraint, "tag")
        type_name = _read_text_field(constraint, "type_name")
        classification = _constraint_classification(constraint)

        if classification == "hard":
            num_hard_constraints += 1
        elif classification == "soft":
            num_soft_constraints += 1
        else:
            num_unclassified_constraints += 1

        if category is None:
            num_constraints_missing_category += 1
        else:
            unique_categories.add(category.casefold())

        if tag is None:
            num_constraints_missing_tag += 1
        else:
            unique_tags.add(tag.casefold())

        if type_name is None:
            num_constraints_missing_type += 1
        else:
            unique_types.add(type_name.casefold())

    return ConstraintStatistics(
        num_hard_constraints=num_hard_constraints,
        num_soft_constraints=num_soft_constraints,
        num_unclassified_constraints=num_unclassified_constraints,
        num_constraints_missing_category=num_constraints_missing_category,
        num_constraints_missing_tag=num_constraints_missing_tag,
        num_constraints_missing_type=num_constraints_missing_type,
        number_of_constraint_categories=len(unique_categories),
        number_of_constraint_tags=len(unique_tags),
        number_of_constraint_types=len(unique_types),
    )


def _safe_count(explicit_count: object, items: object) -> int:
    """Return a non-negative count using an explicit value or list length."""

    if isinstance(explicit_count, int):
        return max(0, explicit_count)
    if items is None:
        return 0
    try:
        return max(0, len(items))
    except TypeError:
        return 0


def _safe_ratio(numerator: int | float, denominator: int | float) -> float:
    """Return a ratio or ``0.0`` when the denominator is missing or zero."""

    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _safe_grid_ratio(numerator: int, left: int, right: int) -> float:
    """Return ``numerator / (left * right)`` with safe zero handling."""

    if left <= 0 or right <= 0:
        return 0.0
    return float(numerator) / float(left * right)


def _estimate_minimum_slots(num_teams: int, round_robin_mode: str) -> int:
    """Estimate the minimum calendar size implied by round-robin structure."""

    if num_teams <= 1:
        return 0

    single_round_slots = num_teams if num_teams % 2 == 1 else num_teams - 1
    if round_robin_mode == "double":
        return single_round_slots * 2
    return single_round_slots


def _extract_round_robin_mode(instance: InstanceSummary) -> str:
    """Return a normalized round-robin mode with a conservative fallback."""

    metadata = getattr(instance, "metadata", None)
    raw_value = _first_non_empty(
        [
            _read_text_field(instance, "round_robin_mode"),
            _read_text_field(metadata, "round_robin_mode"),
        ]
    )
    if raw_value is None:
        return "single"

    normalized = raw_value.casefold()
    if "double" in normalized:
        return "double"
    return "single"


def _constraint_classification(constraint: object) -> _ConstraintClass:
    """Classify a constraint into hard, soft, or unclassified."""

    explicit_type = _read_text_field(constraint, "type_name")
    if explicit_type:
        normalized = explicit_type.casefold()
        if "hard" in normalized and "soft" not in normalized:
            return "hard"
        if "soft" in normalized and "hard" not in normalized:
            return "soft"

    has_hard_token = _constraint_has_token(constraint, "hard")
    has_soft_token = _constraint_has_token(constraint, "soft")
    if has_hard_token and not has_soft_token:
        return "hard"
    if has_soft_token and not has_hard_token:
        return "soft"
    return "unclassified"


def _constraint_has_token(constraint: object, token: str) -> bool:
    """Check a constraint's descriptive fields for a classification token."""

    normalized_token = token.casefold()
    for value in _constraint_descriptors(constraint):
        if normalized_token in value.casefold():
            return True
    return False


def _constraint_descriptors(constraint: object) -> list[str]:
    """Collect text descriptors that characterize a constraint."""

    candidates = [
        _read_text_field(constraint, "category"),
        _read_text_field(constraint, "type_name"),
        _read_text_field(constraint, "tag"),
    ]
    return [candidate for candidate in candidates if candidate]


def _extract_objective_name(instance: InstanceSummary) -> str:
    """Extract a simple objective label if one is available."""

    metadata = getattr(instance, "metadata", None)
    return _first_non_empty(
        [
            _read_text_field(instance, "objective_name"),
            _read_text_field(instance, "objective"),
            _read_text_field(instance, "objective_type"),
            _read_text_field(metadata, "objective_name"),
            _read_text_field(metadata, "objective"),
            _read_text_field(metadata, "objective_type"),
        ]
    ) or ""


def _extract_objective_sense(instance: InstanceSummary) -> str:
    """Extract the optimization sense if it is available."""

    metadata = getattr(instance, "metadata", None)
    return _first_non_empty(
        [
            _read_text_field(instance, "objective_sense"),
            _read_text_field(instance, "sense"),
            _read_text_field(instance, "optimization_sense"),
            _read_text_field(metadata, "objective_sense"),
            _read_text_field(metadata, "sense"),
            _read_text_field(metadata, "optimization_sense"),
        ]
    ) or ""


def _is_minimization(value: str) -> bool:
    """Return whether the given optimization sense represents minimization."""

    normalized = value.casefold()
    return any(token in normalized for token in {"min", "minimum", "minimize", "minimization"})


def _is_maximization(value: str) -> bool:
    """Return whether the given optimization sense represents maximization."""

    normalized = value.casefold()
    return any(token in normalized for token in {"max", "maximum", "maximize", "maximization"})


def _read_text_field(source: object, field_name: str) -> str | None:
    """Read a text-like field from an object or mapping."""

    if source is None:
        return None

    value: object | None
    if isinstance(source, dict):
        value = source.get(field_name)
    else:
        value = getattr(source, field_name, None)

    if value is None:
        return None

    normalized = str(value).strip()
    return normalized or None


def _first_non_empty(values: list[str | None]) -> str | None:
    """Return the first non-empty string from a list of candidates."""

    for value in values:
        if value:
            return value
    return None
