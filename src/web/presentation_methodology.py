"""Build the methodology section for the thesis-defense dashboard."""

from __future__ import annotations

from typing import Any

import pandas as pd


METHODOLOGY_FIGURE_ORDER: tuple[str, ...] = ()


def build_methodology_section(
    *,
    selection_dataset: pd.DataFrame | None,
    combined_benchmark: pd.DataFrame | None,
    dataset_summary: pd.DataFrame | None,
    evaluation_run_summary: dict[str, Any] | None,
    figure_payloads: list[dict[str, Any]],
    intro: str,
) -> dict[str, Any]:
    """Build the dashboard section that explains how to read the results."""

    real_instance_count = _summary_count(dataset_summary, "Reālo instanču skaits")
    synthetic_instance_count = _summary_count(dataset_summary, "Sintētisko instanču skaits")
    observed_target_count = _observed_target_count(selection_dataset)
    portfolio_solver_count = _portfolio_solver_count(combined_benchmark)
    best_solver_tracks_source = _best_solver_tracks_dataset_source(selection_dataset)
    validation_label = _validation_label(evaluation_run_summary)

    cards = [
        {
            "label": "best_solver klašu tvērums",
            "value": (
                f"{observed_target_count} aktīvas klases"
                if observed_target_count is not None
                else "Nav datu"
            ),
            "description": (
                "Gala atlases uzdevumā parādās tikai risinātāji, kas kādā instancē kļuva par best_solver."
            ),
        },
        {
            "label": "Reģistrētais portfelis",
            "value": (
                f"{portfolio_solver_count} reģistrēti varianti"
                if portfolio_solver_count is not None
                else "Jāpārbauda"
            ),
            "description": "Timefold ir reģistrēts kā integrācijas saskarne, bet šajā konfigurācijā nav aktīvs salīdzinājums.",
        },
        {
            "label": "Datu avota efekts",
            "value": "Jāņem vērā" if best_solver_tracks_source else "Jāpārbauda",
            "description": (
                "Reālās un sintētiskās instances var netieši atšķirties arī pēc strukturālajām pazīmēm."
            ),
        },
        {
            "label": "Validācijas lasījums",
            "value": validation_label,
            "description": (
                "Pašreizējā validācija ir iekšēji korekta, bet nākamais spēcīgais tests būtu "
                "source-holdout scenārijs."
            ),
        },
    ]

    return {
        "id": "methodology",
        "title": "Interpretācija un ierobežojumi",
        "intro": intro,
        "takeaway": _takeaway(best_solver_tracks_source, observed_target_count, portfolio_solver_count),
        "cards": cards,
        "highlights": _interpretation_notes(),
        "table_title": "Eksperimenta ierobežojumu kopsavilkums",
        "table_note": (
            "Sadaļa atbilst darba praktiskās daļas noslēgumam, kur rezultāti interpretēti tikai "
            "konkrētās datu kopas, atskaites portfeļa un vērtēšanas tvēruma robežās."
        ),
        "table_rows": _review_rows(real_instance_count, synthetic_instance_count),
        "figures": _select_methodology_figures(figure_payloads),
    }


def _interpretation_notes() -> list[str]:
    return [
        (
            "Aizstāvēšanā drošākā interpretācija: rezultāti parāda algoritmu izvēles pieejas "
            "realizējamību šajā eksperimentālajā uzstādījumā."
        ),
        (
            "Gala mērķī faktiski ir 2 aktīvas best_solver klases: reālajām instancēm simulētā rūdīšana, "
            "sintētiskajām instancēm CP-SAT."
        ),
        (
            "Datu kopa nav pilnīgi līdzsvarota pēc izcelsmes: 54 instances ir reālas un 180 ir sintētiskas."
        ),
        (
            "Timefold šajā eksperimentālajā konfigurācijā nav konfigurēts kā aktīvs veiktspējas salīdzinājuma dalībnieks."
        ),
        (
            "CP-SAT un simulētā rūdīšana ir atskaites risinātāji ar ierobežotu tvērumu, nevis pilns ITC2021 risinātāju portfelis."
        ),
        (
            "Nākamais spēcīgākais tests būtu source-holdout sadalījums vai plašāka reālo instanču pārbaude."
        ),
    ]


def _review_rows(
    real_instance_count: int | None,
    synthetic_instance_count: int | None,
) -> list[dict[str, str]]:
    dataset_text = (
        f"Izmantotas {real_instance_count} reālās un {synthetic_instance_count} sintētiskās instances."
        if real_instance_count is not None and synthetic_instance_count is not None
        else "Jauktā datu kopa apvieno reālo un sintētisko avotu."
    )
    return [
        {
            "Joma": "Datu kopa",
            "Ko tas nozīmē": dataset_text,
            "Ieteiktais uzlabojums": "Pievienot vairāk reālu instanču un source-holdout pārbaudi.",
        },
        {
            "Joma": "Pazīmes",
            "Ko tas nozīmē": (
                "Modeļa ievadē netiek izmantotas objective_, benchmark_, label_, target_, "
                "dataset_, source_, solver_, scoring_ un rezultātu statusa kolonnas."
            ),
            "Ieteiktais uzlabojums": (
                "Pārbaudīt, cik labi tikai strukturālās pazīmes prognozē datu avotu."
            ),
        },
        {
            "Joma": "Risinātāju portfelis",
            "Ko tas nozīmē": (
                "Portfelī reģistrēti 4 risināšanas varianti, bet Timefold nav konfigurēts un diagnostiskā pieeja nav praktisks kalendāra risinātājs."
            ),
            "Ieteiktais uzlabojums": (
                "Pievienot plašāku aktīvu risinātāju portfeli vai pilnībā konfigurētu Timefold risinājumu."
            ),
        },
        {
            "Joma": "best_solver definīcija",
            "Ko tas nozīmē": "Mērķis ir reproducējams, bet nav izvēlēts mehāniski tikai pēc mazākās mērķfunkcijas vērtības.",
            "Ieteiktais uzlabojums": (
                "Palaist jutīguma analīzi ar un bez partially_supported kandidātiem."
            ),
        },
        {
            "Joma": "SBS/VBS un validācija",
            "Ko tas nozīmē": (
                "SBS tiek rēķināts no apmācības daļas, VBS no testa daļas, "
                "tāpēc salīdzinājums nav tieša noplūde."
            ),
            "Ieteiktais uzlabojums": (
                "Ziņot papildu rezultātus pa datu avotiem un grouped/source-holdout dalījumos."
            ),
        },
    ]


def _takeaway(
    best_solver_tracks_source: bool,
    observed_target_count: int | None,
    portfolio_solver_count: int | None,
) -> str:
    if (
        best_solver_tracks_source
        and observed_target_count is not None
        and portfolio_solver_count is not None
    ):
        return (
            "Rezultāti apliecina pieejas realizējamību šajā eksperimentālajā uzstādījumā, bet jāinterpretē piesardzīgi: "
            f"mērķa klasēs parādās {observed_target_count} no "
            f"{portfolio_solver_count} portfelī reģistrētajiem variantiem, "
            "un best_solver cieši sakrīt ar datu avotu."
        )
    return (
        "Rezultāti jālasa kopā ar datu kopas, risinātāju portfeļa un validācijas ierobežojumiem."
    )


def _validation_label(evaluation_run_summary: dict[str, Any] | None) -> str:
    settings = (
        evaluation_run_summary.get("settings", {}) if isinstance(evaluation_run_summary, dict) else {}
    )
    folds = settings.get("cross_validation_folds")
    repeats = settings.get("repeats")
    return f"{repeats}x{folds} krustotā pārbaude" if folds and repeats else "Atkārtota krustotā pārbaude"


def _observed_target_count(selection_dataset: pd.DataFrame | None) -> int | None:
    if (
        selection_dataset is None
        or selection_dataset.empty
        or "best_solver" not in selection_dataset.columns
    ):
        return None
    return int(selection_dataset["best_solver"].dropna().astype(str).nunique())


def _portfolio_solver_count(combined_benchmark: pd.DataFrame | None) -> int | None:
    if combined_benchmark is None or combined_benchmark.empty:
        return None
    solver_column = (
        "solver_registry_name" if "solver_registry_name" in combined_benchmark.columns else "solver_name"
    )
    if solver_column not in combined_benchmark.columns:
        return None
    return int(combined_benchmark[solver_column].dropna().astype(str).nunique())


def _best_solver_tracks_dataset_source(selection_dataset: pd.DataFrame | None) -> bool:
    if (
        selection_dataset is None
        or selection_dataset.empty
        or "dataset_type" not in selection_dataset.columns
        or "best_solver" not in selection_dataset.columns
    ):
        return False

    labels_by_source = (
        selection_dataset.dropna(subset=["dataset_type", "best_solver"])
        .groupby("dataset_type")["best_solver"]
        .nunique()
    )
    return bool(
        not labels_by_source.empty
        and labels_by_source.max() == 1
        and labels_by_source.min() == 1
    )


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


def _select_methodology_figures(figure_payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {item["id"]: item for item in figure_payloads}
    return [by_id[figure_id] for figure_id in METHODOLOGY_FIGURE_ORDER if figure_id in by_id]
