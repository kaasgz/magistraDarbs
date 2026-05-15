"""Helpers for XML instance folder hygiene and source separation."""

from __future__ import annotations

from pathlib import Path
from typing import Literal


InstanceSourceKind = Literal["real", "synthetic", "unknown"]


def collect_xml_files(input_path: Path) -> list[Path]:
    """Collect XML files recursively in a stable order."""

    files = [
        path
        for path in input_path.rglob("*")
        if path.is_file() and path.suffix.lower() == ".xml"
    ]
    return sorted(files, key=lambda path: str(path.relative_to(input_path)).lower())


def infer_expected_source_from_path(input_path: Path) -> InstanceSourceKind | None:
    """Infer the intended source kind from the folder path when possible."""

    for part in reversed(input_path.parts):
        normalized = part.strip().casefold()
        if normalized == "real":
            return "real"
        if normalized == "synthetic":
            return "synthetic"
    return None


def validate_folder_source_hygiene(input_path: Path, xml_files: list[Path]) -> InstanceSourceKind | None:
    """Reject folder layouts that mix real and synthetic subtrees."""

    nested_sources = nested_source_kinds(input_path, xml_files)
    if len(nested_sources) > 1:
        raise ValueError(
            "Input folder mixes real and synthetic XML subfolders. "
            "Point the pipeline to one explicit source folder such as "
            "'data/raw/real' or 'data/raw/synthetic'."
        )

    expected_source = infer_expected_source_from_path(input_path)
    if expected_source is not None:
        return expected_source
    if len(nested_sources) == 1:
        return next(iter(nested_sources))
    return None


def validate_loaded_instance_source(
    instance: object,
    xml_file: Path,
    *,
    expected_source: InstanceSourceKind | None,
) -> None:
    """Validate one loaded instance against the expected source folder."""

    metadata = getattr(instance, "metadata", None)
    synthetic = getattr(metadata, "synthetic", None)

    if expected_source == "real" and synthetic is True:
        raise ValueError(
            f"Real-data folder contains a synthetic instance: {xml_file.as_posix()}"
        )
    if expected_source == "synthetic" and synthetic is not True:
        raise ValueError(
            "Synthetic-data folders must contain instances explicitly marked synthetic. "
            f"Found: {xml_file.as_posix()}"
        )


def resolve_instance_source_kind(
    instance: object | None,
    *,
    xml_file: Path,
    input_folder: Path,
    expected_source: InstanceSourceKind | None,
) -> tuple[InstanceSourceKind, str]:
    """Resolve whether one file should be treated as real or synthetic."""

    metadata = getattr(instance, "metadata", None) if instance is not None else None
    synthetic = getattr(metadata, "synthetic", None)
    if synthetic is True:
        return "synthetic", "metadata"
    if synthetic is False:
        return "real", "metadata"
    if expected_source in {"real", "synthetic"}:
        return expected_source, "folder"

    relative_sources = nested_source_kinds(input_folder, [xml_file])
    if len(relative_sources) == 1:
        return next(iter(relative_sources)), "relative_path"
    return "unknown", "unknown"


def register_observed_source_kind(
    observed_source_kinds: set[InstanceSourceKind],
    source_kind: InstanceSourceKind,
    *,
    input_path: Path,
) -> set[InstanceSourceKind]:
    """Track resolved instance sources and reject mixed real/synthetic batches."""

    if source_kind not in {"real", "synthetic"}:
        return set(observed_source_kinds)

    updated_kinds = {
        kind
        for kind in observed_source_kinds
        if kind in {"real", "synthetic"}
    }
    updated_kinds.add(source_kind)
    if len(updated_kinds) > 1:
        raise ValueError(
            "Input folder mixes real and synthetic instances in one batch. "
            "Use separate runs for 'data/raw/real' and 'data/raw/synthetic'. "
            f"Offending folder: {input_path.as_posix()}"
        )
    return updated_kinds


def nested_source_kinds(input_path: Path, xml_files: list[Path]) -> set[InstanceSourceKind]:
    """Detect real/synthetic subfolder markers under one input folder."""

    detected: set[InstanceSourceKind] = set()
    for path in xml_files:
        relative_parts = [part.casefold() for part in path.relative_to(input_path).parts[:-1]]
        if "real" in relative_parts:
            detected.add("real")
        if "synthetic" in relative_parts:
            detected.add("synthetic")
    return detected
