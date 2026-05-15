"""Regression tests for thesis-facing presentation plots."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from src.thesis import plots


def test_plot_selector_performance_uses_localized_selector_results(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The main metric figure should read values from the localized thesis table."""

    selector_results = pd.DataFrame(
        [
            {
                "Precizitāte": 0.9285714285714286,
                "Sabalansētā precizitāte": 0.8817596252378861,
                "Regret pret virtual best": 0.23412698412698418,
                "Uzlabojums pret single best": 0.06349206349206327,
            }
        ]
    )
    captured: dict[str, list[str]] = {}

    def _capture(fig: plt.Figure, output_path: str | Path) -> None:
        captured["texts"] = [text.get_text() for axis in fig.axes for text in axis.texts]
        fig.savefig(output_path)
        plt.close(fig)

    monkeypatch.setattr(plots, "_save_figure", _capture)

    output_path = tmp_path / "selector_performance.png"
    plots.plot_selector_performance(selector_results, output_path)

    assert output_path.exists()
    assert captured["texts"] == ["0.9286", "0.8818", "0.2341", "0.0635"]


def test_plot_solver_comparison_uses_quality_not_coverage_for_synthetic_panel(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The synthetic solver comparison panel should no longer plot feasible coverage."""

    solver_comparison = pd.DataFrame(
        [
            {
                "Datu kopa": "Reālie dati",
                "Algoritms": "CP-SAT",
                "Vidējā kvalitāte": 30.0,
                "Vidējais laiks (s)": 1.2,
                "Feasible pārklājums": 1.0,
            },
            {
                "Datu kopa": "Reālie dati",
                "Algoritms": "Simulētā rūdīšana",
                "Vidējā kvalitāte": 28.0,
                "Vidējais laiks (s)": 2.0,
                "Feasible pārklājums": 1.0,
            },
            {
                "Datu kopa": "Sintētiskie dati",
                "Algoritms": "CP-SAT",
                "Vidējā kvalitāte": 6.0,
                "Vidējais laiks (s)": 0.9,
                "Feasible pārklājums": 0.10,
            },
            {
                "Datu kopa": "Sintētiskie dati",
                "Algoritms": "Simulētā rūdīšana",
                "Vidējā kvalitāte": 8.0,
                "Vidējais laiks (s)": 1.4,
                "Feasible pārklājums": 0.95,
            },
        ]
    )
    captured: dict[str, list[str]] = {}

    def _capture(fig: plt.Figure, output_path: str | Path) -> None:
        captured["titles"] = [axis.get_title() for axis in fig.axes]
        captured["synthetic_texts"] = [text.get_text() for text in fig.axes[1].texts]
        fig.savefig(output_path)
        plt.close(fig)

    monkeypatch.setattr(plots, "_save_figure", _capture)

    output_path = tmp_path / "solver_comparison.png"
    plots.plot_solver_comparison(solver_comparison, output_path)

    assert output_path.exists()
    assert captured["titles"][1] == "Vidējā kvalitāte sintētiskajās instancēs"
    assert "6.00" in captured["synthetic_texts"]
    assert "8.00" in captured["synthetic_texts"]
    assert "0.10" not in captured["synthetic_texts"]


def test_plot_dataset_distribution_shows_only_dataset_counts(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The dataset figure should no longer include the best-solver class panel."""

    selection_dataset = pd.DataFrame(
        [
            {"dataset_type": "real", "best_solver": "simulated_annealing_solver"},
            {"dataset_type": "real", "best_solver": "simulated_annealing_solver"},
            {"dataset_type": "synthetic", "best_solver": "cpsat_solver"},
        ]
    )
    captured: dict[str, object] = {}

    def _capture(fig: plt.Figure, output_path: str | Path) -> None:
        captured["axes_count"] = len(fig.axes)
        captured["titles"] = [axis.get_title() for axis in fig.axes]
        fig.savefig(output_path)
        plt.close(fig)

    monkeypatch.setattr(plots, "_save_figure", _capture)

    output_path = tmp_path / "dataset_distribution.png"
    plots.plot_dataset_distribution(selection_dataset, output_path)

    assert output_path.exists()
    assert captured["axes_count"] == 1
    assert captured["titles"] == ["Instanču skaits pa datu tipiem"]


def test_plot_feature_importance_shows_only_top_10_features(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The thesis feature-importance figure should not include a feature-group panel."""

    feature_importance = pd.DataFrame(
        [
            {"Rangs": index + 1, "Pazīme": f"feature {index}", "Grupa": "Izmērs", "Nozīmīgums": 0.2 - index * 0.01}
            for index in range(12)
        ]
    )
    captured: dict[str, object] = {}

    def _capture(fig: plt.Figure, output_path: str | Path) -> None:
        captured["axes_count"] = len(fig.axes)
        captured["titles"] = [axis.get_title() for axis in fig.axes]
        captured["texts"] = [text.get_text() for axis in fig.axes for text in axis.texts]
        fig.savefig(output_path)
        plt.close(fig)

    monkeypatch.setattr(plots, "_save_figure", _capture)

    output_path = tmp_path / "feature_importance.png"
    plots.plot_feature_importance(feature_importance, output_path)

    assert output_path.exists()
    assert captured["axes_count"] == 1
    assert captured["titles"] == ["Desmit nozīmīgākās strukturālās pazīmes nejaušo mežu klasifikatorā"]
    assert "0,2000" in captured["texts"]


def test_plot_best_solver_class_distribution_is_generated_separately(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Best-solver class balance should be exported as its own figure."""

    selection_dataset = pd.DataFrame(
        [
            {"dataset_type": "real", "best_solver": "simulated_annealing_solver"},
            {"dataset_type": "real", "best_solver": "simulated_annealing_solver"},
            {"dataset_type": "synthetic", "best_solver": "cpsat_solver"},
        ]
    )
    captured: dict[str, list[str]] = {}

    def _capture(fig: plt.Figure, output_path: str | Path) -> None:
        captured["titles"] = [axis.get_title() for axis in fig.axes]
        captured["texts"] = [text.get_text() for axis in fig.axes for text in axis.texts]
        fig.savefig(output_path)
        plt.close(fig)

    monkeypatch.setattr(plots, "_save_figure", _capture)

    output_path = tmp_path / "best_solver_class_distribution.png"
    plots.plot_best_solver_class_distribution(selection_dataset, output_path)

    assert output_path.exists()
    assert captured["titles"] == ["Labākā algoritma klašu sadalījums"]
    assert captured["texts"] == ["2", "1"]


def test_plot_confusion_matrix_aggregates_validation_predictions(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """The confusion matrix should summarize all split-level predictions."""

    evaluation = pd.DataFrame(
        [
            {"true_best_solver": "cpsat_solver", "selected_solver": "cpsat_solver"},
            {"true_best_solver": "cpsat_solver", "selected_solver": "cpsat_solver"},
            {"true_best_solver": "simulated_annealing_solver", "selected_solver": "cpsat_solver"},
            {
                "true_best_solver": "simulated_annealing_solver",
                "selected_solver": "simulated_annealing_solver",
            },
        ]
    )
    captured: dict[str, list[str]] = {}

    def _capture(fig: plt.Figure, output_path: str | Path) -> None:
        captured["texts"] = [text.get_text() for axis in fig.axes for text in axis.texts]
        fig.savefig(output_path)
        plt.close(fig)

    monkeypatch.setattr(plots, "_save_figure", _capture)

    output_path = tmp_path / "confusion_matrix.png"
    plots.plot_confusion_matrix(evaluation, output_path)

    assert output_path.exists()
    assert "2\n100.0%" in captured["texts"]
    assert "1\n50.0%" in captured["texts"]
