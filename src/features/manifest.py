"""Feature definitions used by the structural feature extraction pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


FeatureDataType = Literal["int", "float", "bool", "str"]


@dataclass(frozen=True, slots=True)
class FeatureDefinition:
    """Documentation record for one extracted feature."""

    name: str
    group: str
    data_type: FeatureDataType
    description: str
    computation: str
    default_behavior: str
    why_it_matters: str


FEATURE_DEFINITIONS: tuple[FeatureDefinition, ...] = (
    FeatureDefinition(
        name="num_teams",
        group="size",
        data_type="int",
        description="Number of teams in the instance.",
        computation="Resolved team_count from parser summary.",
        default_behavior="0 when no teams can be recovered.",
        why_it_matters="Team count strongly affects search-space size and symmetry structure.",
    ),
    FeatureDefinition(
        name="num_slots",
        group="size",
        data_type="int",
        description="Number of available slots or rounds.",
        computation="Resolved slot_count from parser summary.",
        default_behavior="0 when the slot section is missing or empty.",
        why_it_matters="Calendar length changes schedule flexibility and feasibility pressure.",
    ),
    FeatureDefinition(
        name="num_constraints",
        group="size",
        data_type="int",
        description="Number of parsed constraint entries.",
        computation="Resolved constraint_count from parser summary.",
        default_behavior="0 when the constraint section is missing or empty.",
        why_it_matters="Constraint volume is a first-order proxy for instance complexity.",
    ),
    FeatureDefinition(
        name="teams_is_even",
        group="size",
        data_type="bool",
        description="Whether the team count is even.",
        computation="num_teams % 2 == 0 when num_teams > 0.",
        default_behavior="False when num_teams is 0.",
        why_it_matters="Odd team counts introduce byes and different round-robin structure.",
    ),
    FeatureDefinition(
        name="estimated_minimum_slots",
        group="size",
        data_type="int",
        description="Estimated minimum slots implied by team count and round-robin mode metadata.",
        computation="Single RR: n if n odd else n-1; doubled when metadata mode is 'double'.",
        default_behavior="0 when num_teams <= 1; assumes single round robin if mode is missing.",
        why_it_matters="A simple lower bound helps quantify calendar tightness.",
    ),
    FeatureDefinition(
        name="slot_pressure",
        group="size",
        data_type="float",
        description="Lower-bound slot requirement divided by available slots.",
        computation="estimated_minimum_slots / num_slots.",
        default_behavior="0.0 when num_slots is 0.",
        why_it_matters="High pressure suggests tighter scheduling and harder feasibility management.",
    ),
    FeatureDefinition(
        name="slot_surplus",
        group="size",
        data_type="int",
        description="Available slots beyond the estimated minimum requirement.",
        computation="max(0, num_slots - estimated_minimum_slots).",
        default_behavior="0 when num_slots <= estimated_minimum_slots or counts are missing.",
        why_it_matters="Extra slots can make constructive and repair heuristics easier.",
    ),
    FeatureDefinition(
        name="num_hard_constraints",
        group="constraint_composition",
        data_type="int",
        description="Number of constraints classified as hard.",
        computation="Count of constraints whose descriptors include a hard classification token.",
        default_behavior="0 when no hard constraints can be identified.",
        why_it_matters="Hard constraints primarily shape feasibility and pruning difficulty.",
    ),
    FeatureDefinition(
        name="num_soft_constraints",
        group="constraint_composition",
        data_type="int",
        description="Number of constraints classified as soft.",
        computation="Count of constraints whose descriptors include a soft classification token.",
        default_behavior="0 when no soft constraints can be identified.",
        why_it_matters="Soft constraints influence objective trade-offs and local-improvement behavior.",
    ),
    FeatureDefinition(
        name="num_unclassified_constraints",
        group="constraint_composition",
        data_type="int",
        description="Number of constraints not classified as hard or soft.",
        computation="num_constraints - num_hard_constraints - num_soft_constraints, lower bounded at 0.",
        default_behavior="0 when all constraints are classified or no constraints exist.",
        why_it_matters="Unclassified constraint metadata signals ambiguity and weaker structural information.",
    ),
    FeatureDefinition(
        name="num_constraints_missing_category",
        group="constraint_composition",
        data_type="int",
        description="Number of constraints with no explicit category.",
        computation="Count of parsed constraints whose category field is empty.",
        default_behavior="0 when all parsed constraints provide a category.",
        why_it_matters="Missing categories reduce the usefulness of structure-aware solver selection.",
    ),
    FeatureDefinition(
        name="num_constraints_missing_tag",
        group="constraint_composition",
        data_type="int",
        description="Number of constraints with no explicit tag.",
        computation="Count of parsed constraints whose tag field is empty.",
        default_behavior="0 when all parsed constraints provide a tag.",
        why_it_matters="Missing tags reduce fine-grained interpretability of the constraint mix.",
    ),
    FeatureDefinition(
        name="num_constraints_missing_type",
        group="constraint_composition",
        data_type="int",
        description="Number of constraints with no explicit type field.",
        computation="Count of parsed constraints whose type_name field is empty.",
        default_behavior="0 when all parsed constraints provide a type.",
        why_it_matters="Missing hard/soft typing makes solver-comparison assumptions less clear.",
    ),
    FeatureDefinition(
        name="ratio_hard_to_all",
        group="density",
        data_type="float",
        description="Share of parsed constraints classified as hard.",
        computation="num_hard_constraints / num_constraints.",
        default_behavior="0.0 when num_constraints is 0.",
        why_it_matters="The hard-to-soft mix affects feasibility pressure and branching behavior.",
    ),
    FeatureDefinition(
        name="ratio_soft_to_all",
        group="density",
        data_type="float",
        description="Share of parsed constraints classified as soft.",
        computation="num_soft_constraints / num_constraints.",
        default_behavior="0.0 when num_constraints is 0.",
        why_it_matters="Soft-heavy instances can favor optimization-oriented improvement methods.",
    ),
    FeatureDefinition(
        name="ratio_unclassified_to_all",
        group="density",
        data_type="float",
        description="Share of parsed constraints that remain unclassified.",
        computation="num_unclassified_constraints / num_constraints.",
        default_behavior="0.0 when num_constraints is 0.",
        why_it_matters="A high value indicates metadata ambiguity and weaker structural signal quality.",
    ),
    FeatureDefinition(
        name="constraints_per_team",
        group="density",
        data_type="float",
        description="Constraint volume normalized by team count.",
        computation="num_constraints / num_teams.",
        default_behavior="0.0 when num_teams is 0.",
        why_it_matters="Measures how much constraint structure is concentrated around each participant.",
    ),
    FeatureDefinition(
        name="constraints_per_slot",
        group="density",
        data_type="float",
        description="Constraint volume normalized by slot count.",
        computation="num_constraints / num_slots.",
        default_behavior="0.0 when num_slots is 0.",
        why_it_matters="Captures how densely the calendar is constrained over time.",
    ),
    FeatureDefinition(
        name="constraints_per_team_slot",
        group="density",
        data_type="float",
        description="Constraint volume normalized by the team-slot grid size.",
        computation="num_constraints / (num_teams * num_slots).",
        default_behavior="0.0 when num_teams * num_slots is 0.",
        why_it_matters="A coarse density proxy for global structural tightness.",
    ),
    FeatureDefinition(
        name="number_of_constraint_categories",
        group="diversity",
        data_type="int",
        description="Number of distinct constraint categories.",
        computation="Count of unique non-empty category labels after case-insensitive normalization.",
        default_behavior="0 when no categories are available.",
        why_it_matters="More category variety can imply a broader mix of structural interactions.",
    ),
    FeatureDefinition(
        name="number_of_constraint_tags",
        group="diversity",
        data_type="int",
        description="Number of distinct constraint tags.",
        computation="Count of unique non-empty tag labels after case-insensitive normalization.",
        default_behavior="0 when no tags are available.",
        why_it_matters="Tag diversity can separate homogeneous from heterogeneous constraint sets.",
    ),
    FeatureDefinition(
        name="number_of_constraint_types",
        group="diversity",
        data_type="int",
        description="Number of distinct explicit constraint type labels.",
        computation="Count of unique non-empty type_name labels after case-insensitive normalization.",
        default_behavior="0 when no explicit types are available.",
        why_it_matters="Type diversity can distinguish purely feasibility-driven instances from mixed ones.",
    ),
    FeatureDefinition(
        name="ratio_constraint_categories_to_constraints",
        group="diversity",
        data_type="float",
        description="Distinct categories divided by total constraints.",
        computation="number_of_constraint_categories / num_constraints.",
        default_behavior="0.0 when num_constraints is 0.",
        why_it_matters="Normalizes category diversity by instance size.",
    ),
    FeatureDefinition(
        name="ratio_constraint_tags_to_constraints",
        group="diversity",
        data_type="float",
        description="Distinct tags divided by total constraints.",
        computation="number_of_constraint_tags / num_constraints.",
        default_behavior="0.0 when num_constraints is 0.",
        why_it_matters="Measures whether constraints repeat a few motifs or many specific patterns.",
    ),
    FeatureDefinition(
        name="ratio_constraint_types_to_constraints",
        group="diversity",
        data_type="float",
        description="Distinct explicit types divided by total constraints.",
        computation="number_of_constraint_types / num_constraints.",
        default_behavior="0.0 when num_constraints is 0.",
        why_it_matters="Highlights whether type information is concentrated or varied.",
    ),
    FeatureDefinition(
        name="objective_present",
        group="objective",
        data_type="bool",
        description="Whether the parser found an objective label or sense.",
        computation="bool(objective_name or objective_sense).",
        default_behavior="False when both metadata fields are missing.",
        why_it_matters="Explicit objectives can indicate whether the instance is mainly feasibility or optimization oriented.",
    ),
    FeatureDefinition(
        name="objective_name",
        group="objective",
        data_type="str",
        description="Objective label extracted from the instance metadata.",
        computation="Normalized parser metadata field objective_name.",
        default_behavior="Empty string when the objective is not available.",
        why_it_matters="Objective families can correlate with solver design and evaluation criteria.",
    ),
    FeatureDefinition(
        name="objective_sense",
        group="objective",
        data_type="str",
        description="Optimization sense extracted from the instance metadata.",
        computation="Normalized parser metadata field objective_sense.",
        default_behavior="Empty string when the sense is not available.",
        why_it_matters="Minimization and maximization tasks can favor different search dynamics.",
    ),
    FeatureDefinition(
        name="objective_is_minimization",
        group="objective",
        data_type="bool",
        description="Whether the objective sense indicates minimization.",
        computation="True when objective_sense contains a minimization token.",
        default_behavior="False when objective_sense is missing or ambiguous.",
        why_it_matters="Provides a compact machine-readable version of the objective direction.",
    ),
    FeatureDefinition(
        name="objective_is_maximization",
        group="objective",
        data_type="bool",
        description="Whether the objective sense indicates maximization.",
        computation="True when objective_sense contains a maximization token.",
        default_behavior="False when objective_sense is missing or ambiguous.",
        why_it_matters="Provides a compact machine-readable version of the objective direction.",
    ),
)


def feature_names() -> tuple[str, ...]:
    """Return the expected feature names in stable order."""

    return tuple(definition.name for definition in FEATURE_DEFINITIONS)


def feature_group_lookup() -> dict[str, str]:
    """Return one stable feature-to-group mapping."""

    return {
        definition.name: definition.group
        for definition in FEATURE_DEFINITIONS
    }


def grouped_feature_names() -> dict[str, tuple[str, ...]]:
    """Return feature names grouped by their documented feature group."""

    grouped: dict[str, list[str]] = {}
    for definition in FEATURE_DEFINITIONS:
        grouped.setdefault(definition.group, []).append(definition.name)
    return {
        group_name: tuple(names)
        for group_name, names in grouped.items()
    }
