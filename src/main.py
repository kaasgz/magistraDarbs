"""Command-line entry point for inspecting one XML instance."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from lxml import etree

from src.parsers import InstanceSummary, load_instance


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for the project entry point."""

    parser = argparse.ArgumentParser(
        description="Load one RobinX / ITC2021 XML instance and print a summary.",
    )
    parser.add_argument(
        "xml_path",
        help="Path to a RobinX / ITC2021 XML instance file.",
    )
    return parser


def format_summary(summary: InstanceSummary) -> str:
    """Format an instance summary as clean human-readable text."""

    categories = ", ".join(summary.constraint_categories) if summary.constraint_categories else "(none)"
    lines = [
        "Instance summary",
        f"Instance name: {summary.metadata.name or '(unknown)'}",
        f"Team count: {summary.team_count}",
        f"Slot count: {summary.slot_count}",
        f"Constraint count: {summary.constraint_count}",
        f"Constraint categories: {categories}",
    ]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Parse command-line arguments, load an instance, and print its summary."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        summary = load_instance(args.xml_path)
    except (OSError, etree.XMLSyntaxError) as exc:
        print(f"Failed to load instance: {exc}", file=sys.stderr)
        return 1

    print(format_summary(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
