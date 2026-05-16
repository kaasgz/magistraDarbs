# Feature grouping helpers for selector interpretability and ablation studies.

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from src.features.manifest import feature_group_lookup, grouped_feature_names


@dataclass(frozen=True, slots=True)
class AblationFeatureSet:

    # One named feature subset for an ablation study.
    name: str
    title: str
    groups: tuple[str, ...]
    feature_columns: tuple[str, ...]


def group_feature_columns(feature_columns: Sequence[str]) -> dict[str, tuple[str, ...]]:

    # Group available selector feature columns using the documented manifest.
    available = set(feature_columns)
    groups = grouped_feature_names()
    grouped_columns = {
        group_name: tuple(column for column in columns if column in available)
        for group_name, columns in groups.items()
    }
    remaining = tuple(column for column in feature_columns if column not in feature_group_lookup())
    if remaining:
        grouped_columns["other"] = remaining
    return grouped_columns


def feature_group_for_column(column_name: str) -> str:

    # Return the documented group for one feature column.
    return feature_group_lookup().get(column_name, "other")


def default_ablation_feature_sets(feature_columns: Sequence[str]) -> tuple[AblationFeatureSet, ...]:

    # Return the default thesis-facing ablation study subsets.
    grouped_columns = group_feature_columns(feature_columns)
    size_columns = grouped_columns.get("size", ())
    composition_columns = grouped_columns.get("constraint_composition", ())
    all_groups = tuple(group_name for group_name, columns in grouped_columns.items() if columns)
    all_columns = tuple(column for column in feature_columns if any(column in columns for columns in grouped_columns.values()))

    feature_sets = (
        AblationFeatureSet(
            name="size_only",
            title="Size features only",
            groups=("size",),
            feature_columns=size_columns,
        ),
        AblationFeatureSet(
            name="size_plus_constraint_composition",
            title="Size + constraint composition",
            groups=("size", "constraint_composition"),
            feature_columns=tuple([*size_columns, *composition_columns]),
        ),
        AblationFeatureSet(
            name="all_features",
            title="All features",
            groups=all_groups,
            feature_columns=all_columns,
        ),
    )
    return tuple(feature_set for feature_set in feature_sets if feature_set.feature_columns)
