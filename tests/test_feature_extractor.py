"""Tests for structural feature extraction."""

from pathlib import Path

import pytest

from src.features import extract_features
from src.parsers import InstanceSummary, TournamentMetadata, load_instance


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


class ObjectiveMetadata(TournamentMetadata):
    """Metadata variant used to test optional objective features."""

    objective_name: str | None = None
    objective_sense: str | None = None
    round_robin_mode: str | None = None


def test_extract_features_returns_expected_grouped_values_for_valid_instance() -> None:
    """The extractor should return stable, interpretable feature values."""

    instance = load_instance(str(FIXTURES_DIR / "sample_robinx.xml"))

    features = extract_features(instance)

    assert features["num_teams"] == 3
    assert features["num_slots"] == 2
    assert features["num_constraints"] == 2
    assert features["teams_is_even"] is False
    assert features["estimated_minimum_slots"] == 3
    assert features["slot_pressure"] == pytest.approx(1.5)
    assert features["slot_surplus"] == 0

    assert features["num_hard_constraints"] == 1
    assert features["num_soft_constraints"] == 0
    assert features["num_unclassified_constraints"] == 1
    assert features["num_constraints_missing_category"] == 0
    assert features["num_constraints_missing_tag"] == 1
    assert features["num_constraints_missing_type"] == 1

    assert features["ratio_hard_to_all"] == pytest.approx(0.5)
    assert features["ratio_soft_to_all"] == pytest.approx(0.0)
    assert features["ratio_unclassified_to_all"] == pytest.approx(0.5)
    assert features["constraints_per_team"] == pytest.approx(2.0 / 3.0)
    assert features["constraints_per_slot"] == pytest.approx(1.0)
    assert features["constraints_per_team_slot"] == pytest.approx(1.0 / 3.0)

    assert features["number_of_constraint_categories"] == 2
    assert features["number_of_constraint_tags"] == 1
    assert features["number_of_constraint_types"] == 1
    assert features["ratio_constraint_categories_to_constraints"] == pytest.approx(1.0)
    assert features["ratio_constraint_tags_to_constraints"] == pytest.approx(0.5)
    assert features["ratio_constraint_types_to_constraints"] == pytest.approx(0.5)

    assert features["objective_present"] is False
    assert features["objective_name"] == ""
    assert features["objective_sense"] == ""
    assert features["objective_is_minimization"] is False
    assert features["objective_is_maximization"] is False


def test_extract_features_returns_safe_defaults_for_sparse_instance() -> None:
    """Missing optional sections should produce stable zero-like fallbacks."""

    instance = load_instance(str(FIXTURES_DIR / "sample_robinx_missing_sections.xml"))

    features = extract_features(instance)

    assert features["num_teams"] == 2
    assert features["num_slots"] == 0
    assert features["num_constraints"] == 0
    assert features["teams_is_even"] is True
    assert features["estimated_minimum_slots"] == 1
    assert features["slot_pressure"] == 0.0
    assert features["slot_surplus"] == 0

    assert features["num_hard_constraints"] == 0
    assert features["num_soft_constraints"] == 0
    assert features["num_unclassified_constraints"] == 0
    assert features["num_constraints_missing_category"] == 0
    assert features["num_constraints_missing_tag"] == 0
    assert features["num_constraints_missing_type"] == 0

    assert features["ratio_hard_to_all"] == 0.0
    assert features["ratio_soft_to_all"] == 0.0
    assert features["ratio_unclassified_to_all"] == 0.0
    assert features["constraints_per_slot"] == 0.0
    assert features["constraints_per_team_slot"] == 0.0

    assert features["number_of_constraint_categories"] == 0
    assert features["number_of_constraint_tags"] == 0
    assert features["number_of_constraint_types"] == 0
    assert features["objective_present"] is False
    assert features["objective_name"] == ""
    assert features["objective_sense"] == ""


def test_extract_features_reads_objective_metadata_when_present() -> None:
    """Objective-related features should be populated when metadata provides them."""

    instance = InstanceSummary(
        metadata=ObjectiveMetadata(
            name="ObjectiveFixture",
            source_path="tests/fixtures/objective.xml",
            objective_name="travel_distance",
            objective_sense="minimize",
            round_robin_mode="double",
        ),
        team_count=4,
        slot_count=6,
        constraint_count=0,
    )

    features = extract_features(instance)

    assert features["objective_present"] is True
    assert features["objective_name"] == "travel_distance"
    assert features["objective_sense"] == "minimize"
    assert features["objective_is_minimization"] is True
    assert features["objective_is_maximization"] is False
    assert features["estimated_minimum_slots"] == 6
    assert features["slot_pressure"] == pytest.approx(1.0)


def test_extract_features_is_deterministic_for_same_fixture() -> None:
    """The same parsed instance should always produce the same feature mapping."""

    instance = load_instance(str(FIXTURES_DIR / "sample_robinx.xml"))

    first = extract_features(instance)
    second = extract_features(instance)

    assert first == second
