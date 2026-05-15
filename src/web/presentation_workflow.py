"""Build the practical-workflow section for the thesis-defense dashboard."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


EXCLUDED_FEATURE_COLUMNS = {
    "best_solver",
    "dataset_type",
    "instance_name",
}
EXCLUDED_FEATURE_PREFIXES = (
    "objective_",
    "benchmark_",
    "label_",
    "target_",
    "dataset_",
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


def build_workflow_section(
    *,
    selection_dataset: pd.DataFrame | None,
    combined_benchmark: pd.DataFrame | None,
    dataset_summary: pd.DataFrame | None,
    evaluation_run_summary: dict[str, Any] | None,
    workspace_root: Path,
    intro: str,
) -> dict[str, Any]:
    """Build the section that maps the thesis practical part to the implementation."""

    total_instances = _summary_count(dataset_summary, "Kopējais instanču skaits")
    real_instances = _summary_count(dataset_summary, "Reālo instanču skaits")
    synthetic_instances = _summary_count(dataset_summary, "Sintētisko instanču skaits")
    feature_count = _structural_feature_count(selection_dataset)
    solver_count = _portfolio_solver_count(combined_benchmark)
    benchmark_rows = len(combined_benchmark.index) if combined_benchmark is not None else None
    validation_label = _validation_label(evaluation_run_summary)

    return {
        "id": "workflow",
        "title": "Eksperimenta process",
        "intro": intro,
        "takeaway": (
            "Darba praktiskajā daļā aprakstītais process sākas ar datu avotiem un sintētisko "
            "instanču sagatavošanu, turpinās ar XML nolasīšanu un strukturālo pazīmju iegūšanu, "
            "un tikai pēc tam pāriet uz risinātāju statusiem, best_solver mērķi un modeļa novērtēšanu."
        ),
        "cards": _workflow_cards(
            total_instances=total_instances,
            real_instances=real_instances,
            synthetic_instances=synthetic_instances,
            feature_count=feature_count,
            solver_count=solver_count,
            benchmark_rows=benchmark_rows,
            validation_label=validation_label,
        ),
        "highlights": _workflow_principles(),
        "table_title": "Eksperimentālās sistēmas galvenie posmi",
        "table_note": (
            "Tabula atbilst darba praktiskajā nodaļā aprakstītajai reproducējamās eksperimentālās sistēmas secībai."
        ),
        "table_rows": _workflow_rows(feature_count=feature_count, solver_count=solver_count),
        "artifact_table_title": "Darba tekstā izmantotie projekta artefakti",
        "artifact_table_note": (
            "Sarakstā atstāti tikai artefakti, kas tiek izmantoti šajā praktiskās daļas pārskatā."
        ),
        "artifact_rows": _artifact_rows(workspace_root),
        "code_table_title": "Svarīgākie koda faili",
        "code_table_note": (
            "Koda karte sasaista darba praktiskajā nodaļā aprakstītos posmus ar repozitorija failiem."
        ),
        "code_rows": _code_rows(workspace_root),
    }


def _workflow_cards(
    *,
    total_instances: int | None,
    real_instances: int | None,
    synthetic_instances: int | None,
    feature_count: int | None,
    solver_count: int | None,
    benchmark_rows: int | None,
    validation_label: str,
) -> list[dict[str, str]]:
    return [
        {
            "label": "Eksperimenta ķēde",
            "value": "8 posmi",
            "description": "No datu avotiem un XML nolasīšanas līdz rezultātu interpretācijai.",
        },
        {
            "label": "Jauktā datu kopa",
            "value": f"{total_instances} instances" if total_instances is not None else "Nav datu",
            "description": (
                f"{real_instances} reālās un {synthetic_instances} sintētiskās instances."
                if real_instances is not None and synthetic_instances is not None
                else "Datu apjoms tiek nolasīts no sagatavotajām darba tabulām."
            ),
        },
        {
            "label": "Pirms-risināšanas pazīmes",
            "value": f"{feature_count} pazīmes" if feature_count is not None else "Nav datu",
            "description": "Modeļa ievadē paliek tikai strukturāli raksturojumi, nevis benchmark rezultāti.",
        },
        {
            "label": "Portfelis un validācija",
            "value": f"{solver_count or 0} reģistrēti risinātāji, {validation_label}",
            "description": (
                f"Benchmark tabulā saglabātas {benchmark_rows} izpildes rindas."
                if benchmark_rows is not None
                else "Risinātāju izpildes apjoms tiek nolasīts no benchmark artefaktiem."
            ),
        },
    ]


def _workflow_principles() -> list[str]:
    return [
        "Datu avoti ir nošķirti: reālās RobinX/ITC2021 instances un autora ģenerētās sintētiskās instances.",
        "Pazīmes raksturo izmēru, ierobežojumu sastāvu, blīvumu un strukturālo daudzveidību.",
        "best_solver tiek noteikts tikai no derīgiem, skaitliski novērtējamiem un interpretējamiem rezultātiem.",
        "SBS un VBS tiek rēķināti validācijas sadalījuma ietvaros, lai salīdzinājums nebūtu tieša noplūde.",
    ]


def _workflow_rows(feature_count: int | None, solver_count: int | None) -> list[dict[str, str]]:
    feature_text = f"{feature_count} strukturālās pazīmes" if feature_count is not None else "strukturālās pazīmes"
    solver_text = f"{solver_count} risināšanas varianti" if solver_count is not None else "risinātāju portfelis"
    return [
        {
            "Posms": "1. Datu avoti",
            "Darba aprakstā": "Reālās RobinX/ITC2021 instances un sintētiski ģenerētas instances.",
            "UI/pierādījums": "Eksperimentā izmantotās datu kopas sastāva kartītes un attēls.",
        },
        {
            "Posms": "2. XML nolasīšana",
            "Darba aprakstā": "Parseris apstrādā nosaukumtelpas, trūkstošas sadaļas un RobinX struktūru.",
            "UI/pierādījums": "Artefaktu tabulā redzama inventarizācija un pazīmju tabulas.",
        },
        {
            "Posms": "3. Strukturālās pazīmes",
            "Darba aprakstā": f"Instance tiek pārveidota par {feature_text}.",
            "UI/pierādījums": "Eksperimentu rezultātu sadaļa rāda svarīgākās strukturālās pazīmes un pazīmju grupas.",
        },
        {
            "Posms": "4. Risinātāju portfelis",
            "Darba aprakstā": f"Portfelī reģistrēti {solver_text}: diagnostiskā atskaites pieeja, CP-SAT, simulētā rūdīšana un Timefold saskarne.",
            "UI/pierādījums": "Risinātāju lomu sadaļa rāda, ka Timefold nav aktīvs salīdzinājuma dalībnieks.",
        },
        {
            "Posms": "5. Rezultātu interpretācija",
            "Darba aprakstā": "Saglabā statusus, pārklājumu, mērķfunkciju un atšķir partially_supported/not_configured rindas.",
            "UI/pierādījums": "Interpretācijas sadaļa skaidro risinātāju pārklājuma un vērtēšanas nosacījumu nozīmi.",
        },
        {
            "Posms": "6. Jauktā algoritmu izvēles datu kopa",
            "Darba aprakstā": "Katra instance kļūst par vienu rindu ar strukturālām pazīmēm un best_solver mērķi.",
            "UI/pierādījums": "Datu sadaļa rāda reālo/sintētisko kopu un mērķa klašu sadalījumu.",
        },
        {
            "Posms": "7. Modeļa novērtēšana",
            "Darba aprakstā": "Random Forest tiek vērtēts ar atkārtotu stratificētu krustoto pārbaudi.",
            "UI/pierādījums": "Modeļa novērtēšanas sadaļa rāda precizitāti, balanced accuracy, regret un SBS/VBS salīdzinājumu.",
        },
        {
            "Posms": "8. Ierobežojumu nolasījums",
            "Darba aprakstā": "Rezultāti jāsaprot kā pieejas realizējamība konkrētajā uzstādījumā, nevis universāls ITC2021 secinājums.",
            "UI/pierādījums": "Interpretācijas un ierobežojumu sadaļa skaidri nodala realizējamību no vispārināšanas riskiem.",
        },
    ]


def _artifact_rows(workspace_root: Path) -> list[dict[str, str]]:
    specs = [
        ("Jauktā algoritmu izvēles datu kopa", "data/processed/selection_dataset_full.csv"),
        ("Risinātāju benchmark rezultāti", "data/results/full_selection/combined_benchmark_results.csv"),
        ("Modeļa novērtējums", "data/results/full_selection/selector_evaluation_summary.csv"),
        ("Pazīmju nozīmīgums", "data/results/full_selection/feature_importance.csv"),
        ("Darba tabulas", "data/results/thesis_tables"),
        ("Darba attēli", "data/results/figures"),
        ("Reproducēšanas ceļvedis", "docs/reproduction_guide.md"),
        ("Reproducējamības audits", "docs/reproducibility_audit.md"),
    ]
    rows: list[dict[str, str]] = []
    for label, relative_path in specs:
        path = workspace_root / relative_path
        rows.append(
            {
                "Artefakts": label,
                "Ceļš": relative_path,
                "Statuss": "Ir" if path.exists() else "Nav atrasts",
            }
        )
    return rows


def _code_rows(workspace_root: Path) -> list[dict[str, str]]:
    specs = [
        (
            "Datu sagatavošana",
            "src/data_generation/synthetic_generator.py; src/parsers/real_dataset_inventory.py",
            "Sintētisko instanču izveide un reālo RobinX/ITC2021 failu inventarizācija.",
        ),
        (
            "XML nolasīšana",
            "src/parsers/robinx_parser.py",
            "RobinX instances struktūras nolasīšana un pārveidošana iekšējā datu modelī.",
        ),
        (
            "Strukturālās pazīmes",
            "src/features/feature_extractor.py; src/features/build_feature_table.py",
            "Pirms-risināšanas pazīmju iegūšana un pazīmju tabulu sagatavošana.",
        ),
        (
            "Risinātāju portfelis",
            "src/solvers/registry.py; src/solvers/cpsat_solver.py; src/solvers/simulated_annealing_solver.py; src/solvers/random_baseline.py",
            "Portfeļa reģistrs un darbā izmantotie atskaites risināšanas varianti.",
        ),
        (
            "Benchmark izpilde",
            "src/experiments/full_benchmark.py; src/experiments/build_solver_compatibility_matrix.py",
            "Risinātāju izpildes rezultātu un atbalsta statusu sagatavošana salīdzināšanai.",
        ),
        (
            "Algoritmu izvēles datu kopa",
            "src/selection/build_selection_dataset_full.py",
            "Jauktās reālo un sintētisko instanču datu kopas izveide ar best_solver mērķi.",
        ),
        (
            "Modeļa apmācība un novērtēšana",
            "src/selection/modeling.py; src/selection/splitting.py; src/selection/train_selector.py; src/selection/evaluate_selector.py",
            "Nejaušo mežu klasifikatora konfigurācija, validācijas sadalījumi, apmācība un SBS/VBS salīdzinājums.",
        ),
        (
            "Darba tabulas, attēli un UI",
            "src/experiments/thesis_report.py; src/thesis/generate_assets.py; src/thesis/plots.py; src/web/report_loader.py",
            "Praktiskajai daļai vajadzīgo tabulu, attēlu un dashboard datu sagatavošana.",
        ),
    ]
    return [
        {
            "Darba posms": stage,
            "Koda fails": paths,
            "Nozīme": description,
            "Statuss": _paths_status(workspace_root, paths),
        }
        for stage, paths, description in specs
    ]


def _paths_status(workspace_root: Path, paths: str) -> str:
    relative_paths = [Path(item.strip()) for item in paths.split(";")]
    return "Ir" if all((workspace_root / path).exists() for path in relative_paths) else "Nav atrasts"


def _structural_feature_count(selection_dataset: pd.DataFrame | None) -> int | None:
    if selection_dataset is None or selection_dataset.empty:
        return None
    feature_columns = [
        column
        for column in selection_dataset.columns
        if column not in EXCLUDED_FEATURE_COLUMNS
        and not column.startswith(EXCLUDED_FEATURE_PREFIXES)
    ]
    return len(feature_columns)


def _portfolio_solver_count(combined_benchmark: pd.DataFrame | None) -> int | None:
    if combined_benchmark is None or combined_benchmark.empty:
        return None
    solver_column = (
        "solver_registry_name" if "solver_registry_name" in combined_benchmark.columns else "solver_name"
    )
    if solver_column not in combined_benchmark.columns:
        return None
    return int(combined_benchmark[solver_column].dropna().astype(str).nunique())


def _validation_label(evaluation_run_summary: dict[str, Any] | None) -> str:
    settings = (
        evaluation_run_summary.get("settings", {}) if isinstance(evaluation_run_summary, dict) else {}
    )
    folds = settings.get("cross_validation_folds")
    repeats = settings.get("repeats")
    return f"{repeats}x{folds} krustotā pārbaude" if folds and repeats else "atkārtota krustotā pārbaude"


def _summary_count(summary_frame: pd.DataFrame | None, label: str) -> int | None:
    if summary_frame is None or summary_frame.empty:
        return None
    if "Rādītājs" not in summary_frame.columns or "Vērtība" not in summary_frame.columns:
        return None
    rows = summary_frame[summary_frame["Rādītājs"] == label]
    if rows.empty:
        return None
    value = rows.iloc[0]["Vērtība"]
    if pd.isna(value):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
