# Build and print a parseability inventory for RobinX / ITC2021 XML folders.

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.parsers.robinx_parser import load_instance
from src.utils import (
    collect_xml_files,
    ensure_parent_directory,
    register_observed_source_kind,
    resolve_instance_source_kind,
    validate_folder_source_hygiene,
    validate_loaded_instance_source,
)


DEFAULT_INPUT_FOLDER = Path("data/raw/real")
DEFAULT_OUTPUT_PATH = Path("data/processed/instance_inventory.csv")


def build_instance_inventory(
    input_folder: str | Path = DEFAULT_INPUT_FOLDER,
    output_csv: str | Path = DEFAULT_OUTPUT_PATH,
) -> Path:

    # Scan one XML folder, validate parseability, and save an inventory CSV.
    input_path = Path(input_folder)
    if not input_path.exists():
        raise FileNotFoundError(f"Input folder does not exist: {input_path}")
    if not input_path.is_dir():
        raise NotADirectoryError(f"Input path is not a folder: {input_path}")

    output_path = Path(output_csv)
    xml_files = collect_xml_files(input_path)
    expected_source = validate_folder_source_hygiene(input_path, xml_files)

    observed_source_kinds: set[str] = set()
    rows: list[dict[str, Any]] = []
    for xml_file in xml_files:
        row = _build_inventory_row(
            xml_file=xml_file,
            input_path=input_path,
            expected_source=expected_source,
        )
        observed_source_kinds = register_observed_source_kind(
            observed_source_kinds,
            str(row["data_source"]),
            input_path=input_path,
        )
        rows.append(row)

    frame = pd.DataFrame(rows, columns=_inventory_columns())
    ensure_parent_directory(output_path)
    frame.to_csv(output_path, index=False)
    return output_path


def instance_inventory_report(inventory_csv: str | Path) -> str:

    # Build a concise readable summary for one instance inventory CSV.
    path = Path(inventory_csv)
    frame = pd.read_csv(path)

    parseable_count = int(frame["parseable"].map(_coerce_bool).sum()) if "parseable" in frame.columns else 0
    source_counts = (
        frame["data_source"].fillna("unknown").astype("string").value_counts().to_dict()
        if "data_source" in frame.columns
        else {}
    )

    lines = [
        f"Inventory file: {path.as_posix()}",
        f"Rows: {len(frame.index)}",
        f"Parseable: {parseable_count}",
        f"Unparseable: {len(frame.index) - parseable_count}",
        "Sources: "
        + ", ".join(
            f"{source}={int(count)}"
            for source, count in sorted(source_counts.items(), key=lambda item: str(item[0]))
        )
        if source_counts
        else "Sources: none",
    ]

    if frame.empty:
        lines.append("Available instances: none")
        return "\n".join(lines)

    summary_columns = [
        "filename",
        "parseable",
        "data_source",
        "instance_name",
        "teams",
        "slots",
        "number_of_constraints",
    ]
    available_columns = [column for column in summary_columns if column in frame.columns]
    preview = frame.loc[:, available_columns].fillna("")
    lines.append("Available instances:")
    lines.append(preview.to_string(index=False))
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:

    # Create the command-line parser for instance inventory generation.
    parser = argparse.ArgumentParser(
        description="Scan XML instances, validate parseability, and save an inventory CSV.",
    )
    parser.add_argument(
        "input_folder",
        nargs="?",
        default=str(DEFAULT_INPUT_FOLDER),
        help="Folder containing RobinX / ITC2021 XML files. Defaults to data/raw/real.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output CSV path. Defaults to data/processed/instance_inventory.csv.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:

    # Run the instance inventory helper from the command line.
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    try:
        output_path = build_instance_inventory(args.input_folder, args.output)
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Failed to build instance inventory: {exc}")
        return 1

    print(instance_inventory_report(output_path))
    return 0


def _build_inventory_row(
    *,
    xml_file: Path,
    input_path: Path,
    expected_source: str | None,
) -> dict[str, Any]:

    # Build one auditable inventory row for a single XML file.
    instance = None
    try:
        instance = load_instance(str(xml_file))
        validate_loaded_instance_source(instance, xml_file, expected_source=expected_source)
    except Exception as exc:
        metadata = getattr(instance, "metadata", None) if instance is not None else None
        source_kind, source_evidence = resolve_instance_source_kind(
            instance,
            xml_file=xml_file,
            input_folder=input_path,
            expected_source=expected_source,
        )
        return {
            "filename": xml_file.name,
            "relative_path": xml_file.relative_to(input_path).as_posix(),
            "parseable": False,
            "instance_name": getattr(metadata, "name", None) or xml_file.stem,
            "teams": getattr(instance, "team_count", None),
            "slots": getattr(instance, "slot_count", None),
            "number_of_constraints": getattr(instance, "constraint_count", None),
            "data_source": source_kind,
            "source_inference": source_evidence,
            "parser_warnings": _parser_warning_summary(instance),
            "parser_note_count": len(getattr(instance, "parser_notes", []) or []),
            "parse_error": f"{type(exc).__name__}: {exc}",
        }

    source_kind, source_evidence = resolve_instance_source_kind(
        instance,
        xml_file=xml_file,
        input_folder=input_path,
        expected_source=expected_source,
    )
    parse_error = _parseability_error(instance)
    metadata = getattr(instance, "metadata", None)

    return {
        "filename": xml_file.name,
        "relative_path": xml_file.relative_to(input_path).as_posix(),
        "parseable": parse_error is None,
        "instance_name": getattr(metadata, "name", None) or xml_file.stem,
        "teams": getattr(instance, "team_count", None),
        "slots": getattr(instance, "slot_count", None),
        "number_of_constraints": getattr(instance, "constraint_count", None),
        "data_source": source_kind,
        "source_inference": source_evidence,
        "parser_warnings": _parser_warning_summary(instance),
        "parser_note_count": len(getattr(instance, "parser_notes", []) or []),
        "parse_error": parse_error,
    }


def _inventory_columns() -> list[str]:

    # Return a stable inventory CSV column order.
    return [
        "filename",
        "relative_path",
        "parseable",
        "instance_name",
        "teams",
        "slots",
        "number_of_constraints",
        "data_source",
        "source_inference",
        "parser_warnings",
        "parser_note_count",
        "parse_error",
    ]


def _parseability_error(instance: object) -> str | None:

    # Return a parseability error when the parsed instance is unusable downstream.
    team_count = getattr(instance, "team_count", 0)
    if not isinstance(team_count, int) or team_count <= 0:
        return "Parsed instance does not expose any teams."
    return None


def _coerce_bool(value: object) -> bool:

    # Convert CSV-style boolean values into booleans.
    if isinstance(value, bool):
        return value
    if pd.isna(value):
        return False
    return str(value).strip().casefold() in {"true", "1", "yes", "y"}


def _parser_warning_summary(instance: object | None) -> str | None:

    # Render warning-level parser notes into a compact inventory field.
    if instance is None:
        return None

    parser_notes = getattr(instance, "parser_notes", []) or []
    warning_messages: list[str] = []
    for note in parser_notes:
        severity = getattr(note, "severity", None)
        if severity != "warning":
            continue
        code = getattr(note, "code", None)
        message = getattr(note, "message", None)
        if code and message:
            warning_messages.append(f"{code}: {message}")
        elif message:
            warning_messages.append(str(message))
        elif code:
            warning_messages.append(str(code))

    if not warning_messages:
        return None
    return " | ".join(warning_messages)


if __name__ == "__main__":
    raise SystemExit(main())
