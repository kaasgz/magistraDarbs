"""Generate thesis-facing validation files, tables, and figures."""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from src.solvers.registry import get_solver_metadata
from src.thesis.document import thesis_markdown
from src.thesis.plots import generate_figures
from src.thesis.presentation_catalog import FIGURE_SPECS
from src.thesis.validation import (
    ValidationContext,
    ValidationRecord,
    build_data_reference_mapping,
    build_source_link_entries,
    build_validation_markdown,
    build_validation_records,
)


UI_FIGURE_EXPORTS: tuple[str, ...] = (
    "dataset_distribution",
    "selector_vs_baselines",
    "best_solver_class_distribution",
    "feature_importance",
)


@dataclass(frozen=True, slots=True)
class ThesisAssetPaths:
    """Filesystem layout for thesis-facing generated assets."""

    workspace_root: Path
    validation_csv: Path
    validation_markdown: Path
    data_references_json: Path
    figures_dir: Path
    thesis_tables_dir: Path
    thesis_ready_dir: Path
    thesis_ready_figures_dir: Path
    latvian_figures_dir: Path
    patched_thesis_markdown: Path
    figures_index_markdown: Path
    legacy_figures_index_markdown: Path

    @classmethod
    def from_workspace(cls, workspace_root: str | Path) -> "ThesisAssetPaths":
        """Build output paths anchored at one workspace root."""

        root = Path(workspace_root)
        return cls(
            workspace_root=root,
            validation_csv=root / "data" / "results" / "thesis_text_validation.csv",
            validation_markdown=root / "data" / "results" / "thesis_text_validation.md",
            data_references_json=root / "data" / "results" / "thesis_data_references.json",
            figures_dir=root / "data" / "results" / "figures",
            thesis_tables_dir=root / "data" / "results" / "thesis_tables",
            thesis_ready_dir=root / "data" / "results" / "thesis_ready",
            thesis_ready_figures_dir=root / "data" / "results" / "thesis_ready" / "figures",
            latvian_figures_dir=root / "atteli_latviski",
            patched_thesis_markdown=root / "magistra_darbs_with_data_refs.md",
            figures_index_markdown=root / "data" / "results" / "thesis_figures_index.md",
            legacy_figures_index_markdown=root / "thesis_figures_index.md",
        )


@dataclass(frozen=True, slots=True)
class ThesisAssetsResult:
    """Summary of the generated thesis-facing assets."""

    validation_csv: Path
    validation_markdown: Path
    data_references_json: Path
    patched_thesis_markdown: Path
    figures_index_markdown: Path
    thesis_tables_dir: Path
    thesis_ready_dir: Path
    figures: dict[str, Path]
    mismatches: int
    not_found: int


def generate_thesis_assets(workspace_root: str | Path = ".") -> ThesisAssetsResult:
    """Generate validation outputs, clean tables, and ready-to-use thesis figures."""

    paths = ThesisAssetPaths.from_workspace(workspace_root)
    paths.validation_csv.parent.mkdir(parents=True, exist_ok=True)
    paths.figures_dir.mkdir(parents=True, exist_ok=True)
    paths.thesis_tables_dir.mkdir(parents=True, exist_ok=True)
    paths.thesis_ready_dir.mkdir(parents=True, exist_ok=True)
    paths.thesis_ready_figures_dir.mkdir(parents=True, exist_ok=True)
    paths.latvian_figures_dir.mkdir(parents=True, exist_ok=True)

    validation_records = build_validation_records(paths.workspace_root)
    validation_frame = pd.DataFrame(record.to_csv_row() for record in validation_records)
    validation_frame.to_csv(paths.validation_csv, index=False)

    validation_markdown_path = _safe_write_text(
        paths.validation_markdown,
        build_validation_markdown(validation_records),
        encoding="utf-8",
    )

    data_reference_mapping = build_data_reference_mapping(validation_records)
    data_references_json_path = _safe_write_text(
        paths.data_references_json,
        json.dumps(data_reference_mapping, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    sentence_references = {
        record.statement_text: [f"[{record.data_reference}]"]
        for record in validation_records
    }
    context = ValidationContext.load(paths.workspace_root)
    patched_markdown = thesis_markdown(
        context.paths.thesis_docx,
        sentence_references=sentence_references,
    )
    patched_markdown += _build_data_references_section(validation_records, paths.workspace_root)
    patched_thesis_markdown_path = _safe_write_text(
        paths.patched_thesis_markdown,
        patched_markdown,
        encoding="utf-8",
    )

    tables = _build_thesis_tables(context, validation_frame)
    _write_table_exports(paths.thesis_tables_dir, tables)
    _write_legacy_table_exports(paths.thesis_ready_dir, tables, validation_frame)

    figures = generate_figures(
        output_dir=paths.figures_dir,
        selector_results=tables["selector_results_table"],
        real_vs_synthetic=tables["real_vs_synthetic_table"],
        solver_comparison=tables["solver_comparison_table"],
        feature_importance=tables["feature_importance_table"],
        selection_dataset=context.selection_dataset,
        selector_evaluation_summary=context.full_evaluation_summary,
        selector_evaluation=context.full_evaluation,
        combined_benchmark=context.full_combined_benchmark,
    )
    for figure_path in figures.values():
        _safe_copy2(figure_path, paths.thesis_ready_figures_dir / figure_path.name)
    for figure_id in UI_FIGURE_EXPORTS:
        figure_path = figures.get(figure_id)
        if figure_path is not None:
            _safe_copy2(figure_path, paths.latvian_figures_dir / figure_path.name)

    figures_index_content = _build_figures_index_markdown(figures, paths.workspace_root)
    figures_index_markdown_path = _safe_write_text(
        paths.figures_index_markdown,
        figures_index_content,
        encoding="utf-8",
    )
    _safe_write_text(
        paths.legacy_figures_index_markdown,
        figures_index_content,
        encoding="utf-8",
    )

    _safe_copy2(paths.validation_csv, paths.thesis_ready_dir / paths.validation_csv.name)
    _safe_copy2(validation_markdown_path, paths.thesis_ready_dir / paths.validation_markdown.name)
    _safe_copy2(data_references_json_path, paths.thesis_ready_dir / paths.data_references_json.name)

    mismatch_count = int((validation_frame["status"] == "MISMATCH").sum())
    not_found_count = int((validation_frame["status"] == "NOT_FOUND").sum())
    return ThesisAssetsResult(
        validation_csv=paths.validation_csv,
        validation_markdown=validation_markdown_path,
        data_references_json=data_references_json_path,
        patched_thesis_markdown=patched_thesis_markdown_path,
        figures_index_markdown=figures_index_markdown_path,
        thesis_tables_dir=paths.thesis_tables_dir,
        thesis_ready_dir=paths.thesis_ready_dir,
        figures=figures,
        mismatches=mismatch_count,
        not_found=not_found_count,
    )


def _build_thesis_tables(
    context: ValidationContext,
    validation_frame: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    """Build clean thesis-facing summary tables from canonical artifacts."""

    selection_dataset = context.selection_dataset.copy()
    run_summary = context.full_evaluation_run_summary
    results = run_summary.get("results", {})
    metrics_by_type = results.get("metrics_by_dataset_type", {})
    solver_comparison = context.solver_comparison.copy()
    feature_importance = context.full_feature_importance.copy()
    model_name = str(run_summary.get("settings", {}).get("model_name", "random_forest"))

    selector_results_table = pd.DataFrame(
        [
            {
                "Modeļa tips": _model_label(model_name),
                "Labākais fiksētais algoritms": _solver_label(results.get("single_best_solver_name")),
                "Precizitāte": results.get("classification_accuracy"),
                "Sabalansētā precizitāte": results.get("balanced_accuracy"),
                "Vidējā izvēlētā kvalitāte": results.get("average_selected_objective"),
                "Vidējā virtual best kvalitāte": results.get("average_virtual_best_objective"),
                "Vidējā single best kvalitāte": results.get("average_single_best_objective"),
                "Regret pret virtual best": results.get("regret_vs_virtual_best"),
                "Uzlabojums pret single best": results.get("improvement_vs_single_best"),
                "Testa instanču skaits": results.get("num_test_instances"),
                "Validācijas sadalījumu skaits": results.get("num_validation_splits"),
            }
        ]
    )

    real_vs_synthetic_rows: list[dict[str, object]] = []
    for dataset_type in ("real", "synthetic"):
        metrics = metrics_by_type.get(dataset_type, {})
        if not metrics:
            continue
        real_vs_synthetic_rows.append(
            {
                "Datu kopa": _dataset_label(dataset_type),
                "Precizitāte": metrics.get("classification_accuracy"),
                "Sabalansētā precizitāte": metrics.get("balanced_accuracy"),
                "Vidējā izvēlētā kvalitāte": metrics.get("average_selected_objective"),
                "Vidējā virtual best kvalitāte": metrics.get("average_virtual_best_objective"),
                "Vidējā single best kvalitāte": metrics.get("average_single_best_objective"),
                "Regret pret virtual best": metrics.get("regret_vs_virtual_best"),
                "Uzlabojums pret single best": _improvement_from_delta(metrics.get("delta_vs_single_best")),
            }
        )
    real_vs_synthetic_table = pd.DataFrame(real_vs_synthetic_rows)

    solver_comparison_table = solver_comparison.loc[
        :,
        [
            "result_scope",
            "solver_registry_name",
            "win_count",
            "average_objective_valid_feasible",
            "average_runtime_seconds",
            "feasible_coverage_ratio",
            "valid_feasible_coverage_ratio",
        ],
    ].sort_values(
        by=["result_scope", "win_count", "average_objective_valid_feasible", "solver_registry_name"],
        ascending=[True, False, True, True],
        na_position="last",
        kind="mergesort",
    ).reset_index(drop=True)
    solver_comparison_table["Loma"] = solver_comparison_table["solver_registry_name"].map(_solver_role_label)
    solver_comparison_table["Interpretācija"] = solver_comparison_table["solver_registry_name"].map(
        _solver_interpretation,
    )
    solver_comparison_table = solver_comparison_table.rename(
        columns={
            "result_scope": "Datu kopa",
            "solver_registry_name": "Algoritms",
            "win_count": "Uzvaras",
            "average_objective_valid_feasible": "Vidējā kvalitāte",
            "average_runtime_seconds": "Vidējais laiks (s)",
            "feasible_coverage_ratio": "Feasible pārklājums",
            "valid_feasible_coverage_ratio": "Salīdzināmais pārklājums",
        }
    )
    solver_comparison_table["Datu kopa"] = solver_comparison_table["Datu kopa"].map(_dataset_label)
    solver_comparison_table["Algoritms"] = solver_comparison_table["Algoritms"].map(_solver_label)
    solver_comparison_table = solver_comparison_table.loc[
        :,
        [
            "Datu kopa",
            "Algoritms",
            "Loma",
            "Interpretācija",
            "Uzvaras",
            "Vidējā kvalitāte",
            "Vidējais laiks (s)",
            "Feasible pārklājums",
            "Salīdzināmais pārklājums",
        ],
    ]

    feature_importance_table = feature_importance.head(15).copy().reset_index(drop=True).rename(
        columns={
            "importance_rank": "Rangs",
            "source_feature": "Pazīme",
            "feature_group": "Grupa",
            "importance": "Nozīmīgums",
        }
    )
    feature_importance_table["Pazīme"] = feature_importance_table["Pazīme"].map(_feature_label)
    feature_importance_table["Grupa"] = feature_importance_table["Grupa"].map(_feature_group_label)
    feature_importance_table = feature_importance_table.loc[:, ["Rangs", "Pazīme", "Grupa", "Nozīmīgums"]]

    feature_group_summary_table = (
        feature_importance.groupby("feature_group", as_index=False)
        .agg(importance=("importance", "sum"))
        .sort_values(by=["importance", "feature_group"], ascending=[False, True], kind="mergesort")
        .rename(columns={"feature_group": "Grupa", "importance": "Kopējais nozīmīgums"})
        .reset_index(drop=True)
    )
    total_importance = float(feature_group_summary_table["Kopējais nozīmīgums"].sum()) or 1.0
    feature_group_summary_table["Īpatsvars"] = (
        feature_group_summary_table["Kopējais nozīmīgums"] / total_importance
    )
    feature_group_summary_table["Grupa"] = feature_group_summary_table["Grupa"].map(_feature_group_label)

    dataset_summary_table = pd.DataFrame(
        [
            {"Rādītājs": "Kopējais instanču skaits", "Vērtība": len(selection_dataset.index)},
            {"Rādītājs": "Reālo instanču skaits", "Vērtība": int((selection_dataset["dataset_type"] == "real").sum())},
            {"Rādītājs": "Sintētisko instanču skaits", "Vērtība": int((selection_dataset["dataset_type"] == "synthetic").sum())},
            {"Rādītājs": "Marķēto instanču skaits", "Vērtība": int(selection_dataset["best_solver"].notna().sum())},
            {
                "Rādītājs": "Atšķirīgo labāko algoritmu skaits",
                "Vērtība": int(selection_dataset["best_solver"].dropna().nunique()),
            },
            {"Rādītājs": "Izmantotais modeļa tips", "Vērtība": _model_label(model_name)},
            {
                "Rādītājs": "Labākais fiksētais algoritms",
                "Vērtība": _solver_label(results.get("single_best_solver_name")),
            },
        ]
    )

    solver_win_distribution_table = (
        selection_dataset.groupby(["dataset_type", "best_solver"])
        .size()
        .reset_index(name="Skaits")
        .rename(columns={"dataset_type": "Datu kopa", "best_solver": "Algoritms"})
    )
    solver_win_distribution_table["Datu kopa"] = solver_win_distribution_table["Datu kopa"].map(_dataset_label)
    solver_win_distribution_table["Algoritms"] = solver_win_distribution_table["Algoritms"].map(_solver_label)

    validation_mismatches = validation_frame[validation_frame["status"] == "MISMATCH"].reset_index(drop=True)
    validation_missing = validation_frame[validation_frame["status"] == "NOT_FOUND"].reset_index(drop=True)

    return {
        "selector_results_table": selector_results_table,
        "solver_comparison_table": solver_comparison_table,
        "feature_importance_table": feature_importance_table,
        "dataset_summary_table": dataset_summary_table,
        "real_vs_synthetic_table": real_vs_synthetic_table,
        "solver_win_distribution_table": solver_win_distribution_table,
        "feature_group_summary_table": feature_group_summary_table,
        "validation_mismatches": validation_mismatches,
        "validation_missing_mappings": validation_missing,
    }


def _write_table_exports(output_dir: Path, tables: dict[str, pd.DataFrame]) -> None:
    """Write thesis tables as CSV and Markdown documents."""

    output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        if name.startswith("validation_"):
            continue
        csv_path = output_dir / f"{name}.csv"
        md_path = output_dir / f"{name}.md"
        table.to_csv(csv_path, index=False)
        _safe_write_text(md_path, _markdown_table_document(name, table), encoding="utf-8")


def _write_legacy_table_exports(
    output_dir: Path,
    tables: dict[str, pd.DataFrame],
    validation_frame: pd.DataFrame,
) -> None:
    """Maintain the previous thesis_ready export layout for compatibility."""

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_table_exports(output_dir, tables)

    legacy_aliases: dict[str, pd.DataFrame] = {
        "selector_overview": tables["selector_results_table"],
        "real_vs_synthetic_comparison": tables["real_vs_synthetic_table"],
        "solver_leaderboard": tables["solver_comparison_table"],
        "solver_win_distribution": tables["solver_win_distribution_table"],
        "solver_runtime_summary": tables["solver_comparison_table"].loc[
            :,
            ["Datu kopa", "Algoritms", "Vidējais laiks (s)", "Feasible pārklājums", "Salīdzināmais pārklājums"],
        ],
        "feature_importance_top_features": tables["feature_importance_table"],
        "feature_group_importance": tables["feature_group_summary_table"],
        "dataset_overview": tables["dataset_summary_table"],
        "best_solver_distribution": tables["solver_win_distribution_table"],
        "validation_mismatches": validation_frame[validation_frame["status"] == "MISMATCH"].reset_index(drop=True),
        "validation_missing_mappings": validation_frame[validation_frame["status"] == "NOT_FOUND"].reset_index(drop=True),
    }
    for name, table in legacy_aliases.items():
        csv_path = output_dir / f"{name}.csv"
        md_path = output_dir / f"{name}.md"
        table.to_csv(csv_path, index=False)
        _safe_write_text(md_path, _markdown_table_document(name, table), encoding="utf-8")


def _markdown_table_document(name: str, table: pd.DataFrame) -> str:
    """Render one clean Markdown document for a thesis-facing table."""

    title = name.replace("_", " ").title()
    return f"# {title}\n\n{_dataframe_to_markdown(table)}\n"


def _dataframe_to_markdown(table: pd.DataFrame) -> str:
    """Render one DataFrame into a simple GitHub-flavored Markdown table."""

    if table.empty:
        return "_No rows available._"

    frame = table.fillna("")
    columns = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for _, row in frame.iterrows():
        values = [_markdown_cell(value) for value in row.tolist()]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def _markdown_cell(value: object) -> str:
    """Normalize one Markdown table cell."""

    if isinstance(value, float):
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value).replace("\n", " ").replace("|", "\\|")


def _model_label(model_name: str) -> str:
    """Return one thesis-friendly model label."""

    mapping = {
        "random_forest": "Random Forest klasifikators",
    }
    return mapping.get(str(model_name), str(model_name).replace("_", " ").title())


def _solver_label(value: object) -> str:
    """Return one readable solver label."""

    mapping = {
        "random_baseline": "Nejaušā bāzlīnija",
        "cpsat_solver": "CP-SAT",
        "simulated_annealing_solver": "Simulētā rūdīšana",
        "timefold": "Timefold",
        None: "",
    }
    return mapping.get(value, str(value).replace("_", " ").title())


def _solver_role_label(value: object) -> str:
    """Return one thesis-safe solver role label."""

    try:
        metadata = get_solver_metadata(str(value))
    except KeyError:
        return "Cits / nav reģistrā"

    mapping = {
        "diagnostic_baseline": "Diagnostiska bāzlīnija",
        "compact_optimization_baseline": "Kompakta optimizācijas bāzlīnija",
        "simplified_heuristic_baseline": "Vienkāršota heuristika",
        "external_integration": "Ārēja integrācija",
    }
    return mapping.get(metadata.role, metadata.role.replace("_", " ").title())


def _solver_interpretation(value: object) -> str:
    """Return one short limitation-aware interpretation note."""

    try:
        metadata = get_solver_metadata(str(value))
    except KeyError:
        return "Nav centrālajā solveru reģistrā; interpretēt piesardzīgi."

    mapping = {
        "diagnostic_baseline": "Nav pilns grafika risinātājs; izmanto cauruļvada pārbaudei.",
        "compact_optimization_baseline": "Daļējs CP-SAT modelis ar ierobežotu round-robin mērķi.",
        "simplified_heuristic_baseline": "Vienkāršota heuristika, nevis pilns ITC2021 risinātājs.",
        "external_integration": "Ārēja integrācija; rezultāts atkarīgs no konfigurētā Timefold modeļa.",
    }
    return mapping.get(metadata.role, metadata.objective_interpretation)


def _dataset_label(value: object) -> str:
    """Return one readable dataset label."""

    mapping = {
        "all": "Jauktā kopa",
        "real": "Reālie dati",
        "synthetic": "Sintētiskie dati",
        None: "",
    }
    return mapping.get(value, str(value).title())


def _feature_group_label(value: object) -> str:
    """Return one readable feature-group label."""

    mapping = {
        "size": "Izmērs",
        "density": "Blīvums",
        "constraint_composition": "Ierobežojumi",
        "diversity": "Daudzveidība",
        "objective": "Mērķfunkcija",
        None: "",
    }
    return mapping.get(value, str(value).replace("_", " ").title())


def _feature_label(value: object) -> str:
    """Return one readable feature label."""

    return str(value)


def _improvement_from_delta(delta_value: object) -> float | None:
    """Convert delta-vs-single-best into positive improvement when possible."""

    if delta_value is None or pd.isna(delta_value):
        return None
    return -float(delta_value)


def _safe_write_text(path: Path, content: str, *, encoding: str) -> Path:
    """Write text to one path, or use a deterministic fallback when the target is locked."""

    try:
        path.write_text(content, encoding=encoding)
        return path
    except PermissionError:
        fallback = path.with_name(f"{path.stem}_generated{path.suffix}")
        fallback.write_text(content, encoding=encoding)
        return fallback


def _safe_copy2(source: Path, destination: Path) -> Path:
    """Copy one file, or use a deterministic fallback destination when locked."""

    try:
        shutil.copy2(source, destination)
        return destination
    except PermissionError:
        fallback = destination.with_name(f"{destination.stem}_generated{destination.suffix}")
        shutil.copy2(source, fallback)
        return fallback


def _build_figures_index_markdown(figures: dict[str, Path], workspace_root: Path) -> str:
    """Build the Latvian thesis figure index."""

    lines = ["# Darbam sagatavoto attēlu indekss", ""]
    for spec in FIGURE_SPECS:
        path = figures[spec.identifier]
        lines.append(f"- `{path.name}`")
        lines.append(f"  Virsraksts: {spec.title}")
        lines.append(f"  Apraksts: {spec.description}")
        lines.append(f"  Nozīme: {spec.meaning}")
        lines.append(
            "  Avots: "
            + _format_github_source_line(f"data/results/figures/{path.name}", workspace_root)
        )
    lines.append("")
    return "\n".join(lines)


def _format_github_source_line(source_file: str, workspace_root: Path) -> str:
    """Render one source path into a human-readable GitHub link line."""

    entries = build_source_link_entries(source_file, workspace_root)
    if not entries:
        return f"`{source_file}`"

    parts: list[str] = []
    for entry in entries:
        path_text = entry["path"]
        url = entry["url"]
        parts.append(f"[{path_text}]({url})" if url else f"`{path_text}`")
    return "Precīzais artefakts GitHub krātuvē (skatīt šeit): " + ", ".join(parts)


def _build_data_references_section(records: list[ValidationRecord], workspace_root: Path) -> str:
    """Append one thesis-friendly `[DATA-x]` reference appendix."""

    lines = ["", "# Datu atsauces", ""]
    for record in records:
        lines.append(f"- [{record.data_reference}] {record.thesis_section}: {record.statement_text}")
        if record.source_file:
            lines.append(
                "  Precīzais avots GitHub krātuvē (skatīt šeit): "
                + _format_reference_links(record.source_file, workspace_root)
            )
        else:
            lines.append("  Tieša faila atsauce netika identificēta automātiski.")
        if record.actual_value:
            lines.append(f"  Faktiskā vērtība: `{record.actual_value}`")
        if record.notes:
            lines.append(f"  Piezīme: {record.notes}")
    lines.append("")
    return "\n".join(lines)


def _format_reference_links(source_file: str, workspace_root: Path) -> str:
    """Format one multi-file source field into Markdown links."""

    entries = build_source_link_entries(source_file, workspace_root)
    parts: list[str] = []
    for entry in entries:
        path_text = entry["path"]
        url = entry["url"]
        parts.append(f"[{path_text}]({url})" if url else f"`{path_text}`")
    return ", ".join(parts) if parts else "`Nav pieejamu failu saišu.`"


def build_argument_parser() -> argparse.ArgumentParser:
    """Create the CLI parser for thesis-asset generation."""

    parser = argparse.ArgumentParser(
        description="Generate thesis validation files, clean tables, and figures.",
    )
    parser.add_argument(
        "--workspace-root",
        default=".",
        help="Workspace root containing the thesis repository.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run thesis-asset generation from the command line."""

    parser = build_argument_parser()
    args = parser.parse_args(argv)
    result = generate_thesis_assets(args.workspace_root)

    print(f"Validation CSV: {result.validation_csv}")
    print(f"Validation report: {result.validation_markdown}")
    print(f"Data references: {result.data_references_json}")
    print(f"Patched thesis Markdown: {result.patched_thesis_markdown}")
    print(f"Figures index: {result.figures_index_markdown}")
    print(f"Thesis tables directory: {result.thesis_tables_dir}")
    print(f"Compatibility directory: {result.thesis_ready_dir}")
    print(f"Mismatches: {result.mismatches}")
    print(f"Manual review items: {result.not_found}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
