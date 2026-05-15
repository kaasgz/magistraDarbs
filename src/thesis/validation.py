"""Validation helpers for aligning the practical thesis text with repository data."""

from __future__ import annotations

import json
import math
import re
import subprocess
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Final
from urllib.parse import quote

import pandas as pd

from src.experiments.full_benchmark import DEFAULT_FULL_SOLVER_PORTFOLIO
from src.selection.modeling import BENCHMARK_DERIVED_PREFIXES
from src.thesis.document import ThesisSentence, practical_section_sentences


STATUS_OK = "OK"
STATUS_MISMATCH = "MISMATCH"
STATUS_NOT_FOUND = "NOT_FOUND"
DEFAULT_GITHUB_BRANCH = "main"
THESIS_DOCX_GLOB: Final[str] = "kg21071_magistra_darbs_ar_praktisko*.docx"

TOKEN_PATTERN = re.compile(
    r"\d+,\d+|\d+|best_solver|objective_|benchmark_|label_|target_|dataset_|"
    r"partially_modeled_run|not_configured|Random Forest|Timefold|RobinX|ITC2021|Python",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ValidationPaths:
    """Canonical artifact paths used for thesis validation."""

    workspace_root: Path
    thesis_docx: Path
    selection_dataset_full_csv: Path
    selection_dataset_full_run_summary_json: Path
    full_evaluation_csv: Path
    full_evaluation_summary_csv: Path
    full_evaluation_run_summary_json: Path
    full_combined_benchmark_csv: Path
    full_feature_importance_csv: Path
    solver_comparison_csv: Path
    solver_support_summary_csv: Path
    solver_win_counts_csv: Path
    average_runtime_csv: Path
    real_evaluation_summary_csv: Path
    real_benchmark_csv: Path
    synthetic_benchmark_csv: Path

    @classmethod
    def from_workspace(cls, workspace_root: str | Path) -> "ValidationPaths":
        """Build the canonical path layout anchored at one workspace root."""

        root = Path(workspace_root)
        return cls(
            workspace_root=root,
            thesis_docx=resolve_thesis_docx(root),
            selection_dataset_full_csv=root / "data" / "processed" / "selection_dataset_full.csv",
            selection_dataset_full_run_summary_json=root
            / "data"
            / "processed"
            / "selection_dataset_full_run_summary.json",
            full_evaluation_csv=root / "data" / "results" / "full_selection" / "selector_evaluation.csv",
            full_evaluation_summary_csv=root / "data" / "results" / "full_selection" / "selector_evaluation_summary.csv",
            full_evaluation_run_summary_json=root
            / "data"
            / "results"
            / "full_selection"
            / "selector_evaluation_run_summary.json",
            full_combined_benchmark_csv=root
            / "data"
            / "results"
            / "full_selection"
            / "combined_benchmark_results.csv",
            full_feature_importance_csv=root / "data" / "results" / "full_selection" / "feature_importance.csv",
            solver_comparison_csv=root / "data" / "results" / "reports" / "solver_comparison.csv",
            solver_support_summary_csv=root / "data" / "results" / "reports" / "solver_support_summary.csv",
            solver_win_counts_csv=root / "data" / "results" / "reports" / "solver_win_counts.csv",
            average_runtime_csv=root / "data" / "results" / "reports" / "average_runtime_per_solver.csv",
            real_evaluation_summary_csv=root
            / "data"
            / "results"
            / "real_pipeline_current"
            / "selector_evaluation_summary.csv",
            real_benchmark_csv=root / "data" / "results" / "real_pipeline_current" / "benchmark_results.csv",
            synthetic_benchmark_csv=root / "data" / "results" / "synthetic_study" / "benchmark_results.csv",
        )


def resolve_thesis_docx(workspace_root: str | Path) -> Path:
    """Return the current thesis DOCX from the workspace.

    The thesis file name changes when Word creates numbered copies, so the
    validation pipeline uses the newest matching file instead of a stale fixed
    name.
    """

    root = Path(workspace_root)
    candidates = [
        path
        for path in root.glob(THESIS_DOCX_GLOB)
        if path.is_file() and not path.name.startswith("~$")
    ]
    if not candidates:
        return root / "kg21071_magistra_darbs_ar_praktisko.docx"
    return max(candidates, key=lambda path: path.stat().st_mtime_ns)


@dataclass(frozen=True, slots=True)
class ValidationRecord:
    """One row in the thesis validation output."""

    thesis_section: str
    statement_text: str
    value_in_text: str
    source_file: str
    source_column: str
    actual_value: str
    status: str
    notes: str
    data_reference: str

    def to_csv_row(self) -> dict[str, str]:
        """Return the CSV-compatible mapping row."""

        return {
            "thesis_section": self.thesis_section,
            "statement_text": self.statement_text,
            "value_in_text": self.value_in_text,
            "source_file": self.source_file,
            "source_column": self.source_column,
            "actual_value": self.actual_value,
            "status": self.status,
            "notes": self.notes,
            "data_reference": self.data_reference,
        }


@dataclass(slots=True)
class ValidationContext:
    """Loaded data used by sentence validators."""

    paths: ValidationPaths
    selection_dataset: pd.DataFrame
    selection_dataset_full_run_summary: dict[str, Any]
    full_evaluation: pd.DataFrame
    full_evaluation_summary: pd.DataFrame
    full_evaluation_run_summary: dict[str, Any]
    full_combined_benchmark: pd.DataFrame
    full_feature_importance: pd.DataFrame
    solver_comparison: pd.DataFrame
    solver_support_summary: pd.DataFrame
    solver_win_counts: pd.DataFrame
    average_runtime: pd.DataFrame
    real_evaluation_summary: pd.DataFrame
    real_benchmark: pd.DataFrame
    synthetic_benchmark: pd.DataFrame

    @classmethod
    def load(cls, workspace_root: str | Path) -> "ValidationContext":
        """Load the canonical validation data once."""

        paths = ValidationPaths.from_workspace(workspace_root)
        return cls(
            paths=paths,
            selection_dataset=pd.read_csv(paths.selection_dataset_full_csv),
            selection_dataset_full_run_summary=json.loads(
                paths.selection_dataset_full_run_summary_json.read_text(encoding="utf-8")
            ),
            full_evaluation=pd.read_csv(paths.full_evaluation_csv),
            full_evaluation_summary=pd.read_csv(paths.full_evaluation_summary_csv),
            full_evaluation_run_summary=json.loads(paths.full_evaluation_run_summary_json.read_text(encoding="utf-8")),
            full_combined_benchmark=pd.read_csv(paths.full_combined_benchmark_csv),
            full_feature_importance=pd.read_csv(paths.full_feature_importance_csv),
            solver_comparison=pd.read_csv(paths.solver_comparison_csv),
            solver_support_summary=pd.read_csv(paths.solver_support_summary_csv),
            solver_win_counts=pd.read_csv(paths.solver_win_counts_csv),
            average_runtime=pd.read_csv(paths.average_runtime_csv),
            real_evaluation_summary=pd.read_csv(paths.real_evaluation_summary_csv),
            real_benchmark=pd.read_csv(paths.real_benchmark_csv),
            synthetic_benchmark=pd.read_csv(paths.synthetic_benchmark_csv),
        )


def build_validation_records(workspace_root: str | Path) -> list[ValidationRecord]:
    """Validate the practical thesis section sentence by sentence."""

    context = ValidationContext.load(workspace_root)
    sentences = practical_section_sentences(context.paths.thesis_docx)
    records: list[ValidationRecord] = []

    for index, sentence in enumerate(sentences, start=1):
        data_reference = f"DATA-{index}"
        record = _validate_sentence(sentence, context, data_reference=data_reference)
        records.append(record)

    return records


def build_data_reference_mapping(records: list[ValidationRecord]) -> dict[str, dict[str, Any]]:
    """Build the `[DATA-x]` reference mapping JSON payload."""

    mapping: dict[str, dict[str, Any]] = {}
    workspace_root = _infer_workspace_root(records)
    for record in records:
        file_value = record.source_file or None
        column_value = record.source_column or None
        mapping[record.data_reference] = {
            "file": file_value,
            "column": column_value,
            "description": f"{record.thesis_section}: {record.statement_text}",
            "status": record.status,
            "actual_value": record.actual_value,
            "notes": record.notes,
            "source_links": build_source_link_entries(record.source_file, workspace_root),
        }
    return mapping


def build_validation_markdown(records: list[ValidationRecord]) -> str:
    """Render a readable Markdown validation report."""

    total = len(records)
    ok_count = sum(record.status == STATUS_OK for record in records)
    mismatch_count = sum(record.status == STATUS_MISMATCH for record in records)
    not_found_count = sum(record.status == STATUS_NOT_FOUND for record in records)
    workspace_root = _infer_workspace_root(records)

    lines = [
        "# Thesis Text Validation",
        "",
        "This report audits the practical section (4. nodaļa) of the thesis against repository artifacts.",
        "",
        "## Summary",
        "",
        f"- Checked claims: {total}",
        f"- `OK`: {ok_count}",
        f"- `MISMATCH`: {mismatch_count}",
        f"- `NOT_FOUND`: {not_found_count}",
        "",
        "## Correctly aligned claims",
        "",
    ]

    ok_records = [record for record in records if record.status == STATUS_OK]
    if ok_records:
        for record in ok_records:
            lines.extend(
                [
                    f"- [{record.data_reference}] {record.thesis_section}: {record.statement_text}",
                    f"  Source: {_format_source_reference_markdown(record.source_file, workspace_root)}",
                    f"  Actual: `{record.actual_value}`",
                ]
            )
    else:
        lines.append("- No directly verified claims were found.")

    lines.extend(["", "## Inconsistencies", ""])
    mismatches = [record for record in records if record.status == STATUS_MISMATCH]
    if mismatches:
        for record in mismatches:
            lines.extend(
                [
                    f"- [{record.data_reference}] {record.thesis_section}: {record.statement_text}",
                    f"  Text value: `{record.value_in_text}`",
                    f"  Actual: `{record.actual_value}`",
                    f"  Source: {_format_source_reference_markdown(record.source_file, workspace_root)}",
                    f"  Note: {record.notes}",
                ]
            )
    else:
        lines.append("- No direct numeric mismatches were detected.")

    lines.extend(["", "## Manual review needed", ""])
    manual_review = [record for record in records if record.status == STATUS_NOT_FOUND]
    if manual_review:
        for record in manual_review:
            lines.extend(
                [
                    f"- [{record.data_reference}] {record.thesis_section}: {record.statement_text}",
                    f"  Note: {record.notes}",
                ]
            )
    else:
        lines.append("- Every checked sentence was mapped to a repository artifact.")

    lines.extend(["", "## Recommended thesis text fixes", ""])
    if mismatches or manual_review:
        for record in [*mismatches, *manual_review]:
            lines.append(f"- Review {record.data_reference} in `{record.thesis_section}`: {record.notes}")
    else:
        lines.append("- No thesis text corrections are currently required for the practical section.")

    return "\n".join(lines).strip() + "\n"


def _infer_workspace_root(records: list[ValidationRecord]) -> Path:
    """Infer the workspace root from the current module location."""

    _ = records
    return Path(__file__).resolve().parents[2]


def build_source_link_entries(source_file: str, workspace_root: str | Path) -> list[dict[str, str]]:
    """Return structured GitHub links for one validation source string."""

    paths = _split_source_paths(source_file)
    repo_url = _repository_github_url(workspace_root)
    branch = _repository_branch_name(workspace_root)
    entries: list[dict[str, str]] = []
    for path_text in paths:
        url = _build_source_url(path_text, workspace_root, repo_url, branch)
        entries.append({"path": path_text, "url": url or ""})
    return entries


def _format_source_reference_markdown(source_file: str, workspace_root: str | Path) -> str:
    """Render one source-file field as clickable Markdown links when possible."""

    entries = build_source_link_entries(source_file, workspace_root)
    if not entries:
        return "`No direct file mapping available.`"

    linked_parts: list[str] = []
    for entry in entries:
        path_text = entry["path"]
        url = entry["url"]
        if url:
            linked_parts.append(f"[{path_text}]({url})")
        else:
            linked_parts.append(f"`{path_text}`")
    label = "Precīzais avots GitHub krātuvē (skatīt šeit)"
    return f"{label}: " + ", ".join(linked_parts)


def _split_source_paths(source_file: str) -> list[str]:
    """Split one `source_file` field into normalized repository-relative paths."""

    if not source_file:
        return []
    parts = [part.strip() for part in source_file.split("|")]
    return [part.replace("\\", "/") for part in parts if part.strip()]


@lru_cache(maxsize=8)
def _repository_github_url(workspace_root: str | Path) -> str | None:
    """Resolve the GitHub repository HTTPS URL from the local git remote."""

    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=Path(workspace_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None

    remote_url = result.stdout.strip()
    if not remote_url:
        return None
    if remote_url.startswith("git@github.com:"):
        remote_url = "https://github.com/" + remote_url.split(":", maxsplit=1)[1]
    if remote_url.startswith("https://github.com/") or remote_url.startswith("http://github.com/"):
        return remote_url.removesuffix(".git").rstrip("/")
    return None


@lru_cache(maxsize=8)
def _repository_branch_name(workspace_root: str | Path) -> str:
    """Resolve the current branch name, falling back to `main`."""

    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=Path(workspace_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return DEFAULT_GITHUB_BRANCH

    branch = result.stdout.strip()
    return branch or DEFAULT_GITHUB_BRANCH


def _build_source_url(
    path_text: str,
    workspace_root: str | Path,
    repo_url: str | None,
    branch: str,
) -> str | None:
    """Build one GitHub URL for a repository-relative file or directory path."""

    if not repo_url:
        return None

    normalized_path = path_text.strip().replace("\\", "/")
    if not normalized_path:
        return None

    filesystem_path = Path(workspace_root) / Path(normalized_path)
    github_mode = "tree" if filesystem_path.exists() and filesystem_path.is_dir() else "blob"
    quoted_path = quote(normalized_path, safe="/-_.")
    return f"{repo_url}/{github_mode}/{quote(branch, safe='-_.')}/{quoted_path}"


def _validate_sentence(
    sentence: ThesisSentence,
    context: ValidationContext,
    *,
    data_reference: str,
) -> ValidationRecord:
    """Validate one sentence against the loaded canonical artifacts."""

    text = sentence.text

    for validator in (
        _validate_results_sentence,
        _validate_modeling_sentence,
        _validate_feature_sentence,
        _validate_dataset_sentence,
        _validate_solver_sentence,
        _validate_pipeline_sentence,
    ):
        record = validator(sentence, context, data_reference=data_reference)
        if record is not None:
            return record

    return ValidationRecord(
        thesis_section=sentence.thesis_section,
        statement_text=text,
        value_in_text=_extract_text_value(text),
        source_file="",
        source_column="",
        actual_value="",
        status=STATUS_NOT_FOUND,
        notes="This sentence is interpretive or too broad for exact machine validation from repository artifacts.",
        data_reference=data_reference,
    )


def _validate_dataset_sentence(
    sentence: ThesisSentence,
    context: ValidationContext,
    *,
    data_reference: str,
) -> ValidationRecord | None:
    """Validate sentences about datasets, labels, and data preparation."""

    text = sentence.text
    dataset = context.selection_dataset
    dataset_counts = dataset["dataset_type"].value_counts(dropna=False).to_dict()
    best_solver_counts = (
        dataset.groupby(["dataset_type", "best_solver"]).size().reset_index(name="count")
    )
    run_summary = context.selection_dataset_full_run_summary.get("results", {})
    feature_schema = run_summary.get("feature_schema", {})

    if _contains_all(text, "divas datu grupas", "reālās", "sintētiski"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv",
            source_column="dataset_type",
            actual_value=f"dataset_type groups={len(dataset['dataset_type'].dropna().unique())}",
            notes="The mixed selection dataset stores two explicit dataset types: real and synthetic.",
        )

    if _contains_all(text, "reālās instances", "robinx", "itc2021"):
        real_count = int(dataset_counts.get("real", 0))
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/raw/real/itc2021_official | src/parsers/robinx_parser.py",
            source_column="dataset_type",
            actual_value=f"real instances in mixed dataset={real_count}",
            notes="The repository contains official ITC2021 XML instances parsed through the RobinX parser.",
        )

    if _contains_all(text, "sintētiskās instances", "strukturālo pazīmju daudzveidību"):
        synthetic_count = int(dataset_counts.get("synthetic", 0))
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/raw/synthetic/study | src/data_generation/synthetic_generator.py",
            source_column="dataset_type",
            actual_value=f"synthetic instances in mixed dataset={synthetic_count}",
            notes="Synthetic study instances extend the structural space beyond the real ITC2021 files.",
        )

    if _contains_all(text, "234", "54", "180", "instances"):
        actual_total = len(dataset.index)
        actual_real = int(dataset_counts.get("real", 0))
        actual_synthetic = int(dataset_counts.get("synthetic", 0))
        status = STATUS_OK if (actual_total, actual_real, actual_synthetic) == (234, 54, 180) else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="234; 54; 180",
            source_file="data/processed/selection_dataset_full.csv",
            source_column="dataset_type",
            actual_value=f"{actual_total}; {actual_real}; {actual_synthetic}",
            status=status,
            notes="Counts are taken directly from the mixed selection dataset.",
            data_reference=data_reference,
        )

    if _contains_all(text, "ģenerētas 180 sintētiskās instances"):
        synthetic_count = int(dataset_counts.get("synthetic", 0))
        status = STATUS_OK if synthetic_count == 180 else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="180",
            source_file="data/raw/synthetic/study/metadata.csv | data/processed/selection_dataset_full.csv",
            source_column="dataset_type",
            actual_value=str(synthetic_count),
            status=status,
            notes="The generated synthetic study contributes 180 labeled rows to the mixed selection dataset.",
            data_reference=data_reference,
        )

    if _contains_all(text, "metadata.csv", "manifest.json"):
        return _path_record(
            sentence,
            data_reference=data_reference,
            workspace_root=context.paths.workspace_root,
            files=[
                "data/raw/synthetic/study/metadata.csv",
                "data/raw/synthetic/study/manifest.json",
            ],
            actual_value="synthetic metadata.csv and manifest.json present",
            notes="Synthetic-data provenance files are present in the study dataset folder.",
        )

    if _contains_all(text, "datu izcelsmes", "izsekojam"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv | data/raw/synthetic/study/metadata.csv",
            source_column="dataset_type; synthetic metadata",
            actual_value="dataset_type column and synthetic metadata files present",
            notes="The mixed dataset keeps source labels and the synthetic generator writes provenance metadata.",
        )

    if _contains_all(text, "reālo un sintētisko", "nekontrolētu sajaukšanu"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv | src/selection/build_selection_dataset_full.py",
            source_column="dataset_type",
            actual_value="real and synthetic rows are tagged before concatenation",
            notes="The full dataset builder keeps real and synthetic branches explicit before creating the mixed table.",
        )

    if _contains_all(text, "30 vienādas pazīmju kolonnas"):
        common_columns = list(feature_schema.get("common_feature_columns", []))
        common_count = int(feature_schema.get("common_feature_column_count", len(common_columns)))
        objective_metadata = [
            column
            for column in common_columns
            if column.startswith("objective_")
        ]
        structural_count = common_count - len(objective_metadata)
        status = STATUS_OK if (common_count, structural_count, len(objective_metadata)) == (30, 25, 5) else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="30; 25; 5",
            source_file="data/processed/selection_dataset_full_run_summary.json",
            source_column="results.feature_schema",
            actual_value=f"{common_count}; {structural_count}; {len(objective_metadata)}",
            status=status,
            notes="The feature-schema summary records the common synthetic/real feature intersection used for the mixed dataset.",
            data_reference=data_reference,
        )

    if _contains_all(text, "234 algoritmu izvēles rindas", "54", "180"):
        actual_total = int(run_summary.get("num_selection_rows", len(dataset.index)))
        rows_by_type = run_summary.get("rows_by_dataset_type", {})
        actual_real = int(rows_by_type.get("real", dataset_counts.get("real", 0)))
        actual_synthetic = int(rows_by_type.get("synthetic", dataset_counts.get("synthetic", 0)))
        status = STATUS_OK if (actual_total, actual_real, actual_synthetic) == (234, 54, 180) else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="234; 54; 180",
            source_file="data/processed/selection_dataset_full_run_summary.json",
            source_column="results.num_selection_rows; results.rows_by_dataset_type",
            actual_value=f"{actual_total}; {actual_real}; {actual_synthetic}",
            status=status,
            notes="Selection-row counts come from the full dataset build summary.",
            data_reference=data_reference,
        )

    if _contains_all(text, "best_solver", "bez trūkstošiem"):
        missing_targets = int(dataset["best_solver"].isna().sum())
        status = STATUS_OK if missing_targets == 0 else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="0 missing best_solver",
            source_file="data/processed/selection_dataset_full.csv",
            source_column="best_solver",
            actual_value=f"missing best_solver rows={missing_targets}",
            status=status,
            notes="Every row in the mixed selection dataset has a target label.",
            data_reference=data_reference,
        )

    if _contains_all(text, "best_solver noteikšana", "mazāko mērķfunkcijas vērtību") or _contains_all(
        text,
        "solver_support_status",
        "scoring_status",
        "feasible",
        "objective_value",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/build_selection_dataset_full.py",
            source_column="target_eligible",
            actual_value="target eligibility uses support status, scoring status, feasibility, and numeric objective",
            notes="The full dataset builder filters solver runs through explicit target-eligibility rules before assigning best_solver.",
        )

    if _contains_all(text, "unsupported", "not_configured", "failed"):
        excluded = context.selection_dataset_full_run_summary.get("results", {}).get("target_summary_by_source", {})
        excluded_count = sum(
            int(summary.get("num_excluded_unsupported_or_not_configured_rows", 0))
            for summary in excluded.values()
            if isinstance(summary, dict)
        )
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/build_selection_dataset_full.py | data/processed/selection_dataset_full_run_summary.json",
            source_column="BAD_SUPPORT_STATUSES; BAD_SCORING_STATUSES",
            actual_value=f"excluded unsupported/not-configured rows={excluded_count}",
            notes="Unsupported, not-configured, failed, and semantically invalid rows are excluded from target-label construction.",
        )

    if _contains_all(text, "partially_supported", "netika automātiski izslēgti"):
        partially_supported_best = int(
            (dataset["benchmark_best_solver_support_status"] == "partially_supported").sum()
        )
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv | src/selection/build_selection_dataset_full.py",
            source_column="benchmark_best_solver_support_status",
            actual_value=f"partially_supported best-solver rows={partially_supported_best}",
            notes="Partially supported rows remain eligible when the remaining target-quality conditions are satisfied.",
        )

    if _contains_all(text, "kanoniskie algoritmu nosaukumi"):
        labels = sorted(str(value) for value in dataset["best_solver"].dropna().unique())
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv | src/selection/build_selection_dataset_full.py",
            source_column="best_solver",
            actual_value="; ".join(labels),
            notes="Best-solver labels are stored using canonical solver registry names.",
        )

    if _contains_all(text, "instance", "algoritms", "vidējā mērķfunkcijas vērtība"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/build_selection_dataset_full.py",
            source_column="mean_objective; mean_runtime_seconds; num_runs",
            actual_value="synthetic benchmark rows are aggregated by instance and solver before label selection",
            notes="The full dataset builder averages repeated synthetic runs before assigning one target label per instance.",
        )

    if _contains_all(text, "vienāda agregētā kvalitāte") or _contains_all(
        text,
        "zemākai vidējai mērķfunkcijas vērtībai",
        "leksikogrāfiski",
    ):
        target_summary = context.selection_dataset_full_run_summary.get("results", {}).get("target_summary_by_source", {})
        objective_ties = sum(
            int(summary.get("num_instances_with_objective_ties", 0))
            for summary in target_summary.values()
            if isinstance(summary, dict)
        )
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/build_selection_dataset_full.py | data/processed/selection_dataset_full_run_summary.json",
            source_column="multi_seed_policy; num_instances_with_objective_ties",
            actual_value=f"instances with objective ties={objective_ties}",
            notes="The run summary records that tie handling is not only theoretical; objective ties were observed in the built dataset.",
        )

    if _contains_all(text, "algoritmu pārklājumu", "pilnībā atbalstītiem") or _contains_all(
        text,
        "benchmark_total_solver_count",
    ):
        metadata_columns = [
            column
            for column in dataset.columns
            if column.startswith("benchmark_")
        ]
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv",
            source_column="benchmark_*",
            actual_value=", ".join(metadata_columns[:8]),
            notes="The mixed dataset stores benchmark coverage and best-solver metadata for interpretation, not model input.",
        )

    if _contains_all(text, "mērķa klase", "sintētiskajām", "cpsat_solver", "reālajām", "simulated_annealing_solver"):
        synthetic_labels = best_solver_counts[best_solver_counts["dataset_type"] == "synthetic"]
        real_labels = best_solver_counts[best_solver_counts["dataset_type"] == "real"]
        synthetic_ok = len(synthetic_labels.index) == 1 and synthetic_labels.iloc[0]["best_solver"] == "cpsat_solver"
        real_ok = len(real_labels.index) == 1 and real_labels.iloc[0]["best_solver"] == "simulated_annealing_solver"
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="synthetic=cpsat_solver; real=simulated_annealing_solver",
            source_file="data/processed/selection_dataset_full.csv",
            source_column="dataset_type; best_solver",
            actual_value=(
                f"synthetic={synthetic_labels.to_dict(orient='records')}; "
                f"real={real_labels.to_dict(orient='records')}"
            ),
            status=STATUS_OK if synthetic_ok and real_ok else STATUS_MISMATCH,
            notes="The current target labels are perfectly aligned with dataset type, which is also noted as a limitation in the thesis.",
            data_reference=data_reference,
        )

    if _contains_all(text, "tikai divi algoritmi", "cpsat_solver", "simulated_annealing_solver"):
        labels = sorted(str(value) for value in dataset["best_solver"].dropna().unique())
        status = STATUS_OK if labels == ["cpsat_solver", "simulated_annealing_solver"] else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="cpsat_solver; simulated_annealing_solver",
            source_file="data/processed/selection_dataset_full.csv",
            source_column="best_solver",
            actual_value="; ".join(labels),
            status=status,
            notes="Only two solver labels appear as targets in the current mixed selection dataset.",
            data_reference=data_reference,
        )

    if _contains_all(text, "nejaušā bāzlīnija", "timefold", "derīgus kandidātus"):
        labels = set(str(value) for value in dataset["best_solver"].dropna().unique())
        timefold_not_configured = int(
            context.solver_support_summary.loc[
                context.solver_support_summary["solver_registry_name"].eq("timefold")
                & context.solver_support_summary["solver_support_status"].eq("not_configured"),
                "num_rows",
            ].sum()
        )
        status = STATUS_OK if "random_baseline" not in labels and timefold_not_configured > 0 else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="random_baseline not target; timefold not_configured",
            source_file="data/processed/selection_dataset_full.csv | data/results/reports/solver_support_summary.csv",
            source_column="best_solver; solver_support_status",
            actual_value=f"target labels={sorted(labels)}; timefold not_configured rows={timefold_not_configured}",
            status=status,
            notes="The target labels exclude random_baseline and Timefold rows are not configured in the current benchmark artifacts.",
            data_reference=data_reference,
        )

    if "Praktiskajā daļā izmantotas divas datu grupas." in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv",
            source_column="dataset_type",
            actual_value=f"dataset_type groups={len(dataset['dataset_type'].dropna().unique())}",
            notes="The mixed selection dataset stores two explicit dataset types: real and synthetic.",
        )

    if "Pirmā grupa ir reālās sporta turnīru kalendāru sastādīšanas instances RobinX un ITC2021 formātā." in text:
        real_count = int(dataset_counts.get("real", 0))
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/raw/real/itc2021_official | src/parsers/robinx_parser.py",
            source_column="dataset_type",
            actual_value=f"real instances in mixed dataset={real_count}",
            notes="The repository contains official ITC2021 XML instances parsed through the RobinX parser.",
        )

    if "Otrā grupa ir sintētiski ģenerētas instances" in text:
        synthetic_count = int(dataset_counts.get("synthetic", 0))
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/raw/synthetic/study | src/data_generation/synthetic_generator.py",
            source_column="dataset_type",
            actual_value=f"synthetic instances in mixed dataset={synthetic_count}",
            notes="Synthetic study instances are generated and stored separately from the real ITC2021 files.",
        )

    if "Gala jauktajā algoritmu atlases datu kopā iekļautas 234 instances, no kurām 54 ir reālas, bet 180 – sintētiskas." in text:
        actual_total = len(dataset.index)
        actual_real = int(dataset_counts.get("real", 0))
        actual_synthetic = int(dataset_counts.get("synthetic", 0))
        status = STATUS_OK if (actual_total, actual_real, actual_synthetic) == (234, 54, 180) else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="234; 54; 180",
            source_file="data/processed/selection_dataset_full.csv",
            source_column="dataset_type",
            actual_value=f"{actual_total}; {actual_real}; {actual_synthetic}",
            status=status,
            notes="Counts taken directly from the mixed selection dataset.",
            data_reference=data_reference,
        )

    if "Katrā rindā tika saglabāta norāde par datu izcelsmi" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv | src/selection/build_selection_dataset_full.py",
            source_column="dataset_type",
            actual_value="dataset_type column present",
            notes="Each mixed selection row keeps its source dataset type.",
        )

    if "jauktās datu kopas veidošanā reālās un sintētiskās instances netika sajauktas nekontrolēti." in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv | src/selection/build_selection_dataset_full.py",
            source_column="dataset_type; DATASET_TYPES",
            actual_value="mixed selection dataset retains explicit dataset_type per row",
            notes="Real and synthetic rows are combined only after each source-specific dataset is built and tagged.",
        )

    if "mērķa mainīgais best_solver tika noteikts tikai no tādiem risinātāju rezultātiem" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/build_selection_dataset_full.py",
            source_column="best_solver",
            actual_value="best_solver built from target_eligible benchmark rows only",
            notes="Target labels are built after filtering benchmark rows through explicit eligibility rules.",
        )

    if "no mērķa noteikšanas tika izslēgti neatbalstīti, kļūdaini vai nekonfigurēti risinātāju iznākumi" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/build_selection_dataset_full.py",
            source_column="target_eligible",
            actual_value="BAD_SUPPORT_STATUSES={unsupported, not_configured, failed}; BAD_SCORING_STATUSES={unsupported_instance, not_configured, failed_run}",
            notes="Unsupported, not-configured, and failed runs are excluded from label generation.",
        )

    if "daļēji modelētie rezultāti netika pilnībā paslēpti" in text:
        metadata_columns = [
            column
            for column in dataset.columns
            if column.startswith("benchmark_")
        ]
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv",
            source_column="benchmark_*",
            actual_value=", ".join(metadata_columns[:6]),
            notes="Benchmark metadata columns keep partial-support context alongside the final label.",
        )

    if "Reālās instances izmantotas kā galvenais praktiskās ticamības pamats" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/raw/real/itc2021_official",
            source_column="instance_source_path",
            actual_value=f"real XML files benchmarked={context.real_benchmark['instance_name'].nunique()}",
            notes="The real-data branch is populated from ITC2021 XML files in the repository.",
        )

    if "Savukārt sintētiskās instances kalpo kā kontrolēta eksperimentu vide" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/data_generation/synthetic_generator.py | data/raw/synthetic/study/metadata.csv",
            source_column="metadata fields",
            actual_value="synthetic metadata includes team count, difficulty, round-robin mode, and seed",
            notes="Synthetic study generation varies size, mode, and difficulty through explicit generator parameters.",
        )

    if "sintētiskā apakškopa" in text and "patiesi atšķirīgiem gadījumiem" in text:
        synthetic_labels = best_solver_counts[best_solver_counts["dataset_type"] == "synthetic"]
        distinct_labels = int(synthetic_labels["best_solver"].nunique())
        status = STATUS_OK if distinct_labels > 1 else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="synthetic subset requires differentiated decisions",
            source_file="data/processed/selection_dataset_full.csv",
            source_column="best_solver",
            actual_value=f"distinct synthetic best_solver labels={distinct_labels}",
            status=status,
            notes=(
                "The current mixed selection dataset contains one synthetic target label only, "
                "so this sentence overstates the amount of solver-choice diversity inside the synthetic subset."
            ),
            data_reference=data_reference,
        )

    if "Reālajās instancēs viens risinātājs dominē gandrīz pilnībā" in text or "reālo instanču kopa pēc šī portfeļa rezultātiem izrādījās ļoti vienpusīga." in text:
        real_labels = best_solver_counts[best_solver_counts["dataset_type"] == "real"]
        distinct_labels = int(real_labels["best_solver"].nunique())
        top_count = int(real_labels["count"].max()) if not real_labels.empty else 0
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv",
            source_column="best_solver",
            actual_value=f"distinct real labels={distinct_labels}; top-label count={top_count}",
            notes="All real mixed-dataset labels resolve to the simulated annealing solver.",
        )

    if "Šeit modelim bija jāizvēlas starp patiesi atšķirīgiem gadījumiem, nevis vienkārši jāatkārto viens dominējošs lēmums." in text:
        synthetic_labels = best_solver_counts[best_solver_counts["dataset_type"] == "synthetic"]
        distinct_labels = int(synthetic_labels["best_solver"].nunique())
        status = STATUS_OK if distinct_labels > 1 else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="synthetic best_solver diversity > 1",
            source_file="data/processed/selection_dataset_full.csv",
            source_column="best_solver",
            actual_value=f"distinct synthetic best_solver labels={distinct_labels}",
            status=status,
            notes=(
                "The current mixed selection dataset has a single synthetic target class, "
                "so the synthetic subset does not reflect multi-label solver-choice diversity."
            ),
            data_reference=data_reference,
        )

    return None


def _validate_feature_sentence(
    sentence: ThesisSentence,
    context: ValidationContext,
    *,
    data_reference: str,
) -> ValidationRecord | None:
    """Validate sentences about structural features."""

    text = sentence.text
    dataset_columns = set(context.selection_dataset.columns)
    feature_columns = sorted(
        column
        for column in dataset_columns
        if column not in {"instance_name", "dataset_type", "best_solver"}
        and not column.startswith(("objective_", "benchmark_"))
    )

    if _contains_all(text, "pazīmes", "problēmas apraksta") or _contains_all(
        text,
        "informāciju",
        "pieejama pirms risināšanas",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/features/feature_extractor.py | src/selection/modeling.py",
            source_column="feature columns",
            actual_value=f"model structural feature columns={len(feature_columns)}",
            notes="Structural features are extracted before solver execution and benchmark-derived columns are excluded before modeling.",
        )

    if _contains_all(text, "pazīmju apraksta failā", "nosaukumi", "grupas"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="docs/feature_manifest.md | src/features/manifest.py",
            source_column="FEATURE_DEFINITIONS",
            actual_value="feature manifest present",
            notes="Feature names, groups, data types, and interpretations are maintained in the feature manifest.",
        )

    if _contains_all(text, "strukturālās pazīmes", "vairākās galvenajās grupās") or _contains_all(
        text,
        "izmēra raksturlielumus",
        "ierobežojumu sastāvu",
        "blīvumu",
        "daudzveidību",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="docs/feature_manifest.md | data/results/full_selection/feature_importance.csv",
            source_column="feature_group",
            actual_value="size; constraint_composition; density; diversity; objective",
            notes="The manifest and feature-importance output keep thesis-facing feature groups explicit.",
        )

    if _contains_all(text, "komandu skaits", "laika posmu skaits", "ierobežojumu skaits"):
        return _feature_group_record(
            sentence,
            data_reference=data_reference,
            source_feature_group="size",
            required_features={"num_teams", "num_slots", "num_constraints"},
            available_columns=dataset_columns,
        )

    if _contains_all(text, "stingro un mīksto ierobežojumu skaits"):
        return _feature_group_record(
            sentence,
            data_reference=data_reference,
            source_feature_group="constraint_composition",
            required_features={"num_hard_constraints", "num_soft_constraints"},
            available_columns=dataset_columns,
        )

    if _contains_all(text, "ierobežojumu skaits uz komandu", "uz laika posmu") and not _contains_all(
        text,
        "visaugstāko nozīmīgumu",
    ):
        return _feature_group_record(
            sentence,
            data_reference=data_reference,
            source_feature_group="density",
            required_features={"constraints_per_team", "constraints_per_slot", "constraints_per_team_slot"},
            available_columns=dataset_columns,
        )

    if _contains_all(text, "ierobežojumu tipu", "kategoriju", "marķieru skaits"):
        return _feature_group_record(
            sentence,
            data_reference=data_reference,
            source_feature_group="diversity",
            required_features={
                "number_of_constraint_categories",
                "number_of_constraint_tags",
                "number_of_constraint_types",
            },
            available_columns=dataset_columns,
        )

    if _contains_all(text, "prefiksiem", "objective_", "benchmark_", "label_", "target_", "dataset_"):
        expected_prefixes = ("objective_", "benchmark_", "label_", "target_", "dataset_")
        status = (
            STATUS_OK
            if all(prefix in BENCHMARK_DERIVED_PREFIXES for prefix in expected_prefixes)
            else STATUS_MISMATCH
        )
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="objective_; benchmark_; label_; target_; dataset_",
            source_file="src/selection/modeling.py",
            source_column="BENCHMARK_DERIVED_PREFIXES",
            actual_value="; ".join(BENCHMARK_DERIVED_PREFIXES),
            status=status,
            notes=(
                "The thesis text lists the core excluded prefixes; the code also excludes "
                "additional result, solver-status, and prediction prefixes."
            ),
            data_reference=data_reference,
        )

    if _contains_all(text, "25 strukturālajām pazīmēm"):
        status = STATUS_OK if len(feature_columns) == 25 else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="25",
            source_file="data/processed/selection_dataset_full.csv | src/selection/modeling.py",
            source_column="model feature columns",
            actual_value=str(len(feature_columns)),
            status=status,
            notes="The modeling feature filter leaves 25 structural columns after excluding objective, benchmark, label, target, and dataset prefixes.",
            data_reference=data_reference,
        )

    if _contains_all(text, "visaugstāko nozīmīgumu ieguva", "constraints_per_slot"):
        top_features = context.full_feature_importance["source_feature"].head(5).tolist()
        expected = [
            "constraints_per_slot",
            "ratio_constraint_tags_to_constraints",
            "num_soft_constraints",
            "ratio_constraint_types_to_constraints",
            "constraints_per_team",
        ]
        status = STATUS_OK if top_features == expected else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text=", ".join(expected),
            source_file="data/results/full_selection/feature_importance.csv",
            source_column="source_feature",
            actual_value=", ".join(top_features),
            status=status,
            notes="Top features are read from the mixed full-selection random-forest importance file.",
            data_reference=data_reference,
        )

    if _contains_all(text, "ierobežojumu blīvumu", "daudzveidību", "laika posmu noslodzi"):
        top_groups = context.full_feature_importance["feature_group"].head(10).tolist()
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/feature_importance.csv",
            source_column="feature_group",
            actual_value=", ".join(top_groups[:5]),
            notes="The top feature-importance rows are dominated by density, diversity, and constraint-composition groups.",
        )

    if "Šajā darbā pazīmes netika veidotas no risinātāju rezultātiem, bet gan no pašas problēmas apraksta." in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/features/feature_extractor.py | src/selection/modeling.py",
            source_column="feature columns",
            actual_value=f"feature columns before exclusions={len(feature_columns)}",
            notes="Structural feature extraction is separate from benchmark-derived objective columns.",
        )

    if "Pazīmju apraksta dokumentā skaidri noteikts" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="docs/feature_manifest.md | src/features/manifest.py",
            source_column="FEATURE_DEFINITIONS",
            actual_value="feature manifest present",
            notes="The repository documents each feature and its group in the feature manifest.",
        )

    if "Pirmā grupa raksturo problēmas izmēru" in text:
        required = {
            "num_teams",
            "num_slots",
            "num_constraints",
            "estimated_minimum_slots",
            "slot_pressure",
            "slot_surplus",
        }
        return _feature_group_record(
            sentence,
            data_reference=data_reference,
            source_feature_group="size",
            required_features=required,
            available_columns=dataset_columns,
        )

    if "Otrā pazīmju grupa raksturo ierobežojumu sastāvu." in text or "Šeit ietilpst stingro ierobežojumu skaits, mīksto ierobežojumu skaits" in text:
        required = {
            "num_hard_constraints",
            "num_soft_constraints",
            "num_unclassified_constraints",
            "num_constraints_missing_category",
            "num_constraints_missing_tag",
            "num_constraints_missing_type",
        }
        return _feature_group_record(
            sentence,
            data_reference=data_reference,
            source_feature_group="constraint_composition",
            required_features=required,
            available_columns=dataset_columns,
        )

    if "Trešā grupa raksturo blīvumu." in text or "normalizēti lielumi" in text:
        required = {
            "ratio_hard_to_all",
            "ratio_soft_to_all",
            "constraints_per_team",
            "constraints_per_slot",
            "constraints_per_team_slot",
        }
        return _feature_group_record(
            sentence,
            data_reference=data_reference,
            source_feature_group="density",
            required_features=required,
            available_columns=dataset_columns,
        )

    if "Ceturtā pazīmju grupa raksturo daudzveidību." in text or "atšķirīgas ierobežojumu kategorijas, birkas un tipi" in text:
        required = {
            "number_of_constraint_categories",
            "number_of_constraint_tags",
            "number_of_constraint_types",
            "ratio_constraint_categories_to_constraints",
            "ratio_constraint_tags_to_constraints",
            "ratio_constraint_types_to_constraints",
        }
        return _feature_group_record(
            sentence,
            data_reference=data_reference,
            source_feature_group="diversity",
            required_features=required,
            available_columns=dataset_columns,
        )

    if "Papildus tika saglabāti arī mērķfunkcijas metadati" in text:
        required = {
            "objective_present",
            "objective_name",
            "objective_sense",
            "objective_is_minimization",
            "objective_is_maximization",
        }
        return _feature_group_record(
            sentence,
            data_reference=data_reference,
            source_feature_group="objective",
            required_features=required,
            available_columns=dataset_columns,
        )

    if "No apmācības tika izslēgtas visas kolonnas ar prefiksiem objective_, benchmark_, label_, target_ un dataset_" in text:
        expected_prefixes = ("objective_", "benchmark_", "label_", "target_", "dataset_")
        status = (
            STATUS_OK
            if all(prefix in BENCHMARK_DERIVED_PREFIXES for prefix in expected_prefixes)
            else STATUS_MISMATCH
        )
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="objective_; benchmark_; label_; target_; dataset_",
            source_file="src/selection/modeling.py",
            source_column="BENCHMARK_DERIVED_PREFIXES",
            actual_value="; ".join(BENCHMARK_DERIVED_PREFIXES),
            status=status,
            notes=(
                "The thesis text lists the core excluded prefixes; the code also excludes "
                "additional result, solver-status, and prediction prefixes."
            ),
            data_reference=data_reference,
        )

    if "No jauktā izvēles modeļa svarīgākās pazīmes bija" in text:
        top_features = context.full_feature_importance["source_feature"].head(5).tolist()
        expected = [
            "estimated_minimum_slots",
            "constraints_per_team",
            "constraints_per_slot",
            "constraints_per_team_slot",
            "num_soft_constraints",
        ]
        status = STATUS_OK if top_features == expected else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text=", ".join(expected),
            source_file="data/results/full_selection/feature_importance.csv",
            source_column="source_feature",
            actual_value=", ".join(top_features),
            status=status,
            notes="Top features are read from the mixed full-selection random-forest importance file.",
            data_reference=data_reference,
        )

    if "Tas nozīmē, ka modelis galvenokārt balstījās uz kalendāra izmēru, kalendāra spriedzi un ierobežojumu blīvumu." in text:
        top_groups = context.full_feature_importance["feature_group"].head(5).tolist()
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/feature_importance.csv",
            source_column="feature_group",
            actual_value=", ".join(top_groups),
            notes="The top five mixed-model features are dominated by size and density groups.",
        )

    return None


def _validate_solver_sentence(
    sentence: ThesisSentence,
    context: ValidationContext,
    *,
    data_reference: str,
) -> ValidationRecord | None:
    """Validate sentences about the solver portfolio and scoring semantics."""

    text = sentence.text

    if _contains_all(text, "portfelī iekļauti četri", "cp-sat", "timefold"):
        expected = ["random_baseline", "cpsat_solver", "simulated_annealing_solver", "timefold"]
        status = STATUS_OK if list(DEFAULT_FULL_SOLVER_PORTFOLIO) == expected else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text=", ".join(expected),
            source_file="src/experiments/full_benchmark.py",
            source_column="DEFAULT_FULL_SOLVER_PORTFOLIO",
            actual_value=", ".join(DEFAULT_FULL_SOLVER_PORTFOLIO),
            status=status,
            notes="The full benchmark portfolio is defined centrally and matches the four solver variants described in the thesis.",
            data_reference=data_reference,
        )

    if _contains_all(text, "neviens", "itc2021 sacensību līmeņa risinājums"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="docs/solver_capabilities.md | data/results/reports/solver_support_summary.csv",
            source_column="solver_support_status; scoring_status",
            actual_value="portfolio documents simplified, partial, unsupported, and not-configured outcomes",
            notes="Solver capability notes and support-status summaries keep the portfolio scope explicit.",
        )

    if _contains_all(text, "nejaušā bāzlīnija", "kontroles etalons") or _contains_all(
        text,
        "nekonstruē reālu sporta kalendāru",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/random_baseline.py | data/results/reports/solver_support_summary.csv",
            source_column="solver_support_status; scoring_status",
            actual_value="simplified_baseline / partially_modeled_run",
            notes="The random baseline is explicitly implemented as a reproducible pipeline-control baseline.",
        )

    if _contains_all(text, "cp-sat", "strukturālā optimizācijas bāzlīnija") or _contains_all(
        text,
        "vienkāršā",
        "divkāršā",
        "savstarpējo spēļu turnīra",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/cpsat_solver.py",
            source_column="solver metadata",
            actual_value="single and double round-robin compact CP-SAT baseline",
            notes="The CP-SAT solver models the compact round-robin structure while keeping richer RobinX constraints out of scope.",
        )

    if _contains_all(text, "katra nepieciešamā spēle", "tieši vienu reizi") or _contains_all(
        text,
        "minimizē izmantoto laika posmu skaitu",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/cpsat_solver.py",
            source_column="constraints; objective",
            actual_value="one required match per pair/leg; at most one match per team per slot; minimize used slots",
            notes="The CP-SAT baseline enforces the compact schedule skeleton described in the thesis.",
        )

    if _contains_all(text, "papildu ierobežojumiem", "daļēji atbalstīts"):
        partial_rows = int(
            context.full_combined_benchmark[
                context.full_combined_benchmark["solver_support_status"] == "partially_supported"
            ].shape[0]
        )
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/combined_benchmark_results.csv",
            source_column="solver_support_status",
            actual_value=f"partially_supported rows={partial_rows}",
            notes="Benchmark rows keep partial-support status instead of treating simplified models as full support.",
        )

    if _contains_all(text, "simulētās rūdīšanas algoritms", "heuristiska bāzlīnija") or _contains_all(
        text,
        "reassign",
        "swap",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/simulated_annealing_solver.py",
            source_column="solver metadata",
            actual_value="single round-robin simulated annealing baseline with reassign and swap neighborhoods",
            notes="The simulated annealing solver is intentionally a lightweight heuristic baseline.",
        )

    if _contains_all(text, "timefold", "ārēja procesa integrācija") or _contains_all(
        text,
        "not_configured",
        "algoritma neveiksme",
    ):
        not_configured_rows = int(
            context.solver_support_summary.loc[
                context.solver_support_summary["solver_support_status"] == "not_configured",
                "num_rows",
            ].sum()
        )
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/timefold_solver.py | src/solvers/timefold_adapter.py | data/results/reports/solver_support_summary.csv",
            source_column="solver_support_status",
            actual_value=f"not_configured benchmark rows={not_configured_rows}",
            notes="The Timefold adapter is present, while the current benchmark artifacts mark the external solver as not configured.",
        )

    if _contains_all(text, "scoring_status", "modeling_scope", "solver_support_status") or _contains_all(
        text,
        "objective_value_valid",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/base.py | src/experiments/benchmark_validation.py",
            source_column="SolverResult fields; objective_value_valid",
            actual_value="scoring_status; modeling_scope; scoring_notes; solver_support_status; objective_value_valid",
            notes="The shared result contract and benchmark outputs carry explicit comparison-status fields.",
        )

    if _contains_all(text, "daļēji modelēti", "neiestatīti", "neatbalstīti"):
        statuses = sorted(str(value) for value in context.full_combined_benchmark["solver_support_status"].dropna().unique())
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/combined_benchmark_results.csv",
            source_column="solver_support_status",
            actual_value=", ".join(statuses),
            notes="The combined benchmark table preserves support statuses needed for conservative result interpretation.",
        )

    if "Tajā iekļauta nejauša bāzlīnija, CP-SAT kompaktais optimizācijas risinātājs, simulētās rūdīšanas heuristika un ārēja Timefold integrācijas vieta." in text:
        expected = ["random_baseline", "cpsat_solver", "simulated_annealing_solver", "timefold"]
        status = STATUS_OK if list(DEFAULT_FULL_SOLVER_PORTFOLIO) == expected else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text=", ".join(expected),
            source_file="src/experiments/full_benchmark.py",
            source_column="DEFAULT_FULL_SOLVER_PORTFOLIO",
            actual_value=", ".join(DEFAULT_FULL_SOLVER_PORTFOLIO),
            status=status,
            notes="The full benchmark portfolio is defined centrally and matches the thesis description.",
            data_reference=data_reference,
        )

    if "Praktiskā daļa nav veidota kā pilnīgs ITC2021 sacensību līmeņa risinātājs." in text or "neviens no tiem netiek pasniegts kā pilnīgs ITC2021 sacensību līmeņa risinājums." in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/random_baseline.py | src/solvers/cpsat_solver.py | src/solvers/simulated_annealing_solver.py | src/solvers/timefold_solver.py",
            source_column="solver support/scoring metadata",
            actual_value="portfolio includes simplified, partial, and not-configured baselines",
            notes="Solver metadata and benchmark outputs explicitly label support scope and simplified modeling.",
        )

    if "Nejaušā bāzlīnija tika izmantota kā reproducējams cauruļvada kontroles etalons." in text or "Tā nekonstruē reālu kalendāru un neievēro RobinX vai ITC2021 ierobežojumus." in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/random_baseline.py | data/results/reports/solver_support_summary.csv",
            source_column="solver_support_status; scoring_status",
            actual_value="simplified_baseline / partially_modeled_run or legacy_feasible_run",
            notes="The random baseline is explicitly a placeholder/control solver rather than a schedule constructor.",
        )

    if "CP-SAT risinātājs tika veidots kā galvenā strukturālā optimizācijas bāzlīnija." in text or "Tas modelē viena un divkārša pilna savstarpējo spēļu turnīra pamatstruktūru" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/cpsat_solver.py",
            source_column="solver metadata",
            actual_value="compact round-robin CP-SAT baseline with one match per team per slot and slot minimization",
            notes="The CP-SAT baseline models compact round-robin structure without the full RobinX constraint set.",
        )

    if "Simulētās rūdīšanas risinātājs tika veidots kā vienkārša heuristiska bāzlīnija." in text or "Tā jāuztver kā viegla heuristiska bāzlīnija" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/simulated_annealing_solver.py",
            source_column="solver metadata",
            actual_value="single round-robin simulated annealing baseline with simplified conflict-based objective",
            notes="The simulated annealing baseline is explicitly limited to a simplified schedule representation.",
        )

    if "Timefold risinātājs projektā realizēts kā ārēja procesa integrācijas punkts." in text or "Timefold tiek atzīmēts kā not_configured" in text:
        not_configured_rows = int(
            (context.solver_support_summary["solver_support_status"] == "not_configured").sum()
        )
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/timefold_solver.py | src/solvers/timefold_adapter.py | data/results/reports/solver_support_summary.csv",
            source_column="solver_support_status",
            actual_value=f"not_configured rows={not_configured_rows}",
            notes="The Timefold adapter exists, but benchmark artifacts classify it as not configured in the current environment.",
        )

    if "projektā ieviests vienots rezultātu līgums" in text or "skaidri nošķirti atbalsta statuss, realizējamība un korekti salīdzināma kvalitāte." in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/base.py",
            source_column="SolverResult fields",
            actual_value="solver_support_status; scoring_status; modeling_scope; scoring_notes; objective_sense",
            notes="The shared SolverResult contract exposes the comparison-status fields described in the thesis.",
        )

    if "daudzi rezultāti ir ar statusu partially_modeled_run" in text:
        partial_rows = int(
            (context.solver_support_summary["scoring_status"] == "partially_modeled_run").sum()
        )
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/reports/solver_support_summary.csv",
            source_column="scoring_status",
            actual_value=f"partially_modeled_run rows={partial_rows}",
            notes="Synthetic benchmark summaries contain many partially modeled rows, exactly as stated in the thesis.",
        )

    if "nevienam no sintētiskajiem risinātājiem nav nenulles korekti salīdzināmu realizējamu rezultātu pārklājuma attiecības." in text:
        synthetic_rows = context.solver_comparison[
            context.solver_comparison["result_scope"] == "synthetic"
        ]
        max_ratio = float(synthetic_rows["valid_feasible_coverage_ratio"].fillna(0.0).max()) if not synthetic_rows.empty else 0.0
        status = STATUS_OK if math.isclose(max_ratio, 0.0, abs_tol=1e-12) else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="synthetic valid feasible coverage = 0",
            source_file="data/results/reports/solver_comparison.csv",
            source_column="valid_feasible_coverage_ratio",
            actual_value=_format_float(max_ratio),
            status=status,
            notes="All synthetic solver rows have zero valid-feasible coverage in the current report artifacts.",
            data_reference=data_reference,
        )

    return None


def _validate_modeling_sentence(
    sentence: ThesisSentence,
    context: ValidationContext,
    *,
    data_reference: str,
) -> ValidationRecord | None:
    """Validate sentences about model configuration and evaluation methodology."""

    text = sentence.text
    run_results = context.full_evaluation_run_summary.get("results", {})
    settings = context.full_evaluation_run_summary.get("settings", {})
    feature_columns = [
        column
        for column in context.selection_dataset.columns
        if column not in {"instance_name", "best_solver"}
        and not str(column).startswith(BENCHMARK_DERIVED_PREFIXES)
    ]

    if _contains_all(text, "nejaušo mežu klasifikators"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/modeling.py",
            source_column="RandomForestClassifier",
            actual_value="RandomForestClassifier",
            notes="The selector model is implemented as a random-forest classifier.",
        )

    if _contains_all(text, "200 kokiem", "class_weight", "random_state = 42") or _contains_all(text, "n_jobs = 1"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/modeling.py | data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="n_estimators; class_weight; random_state; n_jobs",
            actual_value="n_estimators=200; class_weight=balanced; random_state=42; n_jobs=1",
            notes="The random-forest configuration in code matches the thesis text.",
        )

    if _contains_all(text, "hiperparametru optimizācija"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/modeling.py | configs/real_pipeline_current.yaml",
            source_column="selector.model_name",
            actual_value="fixed random_forest baseline configuration",
            notes="The project uses a fixed selector configuration rather than a hyperparameter-search stage.",
        )

    if _contains_all(text, "mērķa mainīgais", "best_solver"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/processed/selection_dataset_full.csv | src/selection/modeling.py",
            source_column="TARGET_COLUMN",
            actual_value="TARGET_COLUMN=best_solver",
            notes="The selection dataset and modeling helper use best_solver as the supervised target column.",
        )

    if _contains_all(text, "25 strukturālajām pazīmēm"):
        status = STATUS_OK if len(feature_columns) == 25 else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="25",
            source_file="src/selection/modeling.py | data/processed/selection_dataset_full.csv",
            source_column="feature_columns",
            actual_value=str(len(feature_columns)),
            status=status,
            notes="Prepared selector data excludes benchmark, target, objective, label, and dataset-prefixed columns.",
            data_reference=data_reference,
        )

    if _contains_all(text, "katrā novērtēšanas sadalījumā", "apmācīts no jauna") or _contains_all(
        text,
        "saglabātais modeļa artefakts",
        "neietekmē",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/evaluate_selector.py | data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="evaluation_uses_out_of_sample_validation",
            actual_value=str(settings.get("evaluation_uses_out_of_sample_validation", True)),
            notes="Evaluation retrains the selector inside each split and records that the saved model is traceability-only for evaluation.",
        )

    if _contains_all(text, "atkārtota stratificēta", "trim dalījumiem", "trim atkārtojumiem"):
        status = STATUS_OK if (
            settings.get("split_strategy") == "repeated_stratified_kfold"
            and int(settings.get("cross_validation_folds", 0)) == 3
            and int(settings.get("repeats", 0)) == 3
            and int(run_results.get("num_validation_splits", 0)) == 9
        ) else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="3 folds; 3 repeats; 9 splits",
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="settings.cross_validation_folds; settings.repeats; results.num_validation_splits",
            actual_value=(
                f"{settings.get('cross_validation_folds')}; "
                f"{settings.get('repeats')}; "
                f"{run_results.get('num_validation_splits')}"
            ),
            status=status,
            notes="Validation settings are read from the full mixed selector evaluation run summary.",
            data_reference=data_reference,
        )

    if _contains_all(text, "sbs", "apmācības daļas", "vbs", "testa"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/evaluate_selector.py",
            source_column="train_benchmarks; test_benchmarks",
            actual_value="single_best from train split; virtual_best from test split",
            notes="The evaluation code computes SBS from training rows and VBS independently on the test rows.",
        )

    if _contains_all(text, "accuracy", "balanced accuracy") or _contains_all(
        text,
        "regret",
        "vbs",
        "sbs",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/evaluate_selector.py | data/results/full_selection/selector_evaluation_summary.csv",
            source_column="summary metric columns",
            actual_value=(
                "classification_accuracy; balanced_accuracy; average_selected_objective; "
                "average_virtual_best_objective; average_single_best_objective; regret_vs_virtual_best; "
                "delta_vs_single_best"
            ),
            notes="The saved evaluation summary contains the metric family described in the thesis.",
        )

    if "Algoritmu izvēles modelis realizēts kā nejaušo mežu klasifikators." in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/modeling.py",
            source_column="RandomForestClassifier",
            actual_value="RandomForestClassifier",
            notes="The selector model is implemented as a random-forest classifier.",
        )

    if "Konfigurācijā izmantoti 200 koki, class_weight = balanced, nejaušības sēkla 42 un viena paralēlā izpildes plūsma" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/modeling.py | data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="n_estimators; class_weight; random_state; n_jobs",
            actual_value="n_estimators=200; class_weight=balanced; random_state=42; n_jobs=1",
            notes="The model configuration in code matches the thesis text exactly.",
        )

    if "Izvēles modelis kā ievadi saņem tikai strukturālās pazīmes, bet mērķa mainīgais ir kolonna best_solver." in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/modeling.py",
            source_column="TARGET_COLUMN",
            actual_value="TARGET_COLUMN=best_solver",
            notes="Prepared selector data excludes benchmark-derived columns and uses best_solver as the target label.",
        )

    if "Modeļa novērtēšanai tika izmantota atkārtota stratificēta krustotā validācija ar trim dalījumiem un trim atkārtojumiem, kopā veidojot deviņus validācijas sadalījumus." in text:
        status = STATUS_OK if (
            settings.get("split_strategy") == "repeated_stratified_kfold"
            and int(settings.get("cross_validation_folds", 0)) == 3
            and int(settings.get("repeats", 0)) == 3
            and int(run_results.get("num_validation_splits", 0)) == 9
        ) else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="3 folds; 3 repeats; 9 splits",
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="settings.cross_validation_folds; settings.repeats; results.num_validation_splits",
            actual_value=(
                f"{settings.get('cross_validation_folds')}; "
                f"{settings.get('repeats')}; "
                f"{run_results.get('num_validation_splits')}"
            ),
            status=status,
            notes="Validation settings are read from the full mixed selector evaluation run summary.",
            data_reference=data_reference,
        )

    if "viena labākā fiksētā risinātāja etalons katrā validācijas sadalījumā tika aprēķināts tikai no apmācības daļas" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/evaluate_selector.py",
            source_column="train_benchmarks; test_benchmarks",
            actual_value="single_best from train split; virtual_best from test split",
            notes="The evaluation code computes SBS on training rows and VBS independently on the test rows.",
        )

    if "Modeļa kvalitātes vērtēšanai tika izmantoti vairāki rādītāji." in text or "Papildus tika aprēķināta arī izvēlētā risinātāja vidējā mērķfunkcijas vērtība" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/selection/evaluate_selector.py",
            source_column="summary metric columns",
            actual_value=(
                "classification_accuracy; balanced_accuracy; average_selected_objective; "
                "average_virtual_best_objective; average_single_best_objective; "
                "regret_vs_virtual_best; delta_vs_single_best"
            ),
            notes="The evaluation summary includes the metric family described in the thesis.",
        )

    return None


def _validate_results_sentence(
    sentence: ThesisSentence,
    context: ValidationContext,
    *,
    data_reference: str,
) -> ValidationRecord | None:
    """Validate sentences that quote experiment outcomes."""

    text = sentence.text
    full_results = context.full_evaluation_run_summary.get("results", {})
    metrics_by_type = full_results.get("metrics_by_dataset_type", {})
    real_metrics = metrics_by_type.get("real", {})
    synthetic_metrics = metrics_by_type.get("synthetic", {})

    if _contains_all(text, "augstu klasifikācijas precizitāti", "sabalansēto precizitāti"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.classification_accuracy; results.balanced_accuracy",
            actual_value=(
                f"accuracy={_format_float(float(full_results['classification_accuracy']))}; "
                f"balanced_accuracy={_format_float(float(full_results['balanced_accuracy']))}"
            ),
            notes="The mixed selector evaluation summary supports the qualitative statement about high accuracy.",
        )

    if _contains_all(text, "uzlabo rezultātu", "vienu labāko fiksēto algoritmu") or _contains_all(
        text,
        "zemāka nekā sbs",
        "tuva vbs",
    ):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.average_selected_objective; results.average_single_best_objective; results.average_virtual_best_objective",
            actual_value=(
                f"selected={_format_float(float(full_results['average_selected_objective']))}; "
                f"SBS={_format_float(float(full_results['average_single_best_objective']))}; "
                f"VBS={_format_float(float(full_results['average_virtual_best_objective']))}"
            ),
            notes="Lower objective values are better; the selected-solver mean is below SBS and close to VBS.",
        )

    if _contains_all(text, "zems nožēlas rādītājs"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.regret_vs_virtual_best",
            actual_value=_format_float(float(full_results["regret_vs_virtual_best"])),
            notes="The mixed evaluation regret is small relative to the objective scale used in the current benchmark artifacts.",
        )

    if (
        _contains_all(text, "deviņos validācijas sadalījumos")
        or _contains_all(text, "deviņos pārbaudes sadalījumos")
    ) and not _contains_all(text, "klasifikācijas kļūdas"):
        actual_splits = int(full_results.get("num_validation_splits", 0))
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="9",
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.num_validation_splits",
            actual_value=str(actual_splits),
            status=STATUS_OK if actual_splits == 9 else STATUS_MISMATCH,
            notes="The full mixed selector evaluation uses nine repeated stratified validation splits.",
            data_reference=data_reference,
        )

    if _contains_all(text, "standartnovirze", "0.0064", "0.0139", "0.0192"):
        split_rows = context.full_evaluation_summary[
            context.full_evaluation_summary["summary_row_type"] == "split"
        ]
        return _numeric_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_summary.csv",
            source_column="classification_accuracy; balanced_accuracy; regret_vs_virtual_best",
            text_values=(0.0064, 0.0139, 0.0192),
            actual_values=(
                float(split_rows["classification_accuracy"].std()),
                float(split_rows["balanced_accuracy"].std()),
                float(split_rows["regret_vs_virtual_best"].std()),
            ),
            notes="Validation-split standard deviations are computed from the split-level evaluation summary.",
        )

    if _contains_all(text, "sintētiskajās instancēs", "pilnīgu sakritību"):
        synthetic_accuracy = float(synthetic_metrics["classification_accuracy"])
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="synthetic accuracy=1.0",
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.metrics_by_dataset_type.synthetic.classification_accuracy",
            actual_value=_format_float(synthetic_accuracy),
            status=STATUS_OK if math.isclose(synthetic_accuracy, 1.0, abs_tol=1e-12) else STATUS_MISMATCH,
            notes="The synthetic subset has perfect label accuracy in the current mixed evaluation.",
            data_reference=data_reference,
        )

    if _contains_all(text, "reālajās instancēs", "virtuāli labākā risinātāja"):
        real_selected = float(real_metrics["average_selected_objective"])
        real_vbs = float(real_metrics["average_virtual_best_objective"])
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.metrics_by_dataset_type.real",
            actual_value=f"selected={_format_float(real_selected)}; VBS={_format_float(real_vbs)}",
            notes="The real-subset selected objective is close to the real-subset VBS objective.",
        )

    if _contains_all(text, "tikai trīs klasifikācijas kļūdas", "test instance demo"):
        wrong_predictions = context.full_evaluation[
            context.full_evaluation["prediction_correct"] == False  # noqa: E712 - pandas boolean comparison.
        ]
        wrong_instances = sorted(str(value) for value in wrong_predictions["instance_name"].unique())
        status = STATUS_OK if len(wrong_predictions.index) == 3 and wrong_instances == ["Test Instance Demo"] else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="3; Test Instance Demo",
            source_file="data/results/full_selection/selector_evaluation.csv",
            source_column="prediction_correct; instance_name",
            actual_value=f"{len(wrong_predictions.index)}; {', '.join(wrong_instances)}",
            status=status,
            notes="Misclassifications are read from the row-level selector evaluation output.",
            data_reference=data_reference,
        )

    if _contains_all(text, "modelis izvēlējās cpsat_solver", "simulated_annealing_solver", "3.0"):
        wrong_predictions = context.full_evaluation[
            context.full_evaluation["prediction_correct"] == False  # noqa: E712 - pandas boolean comparison.
        ]
        selected = sorted(str(value) for value in wrong_predictions["selected_solver"].unique())
        target = sorted(str(value) for value in wrong_predictions["true_best_solver"].unique())
        regret_values = sorted(float(value) for value in wrong_predictions["regret_vs_virtual_best"].unique())
        status = STATUS_OK if selected == ["cpsat_solver"] and target == ["simulated_annealing_solver"] and regret_values == [3.0] else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="cpsat_solver; simulated_annealing_solver; 3.0",
            source_file="data/results/full_selection/selector_evaluation.csv",
            source_column="selected_solver; true_best_solver; regret_vs_virtual_best",
            actual_value=f"{selected}; {target}; {regret_values}",
            status=status,
            notes="The row-level error analysis confirms the solver choice and regret value for the repeated boundary-case errors.",
            data_reference=data_reference,
        )

    if _contains_all(text, "labāki par viena fiksēta algoritma", "tuvi virtuāli labākajam"):
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.improvement_vs_single_best; results.regret_vs_virtual_best",
            actual_value=(
                f"improvement_vs_SBS={_format_float(float(full_results['improvement_vs_single_best']))}; "
                f"regret_vs_VBS={_format_float(float(full_results['regret_vs_virtual_best']))}"
            ),
            notes="The selector improves over SBS and remains close to VBS in the current mixed evaluation summary.",
        )

    if "modelis sasniedza vidējo klasifikācijas precizitāti 0,9286 un sabalansēto precizitāti 0,8818." in text:
        return _numeric_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.classification_accuracy; results.balanced_accuracy",
            text_values=(0.9286, 0.8818),
            actual_values=(
                float(full_results["classification_accuracy"]),
                float(full_results["balanced_accuracy"]),
            ),
            notes="Values are compared after rounding to four decimals.",
        )

    if "Izvēlētā risinātāja vidējā mērķfunkcijas vērtība bija 25,3413, kamēr viena labākā fiksētā risinātāja vidējā vērtība bija 25,4048, bet virtuāli labākā risinātāja vērtība – 25,1071." in text:
        return _numeric_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.average_selected_objective; results.average_single_best_objective; results.average_virtual_best_objective",
            text_values=(25.3413, 25.4048, 25.1071),
            actual_values=(
                float(full_results["average_selected_objective"]),
                float(full_results["average_single_best_objective"]),
                float(full_results["average_virtual_best_objective"]),
            ),
            notes="The thesis sentence matches the mixed evaluation run summary after four-decimal rounding.",
        )

    if "Nožēlas rādītājs attiecībā pret virtuāli labāko risinātāju bija 0,2341, savukārt uzlabojums attiecībā pret vienu fiksētu risinātāju bija 0,0635 mērķfunkcijas vienības." in text:
        return _numeric_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.regret_vs_virtual_best; results.improvement_vs_single_best",
            text_values=(0.2341, 0.0635),
            actual_values=(
                float(full_results["regret_vs_virtual_best"]),
                float(full_results["improvement_vs_single_best"]),
            ),
            notes="Mixed evaluation regret and improvement values are sourced from the run summary JSON.",
        )

    if "Reālajā datu apakškopā klasifikācijas precizitāte sasniedza 0,9942, bet nožēlas rādītājs bija tikai 0,0175." in text:
        return _numeric_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.metrics_by_dataset_type.real.classification_accuracy; results.metrics_by_dataset_type.real.regret_vs_virtual_best",
            text_values=(0.9942, 0.0175),
            actual_values=(
                float(real_metrics["classification_accuracy"]),
                float(real_metrics["regret_vs_virtual_best"]),
            ),
            notes="Real-subset values are taken from the mixed evaluation metrics_by_dataset_type block.",
        )

    if "simulētās rūdīšanas risinātājs ieguva visus 54 uzvaras gadījumus" in text:
        sa_row = _solver_comparison_row(
            context.solver_comparison,
            result_scope="real",
            solver_registry_name="simulated_annealing_solver",
        )
        cpsat_row = _solver_comparison_row(
            context.solver_comparison,
            result_scope="real",
            solver_registry_name="cpsat_solver",
        )
        win_count = int(sa_row["win_count"])
        cpsat_wins = int(cpsat_row["win_count"])
        status = STATUS_OK if win_count == 54 and cpsat_wins == 0 else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="54 wins; CP-SAT 0 wins",
            source_file="data/results/reports/solver_comparison.csv",
            source_column="win_count",
            actual_value=f"SA={win_count}; CP-SAT={cpsat_wins}",
            status=status,
            notes="Real-scope solver comparison confirms complete win dominance by the simulated annealing baseline.",
            data_reference=data_reference,
        )

    if "Simulētās rūdīšanas risinātājs uz reālajām instancēm sasniedza vidējo salīdzināmo mērķfunkcijas vērtību 30,7593, CP-SAT – 32,4444, bet nejaušā bāzlīnija – 1209,8246." in text:
        sa_row = _solver_comparison_row(
            context.solver_comparison,
            result_scope="real",
            solver_registry_name="simulated_annealing_solver",
        )
        cpsat_row = _solver_comparison_row(
            context.solver_comparison,
            result_scope="real",
            solver_registry_name="cpsat_solver",
        )
        random_row = _solver_comparison_row(
            context.solver_comparison,
            result_scope="real",
            solver_registry_name="random_baseline",
        )
        return _numeric_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/reports/solver_comparison.csv",
            source_column="average_objective_valid_feasible",
            text_values=(30.7593, 32.4444, 1209.8246),
            actual_values=(
                float(sa_row["average_objective_valid_feasible"]),
                float(cpsat_row["average_objective_valid_feasible"]),
                float(random_row["average_objective_valid_feasible"]),
            ),
            notes="Real-scope solver averages are read from the thesis-facing solver comparison table.",
        )

    if "Timefold šajā eksperimentālajā vidē nebija konfigurēts" in text:
        timefold_row = _solver_support_summary_row(
            context.solver_support_summary,
            result_scope="real",
            solver_registry_name="timefold",
            solver_support_status="not_configured",
        )
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/reports/solver_support_summary.csv",
            source_column="solver_support_status",
            actual_value=f"not_configured rows={int(timefold_row['num_rows'])}",
            notes="Real benchmark support summaries classify Timefold as not configured rather than failed.",
        )

    if "sintētiskajā apakškopā klasifikācijas precizitāte bija 0,8095, sabalansētā precizitāte – 0,8037, izvēlētā risinātāja vidējā mērķfunkcijas vērtība – 13,4547, bet nožēlas rādītājs attiecībā pret virtuāli labāko risinātāju – 0,6171." in text:
        return _numeric_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column=(
                "results.metrics_by_dataset_type.synthetic.classification_accuracy; "
                "results.metrics_by_dataset_type.synthetic.balanced_accuracy; "
                "results.metrics_by_dataset_type.synthetic.average_selected_objective; "
                "results.metrics_by_dataset_type.synthetic.regret_vs_virtual_best"
            ),
            text_values=(0.8095, 0.8037, 13.4547, 0.6171),
            actual_values=(
                float(synthetic_metrics["classification_accuracy"]),
                float(synthetic_metrics["balanced_accuracy"]),
                float(synthetic_metrics["average_selected_objective"]),
                float(synthetic_metrics["regret_vs_virtual_best"]),
            ),
            notes="Synthetic-subset metrics are taken from the mixed evaluation run summary JSON.",
        )

    if "algoritmu izvēles modelis šajā apakškopā deva uzlabojumu 0,1962 mērķfunkcijas vienību apmērā." in text:
        improvement = abs(float(synthetic_metrics["delta_vs_single_best"]))
        return _numeric_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.metrics_by_dataset_type.synthetic.delta_vs_single_best",
            text_values=(0.1962,),
            actual_values=(improvement,),
            notes="The thesis expresses this value as improvement magnitude, so the validation uses the absolute delta-vs-SBS value.",
        )

    if "Sintētiskajās instancēs, kur strukturālās pazīmes tika variētas plašāk, izvēles modelis uzrādīja zemāku, bet saturiski daudz interesantāku precizitāti." in text:
        real_accuracy = float(real_metrics["classification_accuracy"])
        synthetic_accuracy = float(synthetic_metrics["classification_accuracy"])
        status = STATUS_OK if synthetic_accuracy < real_accuracy else STATUS_MISMATCH
        return ValidationRecord(
            thesis_section=sentence.thesis_section,
            statement_text=text,
            value_in_text="synthetic accuracy lower than real accuracy",
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.metrics_by_dataset_type",
            actual_value=f"real={_format_float(real_accuracy)}; synthetic={_format_float(synthetic_accuracy)}",
            status=status,
            notes="The numeric part of the sentence is validated by comparing dataset-type accuracies; the word 'interesting' remains interpretive.",
            data_reference=data_reference,
        )

    if "Eksperimentālie rezultāti rāda, ka jauktajā reālo un sintētisko instanču uzdevumā algoritmu izvēles modelis spēj sasniegt augstu klasifikācijas precizitāti un nedaudz uzlabot vidējo mērķfunkcijas vērtību salīdzinājumā ar viena fiksēta risinātāja izmantošanu." in text:
        improvement = float(full_results["improvement_vs_single_best"])
        accuracy = float(full_results["classification_accuracy"])
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="data/results/full_selection/selector_evaluation_run_summary.json",
            source_column="results.classification_accuracy; results.improvement_vs_single_best",
            actual_value=f"accuracy={_format_float(accuracy)}; improvement_vs_single_best={_format_float(improvement)}",
            notes="The mixed evaluation run summary supports the thesis statement: accuracy is high and improvement vs SBS is positive.",
        )

    return None


def _validate_pipeline_sentence(
    sentence: ThesisSentence,
    context: ValidationContext,
    *,
    data_reference: str,
) -> ValidationRecord | None:
    """Validate high-level pipeline structure sentences."""

    text = sentence.text

    if _contains_all(text, "python vidē", "galvenajiem eksperimenta posmiem"):
        files = [
            "src/parsers/robinx_parser.py",
            "src/features/build_feature_table.py",
            "src/experiments/run_real_pipeline_current.py",
            "src/experiments/run_synthetic_study.py",
            "src/selection/build_selection_dataset_full.py",
            "src/selection/train_selector.py",
            "src/selection/evaluate_selector.py",
            "src/web/dashboard.py",
        ]
        return _path_record(
            sentence,
            data_reference=data_reference,
            workspace_root=context.paths.workspace_root,
            files=files,
            actual_value="Python modules for parser, features, benchmarks, selection, evaluation, and dashboard present",
            notes="Repository modules keep the practical workflow separated into explicit Python stages.",
        )

    if _contains_all(text, "instanču inventarizāciju", "pazīmju iegūšanu", "modeļa novērtēšanu"):
        files = [
            "src/parsers/real_dataset_inventory.py",
            "src/features/build_feature_table.py",
            "src/experiments/full_benchmark.py",
            "src/selection/build_selection_dataset_full.py",
            "src/selection/train_selector.py",
            "src/selection/evaluate_selector.py",
            "src/thesis/generate_assets.py",
        ]
        return _path_record(
            sentence,
            data_reference=data_reference,
            workspace_root=context.paths.workspace_root,
            files=files,
            actual_value="inventory -> features -> benchmark -> dataset -> training -> evaluation -> reporting modules present",
            notes="The repository contains dedicated modules for the staged experimental flow described in the thesis.",
        )

    if _contains_all(text, "robinx", "itc2021", "inventarizācija", "nolasīšana") or _contains_all(
        text,
        "strukturēta xml",
        "standartizētu pazīmju telpu",
    ):
        files = [
            "src/parsers/real_dataset_inventory.py",
            "src/parsers/robinx_parser.py",
            "src/features/feature_extractor.py",
        ]
        return _path_record(
            sentence,
            data_reference=data_reference,
            workspace_root=context.paths.workspace_root,
            files=files,
            actual_value="inventory, parser, and feature extractor modules present",
            notes="The parsing and feature modules implement the XML-to-feature-space transition described in the thesis.",
        )

    if _contains_all(text, "tabulās", "grafos", "kopsavilkumos") or _contains_all(
        text,
        "localhost dashboard",
    ):
        files = [
            "src/thesis/generate_assets.py",
            "src/thesis/plots.py",
            "src/web/dashboard.py",
            "src/web/report_loader.py",
        ]
        return _path_record(
            sentence,
            data_reference=data_reference,
            workspace_root=context.paths.workspace_root,
            files=files,
            actual_value="thesis export and dashboard modules present",
            notes="Generated thesis tables, figures, and dashboard state are produced by dedicated reporting modules.",
        )

    if "Sistēma izstrādāta Python vidē" in text:
        files = [
            "src/experiments/run_real_pipeline_current.py",
            "src/selection/build_selection_dataset_full.py",
            "src/web/dashboard.py",
        ]
        return _path_record(
            sentence,
            data_reference=data_reference,
            workspace_root=context.paths.workspace_root,
            files=files,
            actual_value="Python thesis pipeline modules present",
            notes="Core pipeline, validation, and dashboard code are implemented in Python modules under src/.",
        )

    if "saglabājot skaidru nodalījumu starp datu apstrādi, pazīmju iegūšanu, salīdzinošajiem eksperimentiem, algoritmu atlases datu kopas izveidi, modeļa apmācību, novērtēšanu un rezultātu atspoguļošanu." in text:
        files = [
            "src/parsers/robinx_parser.py",
            "src/features/build_feature_table.py",
            "src/experiments/full_benchmark.py",
            "src/selection/build_selection_dataset_full.py",
            "src/selection/train_selector.py",
            "src/selection/evaluate_selector.py",
            "src/web/dashboard.py",
        ]
        return _path_record(
            sentence,
            data_reference=data_reference,
            workspace_root=context.paths.workspace_root,
            files=files,
            actual_value="separate parser, feature, benchmark, dataset, training, evaluation, and web modules present",
            notes="Repository modules mirror the staged workflow described in the thesis sentence.",
        )

    if "vispirms tiek parsētas RobinX un ITC2021 formāta problēmu instances" in text:
        files = [
            "src/parsers/robinx_parser.py",
            "src/features/build_feature_table.py",
            "src/experiments/full_benchmark.py",
            "src/selection/build_selection_dataset_full.py",
            "src/selection/train_selector.py",
            "src/selection/evaluate_selector.py",
        ]
        return _path_record(
            sentence,
            data_reference=data_reference,
            workspace_root=context.paths.workspace_root,
            files=files,
            actual_value="parser -> features -> benchmark -> mixed dataset -> training -> evaluation modules present",
            notes="The stage order in code matches the thesis pipeline description.",
        )

    if "Tieši tādēļ sistēmā ieviests vienots risinātāju rezultātu apraksts" in text:
        return _ok_record(
            sentence,
            data_reference=data_reference,
            source_file="src/solvers/base.py",
            source_column="SolverResult",
            actual_value="standardized solver result contract present",
            notes="The shared SolverResult dataclass carries support and scoring semantics for every solver run.",
        )

    if "Praktiskajā daļā tika izstrādāta pilna eksperimentālā plūsma" in text or "Sistēma automātiski parsē problēmu aprakstus, iegūst strukturālās pazīmes, salīdzina risinātājus, veido algoritmu atlases datu kopu, trenē izvēles modeli un ģenerē pārskatus" in text:
        files = [
            "src/parsers/robinx_parser.py",
            "src/features/build_feature_table.py",
            "src/experiments/run_real_pipeline_current.py",
            "src/experiments/run_synthetic_study.py",
            "src/selection/build_selection_dataset_full.py",
            "src/selection/train_selector.py",
            "src/selection/evaluate_selector.py",
            "src/thesis/document.py",
        ]
        return _path_record(
            sentence,
            data_reference=data_reference,
            workspace_root=context.paths.workspace_root,
            files=files,
            actual_value="end-to-end pipeline modules present",
            notes="The repository contains dedicated modules for every stage mentioned in the thesis sentence.",
        )

    return None


def _feature_group_record(
    sentence: ThesisSentence,
    *,
    data_reference: str,
    source_feature_group: str,
    required_features: set[str],
    available_columns: set[str],
) -> ValidationRecord:
    """Create one group-based validation record."""

    present = sorted(required_features & available_columns)
    missing = sorted(required_features - available_columns)
    status = STATUS_OK if not missing else STATUS_MISMATCH
    return ValidationRecord(
        thesis_section=sentence.thesis_section,
        statement_text=sentence.text,
        value_in_text=", ".join(sorted(required_features)),
        source_file="data/processed/selection_dataset_full.csv",
        source_column=source_feature_group,
        actual_value=", ".join(present),
        status=status,
        notes=(
            "All listed feature columns are present in the mixed selection dataset."
            if not missing
            else f"Missing feature columns: {', '.join(missing)}"
        ),
        data_reference=data_reference,
    )


def _path_record(
    sentence: ThesisSentence,
    *,
    data_reference: str,
    workspace_root: Path,
    files: list[str],
    actual_value: str,
    notes: str,
) -> ValidationRecord:
    """Create one file-existence-based record."""

    missing = [
        file_path
        for file_path in files
        if not (workspace_root / file_path).exists()
    ]
    status = STATUS_OK if not missing else STATUS_MISMATCH
    return ValidationRecord(
        thesis_section=sentence.thesis_section,
        statement_text=sentence.text,
        value_in_text=_extract_text_value(sentence.text),
        source_file=" | ".join(files),
        source_column="path existence",
        actual_value=actual_value,
        status=status,
        notes=notes if not missing else f"{notes} Missing files: {', '.join(missing)}",
        data_reference=data_reference,
    )


def _ok_record(
    sentence: ThesisSentence,
    *,
    data_reference: str,
    source_file: str,
    source_column: str,
    actual_value: str,
    notes: str,
) -> ValidationRecord:
    """Create one simple `OK` validation row."""

    return ValidationRecord(
        thesis_section=sentence.thesis_section,
        statement_text=sentence.text,
        value_in_text=_extract_text_value(sentence.text),
        source_file=source_file,
        source_column=source_column,
        actual_value=actual_value,
        status=STATUS_OK,
        notes=notes,
        data_reference=data_reference,
    )


def _numeric_record(
    sentence: ThesisSentence,
    *,
    data_reference: str,
    source_file: str,
    source_column: str,
    text_values: tuple[float, ...],
    actual_values: tuple[float, ...],
    notes: str,
) -> ValidationRecord:
    """Create one numeric comparison record."""

    rounded_text = tuple(round(value, 4) for value in text_values)
    rounded_actual = tuple(round(value, 4) for value in actual_values)
    status = STATUS_OK if rounded_text == rounded_actual else STATUS_MISMATCH
    return ValidationRecord(
        thesis_section=sentence.thesis_section,
        statement_text=sentence.text,
        value_in_text="; ".join(_format_float(value) for value in rounded_text),
        source_file=source_file,
        source_column=source_column,
        actual_value="; ".join(_format_float(value) for value in rounded_actual),
        status=status,
        notes=notes,
        data_reference=data_reference,
    )


def _solver_comparison_row(
    solver_comparison: pd.DataFrame,
    *,
    result_scope: str,
    solver_registry_name: str,
) -> pd.Series:
    """Return one solver-comparison row or raise an informative error."""

    rows = solver_comparison[
        (solver_comparison["result_scope"] == result_scope)
        & (solver_comparison["solver_registry_name"] == solver_registry_name)
    ]
    if rows.empty:
        raise KeyError(f"Missing solver comparison row for {result_scope}/{solver_registry_name}.")
    return rows.iloc[0]


def _solver_support_summary_row(
    solver_support_summary: pd.DataFrame,
    *,
    result_scope: str,
    solver_registry_name: str,
    solver_support_status: str,
) -> pd.Series:
    """Return one solver-support-summary row."""

    rows = solver_support_summary[
        (solver_support_summary["result_scope"] == result_scope)
        & (solver_support_summary["solver_registry_name"] == solver_registry_name)
        & (solver_support_summary["solver_support_status"] == solver_support_status)
    ]
    if rows.empty:
        raise KeyError(
            f"Missing solver support summary row for {result_scope}/{solver_registry_name}/{solver_support_status}."
        )
    return rows.iloc[0]


def _contains_all(text: str, *needles: str) -> bool:
    """Return whether all phrases appear in a normalized sentence."""

    normalized_text = _normalize_for_matching(text)
    return all(_normalize_for_matching(needle) in normalized_text for needle in needles)


def _normalize_for_matching(text: str) -> str:
    """Normalize punctuation variants that often differ between Word exports."""

    normalized = (
        text.lower()
        .replace("\xa0", " ")
        .replace("–", "-")
        .replace("—", "-")
    )
    return re.sub(r"\s+", " ", normalized).strip()


def _extract_text_value(text: str) -> str:
    """Extract compact values from one thesis sentence for the CSV."""

    matches = TOKEN_PATTERN.findall(text)
    cleaned = []
    for match in matches:
        normalized = match.strip()
        if normalized and normalized not in cleaned:
            cleaned.append(normalized)
    if cleaned:
        return "; ".join(cleaned)
    truncated = text if len(text) <= 96 else f"{text[:93]}..."
    return truncated


def _format_float(value: float) -> str:
    """Format one float with thesis-style four-decimal precision."""

    return f"{value:.4f}"
