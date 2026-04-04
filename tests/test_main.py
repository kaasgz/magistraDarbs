"""Tests for the command-line entry point."""

from pathlib import Path

from src.main import format_summary, main
from src.parsers import load_instance


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_format_summary_contains_requested_fields() -> None:
    """The formatted summary should include the key thesis-facing fields."""

    summary = load_instance(str(FIXTURES_DIR / "sample_robinx.xml"))

    output = format_summary(summary)

    assert "Instance name: SampleRobinX" in output
    assert "Team count: 3" in output
    assert "Slot count: 2" in output
    assert "Constraint count: 2" in output
    assert "Constraint categories: Break, Capacity, Hard, HomeAway" in output


def test_main_prints_summary_for_valid_instance(capsys) -> None:
    """The CLI should print a readable summary for a valid instance."""

    exit_code = main([str(FIXTURES_DIR / "sample_robinx.xml")])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Instance summary" in captured.out
    assert "Instance name: SampleRobinX" in captured.out
