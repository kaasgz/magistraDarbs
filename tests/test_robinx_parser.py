"""Tests for the RobinX parser."""

from pathlib import Path

from src.parsers.robinx_parser import load_instance


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_load_instance_succeeds_for_valid_xml() -> None:
    """A valid fixture should load into a typed summary with transparent notes."""

    fixture_path = FIXTURES_DIR / "sample_robinx.xml"

    summary = load_instance(str(fixture_path))
    note_codes = {note.code for note in summary.parser_notes}

    assert summary.metadata.name == "SampleRobinX"
    assert summary.metadata.source_path == str(fixture_path)
    assert len(summary.teams) == 3
    assert len(summary.slots) == 2
    assert len(summary.constraints) == 2
    assert summary.constraint_categories == ["Break", "Capacity", "Hard", "HomeAway"]
    assert note_codes == {"constraints_missing_tag", "constraints_missing_type"}


def test_load_instance_extracts_team_and_slot_counts() -> None:
    """Parsed aggregate counts should match the underlying fixture contents."""

    fixture_path = FIXTURES_DIR / "sample_robinx.xml"

    summary = load_instance(str(fixture_path))

    assert summary.team_count == 3
    assert [team.identifier for team in summary.teams] == ["T1", "T2", "T3"]
    assert summary.slot_count == 2
    assert [slot.identifier for slot in summary.slots] == ["S1", "S2"]
    assert summary.constraint_count == 2


def test_load_instance_handles_missing_optional_sections_with_parser_notes() -> None:
    """Missing slots and constraints should not cause parsing failures."""

    fixture_path = FIXTURES_DIR / "sample_robinx_missing_sections.xml"

    summary = load_instance(str(fixture_path))
    note_codes = {note.code for note in summary.parser_notes}

    assert summary.metadata.name == "sample_robinx_missing_sections"
    assert summary.team_count == 2
    assert summary.slot_count == 0
    assert summary.constraint_count == 0
    assert summary.slots == []
    assert summary.constraints == []
    assert summary.constraint_categories == []
    assert note_codes == {
        "missing_constraints_section",
        "missing_instance_name",
        "missing_slots_section",
    }


def test_load_instance_recovers_from_partially_malformed_xml(tmp_path: Path) -> None:
    """Recoverable XML should still produce a summary and a recovery note."""

    xml_path = tmp_path / "recoverable.xml"
    xml_path.write_text(
        "\n".join(
            [
                '<Instance name="RecoverableFixture">',
                "  <Teams>",
                '    <Team id="T1" name="Team A" />',
                '    <Team id="T2" name="Team B" />',
                "  </Teams>",
                "  <Slots>",
                '    <Slot id="S1" name="Round 1">',
                "  </Slots>",
                "</Instance>",
            ]
        ),
        encoding="utf-8",
    )

    summary = load_instance(str(xml_path))
    note_codes = {note.code for note in summary.parser_notes}

    assert summary.metadata.name == "RecoverableFixture"
    assert summary.team_count == 2
    assert summary.slot_count == 1
    assert "xml_recovery_applied" in note_codes


def test_load_instance_preserves_unknown_constraint_category_and_tag(tmp_path: Path) -> None:
    """Unknown constraint descriptors should be preserved rather than rejected."""

    xml_path = tmp_path / "unknown_constraint.xml"
    xml_path.write_text(
        "\n".join(
            [
                '<Instance name="UnknownConstraintFixture">',
                "  <Teams>",
                '    <Team id="T1" name="Team A" />',
                '    <Team id="T2" name="Team B" />',
                "  </Teams>",
                "  <Constraints>",
                '    <Constraint id="C1" category="ExperimentalWindow" tag="PrimeBlock" type="Soft" />',
                "  </Constraints>",
                "</Instance>",
            ]
        ),
        encoding="utf-8",
    )

    summary = load_instance(str(xml_path))

    assert summary.constraint_count == 1
    assert summary.constraints[0].category == "ExperimentalWindow"
    assert summary.constraints[0].tag == "PrimeBlock"
    assert summary.constraints[0].type_name == "Soft"


def test_load_instance_supports_itc2021_style_grouped_constraints_and_lowercase_resources(
    tmp_path: Path,
) -> None:
    """Official-style ITC2021 XML should yield teams, slots, grouped constraints, and double RR metadata."""

    xml_path = tmp_path / "itc2021_style.xml"
    xml_path.write_text(
        "\n".join(
            [
                '<?xml version="1.0" encoding="UTF-8"?>',
                "<Instance>",
                "  <MetaData>",
                "    <InstanceName>ITC2021 Style</InstanceName>",
                "  </MetaData>",
                "  <Structure>",
                "    <Format>",
                "      <numberRoundRobin>2</numberRoundRobin>",
                "    </Format>",
                "  </Structure>",
                "  <ObjectiveFunction>",
                "    <Objective>SC</Objective>",
                "  </ObjectiveFunction>",
                "  <Resources>",
                "    <Teams>",
                '      <team id="0" name="Team 0" />',
                '      <team id="1" name="Team 1" />',
                '      <team id="2" name="Team 2" />',
                '      <team id="3" name="Team 3" />',
                "    </Teams>",
                "    <Slots>",
                '      <slot id="0" name="Slot 0" />',
                '      <slot id="1" name="Slot 1" />',
                '      <slot id="2" name="Slot 2" />',
                '      <slot id="3" name="Slot 3" />',
                '      <slot id="4" name="Slot 4" />',
                '      <slot id="5" name="Slot 5" />',
                "    </Slots>",
                "  </Resources>",
                "  <Constraints>",
                "    <CapacityConstraints>",
                '      <CA1 teams="0" slots="0;1" type="HARD" max="1" min="0" />',
                '      <CA1 teams="1" slots="2;3" type="SOFT" max="1" min="0" />',
                "    </CapacityConstraints>",
                "    <BreakConstraints>",
                '      <BR2 teams="0;1;2;3" slots="0;1;2;3;4;5" type="HARD" intp="2" />',
                "    </BreakConstraints>",
                "  </Constraints>",
                "</Instance>",
            ]
        ),
        encoding="utf-8",
    )

    summary = load_instance(str(xml_path))

    assert summary.metadata.name == "ITC2021 Style"
    assert summary.metadata.objective_name == "SC"
    assert summary.metadata.round_robin_mode == "double"
    assert summary.team_count == 4
    assert summary.slot_count == 6
    assert summary.constraint_count == 3
    assert {constraint.category for constraint in summary.constraints} == {"Break", "Capacity"}
    assert {constraint.tag for constraint in summary.constraints} == {"BR2", "CA1"}
