# Tests for the local dashboard backend service.

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from src.web.dashboard import DashboardService


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_dashboard_state_is_empty_before_first_run(tmp_path: Path) -> None:

    # The dashboard should report an empty workspace cleanly.
    service = DashboardService(workspace_root=tmp_path)

    state = service.build_dashboard_state()

    assert state["overview"]["instance_count"] == 0
    assert state["overview"]["benchmark_rows"] == 0
    assert state["solver_leaderboard"] == []
    assert state["artifacts"]["demo_features"]["exists"] is False
    assert state["mode_controls"]["real"]["instance_count"] == 0
    assert state["instance_inspector"]["title"] == "No instance loaded"
    assert state["thesis_pipeline"]["available"] is False
    assert "No thesis pipeline artifacts" in state["thesis_pipeline"]["empty_state"]
    assert state["main_pipeline"]["available"] is False
    assert state["mixed_dataset"]["available"] is False
    assert "No mixed selection dataset" in state["mixed_dataset"]["empty_state"]
    assert state["benchmark_reports"]["available"] is False
    assert "No thesis-facing benchmark reports" in state["benchmark_reports"]["empty_state"]
    assert state["artifact_browser"]["groups"][0]["scope"] == "thesis"
    assert state["artifact_browser"]["groups"][0]["available_count"] == 0
    assert state["artifact_browser"]["groups"][1]["scope"] == "reports"
    assert state["artifact_browser"]["groups"][1]["available_count"] == 0


def test_load_real_instance_updates_dashboard_inspector(tmp_path: Path) -> None:

    # Loading a real XML should populate the inspector without running the demo pipeline.
    real_dir = tmp_path / "data" / "raw" / "real"
    real_dir.mkdir(parents=True)
    (real_dir / "sample.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    service = DashboardService(workspace_root=tmp_path)
    state = service.load_real_instance("sample.xml")

    assert state["instance_inspector"]["source_kind"] == "real"
    assert state["instance_inspector"]["source_badge"] == "Real"
    assert state["instance_inspector"]["title"] == "SampleRobinX"
    assert any(item["label"] == "Teams" and item["value"] == 3 for item in state["instance_inspector"]["summary_items"])
    feature_groups = state["instance_inspector"]["feature_groups"]
    assert any(group["group"] == "size" for group in feature_groups)
    assert state["overview"]["benchmark_rows"] == 0


def test_generate_synthetic_preview_marks_instance_as_synthetic(tmp_path: Path) -> None:

    # Synthetic preview mode should create a labeled synthetic instance in the demo preview area.
    service = DashboardService(
        workspace_root=tmp_path,
        default_random_seed=5,
    )
    state = service.generate_synthetic_preview(
        difficulty_level="easy",
        random_seed=5,
    )

    assert state["instance_inspector"]["source_kind"] == "synthetic"
    assert state["instance_inspector"]["source_badge"] == "Synthetic"
    assert state["instance_inspector"]["mode"] == "synthetic"
    assert "data/raw/synthetic/demo_preview" in (state["instance_inspector"]["workspace_path"] or "")
    assert state["artifacts"]["synthetic_preview"]["exists"] is True


def test_bootstrap_demo_pipeline_creates_dashboard_artifacts(tmp_path: Path) -> None:

    # Running the dashboard bootstrap should generate artifacts and metrics.
    service = DashboardService(
        workspace_root=tmp_path,
        default_instance_count=4,
        default_random_seed=7,
        default_time_limit_seconds=1,
    )

    state = service.bootstrap_demo_pipeline(
        instance_count=4,
        random_seed=7,
        time_limit_seconds=1,
    )

    assert state["overview"]["instance_count"] == 4
    assert state["overview"]["feature_rows"] == 4
    assert state["overview"]["benchmark_rows"] == 12
    assert state["overview"]["selection_rows"] == 4
    assert state["training"]["model_name"] == "random_forest"
    assert 0.0 <= float(state["training"]["accuracy"]) <= 1.0
    assert state["evaluation"]["num_test_instances"] >= 1
    assert state["instance_inspector"]["source_kind"] == "synthetic"
    assert state["artifacts"]["demo_model"]["exists"] is True
    assert state["artifacts"]["demo_instances"]["path"].startswith("data/raw/synthetic/")
    assert state["previews"]["benchmarks"]


def test_dashboard_state_exposes_main_real_pipeline_artifacts(tmp_path: Path) -> None:

    # The dashboard should expose the latest main real-data pipeline artifacts separately.
    processed_dir = tmp_path / "data" / "processed"
    results_dir = tmp_path / "data" / "results"
    processed_dir.mkdir(parents=True)
    results_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "filename": "sample.xml",
                "parseable": True,
                "instance_name": "SampleRobinX",
                "teams": 4,
                "slots": 6,
                "number_of_constraints": 3,
                "parser_warnings": "",
            }
        ]
    ).to_csv(processed_dir / "real_dataset_inventory.csv", index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "SampleRobinX",
                "num_teams": 4,
                "num_slots": 6,
                "num_constraints": 3,
            }
        ]
    ).to_csv(processed_dir / "features.csv", index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "SampleRobinX",
                "solver_name": "simulated_annealing_baseline",
                "objective_value": 10.0,
                "runtime_seconds": 0.5,
                "feasible": True,
                "status": "FEASIBLE",
            },
            {
                "instance_name": "SampleRobinX",
                "solver_name": "random_baseline",
                "objective_value": 14.0,
                "runtime_seconds": 0.1,
                "feasible": True,
                "status": "placeholder_feasible",
            },
        ]
    ).to_csv(results_dir / "benchmark_results.csv", index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "SampleRobinX",
                "num_teams": 4,
                "num_slots": 6,
                "num_constraints": 3,
                "best_solver": "simulated_annealing_baseline",
            }
        ]
    ).to_csv(processed_dir / "selection_dataset.csv", index=False)
    pd.DataFrame(
        [{"feature": "num_teams", "importance": 0.75}],
    ).to_csv(results_dir / "random_forest_feature_importance.csv", index=False)
    pd.DataFrame(
        [
            {
                "summary_row_type": "aggregate_mean",
                "classification_accuracy": 1.0,
                "regret_vs_virtual_best": 0.0,
            }
        ]
    ).to_csv(results_dir / "selector_evaluation.csv", index=False)
    (results_dir / "random_forest_selector.joblib").write_text("placeholder", encoding="utf-8")
    (results_dir / "selector_evaluation_summary.csv").write_text("summary\n", encoding="utf-8")
    (results_dir / "selector_evaluation_summary.md").write_text("# Summary\n", encoding="utf-8")

    (results_dir / "random_forest_selector_run_summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-04T21:12:58+03:00",
                "settings": {"split_strategy": "repeated_stratified_kfold"},
                "outputs": {"model_output": "data/results/random_forest_selector.joblib"},
                "results": {
                    "accuracy": 1.0,
                    "balanced_accuracy": None,
                    "num_train_rows": 1,
                    "num_test_rows": 1,
                    "num_labeled_rows": 1,
                    "num_validation_splits": 1,
                },
            }
        ),
        encoding="utf-8",
    )
    (results_dir / "selector_evaluation_run_summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-04T21:13:01+03:00",
                "settings": {"split_strategy": "repeated_stratified_kfold"},
                "outputs": {"evaluation_summary_csv": "data/results/selector_evaluation_summary.csv"},
                "results": {
                    "single_best_solver_name": "simulated_annealing_baseline",
                    "classification_accuracy": 1.0,
                    "regret_vs_virtual_best": 0.0,
                    "num_test_instances": 1,
                    "num_validation_splits": 1,
                },
            }
        ),
        encoding="utf-8",
    )

    service = DashboardService(workspace_root=tmp_path)
    state = service.build_dashboard_state()

    assert state["main_pipeline"]["available"] is True
    assert state["main_pipeline"]["overview"]["parseable_real_files"] == 1
    assert state["main_pipeline"]["overview"]["benchmark_rows"] == 2
    assert state["main_pipeline"]["training"]["accuracy"] == 1.0
    assert state["main_pipeline"]["evaluation"]["single_best_solver_name"] == "simulated_annealing_baseline"
    assert state["main_pipeline"]["solver_leaderboard"]
    assert state["main_pipeline"]["feature_importance"]
    assert state["main_pipeline"]["previews"]["inventory"]


def test_dashboard_state_exposes_thesis_pipeline_results(tmp_path: Path) -> None:

    # The dashboard should expose thesis-mode artifacts separately from demo outputs.
    raw_dir = tmp_path / "data" / "raw" / "synthetic" / "generated"
    processed_dir = tmp_path / "data" / "processed" / "thesis_pipeline"
    results_dir = tmp_path / "data" / "results" / "thesis_pipeline"
    raw_dir.mkdir(parents=True)
    processed_dir.mkdir(parents=True)
    results_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "instance_name": "thesis_easy_001",
                "difficulty": "easy",
                "random_seed": 42,
                "team_count": 4,
            },
            {
                "instance_name": "thesis_hard_002",
                "difficulty": "hard",
                "random_seed": 42,
                "team_count": 12,
            },
        ]
    ).to_csv(raw_dir / "metadata.csv", index=False)
    pd.DataFrame(
        [
            {"instance_name": "thesis_easy_001", "num_teams": 4, "num_slots": 6, "num_constraints": 3},
            {"instance_name": "thesis_hard_002", "num_teams": 12, "num_slots": 14, "num_constraints": 12},
        ]
    ).to_csv(processed_dir / "features.csv", index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "thesis_easy_001",
                "solver_name": "cpsat_round_robin",
                "solver_registry_name": "cpsat_solver",
                "objective_value": 6.0,
                "runtime_seconds": 0.4,
                "feasible": True,
                "solver_support_status": "partial_support",
                "status": "FEASIBLE",
            },
            {
                "instance_name": "thesis_easy_001",
                "solver_name": "random_baseline",
                "solver_registry_name": "random_baseline",
                "objective_value": 12.0,
                "runtime_seconds": 0.1,
                "feasible": True,
                "solver_support_status": "simplified_baseline",
                "status": "placeholder_feasible",
            },
            {
                "instance_name": "thesis_hard_002",
                "solver_name": "simulated_annealing_baseline",
                "solver_registry_name": "simulated_annealing_solver",
                "objective_value": 20.0,
                "runtime_seconds": 1.2,
                "feasible": True,
                "solver_support_status": "simplified_baseline",
                "status": "FEASIBLE",
            },
            {
                "instance_name": "thesis_hard_002",
                "solver_name": "timefold",
                "solver_registry_name": "timefold",
                "objective_value": None,
                "runtime_seconds": 0.0,
                "feasible": False,
                "solver_support_status": "not_configured",
                "status": "NOT_CONFIGURED",
            },
        ]
    ).to_csv(results_dir / "full_benchmark_results.csv", index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "thesis_easy_001",
                "num_teams": 4,
                "num_slots": 6,
                "best_solver": "cpsat_round_robin",
            },
            {
                "instance_name": "thesis_hard_002",
                "num_teams": 12,
                "num_slots": 14,
                "best_solver": "simulated_annealing_baseline",
            },
        ]
    ).to_csv(processed_dir / "selection_dataset.csv", index=False)
    pd.DataFrame(
        [
            {
                "importance_rank": 1,
                "feature": "numeric__num_teams",
                "source_feature": "num_teams",
                "feature_group": "size",
                "importance": 0.7,
            }
        ]
    ).to_csv(results_dir / "feature_importance.csv", index=False)
    pd.DataFrame(
        [
            {
                "summary_row_type": "aggregate_mean",
                "single_best_solver_name": "cpsat_round_robin",
                "classification_accuracy": 0.75,
                "balanced_accuracy": 0.7,
                "average_selected_objective": 13.0,
                "average_virtual_best_objective": 12.0,
                "average_single_best_objective": 14.0,
                "regret_vs_virtual_best": 1.0,
                "delta_vs_single_best": -1.0,
                "improvement_vs_single_best": 1.0,
                "split_strategy": "holdout",
                "num_test_rows": 2,
            }
        ]
    ).to_csv(results_dir / "selector_evaluation_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "thesis_easy_001",
                "selected_solver": "cpsat_round_robin",
                "true_best_solver": "cpsat_round_robin",
            }
        ]
    ).to_csv(results_dir / "selector_evaluation.csv", index=False)
    (results_dir / "random_forest_selector.joblib").write_text("placeholder", encoding="utf-8")
    (results_dir / "selector_evaluation_summary.md").write_text("# Selector Evaluation Summary\n", encoding="utf-8")
    (results_dir / "thesis_pipeline_summary.md").write_text("# Thesis Experiment Pipeline Summary\n", encoding="utf-8")
    (results_dir / "selector_training_run_summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T12:00:00+03:00",
                "settings": {"split_strategy": "holdout"},
                "outputs": {"model_output": "data/results/thesis_pipeline/random_forest_selector.joblib"},
                "results": {
                    "accuracy": 0.75,
                    "balanced_accuracy": 0.7,
                    "num_train_rows": 6,
                    "num_test_rows": 2,
                    "num_labeled_rows": 8,
                    "num_validation_splits": 1,
                },
            }
        ),
        encoding="utf-8",
    )
    (results_dir / "selector_evaluation_run_summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T12:01:00+03:00",
                "settings": {"split_strategy": "holdout"},
                "outputs": {"evaluation_summary_csv": "data/results/thesis_pipeline/selector_evaluation_summary.csv"},
                "results": {
                    "single_best_solver_name": "cpsat_round_robin",
                    "classification_accuracy": 0.75,
                    "balanced_accuracy": 0.7,
                    "average_selected_objective": 13.0,
                    "average_virtual_best_objective": 12.0,
                    "average_single_best_objective": 14.0,
                    "regret_vs_virtual_best": 1.0,
                    "delta_vs_single_best": -1.0,
                    "improvement_vs_single_best": 1.0,
                    "num_test_instances": 2,
                    "num_validation_splits": 1,
                },
            }
        ),
        encoding="utf-8",
    )
    (results_dir / "thesis_pipeline_run_summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T12:02:00+03:00",
                "settings": {"dataset_size": 2, "time_limit_seconds": 5, "seed": 42},
                "results": {"dataset_generated": True},
            }
        ),
        encoding="utf-8",
    )

    service = DashboardService(workspace_root=tmp_path)
    state = service.build_dashboard_state()
    thesis = state["thesis_pipeline"]

    assert thesis["available"] is True
    assert thesis["scope"]["title"] == "Thesis Pipeline Results"
    assert thesis["overview"]["dataset_rows"] == 2
    assert thesis["overview"]["benchmark_rows"] == 4
    assert thesis["overview"]["feasible_runs"] == 3
    assert thesis["overview"]["support_counts"]["not_configured"] == 1
    assert thesis["training"]["accuracy"] == 0.75
    assert thesis["evaluation"]["average_virtual_best_objective"] == 12.0
    assert {row["method"] for row in thesis["selector_comparison"]} == {
        "Selector",
        "Single Best Solver",
        "Virtual Best Solver",
    }
    assert thesis["solver_leaderboard"]
    assert thesis["feature_importance"][0]["source_feature"] == "num_teams"
    assert thesis["charts"]["average_objective_per_solver"]
    assert thesis["charts"]["average_runtime_per_solver"]
    assert thesis["charts"]["solver_win_counts"]
    assert thesis["charts"]["selector_baseline_comparison"]
    assert thesis["charts"]["top_feature_importances"]
    assert thesis["artifacts"]["thesis_summary_report"]["exists"] is True

    browser = state["artifact_browser"]
    thesis_group = next(group for group in browser["groups"] if group["scope"] == "thesis")
    demo_group = next(group for group in browser["groups"] if group["scope"] == "demo")
    assert thesis_group["available_count"] >= 8
    assert demo_group["available_count"] == 0
    assert {artifact["scope"] for artifact in thesis_group["artifacts"]} == {"thesis"}

    csv_preview = service.preview_artifact("thesis_benchmark_results")
    markdown_preview = service.preview_artifact("thesis_summary_report")

    assert csv_preview["preview_kind"] == "csv"
    assert csv_preview["artifact"]["artifact_type"] == "Benchmark Results"
    assert csv_preview["total_rows"] == 4
    assert csv_preview["rows"][0]["instance_name"] == "thesis_easy_001"
    assert markdown_preview["preview_kind"] == "markdown"
    assert "Thesis Experiment Pipeline Summary" in markdown_preview["text"]


def test_dashboard_state_exposes_thesis_benchmark_reports(tmp_path: Path) -> None:

    # The dashboard should expose generated thesis benchmark reports in a separate section.
    reports_dir = tmp_path / "data" / "results" / "reports"
    reports_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "result_scope": "synthetic",
                "solver_registry_name": "cpsat_solver",
                "solver_name": "cpsat_round_robin",
                "num_instances_solved": 2,
                "coverage_ratio": 1.0,
                "win_count": 2,
                "average_objective": 9.0,
                "average_runtime_seconds": 0.5,
            },
            {
                "result_scope": "synthetic",
                "solver_registry_name": "random_baseline",
                "solver_name": "random_baseline",
                "num_instances_solved": 2,
                "coverage_ratio": 1.0,
                "win_count": 0,
                "average_objective": 20.0,
                "average_runtime_seconds": 0.1,
            },
        ]
    ).to_csv(reports_dir / "solver_comparison.csv", index=False)
    pd.DataFrame(
        [
            {
                "result_scope": "synthetic",
                "solver_registry_name": "cpsat_solver",
                "solver_name": "cpsat_round_robin",
                "win_count": 2,
            },
            {
                "result_scope": "synthetic",
                "solver_registry_name": "random_baseline",
                "solver_name": "random_baseline",
                "win_count": 0,
            },
        ]
    ).to_csv(reports_dir / "solver_win_counts.csv", index=False)
    pd.DataFrame(
        [
            {
                "result_scope": "synthetic",
                "solver_registry_name": "cpsat_solver",
                "solver_name": "cpsat_round_robin",
                "average_objective": 9.0,
                "num_instances_solved": 2,
            }
        ]
    ).to_csv(reports_dir / "average_objective_per_solver.csv", index=False)
    pd.DataFrame(
        [
            {
                "result_scope": "synthetic",
                "solver_registry_name": "cpsat_solver",
                "solver_name": "cpsat_round_robin",
                "average_runtime_seconds": 0.5,
                "num_runs": 2,
            }
        ]
    ).to_csv(reports_dir / "average_runtime_per_solver.csv", index=False)
    pd.DataFrame(
        [
            {
                "result_scope": "synthetic",
                "method": "selector",
                "reference_solver_name": None,
                "average_objective": 8.5,
                "objective_gap_vs_virtual_best": 0.5,
                "objective_gap_vs_single_best": -0.5,
                "classification_accuracy": 0.8,
                "balanced_accuracy": 0.75,
            },
            {
                "result_scope": "synthetic",
                "method": "single_best_solver",
                "reference_solver_name": "cpsat_round_robin",
                "average_objective": 9.0,
                "objective_gap_vs_virtual_best": 1.0,
                "objective_gap_vs_single_best": 0.0,
            },
            {
                "result_scope": "synthetic",
                "method": "virtual_best_solver",
                "reference_solver_name": "oracle",
                "average_objective": 8.0,
                "objective_gap_vs_virtual_best": 0.0,
                "objective_gap_vs_single_best": -1.0,
            },
        ]
    ).to_csv(reports_dir / "selector_vs_baselines.csv", index=False)
    pd.DataFrame(
        [
            {
                "result_scope": "synthetic",
                "importance_rank": 1,
                "feature": "numeric__num_teams",
                "source_feature": "num_teams",
                "feature_group": "size",
                "importance": 0.6,
                "importance_share": 0.6,
                "cumulative_importance_share": 0.6,
            }
        ]
    ).to_csv(reports_dir / "feature_importance_summary.csv", index=False)
    pd.DataFrame(
        [
            {
                "result_scope": "synthetic",
                "solver_registry_name": "cpsat_solver",
                "solver_name": "cpsat_round_robin",
                "solver_support_status": "supported",
                "scoring_status": "supported_feasible_run",
                "num_rows": 2,
                "num_feasible_runs": 2,
                "num_valid_feasible_runs": 2,
                "num_instances": 2,
                "row_ratio_within_solver": 1.0,
                "average_runtime_seconds": 0.5,
            }
        ]
    ).to_csv(reports_dir / "solver_support_summary.csv", index=False)
    (reports_dir / "thesis_benchmark_report.md").write_text(
        "# Thesis Benchmark And Selector Report\n\nSynthetic report fixture.\n",
        encoding="utf-8",
    )
    (reports_dir / "solver_comparison.md").write_text("# Solver Comparison Table\n", encoding="utf-8")
    (reports_dir / "solver_support_summary.md").write_text("# Solver Support Summary\n", encoding="utf-8")
    (reports_dir / "selector_vs_baselines.md").write_text("# Selector Vs Baselines\n", encoding="utf-8")
    (reports_dir / "feature_importance_summary.md").write_text("# Feature Importance Summary\n", encoding="utf-8")
    (reports_dir / "thesis_benchmark_report_run_summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-19T12:03:00+03:00",
                "settings": {
                    "result_scope": "auto",
                    "resolved_report_scope": "synthetic",
                    "top_feature_count": 15,
                },
                "results": {
                    "num_solver_rows": 2,
                    "num_selector_rows": 3,
                    "num_feature_importance_rows": 1,
                },
            }
        ),
        encoding="utf-8",
    )

    service = DashboardService(workspace_root=tmp_path)
    state = service.build_dashboard_state()
    reports = state["benchmark_reports"]

    assert reports["available"] is True
    assert state["thesis_reports"]["available"] is True
    assert reports["scope"]["title"] == "Thesis Reports"
    assert reports["scope"]["result_scope"] == "synthetic"
    assert reports["overview"]["solver_count"] == 2
    assert reports["overview"]["best_win_solver"] == "cpsat_round_robin"
    assert reports["overview"]["selector_average_objective"] == 8.5
    assert reports["overview"]["top_feature"] == "num_teams"
    assert reports["solver_comparison"][0]["solver_name"] == "cpsat_round_robin"
    assert reports["support_summary"][0]["solver_support_status"] == "supported"
    assert {row["method"] for row in reports["selector_vs_baselines"]} == {
        "selector",
        "single_best_solver",
        "virtual_best_solver",
    }
    assert reports["feature_importance_summary"][0]["source_feature"] == "num_teams"
    assert reports["markdown_reports"][0]["file_name"] == "thesis_benchmark_report.md"
    assert reports["artifacts"]["thesis_benchmark_report"]["exists"] is True

    report_group = next(group for group in state["artifact_browser"]["groups"] if group["scope"] == "reports")
    assert report_group["available_count"] >= 7
    assert {artifact["scope"] for artifact in report_group["artifacts"]} == {"reports"}

    csv_preview = service.preview_artifact("report_solver_comparison")
    markdown_preview = service.preview_artifact("report_summary_markdown")

    assert csv_preview["preview_kind"] == "csv"
    assert csv_preview["artifact"]["artifact_type"] == "Solver Comparison"
    assert csv_preview["rows"][0]["solver_name"] == "cpsat_round_robin"
    assert markdown_preview["preview_kind"] == "markdown"
    assert "Thesis Benchmark And Selector Report" in markdown_preview["text"]


def test_dashboard_state_exposes_mixed_dataset_results(tmp_path: Path) -> None:

    # The dashboard should expose mixed synthetic/real outputs without running pipelines.
    processed_dir = tmp_path / "data" / "processed"
    full_results_dir = tmp_path / "data" / "results" / "full_selection"
    processed_dir.mkdir(parents=True)
    full_results_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "instance_name": "synthetic_a",
                "dataset_type": "synthetic",
                "num_teams": 8,
                "num_slots": 14,
                "best_solver": "cpsat_solver",
                "benchmark_solver_support_coverage": "eligible=2/3; not_configured=1",
                "benchmark_eligible_solver_count": 2,
                "benchmark_best_solver_support_status": "supported",
                "benchmark_best_solver_scoring_status": "supported_feasible_run",
                "benchmark_best_solver_mean_objective": 12.0,
            },
            {
                "instance_name": "real_a",
                "dataset_type": "real",
                "num_teams": 16,
                "num_slots": 30,
                "best_solver": "simulated_annealing_solver",
                "benchmark_solver_support_coverage": "eligible=3/4; not_configured=1",
                "benchmark_eligible_solver_count": 3,
                "benchmark_best_solver_support_status": "simplified_baseline",
                "benchmark_best_solver_scoring_status": "legacy_feasible_run",
                "benchmark_best_solver_mean_objective": 28.0,
            },
        ]
    ).to_csv(processed_dir / "selection_dataset_full.csv", index=False)
    (processed_dir / "selection_dataset_full_run_summary.json").write_text(
        json.dumps(
            {
                "generated_at": "2026-04-20T18:21:37+03:00",
                "settings": {
                    "target_policy": "exclude_unsupported_not_configured_failed",
                    "feature_schema_policy": "intersection_of_synthetic_and_real_features",
                },
                "results": {
                    "rows_by_dataset_type": {"synthetic": 1, "real": 1},
                    "feature_schema": {"common_feature_column_count": 4},
                },
            }
        ),
        encoding="utf-8",
    )
    (full_results_dir / "selector_evaluation_run_summary.json").write_text(
        json.dumps(
            {
                "results": {
                    "single_best_solver_name": "cpsat_solver",
                    "classification_accuracy": 0.75,
                    "balanced_accuracy": 0.7,
                    "average_selected_objective": 20.0,
                    "average_virtual_best_objective": 19.0,
                    "average_single_best_objective": 21.0,
                    "regret_vs_virtual_best": 1.0,
                    "delta_vs_single_best": -1.0,
                    "num_validation_splits": 3,
                    "metrics_by_dataset_type": {
                        "synthetic": {
                            "classification_accuracy": 0.5,
                            "balanced_accuracy": 0.5,
                            "average_selected_objective": 12.0,
                            "average_virtual_best_objective": 11.0,
                            "average_single_best_objective": 13.0,
                            "regret_vs_virtual_best": 1.0,
                            "delta_vs_single_best": -1.0,
                        },
                        "real": {
                            "classification_accuracy": 1.0,
                            "average_selected_objective": 28.0,
                            "average_virtual_best_objective": 28.0,
                            "average_single_best_objective": 28.0,
                            "regret_vs_virtual_best": 0.0,
                            "delta_vs_single_best": 0.0,
                        },
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    service = DashboardService(workspace_root=tmp_path)
    state = service.build_dashboard_state()
    mixed = state["mixed_dataset"]

    assert mixed["available"] is True
    assert mixed["overview"]["synthetic_instances"] == 1
    assert mixed["overview"]["real_instances"] == 1
    assert mixed["overview"]["selector_classification_accuracy"] == 0.75
    assert {row["dataset_type"] for row in mixed["selector_metrics"]["rows"]} == {"all", "real", "synthetic"}
    assert mixed["counts_by_dataset_type"][0]["dataset_type"] == "real"
    assert mixed["preview_rows"][0]["instance_name"] == "synthetic_a"

    mixed_group = next(group for group in state["artifact_browser"]["groups"] if group["scope"] == "mixed")
    assert mixed_group["available_count"] == 1


def test_dashboard_state_exposes_presentation_ready_sections(tmp_path: Path) -> None:

    # The dashboard should expose the Latvian presentation-ready thesis view.
    results_dir = tmp_path / "data" / "results"
    processed_dir = tmp_path / "data" / "processed"
    thesis_tables_dir = results_dir / "thesis_tables"
    figures_dir = results_dir / "figures"
    full_selection_dir = results_dir / "full_selection"
    processed_dir.mkdir(parents=True)
    thesis_tables_dir.mkdir(parents=True)
    figures_dir.mkdir(parents=True)
    full_selection_dir.mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "Modeļa tips": "Random Forest klasifikators",
                "Labākais fiksētais algoritms": "Simulētā rūdīšana",
                "Precizitāte": 0.11,
                "Sabalansētā precizitāte": 0.22,
                "Vidējā izvēlētā kvalitāte": 10.0,
                "Vidējā virtual best kvalitāte": 9.0,
                "Vidējā single best kvalitāte": 11.0,
                "Regret pret virtual best": 1.0,
                "Uzlabojums pret single best": 0.0,
                "Validācijas sadalījumu skaits": 9,
                "Testa instanču skaits": 252,
            }
        ]
    ).to_csv(thesis_tables_dir / "selector_results_table.csv", index=False)
    pd.DataFrame(
        [
            {
                "Datu kopa": "Reālie dati",
                "Precizitāte": 0.99,
                "Sabalansētā precizitāte": None,
                "Vidējā izvēlētā kvalitāte": 31.90,
                "Vidējā virtual best kvalitāte": 31.89,
                "Vidējā single best kvalitāte": 31.89,
                "Regret pret virtual best": 0.02,
                "Uzlabojums pret single best": 0.00,
            },
            {
                "Datu kopa": "Sintētiskie dati",
                "Precizitāte": 0.81,
                "Sabalansētā precizitāte": 0.80,
                "Vidējā izvēlētā kvalitāte": 13.45,
                "Vidējā virtual best kvalitāte": 12.84,
                "Vidējā single best kvalitāte": 13.65,
                "Regret pret virtual best": 0.62,
                "Uzlabojums pret single best": 0.20,
            },
        ]
    ).to_csv(thesis_tables_dir / "real_vs_synthetic_table.csv", index=False)
    pd.DataFrame(
        [
            {
                "Datu kopa": "Reālie dati",
                "Algoritms": "Simulētā rūdīšana",
                "Uzvaras": 54,
                "Vidējā kvalitāte": 30.75,
                "Vidējais laiks (s)": 1.81,
                "Feasible pārklājums": 1.0,
                "Salīdzināmais pārklājums": 1.0,
            }
        ]
    ).to_csv(thesis_tables_dir / "solver_comparison_table.csv", index=False)
    pd.DataFrame(
        [
            {"Datu kopa": "Reālie dati", "Algoritms": "Simulētā rūdīšana", "Skaits": 54}
        ]
    ).to_csv(thesis_tables_dir / "solver_win_distribution_table.csv", index=False)
    pd.DataFrame(
        [
            {"Rangs": 1, "Pazīme": "estimated minimum slots", "Grupa": "Izmērs", "Nozīmīgums": 0.11}
        ]
    ).to_csv(thesis_tables_dir / "feature_importance_table.csv", index=False)
    pd.DataFrame(
        [
            {"Grupa": "Izmērs", "Kopējais nozīmīgums": 0.30, "Īpatsvars": 0.45}
        ]
    ).to_csv(thesis_tables_dir / "feature_group_summary_table.csv", index=False)
    pd.DataFrame(
        [
            {"Rādītājs": "Kopējais instanču skaits", "Vērtība": 234},
            {"Rādītājs": "Reālo instanču skaits", "Vērtība": 54},
            {"Rādītājs": "Sintētisko instanču skaits", "Vērtība": 180},
            {"Rādītājs": "Izmantotais modeļa tips", "Vērtība": "Random Forest klasifikators"},
        ]
    ).to_csv(thesis_tables_dir / "dataset_summary_table.csv", index=False)
    pd.DataFrame(
        [
            {
                "instance_name": "real_1",
                "dataset_type": "real",
                "best_solver": "simulated_annealing_solver",
                "num_teams": 16,
                "num_slots": 30,
            },
            {
                "instance_name": "real_2",
                "dataset_type": "real",
                "best_solver": "simulated_annealing_solver",
                "num_teams": 18,
                "num_slots": 34,
            },
            {
                "instance_name": "synthetic_1",
                "dataset_type": "synthetic",
                "best_solver": "cpsat_solver",
                "num_teams": 8,
                "num_slots": 14,
            },
            {
                "instance_name": "synthetic_2",
                "dataset_type": "synthetic",
                "best_solver": "cpsat_solver",
                "num_teams": 10,
                "num_slots": 18,
            },
        ]
    ).to_csv(processed_dir / "selection_dataset_full.csv", index=False)
    (results_dir / "thesis_figures_index.md").write_text("# Attēli\n", encoding="utf-8")
    pd.DataFrame(
        [
            {"instance_name": "real_1", "solver_registry_name": "random_baseline"},
            {"instance_name": "real_1", "solver_registry_name": "cpsat_solver"},
            {"instance_name": "real_1", "solver_registry_name": "simulated_annealing_solver"},
            {"instance_name": "real_1", "solver_registry_name": "timefold"},
        ]
    ).to_csv(full_selection_dir / "combined_benchmark_results.csv", index=False)
    pd.DataFrame(
        [
            {
                "summary_row_type": "aggregate_mean",
                "dataset_type": "all",
                "single_best_solver_name": "simulated_annealing_solver",
                "classification_accuracy": 0.9285714285714286,
                "balanced_accuracy": 0.8817596252378861,
                "average_selected_objective": 25.34126984126984,
                "average_virtual_best_objective": 25.107142857142854,
                "average_single_best_objective": 25.404761904761905,
                "regret_vs_virtual_best": 0.23412698412698418,
                "delta_vs_single_best": -0.06349206349206327,
                "improvement_vs_single_best": 0.06349206349206327,
            }
        ]
    ).to_csv(full_selection_dir / "selector_evaluation_summary.csv", index=False)
    (full_selection_dir / "selector_evaluation_run_summary.json").write_text(
        json.dumps({"settings": {"cross_validation_folds": 3, "repeats": 3}}),
        encoding="utf-8",
    )

    for figure_name in (
        "selector_performance.png",
        "dataset_distribution.png",
        "best_solver_class_distribution.png",
        "constraint_distribution.png",
        "teams_vs_slots_plot.png",
        "real_vs_synthetic.png",
        "objective_distribution.png",
        "runtime_distribution.png",
        "solver_comparison.png",
        "solver_runtime.png",
        "solver_win_distribution.png",
        "feature_importance.png",
        "feature_correlation_matrix.png",
        "constraints_vs_objective.png",
        "accuracy_by_dataset_type.png",
        "regret_distribution.png",
        "confusion_matrix.png",
    ):
        (figures_dir / figure_name).write_bytes(b"png")

    service = DashboardService(workspace_root=tmp_path)
    state = service.build_dashboard_state()

    presentation = state["presentation_dashboard"]
    assert presentation["available"] is True
    assert presentation["header"]["title"] == "Maģistra darba praktiskās daļas pārskats"
    assert [item["id"] for item in presentation["navigation"]] == [
        "overview",
        "workflow",
        "results",
        "solver",
        "best_solver",
        "features",
        "datasets",
        "methodology",
        "implementation",
    ]
    assert presentation["sections"]["workflow"]["cards"]
    assert len(presentation["sections"]["workflow"]["table_rows"]) == 8
    assert any(card["value"] == "2 pazīmes" for card in presentation["sections"]["workflow"]["cards"])
    assert any(
        row["Artefakts"] == "Jauktā algoritmu izvēles datu kopa"
        for row in presentation["sections"]["workflow"]["artifact_rows"]
    )
    assert presentation["sections"]["workflow"]["code_table_title"] == "Svarīgākie koda faili"
    assert len(presentation["sections"]["workflow"]["code_rows"]) == 8
    assert any(
        row["Darba posms"] == "Modeļa apmācība un novērtēšana"
        and "src/selection/train_selector.py" in row["Koda fails"]
        for row in presentation["sections"]["workflow"]["code_rows"]
    )
    assert presentation["sections"]["overview"]["cards"]
    assert presentation["sections"]["results"]["cards"]
    assert presentation["sections"]["overview"]["takeaway"]
    assert presentation["sections"]["results"]["takeaway"]
    assert presentation["sections"]["methodology"]["cards"]
    assert presentation["sections"]["methodology"]["table_rows"]
    assert presentation["sections"]["implementation"]["cards"]
    assert len(presentation["sections"]["implementation"]["table_rows"]) == 8
    assert presentation["sections"]["implementation"]["table_title"] == "Īstenotie praktiskās daļas posmi"
    assert any(
        row["Artefakts"] == "Jauktā algoritmu izvēles datu kopa"
        and row["Statuss"] == "Ir"
        for row in presentation["sections"]["implementation"]["artifact_rows"]
    )
    assert presentation["sections"]["solver"]["table_rows"]
    assert "Loma" in presentation["sections"]["solver"]["table_rows"][0]
    assert "Interpretācijas tvērums" in presentation["sections"]["solver"]["table_rows"][0]
    assert presentation["sections"]["best_solver"]["table_rows"]
    assert any(card["value"] == "2 aktīvas klases" for card in presentation["sections"]["best_solver"]["cards"])
    assert presentation["sections"]["datasets"]["table_rows"]
    assert [card["value"] for card in presentation["sections"]["results"]["cards"]] == [
        "0,9286",
        "0,8818",
        "0,2341",
        "0,0635",
    ]
    assert [figure["id"] for figure in presentation["sections"]["overview"]["figures"]] == [
        "dataset_distribution",
    ]
    assert [figure["id"] for figure in presentation["sections"]["results"]["figures"]] == [
        "selector_vs_baselines",
    ]
    assert presentation["sections"]["solver"]["figures"] == []
    assert [figure["id"] for figure in presentation["sections"]["best_solver"]["figures"]] == [
        "best_solver_class_distribution",
    ]
    assert [figure["id"] for figure in presentation["sections"]["features"]["figures"]] == [
        "feature_importance",
    ]
    assert presentation["sections"]["datasets"]["figures"] == []
    assert presentation["sections"]["methodology"]["figures"] == []
    assert any(card["value"] == "2 aktīvas klases" for card in presentation["sections"]["methodology"]["cards"])
    assert any(item["id"] == "methodology" for item in presentation["navigation"])
    assert any(item["id"] == "implementation" for item in presentation["navigation"])
    assert presentation["sections"]["overview"]["figures"][0]["exists"] is True


def test_dashboard_resolves_generated_results_files_only(tmp_path: Path) -> None:

    # Generated-file serving should stay inside data/results.
    results_dir = tmp_path / "data" / "results" / "figures"
    results_dir.mkdir(parents=True)
    figure_path = results_dir / "selector_performance.png"
    figure_path.write_bytes(b"png")

    service = DashboardService(workspace_root=tmp_path)

    resolved = service.resolve_generated_file("data/results/figures/selector_performance.png")

    assert resolved == figure_path.resolve()


def test_dashboard_rejects_generated_path_outside_results(tmp_path: Path) -> None:

    # A sibling folder with a similar prefix must not pass the results whitelist.
    sibling_dir = tmp_path / "data" / "results_backup"
    sibling_dir.mkdir(parents=True)
    (sibling_dir / "selector_performance.png").write_bytes(b"png")

    service = DashboardService(workspace_root=tmp_path)

    with pytest.raises(ValueError, match="outside the allowed results directory"):
        service.resolve_generated_file("data/results_backup/selector_performance.png")
