# Build a conservative solver compatibility matrix for real XML instances.

from __future__ import annotations

import argparse
import logging
import shutil
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import pandas as pd

from src.experiments.full_benchmark import DEFAULT_FULL_SOLVER_PORTFOLIO
from src.parsers import load_instance
from src.utils import collect_xml_files, ensure_parent_directory


LOGGER = logging.getLogger(__name__)

DEFAULT_INPUT_FOLDER = Path("data/raw/real")
DEFAULT_OUTPUT_CSV = Path("data/processed/real_pipeline_current/solver_compatibility_matrix.csv")
DEFAULT_SUMMARY_MARKDOWN = Path("data/results/real_pipeline_current/solver_compatibility_summary.md")

SupportStatus = Literal["supported", "partially_supported", "unsupported", "not_configured"]


@dataclass(frozen=True, slots=True)
class CompatibilitySettings:

    # Resolved settings for compatibility matrix construction.
    input_folder: Path
    output_csv: Path
    summary_markdown: Path
    solver_names: tuple[str, ...]
    timefold_executable_path: Path | None


@dataclass(frozen=True, slots=True)
class InstanceProfile:

    # Parsed instance facts needed for compatibility decisions.
    instance_name: str
    round_robin_mode: str | None
    constraint_families: tuple[str, ...]
    parser_note_codes: tuple[str, ...]
    parser_warning_codes: tuple[str, ...]
    team_count: int
    slot_count: int


@dataclass(frozen=True, slots=True)
class CompatibilityDecision:

    # One solver compatibility classification.
    support_status: SupportStatus
    unsupported_constraint_families: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CompatibilityMatrixResult:

    # Paths and row count produced by a matrix build.
    matrix_csv: Path
    summary_markdown: Path
    num_rows: int
    num_instances: int


def build_solver_compatibility_matrix(
    *,
    input_folder: str | Path = DEFAULT_INPUT_FOLDER,
    output_csv: str | Path = DEFAULT_OUTPUT_CSV,
    summary_markdown: str | Path = DEFAULT_SUMMARY_MARKDOWN,
    solver_names: Sequence[str] = DEFAULT_FULL_SOLVER_PORTFOLIO,
    timefold_executable_path: str | Path | None = None,
) -> CompatibilityMatrixResult:

    # Build and save a per-instance, per-solver compatibility matrix.
    settings = CompatibilitySettings(
        input_folder=Path(input_folder),
        output_csv=Path(output_csv),
        summary_markdown=Path(summary_markdown),
        solver_names=tuple(solver_names),
        timefold_executable_path=_optional_path(timefold_executable_path),
    )
    _validate_settings(settings)

    rows = _build_matrix_rows(settings)
    matrix = pd.DataFrame(rows, columns=_matrix_columns())
    matrix = matrix.sort_values(
        by=["instance_name", "solver_name"],
        ascending=[True, True],
        kind="mergesort",
    ).reset_index(drop=True)

    ensure_parent_directory(settings.output_csv)
    matrix.to_csv(settings.output_csv, index=False)
    ensure_parent_directory(settings.summary_markdown)
    settings.summary_markdown.write_text(
        _render_summary_markdown(settings=settings, matrix=matrix),
        encoding="utf-8",
    )

    LOGGER.info("Saved %d compatibility rows to %s", len(matrix.index), settings.output_csv)
    LOGGER.info("Saved compatibility summary to %s", settings.summary_markdown)
    return CompatibilityMatrixResult(
        matrix_csv=settings.output_csv,
        summary_markdown=settings.summary_markdown,
        num_rows=len(matrix.index),
        num_instances=int(matrix["instance_name"].nunique()) if not matrix.empty else 0,
    )


def build_argument_parser() -> argparse.ArgumentParser:

    # Create the CLI parser for the compatibility matrix builder.
    parser = argparse.ArgumentParser(
        description="Build a conservative solver compatibility matrix for real XML instances.",
    )
    parser.add_argument(
        "--input-folder",
        default=str(DEFAULT_INPUT_FOLDER),
        help="Folder containing real RobinX / ITC2021 XML files.",
    )
    parser.add_argument(
        "--output-csv",
        default=str(DEFAULT_OUTPUT_CSV),
        help="Output CSV path for the compatibility matrix.",
    )
    parser.add_argument(
        "--summary-markdown",
        default=str(DEFAULT_SUMMARY_MARKDOWN),
        help="Output Markdown path for the compatibility summary.",
    )
    parser.add_argument(
        "--timefold-executable",
        default=None,
        help="Optional external Timefold executable path. If omitted, Timefold is not_configured.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:

    # Run compatibility matrix construction from the command line.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        result = build_solver_compatibility_matrix(
            input_folder=args.input_folder,
            output_csv=args.output_csv,
            summary_markdown=args.summary_markdown,
            timefold_executable_path=args.timefold_executable,
        )
    except (FileNotFoundError, NotADirectoryError, ValueError) as exc:
        LOGGER.error("Failed to build solver compatibility matrix: %s", exc)
        return 1

    print(f"Solver compatibility matrix saved to {result.matrix_csv}")
    print(f"Solver compatibility summary saved to {result.summary_markdown}")
    return 0


def _build_matrix_rows(settings: CompatibilitySettings) -> list[dict[str, str]]:

    # Build all matrix rows using the current parser and static solver scope.
    xml_files = collect_xml_files(settings.input_folder)
    rows: list[dict[str, str]] = []
    for xml_file in xml_files:
        LOGGER.info("Assessing solver compatibility for %s", xml_file)
        try:
            instance = load_instance(str(xml_file))
            profile = _profile_instance(instance, xml_file)
        except Exception as exc:
            rows.extend(
                _parser_failure_rows(
                    xml_file=xml_file,
                    settings=settings,
                    error=exc,
                )
            )
            continue

        if profile.team_count <= 0:
            rows.extend(
                _global_unsupported_rows(
                    profile=profile,
                    settings=settings,
                    reason="parser limitation: no teams were extracted",
                )
            )
            continue

        for solver_name in settings.solver_names:
            decision = _assess_solver(profile, solver_name, settings)
            rows.append(
                {
                    "instance_name": profile.instance_name,
                    "solver_name": solver_name,
                    "support_status": decision.support_status,
                    "unsupported_constraint_families": _join_values(
                        decision.unsupported_constraint_families
                    ),
                    "notes": _join_values(decision.notes),
                }
            )
    return rows


def _profile_instance(instance: object, xml_file: Path) -> InstanceProfile:

    # Extract the compatibility-relevant profile from one parsed instance.
    metadata = getattr(instance, "metadata", None)
    instance_name = _first_non_empty(
        [
            getattr(metadata, "name", None),
            xml_file.stem,
        ]
    )
    parser_notes = list(getattr(instance, "parser_notes", []) or [])
    parser_note_codes = tuple(
        sorted(
            str(getattr(note, "code", "parser_note")).strip()
            for note in parser_notes
            if str(getattr(note, "code", "")).strip()
        )
    )
    parser_warning_codes = tuple(
        sorted(
            str(getattr(note, "code", "parser_warning")).strip()
            for note in parser_notes
            if str(getattr(note, "severity", "")).casefold() == "warning"
            and str(getattr(note, "code", "")).strip()
        )
    )
    return InstanceProfile(
        instance_name=instance_name or xml_file.stem,
        round_robin_mode=_normalize_round_robin_mode(getattr(metadata, "round_robin_mode", None)),
        constraint_families=_extract_constraint_families(instance),
        parser_note_codes=parser_note_codes,
        parser_warning_codes=parser_warning_codes,
        team_count=_safe_nonnegative_int(getattr(instance, "team_count", 0)),
        slot_count=_safe_nonnegative_int(getattr(instance, "slot_count", 0)),
    )


def _assess_solver(
    profile: InstanceProfile,
    solver_name: str,
    settings: CompatibilitySettings,
) -> CompatibilityDecision:

    # Return the conservative compatibility decision for one solver.
    normalized_solver = solver_name.strip().casefold()
    if normalized_solver == "random_baseline":
        return _assess_random_baseline(profile)
    if normalized_solver == "cpsat_solver":
        return _assess_cpsat_solver(profile)
    if normalized_solver == "simulated_annealing_solver":
        return _assess_simulated_annealing_solver(profile)
    if normalized_solver == "timefold":
        return _assess_timefold(profile, settings)
    return CompatibilityDecision(
        support_status="unsupported",
        unsupported_constraint_families=(),
        notes=(f"unknown solver registry name: {solver_name}",),
    )


def _assess_random_baseline(profile: InstanceProfile) -> CompatibilityDecision:

    # Classify the diagnostic random baseline.
    notes = [
        "diagnostic control baseline only; returns deterministic synthetic scores",
        "does not construct a real schedule",
        "does not enforce RobinX / ITC2021 constraints",
    ]
    notes.extend(_parser_note_text(profile))
    return CompatibilityDecision(
        support_status="partially_supported",
        unsupported_constraint_families=profile.constraint_families,
        notes=tuple(notes),
    )


def _assess_cpsat_solver(profile: InstanceProfile) -> CompatibilityDecision:

    # Classify the CP-SAT round-robin baseline.
    notes: list[str] = []
    if profile.round_robin_mode not in {"single", "double"}:
        notes.append("round-robin mode missing or ambiguous; solver falls back to single round robin")

    if profile.round_robin_mode == "double":
        notes.append("models double round robin with explicit home/away legs")
    else:
        notes.append("models compact single round-robin structure")

    if profile.constraint_families:
        notes.append("parsed constraint families are recorded but not enforced by the CP-SAT baseline")
        status: SupportStatus = "partially_supported"
    else:
        status = "supported"

    if profile.round_robin_mode is None:
        status = "partially_supported"
    notes.extend(_slot_note(profile))
    notes.extend(_parser_note_text(profile))
    return CompatibilityDecision(
        support_status=status,
        unsupported_constraint_families=profile.constraint_families,
        notes=tuple(notes),
    )


def _assess_simulated_annealing_solver(profile: InstanceProfile) -> CompatibilityDecision:

    # Classify the simplified simulated annealing baseline.
    notes = [
        "simplified single round-robin search",
        "does not model explicit home/away decisions",
        "does not directly enforce RobinX / ITC2021 constraints",
    ]
    if profile.round_robin_mode == "double":
        notes.insert(0, "unsupported round-robin mode: double")
        notes.extend(_parser_note_text(profile))
        return CompatibilityDecision(
            support_status="unsupported",
            unsupported_constraint_families=profile.constraint_families,
            notes=tuple(notes),
        )

    if profile.round_robin_mode is None:
        notes.insert(0, "round-robin mode missing or ambiguous; solver assumes single round robin")

    status: SupportStatus = "partially_supported" if profile.constraint_families or profile.round_robin_mode is None else "supported"
    notes.extend(_slot_note(profile))
    notes.extend(_parser_note_text(profile))
    return CompatibilityDecision(
        support_status=status,
        unsupported_constraint_families=profile.constraint_families,
        notes=tuple(notes),
    )


def _assess_timefold(
    profile: InstanceProfile,
    settings: CompatibilitySettings,
) -> CompatibilityDecision:

    # Classify the external Timefold integration.
    if settings.timefold_executable_path is None:
        return CompatibilityDecision(
            support_status="not_configured",
            unsupported_constraint_families=profile.constraint_families,
            notes=(
                "missing external solver executable",
                "Python repository does not bundle or download a Timefold runtime",
            ),
        )
    if not _executable_exists(settings.timefold_executable_path):
        return CompatibilityDecision(
            support_status="not_configured",
            unsupported_constraint_families=profile.constraint_families,
            notes=(f"configured Timefold executable was not found: {settings.timefold_executable_path}",),
        )

    notes: list[str] = [
        "external subprocess integration configured",
        "Python adapter exports round-robin structure and declared constraints as metadata",
        "constraint enforcement depends on the external Timefold model",
    ]
    if profile.round_robin_mode not in {"single", "double"}:
        notes.insert(0, "round-robin mode missing or ambiguous; adapter falls back to single round robin")

    status: SupportStatus = "partially_supported"
    if not profile.constraint_families and profile.round_robin_mode in {"single", "double"}:
        status = "supported"
    notes.extend(_parser_note_text(profile))
    return CompatibilityDecision(
        support_status=status,
        unsupported_constraint_families=profile.constraint_families,
        notes=tuple(notes),
    )


def _parser_failure_rows(
    *,
    xml_file: Path,
    settings: CompatibilitySettings,
    error: Exception,
) -> list[dict[str, str]]:

    # Return unsupported rows for an XML file the current parser cannot load.
    note = f"parser limitation: {type(error).__name__}: {error}"
    return [
        {
            "instance_name": xml_file.stem,
            "solver_name": solver_name,
            "support_status": "unsupported",
            "unsupported_constraint_families": "",
            "notes": note,
        }
        for solver_name in settings.solver_names
    ]


def _global_unsupported_rows(
    *,
    profile: InstanceProfile,
    settings: CompatibilitySettings,
    reason: str,
) -> list[dict[str, str]]:

    # Return unsupported rows when the parsed instance is unusable by all solvers.
    notes = _join_values((reason, *_parser_note_text(profile)))
    return [
        {
            "instance_name": profile.instance_name,
            "solver_name": solver_name,
            "support_status": "unsupported",
            "unsupported_constraint_families": _join_values(profile.constraint_families),
            "notes": notes,
        }
        for solver_name in settings.solver_names
    ]


def _render_summary_markdown(
    *,
    settings: CompatibilitySettings,
    matrix: pd.DataFrame,
) -> str:

    # Render a thesis-friendly Markdown summary for the matrix.
    lines = [
        "# Solver Compatibility Summary",
        "",
        "## Scope",
        "",
        f"- Input folder: `{settings.input_folder.as_posix()}`",
        f"- Matrix CSV: `{settings.output_csv.as_posix()}`",
        f"- Solver portfolio: `{', '.join(settings.solver_names)}`",
        f"- Timefold executable: `{_path_or_not_configured(settings.timefold_executable_path)}`",
        "- Compatibility is based on the currently implemented modeling scope, not benchmark success alone.",
        "",
        "## Counts By Solver And Status",
        "",
    ]
    lines.extend(_render_counts_table(matrix))
    lines.extend(
        [
            "",
            "## Interpretation Notes",
            "",
            "- `supported` means the implemented solver model covers the parsed structural format without known unsupported constraint families.",
            "- `partially_supported` means the solver can process the instance only under simplifying assumptions.",
            "- `unsupported` means the parsed instance requires structure outside the solver's current model.",
            "- `not_configured` is used for external solvers such as Timefold when no executable is available.",
            "",
        ]
    )
    return "\n".join(lines)


def _render_counts_table(matrix: pd.DataFrame) -> list[str]:

    # Render counts grouped by solver and support status.
    lines = ["| solver_name | support_status | count |", "| --- | --- | ---: |"]
    if matrix.empty:
        lines.append("| none | none | 0 |")
        return lines

    counts = Counter(
        (str(row["solver_name"]), str(row["support_status"]))
        for row in matrix.to_dict(orient="records")
    )
    for solver_name, support_status in sorted(counts):
        lines.append(f"| `{solver_name}` | `{support_status}` | {counts[(solver_name, support_status)]} |")
    return lines


def _validate_settings(settings: CompatibilitySettings) -> None:

    # Validate user-facing paths and solver list before writing outputs.
    if not settings.input_folder.exists():
        raise FileNotFoundError(f"Input folder does not exist: {settings.input_folder}")
    if not settings.input_folder.is_dir():
        raise NotADirectoryError(f"Input path is not a folder: {settings.input_folder}")
    if not collect_xml_files(settings.input_folder):
        raise ValueError(f"No XML files found under {settings.input_folder.as_posix()}.")
    if not settings.solver_names:
        raise ValueError("At least one solver name is required.")


def _matrix_columns() -> list[str]:

    # Return the stable required CSV column order.
    return [
        "instance_name",
        "solver_name",
        "support_status",
        "unsupported_constraint_families",
        "notes",
    ]


def _extract_constraint_families(instance: object) -> tuple[str, ...]:

    # Extract stable constraint-family labels from the parsed instance.
    constraints = list(getattr(instance, "constraints", []) or [])
    families: set[str] = set()
    for constraint in constraints:
        for field_name in ("category", "tag", "type_name"):
            value = getattr(constraint, field_name, None)
            if isinstance(value, str) and value.strip():
                families.add(value.strip())
    return tuple(sorted(families, key=str.casefold))


def _normalize_round_robin_mode(value: object) -> str | None:

    # Normalize the parsed round-robin mode for compatibility checks.
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().casefold()
    if "double" in normalized:
        return "double"
    if "single" in normalized:
        return "single"
    return None


def _slot_note(profile: InstanceProfile) -> tuple[str, ...]:

    # Return a note when no explicit slots were parsed.
    if profile.slot_count > 0:
        return ()
    return ("no slots parsed; solver would use an internally inferred slot count",)


def _parser_note_text(profile: InstanceProfile) -> tuple[str, ...]:

    # Return compact parser-note text for compatibility notes.
    if not profile.parser_warning_codes:
        return ()
    return (f"parser warnings: {_join_values(profile.parser_warning_codes)}",)


def _join_values(values: Sequence[str]) -> str:

    # Join strings for CSV fields using a stable separator.
    return "; ".join(str(value).strip() for value in values if str(value).strip())


def _first_non_empty(values: Sequence[object]) -> str | None:

    # Return the first non-empty string from a sequence.
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _safe_nonnegative_int(value: object) -> int:

    # Convert a count-like value to a non-negative integer.
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return max(0, value)
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _optional_path(value: str | Path | None) -> Path | None:

    # Convert nullable path input into a Path.
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Path(text)


def _executable_exists(path: Path) -> bool:

    # Return whether a configured external executable can be launched.
    if path.exists():
        return True
    return shutil.which(str(path)) is not None


def _path_or_not_configured(path: Path | None) -> str:

    # Return a path string or the standard not-configured marker.
    if path is None:
        return "not configured"
    return path.as_posix()


__all__ = [
    "CompatibilityMatrixResult",
    "CompatibilitySettings",
    "DEFAULT_INPUT_FOLDER",
    "DEFAULT_OUTPUT_CSV",
    "DEFAULT_SUMMARY_MARKDOWN",
    "build_solver_compatibility_matrix",
]


if __name__ == "__main__":
    raise SystemExit(main())
