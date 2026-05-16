# Tests for feature validation helpers.

from __future__ import annotations

import pytest

from src.features import FEATURE_DEFINITIONS, feature_names
from src.features.validation import (
    FeatureValidationError,
    ensure_valid_features,
    validate_feature_names,
    validate_feature_values,
)


def test_validate_feature_names_detects_duplicates() -> None:

    # Duplicate feature names should be reported explicitly.
    issues = validate_feature_names(["num_teams", "num_slots", "num_teams"])

    assert len(issues) == 1
    assert issues[0].code == "duplicate_feature_name"
    assert issues[0].feature_name == "num_teams"


def test_validate_feature_values_detects_non_finite_and_invalid_ratio_values() -> None:

    # Non-finite values and invalid ratios should be flagged.
    issues = validate_feature_values(
        {
            "ratio_hard_to_all": 1.25,
            "constraints_per_team": float("inf"),
            "num_constraints": -1,
        }
    )
    issue_codes = {issue.code for issue in issues}

    assert "invalid_ratio_value" in issue_codes
    assert "non_finite_numeric_value" in issue_codes
    assert "negative_count_value" in issue_codes


def test_ensure_valid_features_accepts_the_documented_feature_schema() -> None:

    # A fully documented feature mapping should pass validation.
    features = {name: 0 for name in feature_names()}
    features["teams_is_even"] = False
    features["objective_present"] = False
    features["objective_name"] = ""
    features["objective_sense"] = ""
    features["objective_is_minimization"] = False
    features["objective_is_maximization"] = False

    ensure_valid_features(features)


def test_ensure_valid_features_rejects_missing_documented_features() -> None:

    # Feature validation should fail when the extracted schema is incomplete.
    features = {name: 0 for name in feature_names()[1:]}
    features["teams_is_even"] = False
    features["objective_present"] = False
    features["objective_name"] = ""
    features["objective_sense"] = ""
    features["objective_is_minimization"] = False
    features["objective_is_maximization"] = False

    with pytest.raises(FeatureValidationError):
        ensure_valid_features(features)


def test_feature_manifest_names_are_unique() -> None:

    # The feature manifest itself should not contain duplicate names.
    names = [definition.name for definition in FEATURE_DEFINITIONS]

    assert names == list(feature_names())
    assert len(names) == len(set(names))
