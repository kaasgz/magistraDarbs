"""Read-only loaders for thesis report dashboard sections."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from src.solvers.registry import get_solver_metadata
from src.thesis.presentation_catalog import FIGURE_SPECS, PRESENTATION_SECTIONS
from src.web.presentation_methodology import build_methodology_section
from src.web.presentation_workflow import build_workflow_section


MARKDOWN_PREVIEW_CHARS = 12_000
PRESENTATION_FIGURES_BY_SECTION: dict[str, tuple[str, ...]] = {
    "overview": ("dataset_distribution",),
    "results": (
        "selector_vs_baselines",
    ),
    "solver": (),
    "best_solver": ("best_solver_class_distribution",),
    "features": ("feature_importance",),
    "datasets": (),
}
SOLVER_LABELS: dict[str, str] = {
    "random_baseline": "Diagnostiskā atskaites pieeja",
    "cpsat_solver": "CP-SAT",
    "simulated_annealing_solver": "Simulētā rūdīšana",
    "timefold": "Timefold",
}
SOLVER_LABEL_TO_REGISTRY: dict[str, str] = {label: key for key, label in SOLVER_LABELS.items()}
SOLVER_LABEL_TO_REGISTRY["Nejaušā bāzlīnija"] = "random_baseline"
SOLVER_ROLE_LABELS: dict[str, str] = {
    "diagnostic_baseline": "Diagnostiskā atskaites pieeja",
    "compact_optimization_baseline": "Strukturāla optimizācijas atskaites pieeja",
    "simplified_heuristic_baseline": "Vienkāršota heiristiska atskaites pieeja",
    "external_integration": "Integrācijas saskarne",
}
SOLVER_ROLE_INTERPRETATION: dict[str, str] = {
    "diagnostic_baseline": "Nav praktisks sporta kalendāra risinātājs; izmanto datu plūsmas diagnostikai.",
    "compact_optimization_baseline": "CP-SAT modelis optimizē pamatstruktūru, nevis pilnu RobinX/ITC2021 ierobežojumu semantiku.",
    "simplified_heuristic_baseline": "Vienkāršota heiristiska atskaites pieeja ar ierobežotu modelēšanas tvērumu.",
    "external_integration": "Timefold integrācijas saskarne; ārējais izpildāmais fails šajā konfigurācijā nav iestatīts.",
}
IMPLEMENTATION_STEP_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "Praktiskās daļas mērķis un vispārējā uzbūve",
        "Definēta reproducējama eksperimentālā plūsma algoritmu izvēles pārbaudei.",
        "src/experiments/run_real_pipeline_current.py; src/experiments/run_synthetic_study.py",
    ),
    (
        "Datu avoti un datu sagatavošana",
        "Sagatavotas reālās RobinX/ITC2021 instances un kontrolēta sintētisko instanču kopa.",
        "data/raw/real/itc2021_official; data/raw/synthetic/study",
    ),
    (
        "Problēmu instanču nolasīšana, apstrāde un strukturālo pazīmju iegūšana",
        "Ieviesta XML nolasīšana un pirms-risināšanas strukturālo pazīmju iegūšana.",
        "src/parsers/robinx_parser.py; src/features/feature_extractor.py",
    ),
    (
        "Risinātāju portfelis un rezultātu interpretācija",
        "Ieviests risinātāju portfelis un vienota rezultātu/statusu interpretācija.",
        "src/solvers; src/experiments/benchmark_validation.py",
    ),
    (
        "Jauktās algoritmu izvēles datu kopas izveide",
        "Izveidota jaukta algoritmu izvēles datu kopa ar best_solver mērķi.",
        "src/selection/build_selection_dataset_full.py; data/processed/selection_dataset_full.csv",
    ),
    (
        "Algoritmu izvēles modeļa izveide un novērtēšana",
        "Apmācīts un novērtēts nejaušo mežu klasifikators algoritmu izvēles uzdevumam.",
        "src/selection/train_selector.py; src/selection/evaluate_selector.py",
    ),
    (
        "Eksperimentu rezultāti",
        "Sagatavoti rezultātu kopsavilkumi, pazīmju nozīmīgums un datu grupu salīdzinājums.",
        "data/results/thesis_tables; data/results/figures",
    ),
    (
        "Rezultātu interpretācija un ierobežojumi",
        "Atsevišķi parādīts eksperimenta tvērums, ierobežojumi un reproducējamie gala artefakti.",
        "docs/reproducibility_audit.md; docs/reproduction_guide.md",
    ),
)


@dataclass(frozen=True, slots=True)
class ReportLoaderPaths:
    """Generated artifact paths read by the dashboard report views."""

    workspace_root: Path
    reports_dir: Path
    solver_comparison_csv: Path
    solver_comparison_markdown: Path
    solver_support_summary_csv: Path
    solver_support_summary_markdown: Path
    solver_win_counts_csv: Path
    solver_win_counts_markdown: Path
    average_objective_csv: Path
    average_objective_markdown: Path
    average_runtime_csv: Path
    average_runtime_markdown: Path
    selector_vs_baselines_csv: Path
    selector_vs_baselines_markdown: Path
    feature_importance_summary_csv: Path
    feature_importance_summary_markdown: Path
    thesis_benchmark_report_markdown: Path
    thesis_benchmark_report_run_summary_json: Path
    mixed_selection_dataset_csv: Path
    mixed_selection_run_summary_json: Path
    full_selection_combined_benchmark_csv: Path
    full_selection_feature_importance_csv: Path
    full_selection_evaluation_csv: Path
    full_selection_evaluation_summary_csv: Path
    full_selection_evaluation_summary_markdown: Path
    full_selection_evaluation_run_summary_json: Path
    synthetic_study_processed_dir: Path
    synthetic_study_results_dir: Path
    synthetic_study_features_csv: Path
    synthetic_study_benchmark_csv: Path
    synthetic_study_selection_dataset_csv: Path
    synthetic_study_selector_summary_csv: Path
    synthetic_study_summary_markdown: Path
    real_current_processed_dir: Path
    real_current_results_dir: Path
    real_current_features_csv: Path
    real_current_benchmark_csv: Path
    real_current_selection_dataset_csv: Path
    real_current_selector_summary_csv: Path
    real_current_compatibility_matrix_csv: Path
    real_current_summary_markdown: Path
    thesis_validation_csv: Path
    thesis_validation_markdown: Path
    thesis_data_references_json: Path
    thesis_tables_dir: Path
    thesis_ready_dir: Path
    thesis_ready_figures_dir: Path
    thesis_selector_results_table_csv: Path
    thesis_solver_comparison_table_csv: Path
    thesis_feature_importance_table_csv: Path
    thesis_dataset_summary_table_csv: Path
    thesis_real_vs_synthetic_table_csv: Path
    thesis_solver_win_distribution_table_csv: Path
    thesis_feature_group_summary_table_csv: Path
    thesis_selector_overview_csv: Path
    thesis_real_vs_synthetic_csv: Path
    thesis_solver_leaderboard_csv: Path
    thesis_solver_win_distribution_csv: Path
    thesis_solver_runtime_csv: Path
    thesis_feature_importance_top_csv: Path
    thesis_feature_group_importance_csv: Path
    thesis_dataset_overview_csv: Path
    thesis_best_solver_distribution_csv: Path
    thesis_validation_mismatches_csv: Path
    thesis_validation_missing_csv: Path
    thesis_figures_index_markdown: Path

    @classmethod
    def from_workspace(cls, workspace_root: str | Path) -> "ReportLoaderPaths":
        """Create the report-loader path layout anchored at the workspace root."""

        root = Path(workspace_root)
        reports_dir = root / "data" / "results" / "reports"
        mixed_results_dir = root / "data" / "results" / "full_selection"
        synthetic_processed_dir = root / "data" / "processed" / "synthetic_study"
        synthetic_results_dir = root / "data" / "results" / "synthetic_study"
        real_processed_dir = root / "data" / "processed" / "real_pipeline_current"
        real_results_dir = root / "data" / "results" / "real_pipeline_current"
        thesis_tables_dir = root / "data" / "results" / "thesis_tables"
        thesis_ready_dir = root / "data" / "results" / "thesis_ready"
        return cls(
            workspace_root=root,
            reports_dir=reports_dir,
            solver_comparison_csv=reports_dir / "solver_comparison.csv",
            solver_comparison_markdown=reports_dir / "solver_comparison.md",
            solver_support_summary_csv=reports_dir / "solver_support_summary.csv",
            solver_support_summary_markdown=reports_dir / "solver_support_summary.md",
            solver_win_counts_csv=reports_dir / "solver_win_counts.csv",
            solver_win_counts_markdown=reports_dir / "solver_win_counts.md",
            average_objective_csv=reports_dir / "average_objective_per_solver.csv",
            average_objective_markdown=reports_dir / "average_objective_per_solver.md",
            average_runtime_csv=reports_dir / "average_runtime_per_solver.csv",
            average_runtime_markdown=reports_dir / "average_runtime_per_solver.md",
            selector_vs_baselines_csv=reports_dir / "selector_vs_baselines.csv",
            selector_vs_baselines_markdown=reports_dir / "selector_vs_baselines.md",
            feature_importance_summary_csv=reports_dir / "feature_importance_summary.csv",
            feature_importance_summary_markdown=reports_dir / "feature_importance_summary.md",
            thesis_benchmark_report_markdown=reports_dir / "thesis_benchmark_report.md",
            thesis_benchmark_report_run_summary_json=reports_dir / "thesis_benchmark_report_run_summary.json",
            mixed_selection_dataset_csv=root / "data" / "processed" / "selection_dataset_full.csv",
            mixed_selection_run_summary_json=root / "data" / "processed" / "selection_dataset_full_run_summary.json",
            full_selection_combined_benchmark_csv=mixed_results_dir / "combined_benchmark_results.csv",
            full_selection_feature_importance_csv=mixed_results_dir / "feature_importance.csv",
            full_selection_evaluation_csv=mixed_results_dir / "selector_evaluation.csv",
            full_selection_evaluation_summary_csv=mixed_results_dir / "selector_evaluation_summary.csv",
            full_selection_evaluation_summary_markdown=mixed_results_dir / "selector_evaluation_summary.md",
            full_selection_evaluation_run_summary_json=mixed_results_dir / "selector_evaluation_run_summary.json",
            synthetic_study_processed_dir=synthetic_processed_dir,
            synthetic_study_results_dir=synthetic_results_dir,
            synthetic_study_features_csv=synthetic_processed_dir / "features.csv",
            synthetic_study_benchmark_csv=synthetic_results_dir / "benchmark_results.csv",
            synthetic_study_selection_dataset_csv=synthetic_processed_dir / "selection_dataset.csv",
            synthetic_study_selector_summary_csv=synthetic_results_dir / "selector_evaluation_summary.csv",
            synthetic_study_summary_markdown=synthetic_results_dir / "synthetic_study_summary.md",
            real_current_processed_dir=real_processed_dir,
            real_current_results_dir=real_results_dir,
            real_current_features_csv=real_processed_dir / "features.csv",
            real_current_benchmark_csv=real_results_dir / "benchmark_results.csv",
            real_current_selection_dataset_csv=real_processed_dir / "selection_dataset.csv",
            real_current_selector_summary_csv=real_results_dir / "selector_evaluation_summary.csv",
            real_current_compatibility_matrix_csv=real_processed_dir / "solver_compatibility_matrix.csv",
            real_current_summary_markdown=real_results_dir / "real_pipeline_current_summary.md",
            thesis_validation_csv=root / "data" / "results" / "thesis_text_validation.csv",
            thesis_validation_markdown=root / "data" / "results" / "thesis_text_validation.md",
            thesis_data_references_json=root / "data" / "results" / "thesis_data_references.json",
            thesis_tables_dir=thesis_tables_dir,
            thesis_ready_dir=thesis_ready_dir,
            thesis_ready_figures_dir=thesis_ready_dir / "figures",
            thesis_selector_results_table_csv=thesis_tables_dir / "selector_results_table.csv",
            thesis_solver_comparison_table_csv=thesis_tables_dir / "solver_comparison_table.csv",
            thesis_feature_importance_table_csv=thesis_tables_dir / "feature_importance_table.csv",
            thesis_dataset_summary_table_csv=thesis_tables_dir / "dataset_summary_table.csv",
            thesis_real_vs_synthetic_table_csv=thesis_tables_dir / "real_vs_synthetic_table.csv",
            thesis_solver_win_distribution_table_csv=thesis_tables_dir / "solver_win_distribution_table.csv",
            thesis_feature_group_summary_table_csv=thesis_tables_dir / "feature_group_summary_table.csv",
            thesis_selector_overview_csv=thesis_ready_dir / "selector_overview.csv",
            thesis_real_vs_synthetic_csv=thesis_ready_dir / "real_vs_synthetic_comparison.csv",
            thesis_solver_leaderboard_csv=thesis_ready_dir / "solver_leaderboard.csv",
            thesis_solver_win_distribution_csv=thesis_ready_dir / "solver_win_distribution.csv",
            thesis_solver_runtime_csv=thesis_ready_dir / "solver_runtime_summary.csv",
            thesis_feature_importance_top_csv=thesis_ready_dir / "feature_importance_top_features.csv",
            thesis_feature_group_importance_csv=thesis_ready_dir / "feature_group_importance.csv",
            thesis_dataset_overview_csv=thesis_ready_dir / "dataset_overview.csv",
            thesis_best_solver_distribution_csv=thesis_ready_dir / "best_solver_distribution.csv",
            thesis_validation_mismatches_csv=thesis_ready_dir / "validation_mismatches.csv",
            thesis_validation_missing_csv=thesis_ready_dir / "validation_missing_mappings.csv",
            thesis_figures_index_markdown=root / "data" / "results" / "thesis_figures_index.md",
        )


def build_thesis_reports_state(workspace_root: str | Path) -> dict[str, Any]:
    """Build the read-only thesis report dashboard state."""

    paths = ReportLoaderPaths.from_workspace(workspace_root)
    solver_comparison = _safe_read_csv(paths.solver_comparison_csv)
    solver_support_summary = _safe_read_csv(paths.solver_support_summary_csv)
    selector_vs_baselines = _safe_read_csv(paths.selector_vs_baselines_csv)
    feature_importance_summary = _safe_read_csv(paths.feature_importance_summary_csv)
    win_counts = _safe_read_csv(paths.solver_win_counts_csv)
    average_objective = _safe_read_csv(paths.average_objective_csv)
    average_runtime = _safe_read_csv(paths.average_runtime_csv)
    run_summary = _load_json_file(paths.thesis_benchmark_report_run_summary_json)
    markdown_reports = _load_markdown_reports(
        paths.workspace_root,
        [
            paths.thesis_benchmark_report_markdown,
            paths.solver_comparison_markdown,
            paths.solver_support_summary_markdown,
            paths.solver_win_counts_markdown,
            paths.average_objective_markdown,
            paths.average_runtime_markdown,
            paths.selector_vs_baselines_markdown,
            paths.feature_importance_summary_markdown,
        ],
    )

    available = any(
        frame is not None
        for frame in (
            solver_comparison,
            solver_support_summary,
            selector_vs_baselines,
            feature_importance_summary,
            win_counts,
            average_objective,
            average_runtime,
        )
    ) or bool(markdown_reports)

    report_scope = _resolve_report_scope(run_summary, solver_comparison, selector_vs_baselines)
    overview = _build_report_overview(
        paths=paths,
        run_summary=run_summary,
        report_scope=report_scope,
        solver_comparison=solver_comparison,
        solver_support_summary=solver_support_summary,
        selector_vs_baselines=selector_vs_baselines,
        feature_importance_summary=feature_importance_summary,
        win_counts=win_counts,
        average_objective=average_objective,
        markdown_reports=markdown_reports,
    )

    return {
        "available": available,
        "empty_state": (
            "No thesis-facing benchmark reports found yet. Run "
            "`python -m src.experiments.thesis_report` and refresh this page."
        ),
        "scope": {
            "title": "Thesis Reports",
            "description": (
                "Read-only thesis report artifacts from data/results/reports. "
                "Performance, coverage, and solver support are shown separately so unsupported "
                "and not-configured runs are not interpreted as valid objective results."
            ),
            "source_folder": "data/results/reports",
            "result_scope": report_scope,
        },
        "overview": overview,
        "solver_comparison": _report_table_records(
            solver_comparison,
            [
                "result_scope",
                "solver_registry_name",
                "solver_name",
                "num_runs",
                "num_feasible_runs",
                "num_valid_feasible_runs",
                "num_instances_total",
                "feasible_coverage_ratio",
                "valid_feasible_coverage_ratio",
                "coverage_ratio",
                "win_count",
                "average_objective_valid_feasible",
                "average_objective",
                "average_runtime_seconds",
            ],
            limit=40,
        ),
        "support_summary": _report_table_records(
            solver_support_summary,
            [
                "result_scope",
                "solver_registry_name",
                "solver_name",
                "solver_support_status",
                "scoring_status",
                "num_rows",
                "num_feasible_runs",
                "num_valid_feasible_runs",
                "num_instances",
                "row_ratio_within_solver",
                "average_runtime_seconds",
            ],
            limit=60,
        ),
        "selector_vs_baselines": _report_table_records(
            selector_vs_baselines,
            [
                "result_scope",
                "method",
                "reference_solver_name",
                "split_strategy",
                "num_validation_splits",
                "average_objective",
                "objective_gap_vs_virtual_best",
                "objective_gap_vs_single_best",
                "classification_accuracy",
                "balanced_accuracy",
            ],
            limit=20,
        ),
        "feature_importance_summary": _report_table_records(
            feature_importance_summary,
            [
                "result_scope",
                "importance_rank",
                "source_feature",
                "feature_group",
                "importance",
                "importance_share",
                "cumulative_importance_share",
            ],
            limit=15,
        ),
        "markdown_reports": markdown_reports,
        "artifacts": _build_thesis_report_artifacts(paths),
    }


def build_thesis_visualization_state(workspace_root: str | Path) -> dict[str, Any]:
    """Build the presentation-ready thesis visualization state."""

    paths = ReportLoaderPaths.from_workspace(workspace_root)
    selector_results = _load_preferred_csv(paths.thesis_selector_results_table_csv, paths.thesis_selector_overview_csv)
    solver_comparison = _load_preferred_csv(paths.thesis_solver_comparison_table_csv, paths.thesis_solver_leaderboard_csv)
    feature_importance = _load_preferred_csv(paths.thesis_feature_importance_table_csv, paths.thesis_feature_importance_top_csv)
    dataset_summary = _load_preferred_csv(paths.thesis_dataset_summary_table_csv, paths.thesis_dataset_overview_csv)
    real_vs_synthetic = _load_preferred_csv(paths.thesis_real_vs_synthetic_table_csv, paths.thesis_real_vs_synthetic_csv)
    solver_wins = _load_preferred_csv(paths.thesis_solver_win_distribution_table_csv, paths.thesis_solver_win_distribution_csv)
    feature_groups = _load_preferred_csv(paths.thesis_feature_group_summary_table_csv, paths.thesis_feature_group_importance_csv)
    selection_dataset = _safe_read_csv(paths.mixed_selection_dataset_csv)
    combined_benchmark = _safe_read_csv(paths.full_selection_combined_benchmark_csv)
    evaluation_summary = _safe_read_csv(paths.full_selection_evaluation_summary_csv)
    evaluation_run_summary = _load_json_file(paths.full_selection_evaluation_run_summary_json)
    figures_index = _load_markdown_reports(paths.workspace_root, [paths.thesis_figures_index_markdown])
    figure_payloads = _build_presentation_figure_payloads(paths)
    selector_results = _build_presentation_selector_results(selector_results, evaluation_summary)

    available = any(
        frame is not None
        for frame in (
            selector_results,
            solver_comparison,
            feature_importance,
            dataset_summary,
            real_vs_synthetic,
        )
    ) or any(item["exists"] for item in figure_payloads)

    portfolio = _presentation_portfolio(solver_comparison)
    sections = {
        "overview": _build_presentation_overview_section(
            selector_results,
            dataset_summary,
            evaluation_run_summary,
            selection_dataset,
            portfolio,
            figure_payloads,
        ),
        "workflow": build_workflow_section(
            selection_dataset=selection_dataset,
            combined_benchmark=combined_benchmark,
            dataset_summary=dataset_summary,
            evaluation_run_summary=evaluation_run_summary,
            workspace_root=paths.workspace_root,
            intro=_presentation_intro("workflow"),
        ),
        "results": _build_presentation_results_section(selector_results, figure_payloads),
        "solver": _build_presentation_solver_section(solver_comparison, figure_payloads),
        "best_solver": _build_presentation_best_solver_section(solver_wins, selection_dataset, figure_payloads),
        "features": _build_presentation_feature_section(feature_importance, feature_groups, figure_payloads),
        "datasets": _build_presentation_dataset_section(real_vs_synthetic, dataset_summary, figure_payloads),
        "methodology": build_methodology_section(
            selection_dataset=selection_dataset,
            combined_benchmark=combined_benchmark,
            dataset_summary=dataset_summary,
            evaluation_run_summary=evaluation_run_summary,
            figure_payloads=figure_payloads,
            intro=_presentation_intro("methodology"),
        ),
        "implementation": _build_presentation_implementation_section(
            paths=paths,
            selection_dataset=selection_dataset,
            combined_benchmark=combined_benchmark,
            dataset_summary=dataset_summary,
            evaluation_run_summary=evaluation_run_summary,
        ),
    }

    return {
        "available": available,
        "empty_state": (
            "Nav atrasti pārskatam sagatavotie artefakti. "
            "Palaid `python -m src.thesis.generate_assets` un atjauno lapu."
        ),
        "header": {
            "title": "Maģistra darba praktiskās daļas pārskats",
            "subtitle": (
                "Šis skats apkopo maģistra darba praktiskās daļas pārbaudei vajadzīgos rezultātus. "
                "Tas nav paredzēts kā pilnvērtīga sporta kalendāru sastādīšanas sistēma, bet kā "
                "reproducējama eksperimenta pārskats."
            ),
            "accent_note": (
                "Skats apkopo algoritmu izvēles eksperimenta datus, risinātāju portfeļa interpretāciju, "
                "modeļa novērtējumu un reproducēšanas artefaktus."
            ),
        },
        "navigation": [
            {"id": section.identifier, "label": section.title}
            for section in PRESENTATION_SECTIONS
        ],
        "sections": sections,
        "figures_index": figures_index[0] if figures_index else None,
        "ready_files": _build_presentation_ready_files(paths, figure_payloads),
    }


def _load_preferred_csv(*paths: Path) -> pd.DataFrame | None:
    """Return the first existing non-empty CSV from a list of preferred paths."""

    for path in paths:
        frame = _safe_read_csv(path)
        if frame is not None:
            return frame
    return None


def _build_presentation_figure_payloads(paths: ReportLoaderPaths) -> list[dict[str, Any]]:
    """Build the figure list used by the presentation-ready UI."""

    figures_dir = paths.workspace_root / "data" / "results" / "figures"
    payloads: list[dict[str, Any]] = []
    for spec in FIGURE_SPECS:
        path = figures_dir / spec.file_name
        payloads.append(
            {
                "id": spec.identifier,
                "section_id": spec.section_id,
                "title": spec.title,
                "description": spec.description,
                "meaning": spec.meaning,
                "path": _relative_path(paths.workspace_root, path),
                "exists": path.exists(),
                "url": _generated_file_url(paths.workspace_root, path) if path.exists() else None,
            }
        )
    return payloads


def _presentation_portfolio(solver_comparison: pd.DataFrame | None) -> list[str]:
    """Return the localized portfolio labels shown in the overview section."""

    solver_comparison = _presentation_solver_frame(solver_comparison)
    if solver_comparison is None or solver_comparison.empty or "Algoritms" not in solver_comparison.columns:
        return []
    return list(dict.fromkeys(solver_comparison["Algoritms"].dropna().astype(str).tolist()))


def _build_presentation_selector_results(
    selector_results: pd.DataFrame | None,
    evaluation_summary: pd.DataFrame | None,
) -> pd.DataFrame | None:
    """Ensure presentation metrics come from the saved aggregate evaluation summary."""

    normalized = _presentation_selector_frame(selector_results)
    aggregate = _aggregate_selector_summary_row(evaluation_summary)
    if aggregate is None:
        return normalized

    improvement = aggregate.get("improvement_vs_single_best")
    if pd.isna(improvement):
        delta = aggregate.get("delta_vs_single_best")
        improvement = -float(delta) if pd.notna(delta) else None

    overrides = {
        "Labākais fiksētais algoritms": _solver_display_name(aggregate.get("single_best_solver_name")),
        "Precizitāte": aggregate.get("classification_accuracy"),
        "Sabalansētā precizitāte": aggregate.get("balanced_accuracy"),
        "Vidējā izvēlētā kvalitāte": aggregate.get("average_selected_objective"),
        "Vidējā virtual best kvalitāte": aggregate.get("average_virtual_best_objective"),
        "Vidējā single best kvalitāte": aggregate.get("average_single_best_objective"),
        "Regret pret virtual best": aggregate.get("regret_vs_virtual_best"),
        "Uzlabojums pret single best": improvement,
    }

    if normalized is None or normalized.empty:
        row = {"Modeļa tips": "Nejaušo mežu klasifikators", **overrides}
        return pd.DataFrame([row])

    merged = normalized.copy()
    first_index = merged.index[0]
    for column, value in overrides.items():
        if value is None or pd.isna(value):
            continue
        merged.at[first_index, column] = value
    return merged


def _aggregate_selector_summary_row(evaluation_summary: pd.DataFrame | None) -> pd.Series | None:
    """Return the aggregate evaluation row for the mixed dataset when available."""

    if evaluation_summary is None or evaluation_summary.empty:
        return None

    if {"summary_row_type", "dataset_type"}.issubset(evaluation_summary.columns):
        rows = evaluation_summary[
            (evaluation_summary["summary_row_type"].astype(str) == "aggregate_mean")
            & (evaluation_summary["dataset_type"].fillna("all").astype(str) == "all")
        ]
        if not rows.empty:
            return rows.iloc[0]

    if "summary_row_type" in evaluation_summary.columns:
        rows = evaluation_summary[evaluation_summary["summary_row_type"].astype(str) == "aggregate_mean"]
        if not rows.empty:
            return rows.iloc[0]

    return evaluation_summary.iloc[0]


def _solver_display_name(value: object) -> str | None:
    """Map one solver registry identifier to a presentation label."""

    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    return SOLVER_LABELS.get(text, text.replace("_", " ").title())


def _presentation_selector_frame(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize selector-results columns for the presentation UI."""

    if frame is None or frame.empty or "Modeļa tips" in frame.columns:
        return frame
    renamed = frame.rename(
        columns={
            "single_best_solver_name": "Labākais fiksētais algoritms",
            "classification_accuracy": "Precizitāte",
            "balanced_accuracy": "Sabalansētā precizitāte",
            "average_selected_objective": "Vidējā izvēlētā kvalitāte",
            "average_virtual_best_objective": "Vidējā virtual best kvalitāte",
            "average_single_best_objective": "Vidējā single best kvalitāte",
            "regret_vs_virtual_best": "Regret pret virtual best",
            "improvement_vs_single_best": "Uzlabojums pret single best",
            "num_test_instances": "Testa instanču skaits",
            "num_validation_splits": "Validācijas sadalījumu skaits",
        }
    ).copy()
    if "Labākais fiksētais algoritms" in renamed.columns:
        renamed["Labākais fiksētais algoritms"] = (
            renamed["Labākais fiksētais algoritms"].astype(str).str.replace("_", " ").str.title()
        )
    if "Modeļa tips" not in renamed.columns:
        renamed["Modeļa tips"] = "Nejaušo mežu klasifikators"
    return renamed


def _presentation_summary_frame(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize the overview summary table for the presentation UI."""

    if frame is None or frame.empty or "Rādītājs" in frame.columns:
        return frame

    if {"metric_type", "label", "count"}.issubset(frame.columns):
        mapped_rows = []
        for row in frame.to_dict(orient="records"):
            label = str(row["label"])
            if label == "total_rows":
                metric = "Kopējais instanču skaits"
            elif label == "real":
                metric = "Reālo instanču skaits"
            elif label == "synthetic":
                metric = "Sintētisko instanču skaits"
            elif label == "labeled_rows":
                metric = "Marķēto instanču skaits"
            elif label == "distinct_best_solvers":
                metric = "Atšķirīgo best_solver klašu skaits"
            else:
                metric = label
            mapped_rows.append({"Rādītājs": metric, "Vērtība": row["count"]})
        return pd.DataFrame(mapped_rows)
    return frame


def _presentation_solver_frame(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize solver-comparison columns for the presentation UI."""

    if frame is None or frame.empty:
        return frame
    solver_ids = _solver_ids_from_frame(frame)
    renamed = frame.rename(
        columns={
            "result_scope": "Datu kopa",
            "solver_registry_name": "Algoritms",
            "win_count": "Uzvaras",
            "average_objective_valid_feasible": "Vidējā kvalitāte",
            "average_runtime_seconds": "Vidējais laiks (s)",
            "feasible_coverage_ratio": "Feasible pārklājums",
            "valid_feasible_coverage_ratio": "Salīdzināmais pārklājums",
        }
    ).copy()
    if "Datu kopa" in renamed.columns:
        renamed["Datu kopa"] = renamed["Datu kopa"].replace({"real": "Reālie dati", "synthetic": "Sintētiskie dati"})
    if "Algoritms" in renamed.columns:
        renamed["Algoritms"] = [
            _solver_display_label(solver_id, fallback)
            for solver_id, fallback in zip(solver_ids, renamed["Algoritms"].tolist(), strict=False)
        ]
        role_values = [_solver_role_label(solver_id) for solver_id in solver_ids]
        interpretation_values = [_solver_interpretation(solver_id) for solver_id in solver_ids]
        if "Loma" in renamed.columns:
            renamed["Loma"] = role_values
        else:
            renamed.insert(
                renamed.columns.get_loc("Algoritms") + 1,
                "Loma",
                role_values,
            )
        if "Interpretācija" in renamed.columns:
            renamed["Interpretācija"] = interpretation_values
        else:
            renamed.insert(
                renamed.columns.get_loc("Loma") + 1 if "Loma" in renamed.columns else len(renamed.columns),
                "Interpretācija",
                interpretation_values,
            )
    return renamed


def _presentation_solver_win_frame(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize solver-win rows for the presentation UI."""

    if frame is None or frame.empty:
        return frame
    solver_ids = _solver_ids_from_frame(frame)
    renamed = frame.rename(
        columns={
            "result_scope": "Datu kopa",
            "solver_registry_name": "Algoritms",
            "win_count": "Skaits",
        }
    ).copy()
    if "Datu kopa" in renamed.columns:
        renamed["Datu kopa"] = renamed["Datu kopa"].replace({"real": "Reālie dati", "synthetic": "Sintētiskie dati"})
    if "Algoritms" in renamed.columns:
        renamed["Algoritms"] = [
            _solver_display_label(solver_id, fallback)
            for solver_id, fallback in zip(solver_ids, renamed["Algoritms"].tolist(), strict=False)
        ]
        role_values = [_solver_role_label(solver_id) for solver_id in solver_ids]
        if "Loma" in renamed.columns:
            renamed["Loma"] = role_values
        else:
            renamed.insert(
                renamed.columns.get_loc("Algoritms") + 1,
                "Loma",
                role_values,
            )
    return renamed


def _solver_ids_from_frame(frame: pd.DataFrame) -> list[str]:
    """Resolve registry-level solver identifiers from a presentation table."""

    if "solver_registry_name" in frame.columns:
        return frame["solver_registry_name"].fillna("").astype(str).tolist()
    if "best_solver" in frame.columns:
        return frame["best_solver"].fillna("").astype(str).tolist()
    if "solver_name" in frame.columns:
        return frame["solver_name"].fillna("").astype(str).tolist()
    if "Algoritms" in frame.columns:
        return [
            SOLVER_LABEL_TO_REGISTRY.get(str(value), str(value).strip())
            for value in frame["Algoritms"].fillna("").tolist()
        ]
    return [""] * len(frame.index)


def _solver_display_label(solver_id: str, fallback: object) -> str:
    """Return a compact display label without hiding the registry identity."""

    normalized = str(solver_id).strip()
    if normalized:
        try:
            metadata = get_solver_metadata(normalized)
            return SOLVER_LABELS.get(metadata.registry_name, metadata.display_name)
        except KeyError:
            pass

    fallback_text = str(fallback).strip()
    return SOLVER_LABELS.get(fallback_text, fallback_text.replace("_", " ").title())


def _solver_role_label(solver_id: str) -> str:
    """Return the dashboard role label for one solver."""

    try:
        metadata = get_solver_metadata(str(solver_id).strip())
    except KeyError:
        return "Cits / nav reģistrā"
    return SOLVER_ROLE_LABELS.get(metadata.role, metadata.role.replace("_", " ").title())


def _solver_interpretation(solver_id: str) -> str:
    """Return a short thesis-safe interpretation note for one solver."""

    try:
        metadata = get_solver_metadata(str(solver_id).strip())
    except KeyError:
        return "Nav centrālajā solveru reģistrā; interpretēt piesardzīgi."
    return SOLVER_ROLE_INTERPRETATION.get(metadata.role, metadata.objective_interpretation)


def _presentation_feature_frame(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize feature-importance columns for the presentation UI."""

    if frame is None or frame.empty:
        return frame
    if "Pazīme" in frame.columns:
        normalized = frame.copy()
        normalized["Pazīme"] = normalized["Pazīme"].astype(str).str.replace(" ", "_")
        return normalized
    renamed = frame.rename(
        columns={
            "importance_rank": "Rangs",
            "source_feature": "Pazīme",
            "feature_group": "Grupa",
            "importance": "Nozīmīgums",
        }
    ).copy()
    if "Grupa" in renamed.columns:
        renamed["Grupa"] = renamed["Grupa"].astype(str).str.replace("_", " ").str.title()
    return renamed


def _presentation_feature_group_frame(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize feature-group rows for the presentation UI."""

    if frame is None or frame.empty or "Grupa" in frame.columns:
        return frame
    renamed = frame.rename(
        columns={
            "feature_group": "Grupa",
            "importance": "Kopējais nozīmīgums",
            "importance_share": "Īpatsvars",
        }
    ).copy()
    if "Grupa" in renamed.columns:
        renamed["Grupa"] = renamed["Grupa"].astype(str).str.replace("_", " ").str.title()
    return renamed


def _presentation_real_vs_synthetic_frame(frame: pd.DataFrame | None) -> pd.DataFrame | None:
    """Normalize real-vs-synthetic table columns for the presentation UI."""

    if frame is None or frame.empty or "Datu kopa" in frame.columns:
        return frame
    renamed = frame.rename(
        columns={
            "dataset_type": "Datu kopa",
            "classification_accuracy": "Precizitāte",
            "balanced_accuracy": "Sabalansētā precizitāte",
            "average_selected_objective": "Vidējā izvēlētā kvalitāte",
            "average_virtual_best_objective": "Vidējā virtual best kvalitāte",
            "average_single_best_objective": "Vidējā single best kvalitāte",
            "regret_vs_virtual_best": "Regret pret virtual best",
            "delta_vs_single_best": "Delta pret single best",
        }
    ).copy()
    if "Datu kopa" in renamed.columns:
        renamed["Datu kopa"] = renamed["Datu kopa"].replace({"real": "Reālie dati", "synthetic": "Sintētiskie dati"})
    return renamed


def _build_presentation_overview_section(
    selector_results: pd.DataFrame | None,
    dataset_summary: pd.DataFrame | None,
    evaluation_run_summary: dict[str, Any] | None,
    selection_dataset: pd.DataFrame | None,
    portfolio: list[str],
    figure_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the overview section for the presentation UI."""

    selector_results = _presentation_selector_frame(selector_results)
    dataset_summary = _presentation_summary_frame(dataset_summary)
    total_instances = _summary_value(dataset_summary, "Kopējais instanču skaits")
    real_instances = _summary_value(dataset_summary, "Reālo instanču skaits")
    synthetic_instances = _summary_value(dataset_summary, "Sintētisko instanču skaits")
    active_best_solver_classes = _first_non_empty(
        _summary_value(dataset_summary, "Atšķirīgo best_solver klašu skaits"),
        _summary_value(dataset_summary, "Atšķirīgo labāko algoritmu skaits"),
    )
    feature_count = _structural_column_count(selection_dataset)
    validation_splits = _row_value(selector_results, 0, "Validācijas sadalījumu skaits")
    settings = evaluation_run_summary.get("settings", {}) if isinstance(evaluation_run_summary, dict) else {}
    folds = settings.get("cross_validation_folds")
    repeats = settings.get("repeats")
    if folds and repeats:
        validation_scheme = f"{repeats}x{folds} atkārtota stratificēta krustotā pārbaude"
    elif validation_splits:
        validation_scheme = f"{validation_splits} validācijas sadalījumi"
    else:
        validation_scheme = "Saglabāta validācijas shēma"

    cards = [
        {
            "label": "Instances",
            "value": f"{int(total_instances)} instances" if total_instances is not None else "Nav datu",
            "description": (
                "Jaukta datu kopa; sintētiskās instances dominē."
                if real_instances is not None and synthetic_instances is not None
                else "Instanču skaits nolasīts no saglabātās datu kopas."
            ),
        },
        {
            "label": "Datu avoti",
            "value": (
                f"{int(real_instances)} reālās / {int(synthetic_instances)} sintētiskās"
                if real_instances is not None and synthetic_instances is not None
                else "Nav datu"
            ),
            "description": "Rezultāti jāinterpretē, ņemot vērā datu izcelsmes nelīdzsvaru.",
        },
        {
            "label": "Strukturālās pazīmes",
            "value": f"{feature_count} pazīmes" if feature_count is not None else "Nav datu",
            "description": "Modeļa ievadē paliek tikai pirms-risināšanas strukturālās pazīmes.",
        },
        {
            "label": "Risinātāju portfelis",
            "value": f"{len(portfolio)} reģistrēti risinātāji" if portfolio else "Nav datu",
            "description": "Timefold ir reģistrēts kā saskarne, nevis aktīvs veiktspējas salīdzinājuma dalībnieks.",
        },
        {
            "label": "best_solver klases",
            "value": (
                f"{int(active_best_solver_classes)} aktīvas klases"
                if active_best_solver_classes is not None
                else "Nav datu"
            ),
            "description": "Gala klasēs parādās reālo datu un sintētisko datu atšķirīgs risinātājs.",
        },
        {
            "label": "Novērtēšana",
            "value": validation_scheme,
            "description": "Atkārtota stratificēta krustotā pārbaude ar saglabātiem pārbaudes sadalījumiem.",
        },
    ]
    highlights = [
        "Skats rāda darba praktiskajā daļā aprakstīto eksperimenta tvērumu un gala interpretācijai nepieciešamos artefaktus.",
        "Augstie rādītāji apliecina pieejas realizējamību šajā uzstādījumā, nevis pilnvērtīgu ITC2021 risinātāju portfeli.",
    ]
    return {
        "id": "overview",
        "title": "Eksperimentālās daļas uzbūve",
        "intro": _presentation_intro("overview"),
        "takeaway": _build_overview_takeaway(real_instances, synthetic_instances),
        "cards": cards,
        "highlights": highlights,
        "portfolio": portfolio,
        "figures": _select_section_figures(figure_payloads, "overview"),
    }


def _build_presentation_results_section(
    selector_results: pd.DataFrame | None,
    figure_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the main-results section for the presentation UI."""

    selector_results = _presentation_selector_frame(selector_results)
    cards = [
        {
            "label": "Modeļa precizitāte",
            "value": _format_numeric(_row_value(selector_results, 0, "Precizitāte"), digits=4),
            "description": "Atbilstība best_solver klasei konkrētajā eksperimentālajā tvērumā.",
        },
        {
            "label": "Sabalansētā precizitāte",
            "value": _format_numeric(_row_value(selector_results, 0, "Sabalansētā precizitāte"), digits=4),
            "description": "Rādītājs, kas mazina klašu īpatsvara ietekmi uz novērtējumu.",
        },
        {
            "label": "Regret pret virtual best",
            "value": _format_numeric(_row_value(selector_results, 0, "Regret pret virtual best"), digits=4),
            "description": "Vidējais kvalitātes zudums pret VBS atskaiti katrai instancei.",
        },
        {
            "label": "Uzlabojums pret single best",
            "value": _format_numeric(_row_value(selector_results, 0, "Uzlabojums pret single best"), digits=4),
            "description": "Vidējais ieguvums pret SBS atskaiti šajā datu kopā.",
        },
    ]
    return {
        "id": "results",
        "title": "Nejaušo mežu klasifikatora novērtēšana",
        "intro": _presentation_intro("results"),
        "takeaway": _build_results_takeaway(selector_results),
        "cards": cards,
        "figures": _select_section_figures(figure_payloads, "results"),
    }


def _build_presentation_solver_section(
    solver_comparison: pd.DataFrame | None,
    figure_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the solver-comparison section for the presentation UI."""

    solver_comparison = _presentation_solver_frame(solver_comparison)
    table_rows = _portfolio_role_rows(solver_comparison)

    return {
        "id": "solver",
        "title": "Risinātāju lomas un interpretācijas tvērums",
        "intro": _presentation_intro("solver"),
        "takeaway": _build_solver_takeaway(table_rows),
        "table_title": "Risinātāju lomas un interpretācijas tvērums",
        "table_note": (
            "Tabula apraksta portfelī reģistrētos risināšanas variantus. Tā nav četru pilnvērtīgi "
            "salīdzināmu algoritmu veiktspējas tabula."
        ),
        "table_rows": table_rows,
        "figures": _select_section_figures(figure_payloads, "solver"),
    }


def _build_presentation_best_solver_section(
    solver_wins: pd.DataFrame | None,
    selection_dataset: pd.DataFrame | None,
    figure_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the separate best_solver target-class section."""

    solver_wins = _presentation_solver_win_frame(solver_wins)
    table_rows = _records(solver_wins) if solver_wins is not None and not solver_wins.empty else []
    class_count = _count_distinct_best_solvers(selection_dataset)
    real_row = _best_solver_row_for_dataset(solver_wins, "Reālie dati")
    synthetic_row = _best_solver_row_for_dataset(solver_wins, "Sintētiskie dati")
    real_solver = real_row.get("Algoritms") if real_row else "Nav datu"
    synthetic_solver = synthetic_row.get("Algoritms") if synthetic_row else "Nav datu"
    real_count = real_row.get("Skaits") if real_row else None
    synthetic_count = synthetic_row.get("Skaits") if synthetic_row else None

    return {
        "id": "best_solver",
        "title": "best_solver klašu sadalījums",
        "intro": _presentation_intro("best_solver"),
        "takeaway": _build_best_solver_takeaway(real_solver, synthetic_solver, class_count),
        "cards": [
            {
                "label": "Aktīvās klases",
                "value": f"{class_count} aktīvas klases" if class_count is not None else "Nav datu",
                "description": "Gala mērķī parādās tikai risinātāji, kas kļuvuši par best_solver.",
            },
            {
                "label": "Reālās instances",
                "value": str(real_solver),
                "description": (
                    f"{int(real_count)} reālajās instancēs gala klase ir šis risinātājs."
                    if real_count is not None
                    else "Reālo instanču best_solver sadalījums nav pieejams."
                ),
            },
            {
                "label": "Sintētiskās instances",
                "value": str(synthetic_solver),
                "description": (
                    f"{int(synthetic_count)} sintētiskajās instancēs gala klase ir šis risinātājs."
                    if synthetic_count is not None
                    else "Sintētisko instanču best_solver sadalījums nav pieejams."
                ),
            },
            {
                "label": "Datu avota efekts",
                "value": "Jāņem vērā",
                "description": "Pašreizējā jauktajā datu kopā best_solver cieši sakrīt ar datu avotu.",
            },
        ],
        "highlights": [
            "best_solver netiek noteikts mehāniski tikai pēc mazākās mērķfunkcijas vērtības; pirms izvēles tiek pārbaudīts rezultāta derīgums un interpretējamība.",
            "Šis sadalījums jālasa kā mērķa klašu struktūra, nevis kā pierādījums par vispārīgi labāko risinātāju.",
        ],
        "table_title": "best_solver klašu sadalījums pēc datu avota",
        "table_note": "Tabula nodala reālo un sintētisko instanču gala klases, lai nepaslēptu datu avota efektu.",
        "table_rows": table_rows,
        "figures": _select_section_figures(figure_payloads, "best_solver"),
    }


def _portfolio_role_rows(solver_comparison: pd.DataFrame | None) -> list[dict[str, str]]:
    """Return one interpretation row per registered solver variant."""

    if solver_comparison is None or solver_comparison.empty or "Algoritms" not in solver_comparison.columns:
        return []

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for _, row in solver_comparison.iterrows():
        solver_name = str(row.get("Algoritms") or "").strip()
        if not solver_name or solver_name in seen:
            continue
        seen.add(solver_name)
        solver_id = SOLVER_LABEL_TO_REGISTRY.get(solver_name, solver_name)
        rows.append(
            {
                "Risināšanas variants": solver_name,
                "Loma": str(row.get("Loma") or _solver_role_label(solver_id)),
                "Interpretācijas tvērums": str(row.get("Interpretācija") or _solver_interpretation(solver_id)),
                "Statuss šajā pārskatā": _solver_status_note(solver_id),
            }
        )
    return rows


def _solver_status_note(solver_id: str) -> str:
    """Return a short thesis-safe status for one solver variant."""

    normalized = str(solver_id).strip()
    if normalized == "timefold":
        return "Reģistrēta integrācijas saskarne; ārējais izpildāmais fails nav konfigurēts."
    if normalized == "random_baseline":
        return "Diagnostiska datu plūsmas pārbaude, nevis praktisks kalendāra risinātājs."
    if normalized == "cpsat_solver":
        return "Aktīva strukturālas pamatstruktūras optimizācijas atskaites pieeja."
    if normalized == "simulated_annealing_solver":
        return "Aktīva vienkāršota heiristiska atskaites pieeja."
    return "Interpretēt kopā ar risinātāja reģistra metadatiem."


def _best_solver_row_for_dataset(frame: pd.DataFrame | None, dataset_label: str) -> dict[str, Any] | None:
    """Return the first best_solver distribution row for one displayed dataset label."""

    if frame is None or frame.empty or "Datu kopa" not in frame.columns:
        return None
    rows = frame[frame["Datu kopa"] == dataset_label]
    if rows.empty:
        return None
    return {str(key): _json_safe_value(value) for key, value in rows.iloc[0].to_dict().items()}


def _count_distinct_best_solvers(selection_dataset: pd.DataFrame | None) -> int | None:
    """Count active best_solver labels in the mixed selection dataset."""

    if selection_dataset is None or selection_dataset.empty or "best_solver" not in selection_dataset.columns:
        return None
    return int(selection_dataset["best_solver"].dropna().astype(str).nunique())


def _build_presentation_feature_section(
    feature_importance: pd.DataFrame | None,
    feature_groups: pd.DataFrame | None,
    figure_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the feature-analysis section for the presentation UI."""

    feature_importance = _presentation_feature_frame(feature_importance)
    feature_groups = _presentation_feature_group_frame(feature_groups)
    feature_rows = _records(feature_importance.head(10)) if feature_importance is not None and not feature_importance.empty else []
    group_rows = _records(feature_groups) if feature_groups is not None and not feature_groups.empty else []
    top_feature = feature_rows[0]["Pazīme"] if feature_rows else "Nav datu"
    top_group = group_rows[0]["Grupa"] if group_rows else "Nav datu"

    return {
        "id": "features",
        "title": "Strukturālo pazīmju nozīmīgums nejaušo mežu klasifikatorā",
        "intro": _presentation_intro("features"),
        "takeaway": _build_feature_takeaway(feature_groups),
        "highlight": (
            f"Svarīgākā individuālā pazīme ir {top_feature}, savukārt dominējošā grupa ir {top_group}; "
            "pazīmju grupu kopsavilkums zemāk redzams tabulā."
            if feature_rows and group_rows
            else "Pazīmju nozīmīguma kopsavilkums būs pieejams pēc artefaktu ģenerēšanas."
        ),
        "table_title": "Desmit nozīmīgākās strukturālās pazīmes",
        "table_rows": feature_rows,
        "secondary_table_title": "Pazīmju grupu kopējais nozīmīgums",
        "secondary_table_rows": group_rows,
        "figures": _select_section_figures(figure_payloads, "features"),
    }


def _build_presentation_dataset_section(
    real_vs_synthetic: pd.DataFrame | None,
    dataset_summary: pd.DataFrame | None,
    figure_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build the real-vs-synthetic comparison section for the presentation UI."""

    real_vs_synthetic = _presentation_real_vs_synthetic_frame(real_vs_synthetic)
    dataset_summary = _presentation_summary_frame(dataset_summary)
    comparison_rows = _records(real_vs_synthetic) if real_vs_synthetic is not None and not real_vs_synthetic.empty else []
    real_instances = _summary_value(dataset_summary, "Reālo instanču skaits")
    synthetic_instances = _summary_value(dataset_summary, "Sintētisko instanču skaits")
    note = (
        f"Salīdzinājumā izmantotas {int(real_instances)} reālās un {int(synthetic_instances)} sintētiskās instances."
        if real_instances is not None and synthetic_instances is not None
        else "Salīdzinājuma tabula balstīta uz saglabātajiem novērtējuma artefaktiem."
    )

    return {
        "id": "datasets",
        "title": "Datu grupu rādītāji",
        "intro": _presentation_intro("datasets"),
        "takeaway": _build_dataset_takeaway(real_vs_synthetic),
        "table_title": "Algoritmu izvēles modeļa rezultāti pa datu grupām",
        "table_note": note,
        "table_rows": comparison_rows,
        "figures": _select_section_figures(figure_payloads, "datasets"),
    }


def _build_presentation_implementation_section(
    *,
    paths: ReportLoaderPaths,
    selection_dataset: pd.DataFrame | None,
    combined_benchmark: pd.DataFrame | None,
    dataset_summary: pd.DataFrame | None,
    evaluation_run_summary: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the implemented-practical-work section."""

    dataset_summary = _presentation_summary_frame(dataset_summary)
    total_instances = _summary_value(dataset_summary, "Kopējais instanču skaits")
    real_instances = _summary_value(dataset_summary, "Reālo instanču skaits")
    synthetic_instances = _summary_value(dataset_summary, "Sintētisko instanču skaits")
    solver_count = _count_unique_solvers(combined_benchmark)
    benchmark_rows = len(combined_benchmark.index) if combined_benchmark is not None else None
    feature_count = _structural_column_count(selection_dataset)
    validation_label = _implementation_validation_label(evaluation_run_summary)

    return {
        "id": "implementation",
        "title": "Artefakti un reproducēšana",
        "intro": _presentation_intro("implementation"),
        "takeaway": (
            "Praktiskajā daļā ir izveidota reproducējama eksperimentālā plūsma: datu sagatavošana, "
            "pazīmju iegūšana, risinātāju portfeļa izpilde, algoritmu izvēles datu kopa, "
            "modeļa novērtēšana un darba attēlu/tabulu sagatavošana."
        ),
        "cards": [
            {
                "label": "Jauktā datu kopa",
                "value": f"{int(total_instances)} instances" if total_instances is not None else "Nav datu",
                "description": (
                    f"{int(real_instances)} reālās un {int(synthetic_instances)} sintētiskās instances."
                    if real_instances is not None and synthetic_instances is not None
                    else "Datu apjoms tiek nolasīts no sagatavotajām darba tabulām."
                ),
            },
            {
                "label": "Strukturālās pazīmes",
                "value": f"{feature_count} lauki" if feature_count is not None else "Nav datu",
                "description": "Pazīmes raksturo instances izmēru, ierobežojumu sastāvu, blīvumu un daudzveidību.",
            },
            {
                "label": "Risinātāju izpildes",
                "value": f"{benchmark_rows} rindas" if benchmark_rows is not None else "Nav datu",
                "description": f"Benchmark tabulā ir {solver_count or 0} reģistrēti risināšanas varianti; Timefold nav konfigurēts kā aktīvs salīdzinājums.",
            },
            {
                "label": "Modeļa novērtēšana",
                "value": validation_label,
                "description": "Rezultāti salīdzināti ar single best un virtual best atskaites punktiem.",
            },
        ],
        "table_title": "Īstenotie praktiskās daļas posmi",
        "table_note": "Tabula apkopo darba praktiskajā daļā aprakstīto eksperimentālo plūsmu.",
        "table_rows": _implementation_step_rows(paths.workspace_root),
        "artifact_table_title": "Galvenie rezultātu artefakti",
        "artifact_table_note": "Sarakstā atstāti praktiskās daļas pārskatam izmantotie dati, tabulas, attēli un reproducēšanas dokumenti.",
        "artifact_rows": _implementation_artifact_rows(paths),
    }


def _structural_column_count(selection_dataset: pd.DataFrame | None) -> int | None:
    """Return the number of structural input columns available in the mixed dataset."""

    if selection_dataset is None or selection_dataset.empty:
        return None
    excluded_columns = {
        "instance_name",
        "dataset_type",
        "best_solver",
    }
    excluded_prefixes = (
        "objective_",
        "benchmark_",
        "label_",
        "target_",
        "source_",
        "solver_",
        "scoring_",
        "selected_",
        "true_",
        "single_best_",
        "virtual_best_",
        "prediction_",
        "regret_",
        "delta_",
        "improvement_",
    )
    columns = [
        column
        for column in selection_dataset.columns
        if column not in excluded_columns and not column.startswith(excluded_prefixes)
    ]
    return len(columns)


def _implementation_validation_label(evaluation_run_summary: dict[str, Any] | None) -> str:
    """Return the validation scheme label used in the implemented workflow."""

    settings = evaluation_run_summary.get("settings", {}) if isinstance(evaluation_run_summary, dict) else {}
    folds = settings.get("cross_validation_folds")
    repeats = settings.get("repeats")
    return f"{repeats}x{folds} krustotā pārbaude" if folds and repeats else "Atkārtota krustotā pārbaude"


def _implementation_step_rows(workspace_root: Path) -> list[dict[str, str]]:
    """Return the implemented thesis-practical workflow rows."""

    rows: list[dict[str, str]] = []
    for stage, implemented, paths in IMPLEMENTATION_STEP_ROWS:
        rows.append(
            {
                "Darba posms": stage,
                "Kas izdarīts": implemented,
                "Kur atrodas": paths,
                "Statuss": _implementation_paths_status(workspace_root, paths),
            }
        )
    return rows


def _implementation_artifact_rows(paths: ReportLoaderPaths) -> list[dict[str, str]]:
    """List the main thesis-practical output artifacts."""

    specs = [
        (
            "Jauktā algoritmu izvēles datu kopa",
            paths.mixed_selection_dataset_csv,
            "Viena rinda katrai instancei ar strukturālajām pazīmēm un best_solver mērķi.",
        ),
        (
            "Risinātāju benchmark rezultāti",
            paths.full_selection_combined_benchmark_csv,
            "Kopējā risinātāju izpildes tabula algoritmu izvēles datu kopai.",
        ),
        (
            "Modeļa novērtējuma kopsavilkums",
            paths.full_selection_evaluation_summary_csv,
            "Galvenie modeļa, single best un virtual best salīdzinājuma rādītāji.",
        ),
        (
            "Pazīmju nozīmīgums",
            paths.full_selection_feature_importance_csv,
            "Nejaušo mežu klasifikatora izmantoto strukturālo pazīmju nozīmīguma tabula.",
        ),
        (
            "Darba tabulas",
            paths.thesis_tables_dir,
            "Tīras CSV tabulas, kas izmantotas praktiskās daļas rezultātu apkopošanai.",
        ),
        (
            "Darba attēli",
            paths.workspace_root / "data" / "results" / "figures",
            "UI un darba tekstā izmantotie rezultātu attēli.",
        ),
        (
            "Reproducēšanas ceļvedis",
            paths.workspace_root / "docs" / "reproduction_guide.md",
            "Komandu secība praktiskās daļas rezultātu pārbūvēšanai.",
        ),
        (
            "Reproducējamības audits",
            paths.workspace_root / "docs" / "reproducibility_audit.md",
            "Pārbaudes piezīmes par praktiskās daļas artefaktu reproducējamību.",
        ),
    ]
    rows: list[dict[str, str]] = []
    for label, path, description in specs:
        rows.append(
            {
                "Artefakts": label,
                "Ceļš": _relative_path(paths.workspace_root, path) or "",
                "Statuss": "Ir" if path.exists() else "Nav atrasts",
                "Apjoms": _artifact_size_label(path),
                "Nozīme": description,
            }
        )
    return rows


def _artifact_size_label(path: Path) -> str:
    """Return a compact size label for one practical output artifact."""

    if not path.exists():
        return "Nav datu"
    if path.is_dir():
        return f"{len(list(path.iterdir()))} ieraksti"
    return _format_file_size(path.stat().st_size)


def _implementation_paths_status(workspace_root: Path, paths: str) -> str:
    """Return whether the implementation row points to existing files or folders."""

    relative_paths = [Path(item.strip()) for item in paths.split(";")]
    return "Ir" if all((workspace_root / path).exists() for path in relative_paths) else "Nav atrasts"


def _build_presentation_ready_files(
    paths: ReportLoaderPaths,
    figure_payloads: list[dict[str, Any]],
) -> dict[str, Any]:
    """List the main files that are ready for thesis insertion."""

    table_paths = [
        paths.thesis_selector_results_table_csv,
        paths.thesis_solver_comparison_table_csv,
        paths.thesis_feature_importance_table_csv,
        paths.thesis_dataset_summary_table_csv,
        paths.thesis_real_vs_synthetic_table_csv,
    ]
    return {
        "figures": figure_payloads,
        "tables": [
            {
                "label": _labelize(path.stem),
                "path": _relative_path(paths.workspace_root, path),
                "exists": path.exists(),
                "url": _generated_file_url(paths.workspace_root, path) if path.exists() else None,
            }
            for path in table_paths
        ],
        "figures_index": {
            "label": "Attēlu indekss",
            **_describe_path(paths.workspace_root, paths.thesis_figures_index_markdown),
            "url": _generated_file_url(paths.workspace_root, paths.thesis_figures_index_markdown)
            if paths.thesis_figures_index_markdown.exists()
            else None,
        },
    }


def _presentation_intro(section_id: str) -> str:
    """Return the configured introduction for one presentation section."""

    for section in PRESENTATION_SECTIONS:
        if section.identifier == section_id:
            return section.intro
    return ""


def _select_section_figures(
    figure_payloads: list[dict[str, Any]],
    section_id: str,
) -> list[dict[str, Any]]:
    """Return the curated figure subset assigned to one presentation section."""

    selected_ids = PRESENTATION_FIGURES_BY_SECTION.get(section_id)
    if selected_ids is None:
        return [item for item in figure_payloads if item["section_id"] == section_id]
    if not selected_ids:
        return []

    by_id = {item["id"]: item for item in figure_payloads}
    return [by_id[figure_id] for figure_id in selected_ids if figure_id in by_id]


def _build_overview_takeaway(real_instances: object | None, synthetic_instances: object | None) -> str:
    """Build the short bold takeaway for the overview section."""

    if real_instances is not None and synthetic_instances is not None:
        return (
            f"Datu kopa apvieno {int(real_instances)} reālās un {int(synthetic_instances)} sintētiskās instances, "
            "un sintētiskās instances veido lielāko daļu; rezultāti jāinterpretē piesardzīgi."
        )
    return "Eksperiments vienotā skatā apvieno datu kopu, risinātāju portfeli un saglabātos novērtējuma artefaktus."


def _build_results_takeaway(selector_results: pd.DataFrame | None) -> str:
    """Build the short bold takeaway for the main-results section."""

    accuracy = _row_value(selector_results, 0, "Precizitāte")
    balanced_accuracy = _row_value(selector_results, 0, "Sabalansētā precizitāte")
    regret = _row_value(selector_results, 0, "Regret pret virtual best")
    improvement = _row_value(selector_results, 0, "Uzlabojums pret single best")
    if None not in {accuracy, balanced_accuracy, regret, improvement}:
        return (
            f"Pašreizējā validācijā modelis sasniedz precizitāti {_format_numeric(accuracy, digits=4)} un sabalansēto "
            f"precizitāti {_format_numeric(balanced_accuracy, digits=4)}; šie skaitļi ir jāinterpretē kopā ar "
            f"regret pret virtual best ({_format_numeric(regret, digits=4)}), ieguvumu pret single best "
            f"({_format_numeric(improvement, digits=4)}) un datu avota efektu."
        )
    return "Galvenie rādītāji apraksta pašreizējā eksperimenta uzvedību, nevis universālu vispārinājumu."


def _build_solver_takeaway(role_rows: list[dict[str, str]]) -> str:
    """Build the short bold takeaway for the solver-comparison section."""

    if role_rows:
        return (
            f"Portfelī ir {len(role_rows)} reģistrēti risināšanas varianti ar atšķirīgu statusu un tvērumu; "
            "Timefold šajā konfigurācijā nav aktīvs veiktspējas salīdzinājuma dalībnieks."
        )
    return "Risinātāju portfelis jāinterpretē kopā ar tā modelēšanas tvērumu un atbalsta statusiem."


def _build_best_solver_takeaway(
    real_solver: object,
    synthetic_solver: object,
    class_count: int | None,
) -> str:
    """Build the short bold takeaway for the best_solver section."""

    class_label = f"{class_count} aktīvas best_solver klases" if class_count is not None else "aktīvās best_solver klases"
    return (
        f"Gala mērķī ir {class_label}: reālajām instancēm {real_solver}, bet sintētiskajām instancēm "
        f"{synthetic_solver}. Tas ir datu avota efekts, kas jāņem vērā pirms jebkādas vispārināšanas."
    )


def _build_feature_takeaway(feature_groups: pd.DataFrame | None) -> str:
    """Build the short bold takeaway for the feature-analysis section."""

    if feature_groups is None or feature_groups.empty or "Grupa" not in feature_groups.columns:
        return "Modeļa lēmumus visvairāk nosaka problēmas strukturālās pazīmes."

    top_groups = feature_groups["Grupa"].dropna().astype(str).tolist()
    if len(top_groups) >= 2:
        return "Lielākais kopējais nozīmīgums ir ierobežojumu daudzveidības un ierobežojumu blīvuma pazīmju grupām."
    return f"Dominējošā pazīmju grupa ir {top_groups[0].lower()}, un tas parāda modeļa saistību ar instanču struktūru."


def _build_dataset_takeaway(real_vs_synthetic: pd.DataFrame | None) -> str:
    """Build the short bold takeaway for the dataset-comparison section."""

    real_row = _dataset_row(real_vs_synthetic, "Reālie dati")
    synthetic_row = _dataset_row(real_vs_synthetic, "Sintētiskie dati")
    if real_row is not None and synthetic_row is not None:
        real_accuracy = real_row.get("Precizitāte")
        synthetic_improvement = synthetic_row.get("Uzlabojums pret single best")
        if pd.notna(real_accuracy) and pd.notna(synthetic_improvement):
            return (
                f"Reālajās instancēs precizitāte ir augsta ({_format_numeric(real_accuracy, digits=4)}), "
                "bet tas jālasa piesardzīgi: mērķa klases un datu avots šajā eksperimentā ir cieši saistīti."
            )
    return "Reālo un sintētisko datu salīdzinājums parāda, ka ieguvums no algoritmu izvēles nav vienāds visās instanču grupās."


def _dataset_row(frame: pd.DataFrame | None, dataset_label: str) -> pd.Series | None:
    """Return one dataset-specific row from the real-vs-synthetic summary."""

    if frame is None or frame.empty or "Datu kopa" not in frame.columns:
        return None
    rows = frame[frame["Datu kopa"] == dataset_label]
    if rows.empty:
        return None
    return rows.iloc[0]


def _summary_value(summary_frame: pd.DataFrame | None, label: str) -> object | None:
    """Look up one scalar value from the summary table."""

    if summary_frame is None or summary_frame.empty:
        return None
    if "Rādītājs" not in summary_frame.columns or "Vērtība" not in summary_frame.columns:
        return None
    rows = summary_frame[summary_frame["Rādītājs"] == label]
    if rows.empty:
        return None
    return _json_safe_value(rows.iloc[0]["Vērtība"])


def _row_value(frame: pd.DataFrame | None, row_index: int, column: str) -> object | None:
    """Read one scalar value from a dataframe row when available."""

    if frame is None or frame.empty or column not in frame.columns or row_index >= len(frame.index):
        return None
    return _json_safe_value(frame.iloc[row_index][column])


def _format_numeric(value: object | None, *, digits: int) -> str:
    """Format one numeric value for dashboard cards."""

    if value is None:
        return "Nav datu"
    try:
        return f"{float(value):.{digits}f}".replace(".", ",")
    except (TypeError, ValueError):
        return str(value)


def build_mixed_dataset_state(workspace_root: str | Path) -> dict[str, Any]:
    """Build the read-only mixed synthetic/real dataset dashboard state."""

    paths = ReportLoaderPaths.from_workspace(workspace_root)
    selection_dataset = _safe_read_csv(paths.mixed_selection_dataset_csv)
    run_summary = _load_json_file(paths.mixed_selection_run_summary_json)
    evaluation_summary = _safe_read_csv(paths.full_selection_evaluation_summary_csv)
    evaluation_run_summary = _load_json_file(paths.full_selection_evaluation_run_summary_json)

    available = selection_dataset is not None
    selector_metrics = _build_mixed_selector_metrics(evaluation_run_summary, evaluation_summary)
    overview = _build_mixed_overview(selection_dataset, run_summary, selector_metrics)
    counts_by_dataset_type = _build_dataset_type_counts(selection_dataset)
    best_solver_distribution = _build_best_solver_distribution(selection_dataset)

    return {
        "available": available,
        "empty_state": (
            "No mixed selection dataset found yet. Run "
            "`python -m src.selection.build_selection_dataset_full` after the real and synthetic studies finish."
        ),
        "scope": {
            "title": "Mixed Dataset Results",
            "description": (
                "Read-only mixed synthetic/real artifacts from data/processed/selection_dataset_full.csv "
                "and data/results/full_selection. Source real, synthetic, demo, and report artifacts remain "
                "in separate folders."
            ),
            "selection_dataset": "data/processed/selection_dataset_full.csv",
            "selector_results_folder": "data/results/full_selection",
        },
        "overview": overview,
        "counts_by_dataset_type": counts_by_dataset_type,
        "best_solver_distribution": best_solver_distribution,
        "selector_metrics": selector_metrics,
        "preview_rows": _mixed_preview_rows(selection_dataset),
        "source_artifacts": _build_mixed_source_artifacts(paths),
        "artifacts": _build_mixed_artifacts(paths),
    }


def build_report_artifact_specs(workspace_root: str | Path) -> list[dict[str, Any]]:
    """Return additional report artifact specs for the dashboard browser."""

    paths = ReportLoaderPaths.from_workspace(workspace_root)
    return [
        _artifact_spec("report_solver_support_summary", "reports", "Solver Support Summary", paths.solver_support_summary_csv, "csv"),
        _artifact_spec(
            "report_solver_support_summary_markdown",
            "reports",
            "Markdown Report",
            paths.solver_support_summary_markdown,
            "markdown",
        ),
        _artifact_spec(
            "real_current_features",
            "real_current",
            "Feature Table",
            paths.real_current_features_csv,
            "csv",
        ),
        _artifact_spec(
            "real_current_benchmark_results",
            "real_current",
            "Benchmark Results",
            paths.real_current_benchmark_csv,
            "csv",
        ),
        _artifact_spec(
            "real_current_selection_dataset",
            "real_current",
            "Selection Dataset",
            paths.real_current_selection_dataset_csv,
            "csv",
        ),
        _artifact_spec(
            "real_current_selector_summary",
            "real_current",
            "Selector Evaluation Summary",
            paths.real_current_selector_summary_csv,
            "csv",
        ),
        _artifact_spec(
            "real_current_compatibility_matrix",
            "real_current",
            "Solver Compatibility Matrix",
            paths.real_current_compatibility_matrix_csv,
            "csv",
        ),
        _artifact_spec(
            "real_current_summary_markdown",
            "real_current",
            "Markdown Summary",
            paths.real_current_summary_markdown,
            "markdown",
        ),
        _artifact_spec(
            "synthetic_study_features",
            "synthetic_study",
            "Feature Table",
            paths.synthetic_study_features_csv,
            "csv",
        ),
        _artifact_spec(
            "synthetic_study_benchmark_results",
            "synthetic_study",
            "Benchmark Results",
            paths.synthetic_study_benchmark_csv,
            "csv",
        ),
        _artifact_spec(
            "synthetic_study_selection_dataset",
            "synthetic_study",
            "Selection Dataset",
            paths.synthetic_study_selection_dataset_csv,
            "csv",
        ),
        _artifact_spec(
            "synthetic_study_selector_summary",
            "synthetic_study",
            "Selector Evaluation Summary",
            paths.synthetic_study_selector_summary_csv,
            "csv",
        ),
        _artifact_spec(
            "synthetic_study_summary_markdown",
            "synthetic_study",
            "Markdown Summary",
            paths.synthetic_study_summary_markdown,
            "markdown",
        ),
        _artifact_spec(
            "mixed_selection_dataset",
            "mixed",
            "Mixed Selection Dataset",
            paths.mixed_selection_dataset_csv,
            "csv",
        ),
        _artifact_spec(
            "mixed_combined_benchmarks",
            "mixed",
            "Combined Benchmark Results",
            paths.full_selection_combined_benchmark_csv,
            "csv",
        ),
        _artifact_spec(
            "mixed_selector_evaluation",
            "mixed",
            "Selector Evaluation",
            paths.full_selection_evaluation_csv,
            "csv",
        ),
        _artifact_spec(
            "mixed_selector_evaluation_summary",
            "mixed",
            "Selector Evaluation Summary",
            paths.full_selection_evaluation_summary_csv,
            "csv",
        ),
        _artifact_spec(
            "mixed_selector_summary_markdown",
            "mixed",
            "Markdown Summary",
            paths.full_selection_evaluation_summary_markdown,
            "markdown",
        ),
        _artifact_spec(
            "mixed_feature_importance",
            "mixed",
            "Feature Importance",
            paths.full_selection_feature_importance_csv,
            "csv",
        ),
    ]


def _build_report_overview(
    *,
    paths: ReportLoaderPaths,
    run_summary: dict[str, Any] | None,
    report_scope: str,
    solver_comparison: pd.DataFrame | None,
    solver_support_summary: pd.DataFrame | None,
    selector_vs_baselines: pd.DataFrame | None,
    feature_importance_summary: pd.DataFrame | None,
    win_counts: pd.DataFrame | None,
    average_objective: pd.DataFrame | None,
    markdown_reports: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build concise thesis-report summary metrics."""

    scope_counts = _instance_counts_by_scope(solver_comparison)
    selector_row = _report_row_by_method(selector_vs_baselines, "selector")
    best_winner = _best_solver_from_win_counts(win_counts, solver_comparison)
    best_objective = _best_solver_from_average_objective(average_objective, solver_comparison)
    top_feature = _top_feature_from_report(feature_importance_summary)
    settings = run_summary.get("settings", {}) if isinstance(run_summary, dict) else {}
    support_status_counts = _support_status_counts(solver_support_summary)

    return {
        "report_scope": report_scope,
        "generated_at": _json_safe_value(run_summary.get("generated_at")) if isinstance(run_summary, dict) else None,
        "configured_scope": _json_safe_value(settings.get("result_scope")) if isinstance(settings, dict) else None,
        "synthetic_instances": scope_counts.get("synthetic", 0),
        "real_instances": scope_counts.get("real", 0),
        "instance_counts_by_scope": [{"result_scope": key, "instances": value} for key, value in scope_counts.items()],
        "solver_count": _count_unique_solvers(solver_comparison),
        "solver_rows": len(solver_comparison.index) if solver_comparison is not None else 0,
        "support_rows": len(solver_support_summary.index) if solver_support_summary is not None else 0,
        "selector_rows": len(selector_vs_baselines.index) if selector_vs_baselines is not None else 0,
        "best_win_solver": best_winner.get("solver_name"),
        "best_win_count": best_winner.get("win_count"),
        "best_average_objective_solver": best_objective.get("solver_name"),
        "best_average_objective": best_objective.get("average_objective"),
        "mean_feasible_coverage_ratio": _numeric_mean(solver_comparison, "feasible_coverage_ratio"),
        "mean_valid_feasible_coverage_ratio": _numeric_mean(
            solver_comparison,
            "valid_feasible_coverage_ratio",
            fallback_column="coverage_ratio",
        ),
        "selector_average_objective": _json_safe_value(selector_row.get("average_objective")),
        "selector_gap_vs_virtual_best": _json_safe_value(selector_row.get("objective_gap_vs_virtual_best")),
        "selector_classification_accuracy": _json_safe_value(selector_row.get("classification_accuracy")),
        "top_feature": top_feature.get("source_feature"),
        "top_feature_importance": top_feature.get("importance"),
        "support_status_counts": support_status_counts,
        "csv_report_count": _count_existing_files(paths.reports_dir, ".csv"),
        "markdown_report_count": len(markdown_reports),
        "interpretation_note": (
            "Objectives are compared only on valid feasible rows. Feasible coverage and solver support status "
            "are reported separately from average objective quality."
        ),
    }


def _build_mixed_overview(
    selection_dataset: pd.DataFrame | None,
    run_summary: dict[str, Any] | None,
    selector_metrics: dict[str, Any],
) -> dict[str, Any]:
    """Build compact mixed-dataset overview cards."""

    rows_by_type = _value_counts(selection_dataset, "dataset_type")
    best_solver_count = (
        int(selection_dataset["best_solver"].dropna().astype(str).nunique())
        if selection_dataset is not None and "best_solver" in selection_dataset.columns
        else 0
    )
    labeled_instances = (
        int(selection_dataset["best_solver"].dropna().count())
        if selection_dataset is not None and "best_solver" in selection_dataset.columns
        else 0
    )
    settings = run_summary.get("settings", {}) if isinstance(run_summary, dict) else {}
    results = run_summary.get("results", {}) if isinstance(run_summary, dict) else {}

    return {
        "selection_rows": int(len(selection_dataset.index)) if selection_dataset is not None else 0,
        "labeled_instances": labeled_instances,
        "synthetic_instances": rows_by_type.get("synthetic", 0),
        "real_instances": rows_by_type.get("real", 0),
        "dataset_type_count": len(rows_by_type),
        "distinct_best_solvers": best_solver_count,
        "average_eligible_solvers": _numeric_mean(selection_dataset, "benchmark_eligible_solver_count"),
        "instances_without_eligible_solver": _count_numeric_matches(
            selection_dataset,
            "benchmark_eligible_solver_count",
            0,
        ),
        "target_policy": _json_safe_value(settings.get("target_policy")) if isinstance(settings, dict) else None,
        "generated_at": _json_safe_value(run_summary.get("generated_at")) if isinstance(run_summary, dict) else None,
        "feature_schema_policy": _json_safe_value(settings.get("feature_schema_policy"))
        if isinstance(settings, dict)
        else None,
        "common_feature_column_count": _nested_value(results, "feature_schema", "common_feature_column_count"),
        "selector_available": bool(selector_metrics.get("available")),
        "selector_classification_accuracy": _nested_value(selector_metrics, "overall", "classification_accuracy"),
        "selector_regret_vs_virtual_best": _nested_value(selector_metrics, "overall", "regret_vs_virtual_best"),
        "selector_delta_vs_single_best": _nested_value(selector_metrics, "overall", "delta_vs_single_best"),
        "interpretation_note": (
            "The mixed target excludes unsupported, failed, and not-configured solver rows before selecting "
            "the deterministic best solver label."
        ),
    }


def _build_dataset_type_counts(selection_dataset: pd.DataFrame | None) -> list[dict[str, Any]]:
    """Summarize mixed selection rows by dataset type."""

    if selection_dataset is None or selection_dataset.empty or "dataset_type" not in selection_dataset.columns:
        return []

    rows: list[dict[str, Any]] = []
    for dataset_type, group in selection_dataset.groupby("dataset_type", dropna=False, sort=True):
        best_solver = group["best_solver"] if "best_solver" in group.columns else pd.Series(dtype=object)
        rows.append(
            {
                "dataset_type": _json_safe_value(dataset_type),
                "selection_rows": int(len(group.index)),
                "labeled_instances": int(best_solver.dropna().count()),
                "distinct_best_solvers": int(best_solver.dropna().astype(str).nunique()),
                "average_eligible_solvers": _json_safe_value(
                    pd.to_numeric(group.get("benchmark_eligible_solver_count"), errors="coerce").mean()
                    if "benchmark_eligible_solver_count" in group.columns
                    else None
                ),
                "instances_without_eligible_solver": _count_numeric_matches(
                    group,
                    "benchmark_eligible_solver_count",
                    0,
                ),
            }
        )
    return rows


def _build_best_solver_distribution(selection_dataset: pd.DataFrame | None) -> list[dict[str, Any]]:
    """Return deterministic best-solver counts by dataset type."""

    if (
        selection_dataset is None
        or selection_dataset.empty
        or "dataset_type" not in selection_dataset.columns
        or "best_solver" not in selection_dataset.columns
    ):
        return []

    frame = selection_dataset.copy()
    frame["best_solver"] = frame["best_solver"].fillna("missing").astype(str)
    counts = (
        frame.groupby(["dataset_type", "best_solver"], dropna=False)
        .size()
        .reset_index(name="count")
        .sort_values(["dataset_type", "count", "best_solver"], ascending=[True, False, True], kind="mergesort")
    )
    return _records(counts.head(30))


def _build_mixed_selector_metrics(
    evaluation_run_summary: dict[str, Any] | None,
    evaluation_summary: pd.DataFrame | None,
) -> dict[str, Any]:
    """Extract overall and by-dataset selector metrics from full-selection artifacts."""

    overall = _selector_overall_from_run_summary(evaluation_run_summary)
    by_dataset_type = _selector_by_dataset_type_from_run_summary(evaluation_run_summary)

    if not overall:
        overall = _selector_overall_from_summary_table(evaluation_summary)
    if not by_dataset_type:
        by_dataset_type = _selector_by_dataset_type_from_summary_table(evaluation_summary)

    rows: list[dict[str, Any]] = []
    if overall:
        rows.append({"dataset_type": "all", **overall})
    rows.extend(by_dataset_type)

    return {
        "available": bool(rows),
        "empty_state": (
            "Mixed selector metrics are not available yet. Run "
            "`python -m src.selection.train_selector --full-dataset` and "
            "`python -m src.selection.evaluate_selector --full-dataset`."
        ),
        "overall": overall,
        "by_dataset_type": by_dataset_type,
        "rows": rows,
    }


def _selector_overall_from_run_summary(run_summary: dict[str, Any] | None) -> dict[str, Any]:
    """Extract full-selection aggregate metrics from the run summary."""

    results = run_summary.get("results", {}) if isinstance(run_summary, dict) else {}
    if not isinstance(results, dict):
        return {}

    return _clean_metric_row(
        {
            "single_best_solver_name": results.get("single_best_solver_name"),
            "classification_accuracy": results.get("classification_accuracy"),
            "balanced_accuracy": results.get("balanced_accuracy"),
            "average_selected_objective": results.get("average_selected_objective"),
            "average_virtual_best_objective": results.get("average_virtual_best_objective"),
            "average_single_best_objective": results.get("average_single_best_objective"),
            "regret_vs_virtual_best": results.get("regret_vs_virtual_best"),
            "delta_vs_single_best": results.get("delta_vs_single_best"),
            "num_validation_splits": results.get("num_validation_splits"),
        }
    )


def _selector_by_dataset_type_from_run_summary(run_summary: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Extract full-selection dataset-type metrics from the run summary."""

    results = run_summary.get("results", {}) if isinstance(run_summary, dict) else {}
    metrics = results.get("metrics_by_dataset_type") if isinstance(results, dict) else None
    if not isinstance(metrics, dict):
        return []

    rows: list[dict[str, Any]] = []
    for dataset_type, values in sorted(metrics.items()):
        if not isinstance(values, dict):
            continue
        rows.append(
            {
                "dataset_type": str(dataset_type),
                **_clean_metric_row(
                    {
                        "classification_accuracy": values.get("classification_accuracy"),
                        "balanced_accuracy": values.get("balanced_accuracy"),
                        "average_selected_objective": values.get("average_selected_objective"),
                        "average_virtual_best_objective": values.get("average_virtual_best_objective"),
                        "average_single_best_objective": values.get("average_single_best_objective"),
                        "regret_vs_virtual_best": values.get("regret_vs_virtual_best"),
                        "delta_vs_single_best": values.get("delta_vs_single_best"),
                    }
                ),
            }
        )
    return rows


def _selector_overall_from_summary_table(frame: pd.DataFrame | None) -> dict[str, Any]:
    """Extract aggregate selector metrics from a summary CSV."""

    if frame is None or frame.empty:
        return {}
    source = frame
    if "summary_row_type" in source.columns:
        matches = source[source["summary_row_type"].astype(str) == "aggregate_mean"]
        if not matches.empty:
            source = matches
    if source.empty:
        return {}
    row = source.iloc[0].to_dict()
    return _clean_metric_row(
        {
            "single_best_solver_name": row.get("single_best_solver_name"),
            "classification_accuracy": row.get("classification_accuracy"),
            "balanced_accuracy": row.get("balanced_accuracy"),
            "average_selected_objective": row.get("average_selected_objective"),
            "average_virtual_best_objective": row.get("average_virtual_best_objective"),
            "average_single_best_objective": row.get("average_single_best_objective"),
            "regret_vs_virtual_best": row.get("regret_vs_virtual_best"),
            "delta_vs_single_best": row.get("delta_vs_single_best"),
            "num_validation_splits": len(frame.index),
        }
    )


def _selector_by_dataset_type_from_summary_table(frame: pd.DataFrame | None) -> list[dict[str, Any]]:
    """Extract by-dataset selector metrics from a summary CSV."""

    if frame is None or frame.empty or "dataset_type" not in frame.columns:
        return []

    source = frame
    if "summary_row_type" in source.columns:
        matches = source[source["summary_row_type"].astype(str).isin(["aggregate_dataset_type_mean", "dataset_type"])]
        if not matches.empty:
            source = matches

    rows: list[dict[str, Any]] = []
    for dataset_type, group in source.groupby("dataset_type", dropna=False, sort=True):
        rows.append(
            {
                "dataset_type": _json_safe_value(dataset_type),
                **_clean_metric_row(
                    {
                        "classification_accuracy": _numeric_series_mean(group.get("classification_accuracy")),
                        "balanced_accuracy": _numeric_series_mean(group.get("balanced_accuracy")),
                        "average_selected_objective": _numeric_series_mean(group.get("average_selected_objective")),
                        "average_virtual_best_objective": _numeric_series_mean(
                            group.get("average_virtual_best_objective")
                        ),
                        "average_single_best_objective": _numeric_series_mean(
                            group.get("average_single_best_objective")
                        ),
                        "regret_vs_virtual_best": _numeric_series_mean(group.get("regret_vs_virtual_best")),
                        "delta_vs_single_best": _numeric_series_mean(group.get("delta_vs_single_best")),
                    }
                ),
            }
        )
    return rows


def _clean_metric_row(row: dict[str, object]) -> dict[str, Any]:
    """Remove fully empty metric entries while preserving explicit zero values."""

    return {key: _json_safe_value(value) for key, value in row.items() if _json_safe_value(value) is not None}


def _mixed_preview_rows(selection_dataset: pd.DataFrame | None) -> list[dict[str, Any]]:
    """Return compact mixed-dataset preview rows."""

    return _report_table_records(
        selection_dataset,
        [
            "dataset_type",
            "instance_name",
            "num_teams",
            "num_slots",
            "best_solver",
            "benchmark_solver_support_coverage",
            "benchmark_eligible_solver_count",
            "benchmark_best_solver_support_status",
            "benchmark_best_solver_scoring_status",
            "benchmark_best_solver_mean_objective",
        ],
        limit=18,
    )


def _build_thesis_report_artifacts(paths: ReportLoaderPaths) -> dict[str, dict[str, Any]]:
    """Return report artifact descriptions for the dashboard."""

    return {
        "report_folder": _describe_path(paths.workspace_root, paths.reports_dir),
        "solver_comparison_csv": _describe_path(paths.workspace_root, paths.solver_comparison_csv),
        "solver_comparison_markdown": _describe_path(paths.workspace_root, paths.solver_comparison_markdown),
        "solver_support_summary_csv": _describe_path(paths.workspace_root, paths.solver_support_summary_csv),
        "solver_support_summary_markdown": _describe_path(
            paths.workspace_root,
            paths.solver_support_summary_markdown,
        ),
        "solver_win_counts_csv": _describe_path(paths.workspace_root, paths.solver_win_counts_csv),
        "solver_win_counts_markdown": _describe_path(paths.workspace_root, paths.solver_win_counts_markdown),
        "average_objective_csv": _describe_path(paths.workspace_root, paths.average_objective_csv),
        "average_objective_markdown": _describe_path(paths.workspace_root, paths.average_objective_markdown),
        "average_runtime_csv": _describe_path(paths.workspace_root, paths.average_runtime_csv),
        "average_runtime_markdown": _describe_path(paths.workspace_root, paths.average_runtime_markdown),
        "selector_vs_baselines_csv": _describe_path(paths.workspace_root, paths.selector_vs_baselines_csv),
        "selector_vs_baselines_markdown": _describe_path(paths.workspace_root, paths.selector_vs_baselines_markdown),
        "feature_importance_summary_csv": _describe_path(paths.workspace_root, paths.feature_importance_summary_csv),
        "feature_importance_summary_markdown": _describe_path(
            paths.workspace_root,
            paths.feature_importance_summary_markdown,
        ),
        "thesis_benchmark_report": _describe_path(paths.workspace_root, paths.thesis_benchmark_report_markdown),
        "report_run_summary": _describe_path(paths.workspace_root, paths.thesis_benchmark_report_run_summary_json),
    }


def _build_mixed_artifacts(paths: ReportLoaderPaths) -> dict[str, dict[str, Any]]:
    """Return mixed-dataset artifact descriptions for the dashboard."""

    return {
        "selection_dataset_full": _describe_path(paths.workspace_root, paths.mixed_selection_dataset_csv),
        "selection_dataset_full_run_summary": _describe_path(
            paths.workspace_root,
            paths.mixed_selection_run_summary_json,
        ),
        "combined_benchmark_results": _describe_path(
            paths.workspace_root,
            paths.full_selection_combined_benchmark_csv,
        ),
        "selector_evaluation": _describe_path(paths.workspace_root, paths.full_selection_evaluation_csv),
        "selector_evaluation_summary": _describe_path(
            paths.workspace_root,
            paths.full_selection_evaluation_summary_csv,
        ),
        "selector_evaluation_markdown": _describe_path(
            paths.workspace_root,
            paths.full_selection_evaluation_summary_markdown,
        ),
        "selector_evaluation_run_summary": _describe_path(
            paths.workspace_root,
            paths.full_selection_evaluation_run_summary_json,
        ),
        "feature_importance": _describe_path(paths.workspace_root, paths.full_selection_feature_importance_csv),
    }


def _build_mixed_source_artifacts(paths: ReportLoaderPaths) -> dict[str, dict[str, Any]]:
    """Return source artifact descriptions separated by real and synthetic scope."""

    return {
        "synthetic_study_processed_folder": _describe_path(paths.workspace_root, paths.synthetic_study_processed_dir),
        "synthetic_study_results_folder": _describe_path(paths.workspace_root, paths.synthetic_study_results_dir),
        "synthetic_study_features": _describe_path(paths.workspace_root, paths.synthetic_study_features_csv),
        "synthetic_study_benchmarks": _describe_path(paths.workspace_root, paths.synthetic_study_benchmark_csv),
        "real_current_processed_folder": _describe_path(paths.workspace_root, paths.real_current_processed_dir),
        "real_current_results_folder": _describe_path(paths.workspace_root, paths.real_current_results_dir),
        "real_current_features": _describe_path(paths.workspace_root, paths.real_current_features_csv),
        "real_current_benchmarks": _describe_path(paths.workspace_root, paths.real_current_benchmark_csv),
    }


def _load_markdown_reports(workspace_root: Path, markdown_paths: list[Path]) -> list[dict[str, Any]]:
    """Load compact previews for generated Markdown reports."""

    reports: list[dict[str, Any]] = []
    for path in markdown_paths:
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        reports.append(
            {
                "file_name": path.name,
                "path": _relative_path(workspace_root, path),
                "title": _labelize(path.stem),
                "text": text[:MARKDOWN_PREVIEW_CHARS],
                "total_chars": len(text),
                "shown_chars": min(len(text), MARKDOWN_PREVIEW_CHARS),
                "truncated": len(text) > MARKDOWN_PREVIEW_CHARS,
            }
        )
    return reports


def _resolve_report_scope(
    run_summary: dict[str, Any] | None,
    solver_comparison: pd.DataFrame | None,
    selector_vs_baselines: pd.DataFrame | None,
) -> str:
    """Resolve the report scope from metadata or table columns."""

    if isinstance(run_summary, dict):
        settings = run_summary.get("settings", {})
        if isinstance(settings, dict) and settings.get("resolved_report_scope"):
            return str(settings["resolved_report_scope"])

    scopes: set[str] = set()
    for frame in (solver_comparison, selector_vs_baselines):
        if frame is not None and "result_scope" in frame.columns:
            scopes.update(frame["result_scope"].dropna().astype(str).tolist())
    if not scopes:
        return "unknown"
    return sorted(scopes)[0] if len(scopes) == 1 else "mixed"


def _report_table_records(frame: pd.DataFrame | None, columns: list[str], *, limit: int) -> list[dict[str, Any]]:
    """Return JSON-safe records for selected columns."""

    if frame is None or frame.empty:
        return []
    available_columns = [column for column in columns if column in frame.columns]
    if not available_columns:
        return []
    return _records(frame.loc[:, available_columns].head(limit))


def _instance_counts_by_scope(solver_comparison: pd.DataFrame | None) -> dict[str, int]:
    """Return max recorded instance count per report scope."""

    if solver_comparison is None or solver_comparison.empty or "result_scope" not in solver_comparison.columns:
        return {}
    count_column = "num_instances_total" if "num_instances_total" in solver_comparison.columns else "num_instances_solved"
    if count_column not in solver_comparison.columns:
        return {}
    frame = solver_comparison.copy()
    frame[count_column] = pd.to_numeric(frame[count_column], errors="coerce")
    grouped = frame.groupby("result_scope", dropna=False)[count_column].max().dropna()
    return {str(scope): int(value) for scope, value in grouped.sort_index().items()}


def _support_status_counts(solver_support_summary: pd.DataFrame | None) -> dict[str, int]:
    """Count support-status rows across report summaries."""

    if (
        solver_support_summary is None
        or solver_support_summary.empty
        or "solver_support_status" not in solver_support_summary.columns
    ):
        return {}
    value_column = "num_rows" if "num_rows" in solver_support_summary.columns else None
    counts: dict[str, int] = {}
    for status, group in solver_support_summary.groupby("solver_support_status", dropna=False):
        if value_column is None:
            counts[str(status)] = int(len(group.index))
        else:
            counts[str(status)] = int(pd.to_numeric(group[value_column], errors="coerce").fillna(0).sum())
    return dict(sorted(counts.items()))


def _best_solver_from_win_counts(
    win_counts: pd.DataFrame | None,
    solver_comparison: pd.DataFrame | None,
) -> dict[str, Any]:
    """Return the solver with the highest report win count."""

    source = win_counts if win_counts is not None and not win_counts.empty else solver_comparison
    if source is None or source.empty or "win_count" not in source.columns:
        return {}

    frame = source.copy()
    frame["win_count"] = pd.to_numeric(frame["win_count"], errors="coerce")
    name_column = "solver_name" if "solver_name" in frame.columns else "solver_registry_name"
    frame = frame.dropna(subset=["win_count"]).sort_values(
        by=["win_count", name_column],
        ascending=[False, True],
        kind="mergesort",
    )
    if frame.empty:
        return {}
    row = frame.iloc[0]
    return {
        "solver_name": _json_safe_value(_first_non_empty(row.get("solver_name"), row.get("solver_registry_name"))),
        "win_count": _json_safe_value(row.get("win_count")),
    }


def _best_solver_from_average_objective(
    average_objective: pd.DataFrame | None,
    solver_comparison: pd.DataFrame | None,
) -> dict[str, Any]:
    """Return the solver with the lowest valid average objective."""

    source = average_objective if average_objective is not None and not average_objective.empty else solver_comparison
    if source is None or source.empty:
        return {}

    objective_column = (
        "average_objective_valid_feasible"
        if "average_objective_valid_feasible" in source.columns
        else "average_objective"
    )
    if objective_column not in source.columns:
        return {}

    frame = source.copy()
    frame[objective_column] = pd.to_numeric(frame[objective_column], errors="coerce")
    name_column = "solver_name" if "solver_name" in frame.columns else "solver_registry_name"
    frame = frame.dropna(subset=[objective_column]).sort_values(
        by=[objective_column, name_column],
        ascending=[True, True],
        kind="mergesort",
    )
    if frame.empty:
        return {}
    row = frame.iloc[0]
    return {
        "solver_name": _json_safe_value(_first_non_empty(row.get("solver_name"), row.get("solver_registry_name"))),
        "average_objective": _json_safe_value(row.get(objective_column)),
    }


def _report_row_by_method(frame: pd.DataFrame | None, method: str) -> dict[str, Any]:
    """Return one row matching a selector comparison method."""

    if frame is None or frame.empty or "method" not in frame.columns:
        return {}
    matches = frame[frame["method"].astype(str).str.casefold() == method.casefold()]
    if matches.empty:
        return {}
    return {column: _json_safe_value(value) for column, value in matches.iloc[0].to_dict().items()}


def _top_feature_from_report(frame: pd.DataFrame | None) -> dict[str, Any]:
    """Return the highest-ranked feature from the report table."""

    if frame is None or frame.empty:
        return {}
    table = frame.copy()
    if "importance_rank" in table.columns:
        table["importance_rank"] = pd.to_numeric(table["importance_rank"], errors="coerce")
        table = table.sort_values(by=["importance_rank"], ascending=[True], kind="mergesort")
    elif "importance" in table.columns:
        table["importance"] = pd.to_numeric(table["importance"], errors="coerce")
        table = table.sort_values(by=["importance"], ascending=[False], kind="mergesort")
    row = table.iloc[0]
    return {
        "source_feature": _json_safe_value(_first_non_empty(row.get("source_feature"), row.get("feature"))),
        "importance": _json_safe_value(row.get("importance")),
    }


def _count_unique_solvers(frame: pd.DataFrame | None) -> int:
    """Count unique solver labels in a report table."""

    if frame is None or frame.empty:
        return 0
    column = "solver_registry_name" if "solver_registry_name" in frame.columns else "solver_name"
    if column not in frame.columns:
        return 0
    return int(frame[column].dropna().astype(str).nunique())


def _count_existing_files(folder: Path, suffix: str) -> int:
    """Count generated files in a folder by suffix."""

    if not folder.exists() or not folder.is_dir():
        return 0
    return len([path for path in folder.iterdir() if path.is_file() and path.suffix == suffix])


def _value_counts(frame: pd.DataFrame | None, column: str) -> dict[str, int]:
    """Return sorted value counts for one column."""

    if frame is None or frame.empty or column not in frame.columns:
        return {}
    counts = frame[column].fillna("missing").astype(str).value_counts().to_dict()
    return {str(key): int(value) for key, value in sorted(counts.items())}


def _numeric_mean(
    frame: pd.DataFrame | None,
    column: str,
    *,
    fallback_column: str | None = None,
) -> float | None:
    """Return a numeric column mean when available."""

    if frame is None or frame.empty:
        return None
    target_column = column if column in frame.columns else fallback_column
    if target_column is None or target_column not in frame.columns:
        return None
    return _json_safe_value(pd.to_numeric(frame[target_column], errors="coerce").mean())  # type: ignore[return-value]


def _numeric_series_mean(series: pd.Series | None) -> float | None:
    """Return a numeric series mean when available."""

    if series is None:
        return None
    return _json_safe_value(pd.to_numeric(series, errors="coerce").mean())  # type: ignore[return-value]


def _count_numeric_matches(frame: pd.DataFrame | None, column: str, target: int) -> int:
    """Count rows where a numeric column equals a target value."""

    if frame is None or frame.empty or column not in frame.columns:
        return 0
    values = pd.to_numeric(frame[column], errors="coerce")
    return int((values == target).sum())


def _nested_value(mapping: dict[str, Any], *keys: str) -> Any:
    """Return a nested dictionary value if all keys exist."""

    value: Any = mapping
    for key in keys:
        if not isinstance(value, dict):
            return None
        value = value.get(key)
    return _json_safe_value(value)


def _first_non_empty(*values: object) -> object | None:
    """Return the first non-empty scalar value."""

    for value in values:
        clean = _json_safe_value(value)
        if clean is None:
            continue
        if str(clean).strip():
            return clean
    return None


def _safe_read_csv(path: Path) -> pd.DataFrame | None:
    """Read a CSV file when it exists and is non-empty."""

    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        return pd.read_csv(path)
    except (FileNotFoundError, pd.errors.EmptyDataError):
        return None


def _load_json_file(path: Path) -> dict[str, Any] | None:
    """Load one JSON file when available."""

    if not path.exists() or path.stat().st_size == 0:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _describe_path(workspace_root: Path, path: Path) -> dict[str, Any]:
    """Describe a generated artifact path without opening large files."""

    exists = path.exists()
    payload: dict[str, Any] = {
        "path": _relative_path(workspace_root, path),
        "exists": exists,
        "path_type": "directory" if exists and path.is_dir() else "file",
    }
    if exists and path.is_file():
        stat = path.stat()
        payload.update(
            {
                "modified_at": _json_safe_value(pd.Timestamp.fromtimestamp(stat.st_mtime).isoformat()),
                "size_bytes": int(stat.st_size),
                "size": _format_file_size(stat.st_size),
            }
        )
    elif exists and path.is_dir():
        payload["entry_count"] = len(list(path.iterdir()))
    return payload


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    """Convert a dataframe to JSON-safe records."""

    records: list[dict[str, Any]] = []
    for row in frame.to_dict(orient="records"):
        records.append({str(key): _json_safe_value(value) for key, value in row.items()})
    return records


def _json_safe_value(value: object) -> object:
    """Convert pandas/numpy scalar values into JSON-safe Python values."""

    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return float(value)
    if hasattr(value, "item"):
        try:
            return _json_safe_value(value.item())  # type: ignore[no-any-return]
        except (TypeError, ValueError):
            pass
    return value


def _relative_path(workspace_root: Path, path: Path | None) -> str | None:
    """Return a display path relative to the workspace when possible."""

    if path is None:
        return None
    try:
        return path.relative_to(workspace_root).as_posix()
    except ValueError:
        return path.as_posix()


def _format_file_size(size_bytes: int) -> str:
    """Format a byte count for dashboard display."""

    size = float(max(0, size_bytes))
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024.0 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size_bytes} B"


def _labelize(value: str) -> str:
    """Format a file stem as a display label."""

    return str(value).replace("_", " ").title()


def _generated_file_url(workspace_root: Path, path: Path) -> str:
    """Return one dashboard URL for a generated file inside the workspace."""

    relative = _relative_path(workspace_root, path)
    return f"/generated/{relative}" if relative is not None else ""


def _artifact_spec(
    artifact_id: str,
    scope: str,
    artifact_type: str,
    path: Path,
    preview_kind: str,
) -> dict[str, Any]:
    """Build one artifact-browser whitelist entry."""

    return {
        "artifact_id": artifact_id,
        "scope": scope,
        "artifact_type": artifact_type,
        "path": path,
        "preview_kind": preview_kind,
    }
