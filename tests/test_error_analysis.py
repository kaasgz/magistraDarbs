"""Tests for selector error analysis."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.selection.error_analysis import analyze_selector_errors


def test_analyze_selector_errors_saves_csv_and_plots(tmp_path: Path) -> None:
    """Error analysis should create the expected thesis-facing artefacts."""

    evaluation_csv = tmp_path / "selector_evaluation.csv"
    selection_dataset_csv = tmp_path / "selection_dataset.csv"
    output_dir = tmp_path / "error_analysis"

    pd.DataFrame(
        [
            {
                "split_id": "holdout",
                "split_strategy": "holdout",
                "repeat_index": 1,
                "fold_index": None,
                "stratified_split": True,
                "instance_name": "inst_1",
                "selected_solver": "solver_b",
                "true_best_solver": "solver_a",
                "prediction_correct": False,
                "selected_solver_objective": 8.0,
                "best_possible_objective": 4.0,
                "single_best_solver": "solver_a",
                "single_best_solver_objective": 4.0,
                "selected_objective_for_scoring": 8.0,
                "single_best_objective_for_scoring": 4.0,
                "regret_vs_virtual_best": 4.0,
                "delta_vs_single_best": 4.0,
                "improvement_vs_single_best": -4.0,
            },
            {
                "split_id": "holdout",
                "split_strategy": "holdout",
                "repeat_index": 1,
                "fold_index": None,
                "stratified_split": True,
                "instance_name": "inst_2",
                "selected_solver": "solver_a",
                "true_best_solver": "solver_a",
                "prediction_correct": True,
                "selected_solver_objective": 3.0,
                "best_possible_objective": 3.0,
                "single_best_solver": "solver_a",
                "single_best_solver_objective": 3.0,
                "selected_objective_for_scoring": 3.0,
                "single_best_objective_for_scoring": 3.0,
                "regret_vs_virtual_best": 0.0,
                "delta_vs_single_best": 0.0,
                "improvement_vs_single_best": 0.0,
            },
            {
                "split_id": "holdout",
                "split_strategy": "holdout",
                "repeat_index": 1,
                "fold_index": None,
                "stratified_split": True,
                "instance_name": "inst_3",
                "selected_solver": "solver_c",
                "true_best_solver": "solver_a",
                "prediction_correct": False,
                "selected_solver_objective": 10.0,
                "best_possible_objective": 5.0,
                "single_best_solver": "solver_a",
                "single_best_solver_objective": 5.0,
                "selected_objective_for_scoring": 10.0,
                "single_best_objective_for_scoring": 5.0,
                "regret_vs_virtual_best": 5.0,
                "delta_vs_single_best": 5.0,
                "improvement_vs_single_best": -5.0,
            },
            {
                "split_id": "holdout",
                "split_strategy": "holdout",
                "repeat_index": 1,
                "fold_index": None,
                "stratified_split": True,
                "instance_name": "inst_4",
                "selected_solver": "solver_b",
                "true_best_solver": "solver_c",
                "prediction_correct": False,
                "selected_solver_objective": 9.0,
                "best_possible_objective": 7.0,
                "single_best_solver": "solver_a",
                "single_best_solver_objective": 8.0,
                "selected_objective_for_scoring": 9.0,
                "single_best_objective_for_scoring": 8.0,
                "regret_vs_virtual_best": 2.0,
                "delta_vs_single_best": 1.0,
                "improvement_vs_single_best": -1.0,
            },
        ]
    ).to_csv(evaluation_csv, index=False)

    pd.DataFrame(
        [
            {"instance_name": "inst_1", "difficulty_level": "easy", "num_teams": 4, "num_slots": 3, "constraints_per_team": 0.5},
            {"instance_name": "inst_2", "difficulty_level": "easy", "num_teams": 4, "num_slots": 3, "constraints_per_team": 0.6},
            {"instance_name": "inst_3", "difficulty_level": "hard", "num_teams": 8, "num_slots": 7, "constraints_per_team": 1.7},
            {"instance_name": "inst_4", "difficulty_level": "medium", "num_teams": 6, "num_slots": 5, "constraints_per_team": 1.1},
        ]
    ).to_csv(selection_dataset_csv, index=False)

    result = analyze_selector_errors(
        evaluation_report_csv=evaluation_csv,
        selection_dataset_csv=selection_dataset_csv,
        output_dir=output_dir,
    )

    assert result.hard_instances_csv.exists()
    assert result.confusion_pairs_csv.exists()
    assert result.cluster_summary_csv.exists()
    assert result.summary_markdown.exists()
    assert result.hard_instance_plot.exists()
    assert result.confusion_plot.exists()
    assert result.feature_pattern_plot.exists()

    hard_instances = pd.read_csv(result.hard_instances_csv)
    cluster_summary = pd.read_csv(result.cluster_summary_csv)
    summary_markdown = result.summary_markdown.read_text(encoding="utf-8")
    assert not hard_instances.empty
    assert list(hard_instances["instance_name"]) == ["inst_3"]
    assert result.num_hard_instances == 1
    assert result.num_confusion_pairs == 3
    assert "difficulty" in set(cluster_summary["cluster_type"])
    assert "feature_group" in set(cluster_summary["cluster_type"])
    assert "Selector Error Analysis Summary" in summary_markdown


def test_analyze_selector_errors_handles_perfect_selector_case(tmp_path: Path) -> None:
    """Analysis should still produce artefacts when there are no hard mistakes."""

    evaluation_csv = tmp_path / "selector_evaluation.csv"
    selection_dataset_csv = tmp_path / "selection_dataset.csv"
    output_dir = tmp_path / "error_analysis"

    pd.DataFrame(
        [
            {
                "split_id": "holdout",
                "split_strategy": "holdout",
                "repeat_index": 1,
                "fold_index": None,
                "stratified_split": True,
                "instance_name": "inst_1",
                "selected_solver": "solver_a",
                "true_best_solver": "solver_a",
                "prediction_correct": True,
                "selected_solver_objective": 2.0,
                "best_possible_objective": 2.0,
                "single_best_solver": "solver_a",
                "single_best_solver_objective": 2.0,
                "selected_objective_for_scoring": 2.0,
                "single_best_objective_for_scoring": 2.0,
                "regret_vs_virtual_best": 0.0,
                "delta_vs_single_best": 0.0,
                "improvement_vs_single_best": 0.0,
            }
        ]
    ).to_csv(evaluation_csv, index=False)

    pd.DataFrame(
        [
            {"instance_name": "inst_1", "num_teams": 4, "num_slots": 3},
        ]
    ).to_csv(selection_dataset_csv, index=False)

    result = analyze_selector_errors(
        evaluation_report_csv=evaluation_csv,
        selection_dataset_csv=selection_dataset_csv,
        output_dir=output_dir,
    )

    hard_instances = pd.read_csv(result.hard_instances_csv)
    assert hard_instances.empty
    assert result.num_hard_instances == 0
