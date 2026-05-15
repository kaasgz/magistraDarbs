"""Reusable matplotlib plots for thesis-facing presentation exports."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from src.thesis.presentation_catalog import FIGURE_SPECS


PALETTE = {
    "ink": "#22313f",
    "muted": "#6d7d8b",
    "accent": "#1f6f78",
    "accent_soft": "#74a8af",
    "accent_warm": "#d88c5a",
    "accent_gold": "#c9a227",
    "real": "#1f6f78",
    "synthetic": "#d88c5a",
    "grid": "#dfe6eb",
    "surface": "#ffffff",
}

SOLVER_LABELS = {
    "random_baseline": "Nejaušā bāzlīnija",
    "cpsat_solver": "CP-SAT",
    "simulated_annealing_solver": "Simulētā rūdīšana",
    "timefold": "Timefold",
}

DATASET_LABELS = {
    "all": "Jauktā kopa",
    "real": "Reālie dati",
    "synthetic": "Sintētiskie dati",
}

FEATURE_GROUP_LABELS = {
    "size": "Izmērs",
    "density": "Blīvums",
    "constraint_composition": "Ierobežojumi",
    "diversity": "Daudzveidība",
    "objective": "Mērķfunkcija",
}

FEATURE_GROUP_COLORS = {
    "size": "#1f6f78",
    "density": "#74a8af",
    "constraint_composition": "#d88c5a",
    "diversity": "#c9a227",
    "objective": "#8b6f47",
}


def generate_figures(
    *,
    output_dir: str | Path,
    selector_results: pd.DataFrame,
    real_vs_synthetic: pd.DataFrame,
    solver_comparison: pd.DataFrame,
    feature_importance: pd.DataFrame,
    selection_dataset: pd.DataFrame,
    selector_evaluation_summary: pd.DataFrame,
    combined_benchmark: pd.DataFrame,
    selector_evaluation: pd.DataFrame | None = None,
) -> dict[str, Path]:
    """Generate all thesis-facing figures and return their output paths."""

    figures_dir = Path(output_dir)
    figures_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        spec.identifier: figures_dir / spec.file_name
        for spec in FIGURE_SPECS
    }

    plot_selector_performance(selector_results, paths["selector_performance"])
    plot_selector_vs_baselines(selector_evaluation_summary, paths["selector_vs_baselines"])
    plot_solver_comparison(solver_comparison, paths["solver_comparison"])
    plot_solver_runtime(solver_comparison, paths["solver_runtime"])
    plot_feature_importance(feature_importance, paths["feature_importance"])
    plot_real_vs_synthetic(real_vs_synthetic, paths["real_vs_synthetic"])
    plot_solver_win_distribution(selection_dataset, paths["solver_win_distribution"])
    plot_dataset_distribution(selection_dataset, paths["dataset_distribution"])
    plot_best_solver_class_distribution(selection_dataset, paths["best_solver_class_distribution"])
    plot_objective_distribution(selection_dataset, paths["objective_distribution"])
    plot_runtime_distribution(combined_benchmark, paths["runtime_distribution"])
    plot_accuracy_by_dataset_type(selector_results, real_vs_synthetic, paths["accuracy_by_dataset_type"])
    plot_regret_distribution(selector_evaluation_summary, paths["regret_distribution"])
    if selector_evaluation is not None:
        plot_confusion_matrix(selector_evaluation, paths["confusion_matrix"])
    plot_feature_correlation_matrix(selection_dataset, feature_importance, paths["feature_correlation_matrix"])
    plot_constraint_distribution(selection_dataset, paths["constraint_distribution"])
    plot_teams_vs_slots(selection_dataset, paths["teams_vs_slots_plot"])
    plot_constraints_vs_objective(selection_dataset, paths["constraints_vs_objective"])

    return paths


def plot_selector_performance(selector_results: pd.DataFrame, output_path: str | Path) -> None:
    """Plot the four main mixed-model performance metrics."""

    selector_results = _normalize_selector_results_frame(selector_results)
    row = selector_results.iloc[0]
    labels = [
        "Precizitāte",
        "Sabalansētā\nprecizitāte",
        "Regret pret\nvirtual best",
        "Uzlabojums pret\nsingle best",
    ]
    values = [
        _float(row.get("classification_accuracy")),
        _float(row.get("balanced_accuracy")),
        _float(row.get("regret_vs_virtual_best")),
        _float(row.get("improvement_vs_single_best")),
    ]
    colors = [
        PALETTE["accent"],
        PALETTE["accent_soft"],
        PALETTE["accent_warm"],
        PALETTE["accent_gold"],
    ]

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    bars = ax.bar(labels, values, color=colors, edgecolor="white", linewidth=1.2, width=0.64)
    ax.set_title("Modeļa galvenie rādītāji", fontsize=14, loc="left")
    ax.set_ylabel("Vērtība")
    _style_axes(ax)
    for bar, value in zip(bars, values, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.4f}", ha="center", va="bottom", fontsize=9)
    _save_figure(fig, output_path)


def plot_selector_vs_baselines(selector_evaluation_summary: pd.DataFrame, output_path: str | Path) -> None:
    """Plot the selector mean objective against SBS and VBS with split-level standard deviations."""

    summary = selector_evaluation_summary.copy()
    mean_row = summary[
        (summary["summary_row_type"].astype(str) == "aggregate_mean")
        & (summary["dataset_type"].fillna("all").astype(str) == "all")
    ]
    std_row = summary[
        (summary["summary_row_type"].astype(str) == "aggregate_std")
        & (summary["dataset_type"].fillna("all").astype(str) == "all")
    ]
    if mean_row.empty or std_row.empty:
        raise ValueError("Selector evaluation summary must contain aggregate mean and std rows.")

    mean_row = mean_row.iloc[0]
    std_row = std_row.iloc[0]
    entries = [
        ("VBS", _float(mean_row.get("average_virtual_best_objective")), _float(std_row.get("average_virtual_best_objective")), PALETTE["accent_soft"]),
        ("Modelis", _float(mean_row.get("average_selected_objective")), _float(std_row.get("average_selected_objective")), PALETTE["accent"]),
        ("SBS", _float(mean_row.get("average_single_best_objective")), _float(std_row.get("average_single_best_objective")), PALETTE["accent_warm"]),
    ]

    fig, ax = plt.subplots(figsize=(9.6, 4.8))
    min_x = min(value - spread for _, value, spread, _ in entries)
    max_x = max(value + spread for _, value, spread, _ in entries)

    for y_index, (label, value, spread, color) in enumerate(reversed(entries)):
        ax.errorbar(
            value,
            y_index,
            xerr=spread,
            fmt="o",
            color=color,
            ecolor=color,
            elinewidth=2.2,
            capsize=5,
            capthick=2.2,
            markersize=9,
            markeredgecolor="white",
            markeredgewidth=1.3,
        )
        ax.text(
            value + spread + 0.035,
            y_index,
            f"{value:.2f} ± {spread:.2f}",
            va="center",
            ha="left",
            fontsize=9.5,
            color=PALETTE["ink"],
        )

    ax.set_yticks(range(len(entries)))
    ax.set_yticklabels([label for label, *_ in reversed(entries)])
    ax.set_xlim(min_x - 0.08, max_x + 0.5)
    ax.set_title("Modeļa, SBS un VBS salīdzinājums", fontsize=14, loc="left")
    ax.set_xlabel("Vidējā mērķfunkcijas vērtība (zemāka ir labāka)")
    _style_axes(ax, axis="x")
    ax.grid(axis="y", visible=False)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)
    _save_figure(fig, output_path)


def plot_real_vs_synthetic(real_vs_synthetic: pd.DataFrame, output_path: str | Path) -> None:
    """Plot the main comparison between real and synthetic subsets."""

    frame = _normalize_real_vs_synthetic_frame(real_vs_synthetic)
    frame["dataset_type"] = frame["dataset_type"].astype(str)
    frame = frame.set_index("dataset_type")
    order = [name for name in ("real", "synthetic") if name in frame.index]

    metrics = [
        ("classification_accuracy", "Precizitāte"),
        ("average_selected_objective", "Vidējā izvēlētā kvalitāte"),
        ("regret_vs_virtual_best", "Regret pret virtual best"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.7))
    fig.suptitle("Reālo un sintētisko datu salīdzinājums", fontsize=14, x=0.06, ha="left")
    for axis, (column, title) in zip(axes, metrics, strict=True):
        values = [_float(frame.loc[item, column]) for item in order]
        bars = axis.bar(
            [_dataset_label(item) for item in order],
            values,
            color=[PALETTE["real"], PALETTE["synthetic"]][: len(values)],
            edgecolor="white",
            linewidth=1.2,
            width=0.62,
        )
        axis.set_title(title, fontsize=11)
        _style_axes(axis)
        for bar, value in zip(bars, values, strict=True):
            axis.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    _save_figure(fig, output_path)


def plot_solver_comparison(solver_comparison: pd.DataFrame, output_path: str | Path) -> None:
    """Plot solver quality on the real and synthetic subsets."""

    frame = _normalize_solver_comparison_frame(solver_comparison)
    real_rows = frame[frame["result_scope"] == "real"].copy()
    real_rows["average_objective_valid_feasible"] = pd.to_numeric(
        real_rows["average_objective_valid_feasible"],
        errors="coerce",
    )
    real_rows = real_rows.dropna(subset=["average_objective_valid_feasible"])
    real_rows = real_rows.sort_values(
        by=["average_objective_valid_feasible", "solver_registry_name"],
        ascending=[True, True],
        na_position="last",
        kind="mergesort",
    )

    synthetic_rows = frame[frame["result_scope"] == "synthetic"].copy()
    synthetic_rows["average_objective_valid_feasible"] = pd.to_numeric(
        synthetic_rows["average_objective_valid_feasible"],
        errors="coerce",
    )
    synthetic_rows = synthetic_rows.dropna(subset=["average_objective_valid_feasible"])
    synthetic_rows = synthetic_rows.sort_values(
        by=["average_objective_valid_feasible", "solver_registry_name"],
        ascending=[True, True],
        na_position="last",
        kind="mergesort",
    )

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.2))
    fig.suptitle("Algoritmu salīdzinājums", fontsize=14, x=0.06, ha="left")

    real_names = [_solver_label(name) for name in real_rows["solver_registry_name"].tolist()]
    axes[0].barh(
        real_names,
        real_rows["average_objective_valid_feasible"].fillna(0.0),
        color=PALETTE["accent"],
        edgecolor="white",
        linewidth=1.1,
    )
    axes[0].invert_yaxis()
    axes[0].set_title("Vidējā kvalitāte reālajās instancēs", fontsize=11)
    axes[0].set_xlabel("Mērķfunkcijas vērtība")
    _style_axes(axes[0], axis="x")

    synthetic_names = [_solver_label(name) for name in synthetic_rows["solver_registry_name"].tolist()]
    bars = axes[1].barh(
        synthetic_names,
        synthetic_rows["average_objective_valid_feasible"].fillna(0.0),
        color=PALETTE["accent_warm"],
        edgecolor="white",
        linewidth=1.1,
    )
    axes[1].set_title("Vidējā kvalitāte sintētiskajās instancēs", fontsize=11)
    axes[1].set_xlabel("Mērķfunkcijas vērtība")
    _style_axes(axes[1], axis="x")
    for bar, value in zip(bars, synthetic_rows["average_objective_valid_feasible"].fillna(0.0), strict=True):
        axes[1].text(
            float(value) + 0.05,
            bar.get_y() + bar.get_height() / 2,
            f"{float(value):.2f}",
            ha="left",
            va="center",
            fontsize=9,
        )
    _save_figure(fig, output_path)


def plot_solver_runtime(solver_comparison: pd.DataFrame, output_path: str | Path) -> None:
    """Plot mean runtime by solver and dataset scope."""

    frame = _normalize_solver_comparison_frame(solver_comparison)
    solvers = list(dict.fromkeys(frame["solver_registry_name"].astype(str).tolist()))
    scopes = [scope for scope in ("real", "synthetic") if scope in frame["result_scope"].astype(str).unique()]
    positions = np.arange(len(solvers))
    width = 0.34

    fig, ax = plt.subplots(figsize=(12, 5.1))
    for index, scope in enumerate(scopes):
        scoped = frame[frame["result_scope"] == scope].set_index("solver_registry_name")
        values = [float(scoped.loc[solver, "average_runtime_seconds"]) if solver in scoped.index else 0.0 for solver in solvers]
        shift = (index - (len(scopes) - 1) / 2) * width
        ax.bar(
            positions + shift,
            values,
            width=width,
            label=_dataset_label(scope),
            color=PALETTE["real"] if scope == "real" else PALETTE["synthetic"],
            edgecolor="white",
            linewidth=1.0,
        )

    ax.set_title("Vidējais izpildes laiks pa algoritmiem", fontsize=14, loc="left")
    ax.set_ylabel("Laiks sekundēs")
    ax.set_xticks(positions, [_solver_label(item) for item in solvers], rotation=18)
    ax.legend(frameon=False)
    _style_axes(ax)
    _save_figure(fig, output_path)


def plot_feature_importance(feature_importance: pd.DataFrame, output_path: str | Path) -> None:
    """Plot the top 10 structural feature importances."""

    normalized = _normalize_feature_importance_frame(feature_importance)
    top_features = normalized.head(10).iloc[::-1].copy()

    fig, ax = plt.subplots(figsize=(11.5, 6.2))
    bars = ax.barh(
        [_labelize_feature(item) for item in top_features["source_feature"].tolist()],
        top_features["importance"].astype(float),
        color=[_feature_group_color(group) for group in top_features["feature_group"].tolist()],
        edgecolor="white",
        linewidth=1.0,
    )
    ax.set_title("Desmit nozīmīgākās strukturālās pazīmes nejaušo mežu klasifikatorā", fontsize=14)
    ax.set_xlabel("Nozīmīgums")
    ax.set_ylabel("Pazīme")
    _style_axes(ax, axis="x")
    for bar, value in zip(bars, top_features["importance"].astype(float), strict=True):
        ax.text(
            value + 0.003,
            bar.get_y() + bar.get_height() / 2,
            f"{value:.4f}".replace(".", ","),
            va="center",
            fontsize=9,
            color=PALETTE["ink"],
        )
    ax.set_xlim(0, max(top_features["importance"].astype(float)) * 1.18)
    _save_figure(fig, output_path)


def plot_solver_win_distribution(selection_dataset: pd.DataFrame, output_path: str | Path) -> None:
    """Plot how often each solver is best by dataset type."""

    pivot = (
        selection_dataset.groupby(["dataset_type", "best_solver"])
        .size()
        .unstack(fill_value=0)
        .reindex(index=["real", "synthetic"], fill_value=0)
    )
    solver_names = list(pivot.columns)
    positions = np.arange(len(pivot.index))
    width = 0.22

    fig, ax = plt.subplots(figsize=(11, 5.2))
    for index, solver_name in enumerate(solver_names):
        shift = (index - (len(solver_names) - 1) / 2) * width
        ax.bar(
            positions + shift,
            pivot[solver_name].astype(float),
            width=width,
            label=_solver_label(solver_name),
            color=_series_color(index),
            edgecolor="white",
            linewidth=1.0,
        )

    ax.set_title("Labāko rezultātu sadalījums pa algoritmiem", fontsize=14, loc="left")
    ax.set_ylabel("Instanču skaits")
    ax.set_xticks(positions, [_dataset_label(item) for item in pivot.index.tolist()])
    ax.legend(frameon=False, ncol=2)
    _style_axes(ax)
    _save_figure(fig, output_path)


def plot_dataset_distribution(selection_dataset: pd.DataFrame, output_path: str | Path) -> None:
    """Plot only the dataset-type composition."""

    dataset_counts = (
        selection_dataset["dataset_type"]
        .value_counts()
        .reindex(["real", "synthetic"], fill_value=0)
    )
    fig, ax = plt.subplots(figsize=(7.2, 5.1))
    fig.suptitle("Datu kopas sastāvs", fontsize=14, x=0.06, ha="left")

    bars = ax.bar(
        [_dataset_label(item) for item in dataset_counts.index.tolist()],
        dataset_counts.astype(float),
        color=[PALETTE["real"], PALETTE["synthetic"]],
        edgecolor="white",
        linewidth=1.0,
        width=0.62,
    )
    ax.set_title("Instanču skaits pa datu tipiem", fontsize=11)
    ax.set_ylabel("Skaits")
    _style_axes(ax)
    for bar, value in zip(bars, dataset_counts.astype(float), strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{int(value)}", ha="center", va="bottom", fontsize=9)

    _save_figure(fig, output_path)


def plot_best_solver_class_distribution(selection_dataset: pd.DataFrame, output_path: str | Path) -> None:
    """Plot the overall best-solver class distribution as a separate figure."""

    solver_counts = selection_dataset["best_solver"].value_counts()

    fig, ax = plt.subplots(figsize=(8.8, 5.1))
    bars = ax.bar(
        [_solver_label(item) for item in solver_counts.index.tolist()],
        solver_counts.astype(float),
        color=[_series_color(index) for index, _ in enumerate(solver_counts.index.tolist())],
        edgecolor="white",
        linewidth=1.0,
        width=0.62,
    )
    ax.set_title("Labākā algoritma klašu sadalījums", fontsize=14)
    ax.set_ylabel("Skaits")
    ax.tick_params(axis="x", rotation=18)
    _style_axes(ax)
    for bar, value in zip(bars, solver_counts.astype(float), strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{int(value)}", ha="center", va="bottom", fontsize=9)
    _save_figure(fig, output_path)


def plot_objective_distribution(selection_dataset: pd.DataFrame, output_path: str | Path) -> None:
    """Plot the distribution of per-instance best objective values."""

    frame = selection_dataset.copy()
    objective_column = "benchmark_best_solver_mean_objective"
    frame = frame.dropna(subset=[objective_column])

    fig, axes = plt.subplots(1, 2, figsize=(13, 5.0))
    fig.suptitle("Mērķfunkcijas vērtību sadalījums", fontsize=14, x=0.06, ha="left")

    for axis, dataset_type, color in (
        (axes[0], "real", PALETTE["real"]),
        (axes[1], "synthetic", PALETTE["synthetic"]),
    ):
        values = frame.loc[frame["dataset_type"] == dataset_type, objective_column].astype(float)
        axis.hist(values, bins=12, color=color, edgecolor="white", linewidth=1.0, alpha=0.9)
        axis.set_title(_dataset_label(dataset_type), fontsize=11)
        axis.set_xlabel("Labākā mērķfunkcijas vērtība")
        axis.set_ylabel("Instanču skaits")
        _style_axes(axis)
    _save_figure(fig, output_path)


def plot_runtime_distribution(combined_benchmark: pd.DataFrame, output_path: str | Path) -> None:
    """Plot runtime distributions across solvers."""

    frame = combined_benchmark.copy()
    frame["runtime_seconds"] = pd.to_numeric(frame["runtime_seconds"], errors="coerce")
    frame = frame.dropna(subset=["runtime_seconds", "solver_registry_name", "dataset_type"])
    solvers = list(dict.fromkeys(frame["solver_registry_name"].astype(str).tolist()))
    dataset_types = ["real", "synthetic"]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.3), sharey=True)
    fig.suptitle("Izpildes laika sadalījums", fontsize=14, x=0.06, ha="left")

    for axis, dataset_type in zip(axes, dataset_types, strict=True):
        values = [
            frame.loc[
                (frame["dataset_type"] == dataset_type) & (frame["solver_registry_name"] == solver),
                "runtime_seconds",
            ].astype(float).tolist()
            for solver in solvers
        ]
        cleaned = [group if group else [0.0] for group in values]
        box = axis.boxplot(cleaned, patch_artist=True, labels=[_solver_label(item) for item in solvers])
        for patch, solver in zip(box["boxes"], solvers, strict=True):
            patch.set_facecolor(_solver_color(solver))
            patch.set_alpha(0.85)
            patch.set_edgecolor("white")
        axis.set_title(_dataset_label(dataset_type), fontsize=11)
        axis.set_ylabel("Laiks sekundēs")
        axis.set_yscale("log")
        axis.tick_params(axis="x", rotation=18)
        _style_axes(axis)
    _save_figure(fig, output_path)


def plot_accuracy_by_dataset_type(
    selector_results: pd.DataFrame,
    real_vs_synthetic: pd.DataFrame,
    output_path: str | Path,
) -> None:
    """Plot accuracy for the mixed, real, and synthetic sets."""

    selector_results = _normalize_selector_results_frame(selector_results)
    overall_row = selector_results.iloc[0]
    values = {
        "all": _float(overall_row.get("classification_accuracy")),
    }
    normalized = _normalize_real_vs_synthetic_frame(real_vs_synthetic)
    for _, row in normalized.iterrows():
        dataset_type = str(row.get("dataset_type"))
        values[dataset_type] = _float(row.get("classification_accuracy"))

    order = ["all", "real", "synthetic"]
    labels = [_dataset_label(item) for item in order if item in values]
    series = [values[item] for item in order if item in values]

    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    bars = ax.bar(
        labels,
        series,
        color=[PALETTE["accent"], PALETTE["real"], PALETTE["synthetic"]][: len(series)],
        edgecolor="white",
        linewidth=1.1,
        width=0.62,
    )
    ax.set_title("Precizitāte pa datu tipiem", fontsize=14, loc="left")
    ax.set_ylabel("Precizitāte")
    _style_axes(ax)
    for bar, value in zip(bars, series, strict=True):
        ax.text(bar.get_x() + bar.get_width() / 2, value, f"{value:.3f}", ha="center", va="bottom", fontsize=9)
    _save_figure(fig, output_path)


def plot_regret_distribution(selector_evaluation_summary: pd.DataFrame, output_path: str | Path) -> None:
    """Plot split-level regret distributions."""

    overall_rows = selector_evaluation_summary[selector_evaluation_summary["summary_row_type"] == "split"].copy()
    dataset_rows = selector_evaluation_summary[
        selector_evaluation_summary["summary_row_type"] == "split_dataset_type"
    ].copy()

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.1))
    fig.suptitle("Regret sadalījums validācijas sadalījumos", fontsize=14, x=0.06, ha="left")

    axes[0].hist(
        overall_rows["regret_vs_virtual_best"].dropna().astype(float),
        bins=9,
        color=PALETTE["accent_warm"],
        edgecolor="white",
        linewidth=1.0,
    )
    axes[0].set_title("Jauktās kopas sadalījums", fontsize=11)
    axes[0].set_xlabel("Regret")
    axes[0].set_ylabel("Sadalījumu skaits")
    _style_axes(axes[0])

    box_values = [
        dataset_rows.loc[dataset_rows["dataset_type"] == dataset_type, "regret_vs_virtual_best"].dropna().astype(float).tolist()
        for dataset_type in ("real", "synthetic")
    ]
    box = axes[1].boxplot(box_values, patch_artist=True, labels=[_dataset_label("real"), _dataset_label("synthetic")])
    for patch, color in zip(box["boxes"], [PALETTE["real"], PALETTE["synthetic"]], strict=True):
        patch.set_facecolor(color)
        patch.set_alpha(0.85)
        patch.set_edgecolor("white")
    axes[1].set_title("Sadale pa datu tipiem", fontsize=11)
    axes[1].set_ylabel("Regret")
    _style_axes(axes[1])
    _save_figure(fig, output_path)


def plot_confusion_matrix(selector_evaluation: pd.DataFrame, output_path: str | Path) -> None:
    """Plot aggregated selector predictions across all validation splits."""

    required_columns = {"true_best_solver", "selected_solver"}
    missing_columns = required_columns.difference(selector_evaluation.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Selector evaluation report is missing required columns: {missing}")

    matrix = pd.crosstab(
        selector_evaluation["true_best_solver"].astype(str),
        selector_evaluation["selected_solver"].astype(str),
    )
    labels = _ordered_solver_labels(set(matrix.index).union(set(matrix.columns)))
    matrix = matrix.reindex(index=labels, columns=labels, fill_value=0)
    row_totals = matrix.sum(axis=1).replace(0, np.nan)
    percentages = matrix.div(row_totals, axis=0).fillna(0.0) * 100.0

    fig, ax = plt.subplots(figsize=(8.8, 6.4))
    image = ax.imshow(matrix.to_numpy(dtype=float), cmap="YlGnBu")
    ax.set_title("Klasifikācijas kļūdu matrica", fontsize=14, loc="left")
    ax.set_xlabel("Prognozētais algoritms")
    ax.set_ylabel("Patiesais labākais algoritms")
    ax.set_xticks(range(len(labels)), [_solver_label(item) for item in labels], rotation=28, ha="right")
    ax.set_yticks(range(len(labels)), [_solver_label(item) for item in labels])

    max_count = float(matrix.to_numpy(dtype=float).max()) if not matrix.empty else 0.0
    threshold = max_count / 2.0
    for row_index, true_label in enumerate(labels):
        for column_index, predicted_label in enumerate(labels):
            count = int(matrix.loc[true_label, predicted_label])
            percent = float(percentages.loc[true_label, predicted_label])
            color = "white" if count > threshold else PALETTE["ink"]
            ax.text(
                column_index,
                row_index,
                f"{count}\n{percent:.1f}%",
                ha="center",
                va="center",
                fontsize=9,
                color=color,
            )

    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    _save_figure(fig, output_path)


def plot_feature_correlation_matrix(
    selection_dataset: pd.DataFrame,
    feature_importance: pd.DataFrame,
    output_path: str | Path,
) -> None:
    """Plot the correlation matrix for the most important numeric features."""

    normalized = _normalize_feature_importance_frame(feature_importance)
    top_features = [
        _normalize_feature_name(item)
        for item in normalized["source_feature"].astype(str).tolist()
        if item in selection_dataset.columns
    ][:8]
    frame = selection_dataset.loc[:, top_features].apply(pd.to_numeric, errors="coerce")
    correlation = frame.corr().fillna(0.0)

    fig, ax = plt.subplots(figsize=(8.5, 7.0))
    image = ax.imshow(correlation.to_numpy(dtype=float), cmap="YlGnBu", vmin=-1.0, vmax=1.0)
    ax.set_title("Svarīgāko pazīmju korelācijas", fontsize=14, loc="left")
    ax.set_xticks(range(len(top_features)), [_labelize_feature(item) for item in top_features], rotation=40, ha="right")
    ax.set_yticks(range(len(top_features)), [_labelize_feature(item) for item in top_features])
    for row_index in range(len(top_features)):
        for column_index in range(len(top_features)):
            ax.text(
                column_index,
                row_index,
                f"{float(correlation.iloc[row_index, column_index]):.2f}",
                ha="center",
                va="center",
                fontsize=8,
                color="black",
            )
    fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
    _save_figure(fig, output_path)


def plot_constraint_distribution(selection_dataset: pd.DataFrame, output_path: str | Path) -> None:
    """Plot distributions of total, hard, and soft constraints."""

    metrics = [
        ("num_constraints", "Kopējais ierobežojumu skaits"),
        ("num_hard_constraints", "Stingrie ierobežojumi"),
        ("num_soft_constraints", "Mīkstie ierobežojumi"),
    ]

    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    fig.suptitle("Ierobežojumu sadalījums instancēs", fontsize=14, x=0.06, ha="left")
    for axis, (column, title) in zip(axes, metrics, strict=True):
        for dataset_type, color in (("real", PALETTE["real"]), ("synthetic", PALETTE["synthetic"])):
            values = selection_dataset.loc[selection_dataset["dataset_type"] == dataset_type, column].astype(float)
            axis.hist(values, bins=12, alpha=0.7, label=_dataset_label(dataset_type), color=color, edgecolor="white", linewidth=0.9)
        axis.set_title(title, fontsize=11)
        axis.set_xlabel("Vērtība")
        axis.set_ylabel("Instanču skaits")
        _style_axes(axis)
    axes[0].legend(frameon=False)
    _save_figure(fig, output_path)


def plot_teams_vs_slots(selection_dataset: pd.DataFrame, output_path: str | Path) -> None:
    """Plot team count against slot count for all instances."""

    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    for dataset_type, color in (("real", PALETTE["real"]), ("synthetic", PALETTE["synthetic"])):
        rows = selection_dataset[selection_dataset["dataset_type"] == dataset_type]
        ax.scatter(
            rows["num_teams"].astype(float),
            rows["num_slots"].astype(float),
            s=np.clip(rows["num_constraints"].astype(float) / 3.0, 18.0, 180.0),
            alpha=0.78,
            color=color,
            label=_dataset_label(dataset_type),
            edgecolors="white",
            linewidths=0.5,
        )

    ax.set_title("Komandu skaits pret laika vietu skaitu", fontsize=14, loc="left")
    ax.set_xlabel("Komandu skaits")
    ax.set_ylabel("Laika vietu skaits")
    ax.legend(frameon=False)
    _style_axes(ax)
    _save_figure(fig, output_path)


def plot_constraints_vs_objective(selection_dataset: pd.DataFrame, output_path: str | Path) -> None:
    """Plot total constraints against the best benchmark objective."""

    frame = selection_dataset.dropna(subset=["benchmark_best_solver_mean_objective"]).copy()
    frame["benchmark_best_solver_mean_objective"] = pd.to_numeric(
        frame["benchmark_best_solver_mean_objective"],
        errors="coerce",
    )
    frame = frame.dropna(subset=["benchmark_best_solver_mean_objective"])

    fig, ax = plt.subplots(figsize=(8.8, 5.4))
    for dataset_type, color in (("real", PALETTE["real"]), ("synthetic", PALETTE["synthetic"])):
        rows = frame[frame["dataset_type"] == dataset_type]
        x_values = rows["num_constraints"].astype(float).to_numpy()
        y_values = rows["benchmark_best_solver_mean_objective"].astype(float).to_numpy()
        ax.scatter(
            x_values,
            y_values,
            alpha=0.76,
            color=color,
            label=_dataset_label(dataset_type),
            edgecolors="white",
            linewidths=0.5,
        )
        if len(x_values) >= 2:
            coefficients = np.polyfit(x_values, y_values, deg=1)
            trend_x = np.linspace(float(x_values.min()), float(x_values.max()), 50)
            trend_y = coefficients[0] * trend_x + coefficients[1]
            ax.plot(trend_x, trend_y, color=color, linewidth=1.4, alpha=0.85)

    ax.set_title("Ierobežojumu skaits pret sasniegto kvalitāti", fontsize=14, loc="left")
    ax.set_xlabel("Ierobežojumu skaits")
    ax.set_ylabel("Labākā mērķfunkcijas vērtība")
    ax.legend(frameon=False)
    _style_axes(ax)
    _save_figure(fig, output_path)


def _style_axes(ax: plt.Axes, axis: str = "y") -> None:
    """Apply one consistent light visual style to the axes."""

    ax.set_facecolor(PALETTE["surface"])
    ax.grid(axis=axis, color=PALETTE["grid"], linestyle="--", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color(PALETTE["grid"])
    ax.spines["bottom"].set_color(PALETTE["grid"])
    ax.tick_params(colors=PALETTE["ink"])
    ax.title.set_color(PALETTE["ink"])
    ax.xaxis.label.set_color(PALETTE["ink"])
    ax.yaxis.label.set_color(PALETTE["ink"])


def _save_figure(fig: plt.Figure, output_path: str | Path) -> None:
    """Save one figure deterministically."""

    fig.patch.set_facecolor(PALETTE["surface"])
    fig.tight_layout()
    fig.savefig(output_path, dpi=190, bbox_inches="tight", facecolor=PALETTE["surface"])
    plt.close(fig)


def _float(value: object) -> float:
    """Convert one value to float, falling back to zero when missing."""

    try:
        if pd.isna(value):
            return 0.0
    except (TypeError, ValueError):
        pass
    return float(value)


def _dataset_label(value: str) -> str:
    """Return the Latvian label for one dataset type."""

    return DATASET_LABELS.get(str(value), str(value))


def _solver_label(value: str) -> str:
    """Return the display label for one solver."""

    return SOLVER_LABELS.get(str(value), str(value).replace("_", " ").title())


def _feature_group_label(value: str) -> str:
    """Return the Latvian label for one feature group."""

    return FEATURE_GROUP_LABELS.get(str(value), str(value).replace("_", " ").title())


def _feature_group_color(value: str) -> str:
    """Return the consistent color for one feature group."""

    return FEATURE_GROUP_COLORS.get(str(value), PALETTE["ink"])


def _series_color(index: int) -> str:
    """Return one stable series color by index."""

    palette = [PALETTE["accent"], PALETTE["accent_warm"], PALETTE["accent_soft"], PALETTE["accent_gold"]]
    return palette[index % len(palette)]


def _solver_color(solver_name: str) -> str:
    """Return one stable color for one solver."""

    ordered = list(SOLVER_LABELS)
    if solver_name in ordered:
        return _series_color(ordered.index(solver_name))
    return PALETTE["accent"]


def _ordered_solver_labels(labels: set[str]) -> list[str]:
    """Return solver labels in portfolio order, followed by unknown labels."""

    ordered = [solver_name for solver_name in SOLVER_LABELS if solver_name in labels]
    ordered.extend(sorted(label for label in labels if label not in SOLVER_LABELS))
    return ordered


def _labelize_feature(value: str) -> str:
    """Turn one raw feature name into a short chart label."""

    return str(value)


def _normalize_solver_comparison_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Accept either localized or raw solver-comparison columns."""

    if "result_scope" in frame.columns:
        return frame.copy()

    renamed = frame.rename(
        columns={
            "Datu kopa": "result_scope",
            "Algoritms": "solver_registry_name",
            "Uzvaras": "win_count",
            "Vidējā kvalitāte": "average_objective_valid_feasible",
            "Vidējais laiks (s)": "average_runtime_seconds",
            "Feasible pārklājums": "feasible_coverage_ratio",
            "Salīdzināmais pārklājums": "valid_feasible_coverage_ratio",
        }
    ).copy()
    if "result_scope" in renamed.columns:
        renamed["result_scope"] = renamed["result_scope"].map(_normalize_dataset_type)
    if "solver_registry_name" in renamed.columns:
        renamed["solver_registry_name"] = renamed["solver_registry_name"].map(_normalize_solver_name)
    return renamed


def _normalize_selector_results_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Accept either localized or raw selector-summary columns."""

    if "classification_accuracy" in frame.columns:
        return frame.copy()

    return frame.rename(
        columns={
            "Precizitāte": "classification_accuracy",
            "Sabalansētā precizitāte": "balanced_accuracy",
            "Vidējā izvēlētā kvalitāte": "average_selected_objective",
            "Vidējā virtual best kvalitāte": "average_virtual_best_objective",
            "Vidējā single best kvalitāte": "average_single_best_objective",
            "Regret pret virtual best": "regret_vs_virtual_best",
            "Uzlabojums pret single best": "improvement_vs_single_best",
        }
    ).copy()


def _normalize_real_vs_synthetic_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Accept either localized or raw real-vs-synthetic columns."""

    if "dataset_type" in frame.columns:
        return frame.copy()

    renamed = frame.rename(
        columns={
            "Datu kopa": "dataset_type",
            "Precizitāte": "classification_accuracy",
            "Sabalansētā precizitāte": "balanced_accuracy",
            "Vidējā izvēlētā kvalitāte": "average_selected_objective",
            "Vidējā virtual best kvalitāte": "average_virtual_best_objective",
            "Vidējā single best kvalitāte": "average_single_best_objective",
            "Regret pret virtual best": "regret_vs_virtual_best",
            "Uzlabojums pret single best": "improvement_vs_single_best",
        }
    ).copy()
    if "dataset_type" in renamed.columns:
        renamed["dataset_type"] = renamed["dataset_type"].map(_normalize_dataset_type)
    return renamed


def _normalize_feature_importance_frame(frame: pd.DataFrame) -> pd.DataFrame:
    """Accept either localized or raw feature-importance columns."""

    if "source_feature" in frame.columns:
        return frame.copy()

    renamed = frame.rename(
        columns={
            "Pazīme": "source_feature",
            "Grupa": "feature_group",
            "Nozīmīgums": "importance",
            "Rangs": "importance_rank",
        }
    ).copy()
    if "feature_group" in renamed.columns:
        renamed["feature_group"] = renamed["feature_group"].map(_normalize_feature_group)
    if "source_feature" in renamed.columns:
        renamed["source_feature"] = renamed["source_feature"].map(_normalize_feature_name)
    return renamed


def _normalize_dataset_type(value: object) -> str:
    """Convert localized dataset labels back to raw identifiers when needed."""

    mapping = {
        "Jauktā kopa": "all",
        "Reālie dati": "real",
        "Sintētiskie dati": "synthetic",
    }
    return mapping.get(str(value), str(value))


def _normalize_solver_name(value: object) -> str:
    """Convert localized solver labels back to registry identifiers when needed."""

    mapping = {
        "Nejaušā bāzlīnija": "random_baseline",
        "CP-SAT": "cpsat_solver",
        "Simulētā rūdīšana": "simulated_annealing_solver",
        "Timefold": "timefold",
    }
    return mapping.get(str(value), str(value))


def _normalize_feature_group(value: object) -> str:
    """Convert localized feature-group labels back to raw identifiers when needed."""

    mapping = {
        "Izmērs": "size",
        "Blīvums": "density",
        "Ierobežojumi": "constraint_composition",
        "Daudzveidība": "diversity",
        "Mērķfunkcija": "objective",
    }
    return mapping.get(str(value), str(value))


def _normalize_feature_name(value: object) -> str:
    """Convert display feature names back to dataframe column names when needed."""

    return str(value).replace(" ", "_")
