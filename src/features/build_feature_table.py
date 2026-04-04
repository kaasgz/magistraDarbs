"""Build a CSV table of structural features for multiple XML instances."""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import pandas as pd

from src.features.feature_extractor import FeatureValue, extract_features
from src.parsers import load_instance
from src.utils import (
    collect_xml_files,
    default_run_summary_path,
    ensure_parent_directory,
    get_compat_path,
    get_random_seed,
    register_observed_source_kind,
    resolve_instance_source_kind,
    load_yaml_config,
    validate_folder_source_hygiene,
    validate_loaded_instance_source,
    write_run_summary,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("configs/feature_config.yaml")
DEFAULT_INPUT_FOLDER = Path("data/raw/real")
DEFAULT_OUTPUT_PATH = Path("data/processed/features.csv")


def build_feature_table(
    input_folder: str | Path,
    output_csv: str | Path = DEFAULT_OUTPUT_PATH,
    *,
    random_seed: int = 42,
    config_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    run_summary_path: str | Path | None = None,
) -> Path:
    """Parse XML instances in a folder and save one feature table as CSV.

    Args:
        input_folder: Folder containing RobinX / ITC2021 XML instances.
        output_csv: Output CSV path. Defaults to ``data/processed/features.csv``.
        random_seed: Recorded in run metadata for reproducibility.
        config_path: Optional YAML config path used for the run.
        config: Optional loaded config snapshot to include in metadata.
        run_summary_path: Optional JSON sidecar path for run metadata.

    Returns:
        The path of the written CSV file.
    """

    input_path = Path(input_folder)
    if not input_path.exists():
        raise FileNotFoundError(f"Input folder does not exist: {input_path}")
    if not input_path.is_dir():
        raise NotADirectoryError(f"Input path is not a folder: {input_path}")

    output_path = Path(output_csv)
    xml_files = collect_xml_files(input_path)
    expected_source = validate_folder_source_hygiene(input_path, xml_files)
    LOGGER.info("Found %d XML files in %s", len(xml_files), input_path)

    rows: list[dict[str, FeatureValue]] = []
    failed_files: list[Path] = []
    observed_source_kinds: set[str] = set()

    for index, xml_file in enumerate(xml_files, start=1):
        LOGGER.info("[%d/%d] Processing %s", index, len(xml_files), xml_file)
        try:
            instance = load_instance(str(xml_file))
        except Exception as exc:
            failed_files.append(xml_file)
            LOGGER.warning(
                "Skipping broken file %s: %s: %s",
                xml_file,
                type(exc).__name__,
                exc,
            )
            continue

        validate_loaded_instance_source(instance, xml_file, expected_source=expected_source)
        source_kind, _ = resolve_instance_source_kind(
            instance,
            xml_file=xml_file,
            input_folder=input_path,
            expected_source=expected_source,
        )
        observed_source_kinds = register_observed_source_kind(
            observed_source_kinds,
            source_kind,
            input_path=input_path,
        )

        try:
            _ensure_minimal_instance_structure(instance, xml_file)
            _log_parser_notes(instance, xml_file)
            features = extract_features(instance)
        except Exception as exc:
            failed_files.append(xml_file)
            LOGGER.warning(
                "Skipping broken file %s: %s: %s",
                xml_file,
                type(exc).__name__,
                exc,
            )
            continue

        row: dict[str, FeatureValue] = {
            "instance_name": instance.metadata.name or xml_file.stem,
        }
        row.update(features)
        rows.append(row)

    columns = _ordered_columns(rows)
    table = pd.DataFrame(rows, columns=columns)
    ensure_parent_directory(output_path)
    table.to_csv(output_path, index=False)

    summary_path = Path(run_summary_path) if run_summary_path is not None else default_run_summary_path(output_path)
    write_run_summary(
        summary_path,
        stage_name="feature_table_build",
        config_path=config_path,
        config=config,
        settings={
            "random_seed": random_seed,
        },
        inputs={
            "instance_folder": input_path,
        },
        outputs={
            "features_csv": output_path,
            "run_summary": summary_path,
        },
        results={
            "num_xml_files_found": len(xml_files),
            "num_feature_rows": len(table.index),
            "num_failed_files": len(failed_files),
            "failed_files": [path.as_posix() for path in failed_files],
            "input_source_kind": expected_source or "unknown",
        },
    )

    LOGGER.info("Saved %d instance rows to %s", len(table.index), output_path)
    LOGGER.info("Saved feature-build run summary to %s", summary_path)
    if failed_files:
        LOGGER.warning("Skipped %d broken files.", len(failed_files))

    return output_path


def build_feature_table_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> Path:
    """Build the feature table using values loaded from a YAML configuration file."""

    config = load_yaml_config(config_path)
    output_path = get_compat_path(config, ["paths.output_csv", "paths.features_csv"], DEFAULT_OUTPUT_PATH)
    summary_path = get_compat_path(
        config,
        ["paths.run_summary", "paths.run_summary_path"],
        default_run_summary_path(output_path),
    )
    return build_feature_table(
        input_folder=get_compat_path(config, ["paths.instance_folder", "paths.input_folder"], DEFAULT_INPUT_FOLDER),
        output_csv=output_path,
        random_seed=get_random_seed(config, 42),
        config_path=config_path,
        config=config,
        run_summary_path=summary_path,
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the command-line parser for feature table generation."""

    parser = argparse.ArgumentParser(
        description="Parse XML instances and build one structural feature CSV table.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the feature-build YAML configuration file.",
    )
    parser.add_argument(
        "input_folder",
        nargs="?",
        help="Folder containing RobinX / ITC2021 XML instance files.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output CSV path. Defaults to the config value or data/processed/features.csv.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Recorded in run metadata for reproducibility.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run the feature table builder from the command line."""

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = load_yaml_config(args.config)
        resolved_output_path = args.output or get_compat_path(
            config,
            ["paths.output_csv", "paths.features_csv"],
            DEFAULT_OUTPUT_PATH,
        )
        output_path = build_feature_table(
            input_folder=args.input_folder
            or get_compat_path(config, ["paths.instance_folder", "paths.input_folder"], DEFAULT_INPUT_FOLDER),
            output_csv=resolved_output_path,
            random_seed=args.random_seed if args.random_seed is not None else get_random_seed(config, 42),
            config_path=args.config,
            config=config,
            run_summary_path=get_compat_path(
                config,
                ["paths.run_summary", "paths.run_summary_path"],
                default_run_summary_path(resolved_output_path),
            ),
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        print(f"Failed to build feature table: {exc}", file=sys.stderr)
        return 1

    print(f"Feature table saved to {output_path}")
    return 0
def _ordered_columns(rows: list[dict[str, FeatureValue]]) -> list[str]:
    """Build a stable CSV column order with ``instance_name`` first."""

    columns = ["instance_name"]
    seen = {"instance_name"}

    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                columns.append(key)

    return columns


def _ensure_minimal_instance_structure(instance: object, xml_file: Path) -> None:
    """Reject instances that do not expose the minimum required structure."""

    team_count = getattr(instance, "team_count", 0)
    if not isinstance(team_count, int) or team_count <= 0:
        raise ValueError(f"Instance {xml_file} does not expose any teams after parsing.")


def _log_parser_notes(instance: object, xml_file: Path) -> None:
    """Log parser notes so recoveries and ambiguities stay visible in the pipeline."""

    parser_notes = list(getattr(instance, "parser_notes", []) or [])
    for note in parser_notes:
        severity = str(getattr(note, "severity", "info")).casefold()
        code = getattr(note, "code", "parser_note")
        message = getattr(note, "message", "")
        log_message = "[%s] %s: %s", code, xml_file.name, message
        if severity == "warning":
            LOGGER.warning(*log_message)
        else:
            LOGGER.info(*log_message)


if __name__ == "__main__":
    raise SystemExit(main())
