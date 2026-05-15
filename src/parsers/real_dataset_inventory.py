"""Real-data inventory helper for RobinX / ITC2021 XML folders."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import pandas as pd

from src.parsers.instance_inventory import build_instance_inventory


DEFAULT_REAL_INPUT_FOLDER = Path("data/raw/real")
DEFAULT_REAL_OUTPUT_PATH = Path("data/processed/real_dataset_inventory.csv")


def build_real_dataset_inventory(
    input_folder: str | Path = DEFAULT_REAL_INPUT_FOLDER,
    output_csv: str | Path = DEFAULT_REAL_OUTPUT_PATH,
) -> Path:
    """Build a recursive inventory for real RobinX / ITC2021 XML files."""

    return build_instance_inventory(input_folder=input_folder, output_csv=output_csv)


def real_dataset_inventory_report(inventory_csv: str | Path = DEFAULT_REAL_OUTPUT_PATH) -> str:
    """Return a concise terminal summary for a real-data inventory CSV."""

    path = Path(inventory_csv)
    frame = pd.read_csv(path)

    total_files = int(len(frame.index))
    parseable_files = int(frame["parseable"].map(_coerce_bool).sum()) if "parseable" in frame.columns else 0
    failed_files = total_files - parseable_files

    lines = [
        f"Inventory file: {path.as_posix()}",
        f"Total files: {total_files}",
        f"Parseable files: {parseable_files}",
        f"Failed files: {failed_files}",
    ]
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for real-data inventory generation."""

    parser = argparse.ArgumentParser(
        description="Scan data/raw/real recursively and save a real-data inventory CSV.",
    )
    parser.add_argument(
        "input_folder",
        nargs="?",
        default=str(DEFAULT_REAL_INPUT_FOLDER),
        help="Folder containing real RobinX / ITC2021 XML files. Defaults to data/raw/real.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_REAL_OUTPUT_PATH),
        help="Output CSV path. Defaults to data/processed/real_dataset_inventory.csv.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the real-data inventory helper from the command line."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        output_path = build_real_dataset_inventory(args.input_folder, args.output)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Failed to build real-data inventory: {exc}")
        return 1

    print(real_dataset_inventory_report(output_path))
    return 0


def _coerce_bool(value: object) -> bool:
    """Convert CSV-style booleans into Python booleans."""

    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


__all__ = [
    "DEFAULT_REAL_INPUT_FOLDER",
    "DEFAULT_REAL_OUTPUT_PATH",
    "build_real_dataset_inventory",
    "real_dataset_inventory_report",
]


if __name__ == "__main__":
    raise SystemExit(main())
