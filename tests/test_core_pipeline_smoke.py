# End-to-end smoke test for the core thesis pipeline.

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.demo.generate_demo_instances import generate_demo_instances
from src.experiments.run_benchmarks import run_benchmarks
from src.features.build_feature_table import build_feature_table
from src.parsers import load_instance
from src.selection.build_selection_dataset import build_selection_dataset
from src.selection.evaluate_selector import evaluate_selector
from src.selection.train_selector import train_selector


FIXED_TIMESTAMP = "2026-04-04T12:00:00+00:00"


def test_core_pipeline_smoke_runs_from_instances_to_selector_artifacts(tmp_path: Path) -> None:

    # A tiny deterministic synthetic batch should exercise the full core pipeline.
    input_dir = tmp_path / "data" / "raw" / "synthetic" / "smoke_instances"
    manifest_path = tmp_path / "data" / "processed" / "smoke_manifest.json"
    features_csv = tmp_path / "data" / "processed" / "smoke_features.csv"
    benchmark_csv = tmp_path / "data" / "results" / "smoke_benchmark_results.csv"
    selection_dataset_csv = tmp_path / "data" / "processed" / "smoke_selection_dataset.csv"
    model_path = tmp_path / "data" / "results" / "smoke_selector.joblib"
    importance_csv = tmp_path / "data" / "results" / "smoke_feature_importance.csv"
    evaluation_csv = tmp_path / "data" / "results" / "smoke_selector_evaluation.csv"
    evaluation_summary_csv = tmp_path / "data" / "results" / "smoke_selector_evaluation_summary.csv"
    evaluation_summary_markdown = tmp_path / "data" / "results" / "smoke_selector_evaluation_summary.md"

    generation_result = generate_demo_instances(
        output_folder=input_dir,
        manifest_path=manifest_path,
        instance_count=4,
        random_seed=17,
        difficulty_level="easy",
        generation_timestamp=FIXED_TIMESTAMP,
    )

    xml_files = sorted(input_dir.glob("*.xml"))
    assert generation_result.instance_count == 4
    assert len(xml_files) == 4

    parsed_instance = load_instance(str(xml_files[0]))
    assert parsed_instance.team_count > 0
    assert parsed_instance.metadata.synthetic is True

    features_path = build_feature_table(
        input_folder=input_dir,
        output_csv=features_csv,
        random_seed=17,
    )
    benchmark_path = run_benchmarks(
        instance_folder=str(input_dir),
        solver_names=["random_baseline", "simulated_annealing_solver"],
        time_limit_seconds=1,
        random_seed=17,
        output_csv=benchmark_csv,
    )
    selection_dataset_path = build_selection_dataset(
        features_csv=features_path,
        benchmark_csv=benchmark_path,
        output_csv=selection_dataset_csv,
        include_solver_objectives=True,
    )
    training_result = train_selector(
        dataset_csv=selection_dataset_path,
        model_path=model_path,
        feature_importance_csv=importance_csv,
        random_seed=17,
        test_size=0.25,
        split_strategy="holdout",
    )
    evaluation_result = evaluate_selector(
        dataset_csv=selection_dataset_path,
        benchmark_csv=benchmark_path,
        model_path=model_path,
        report_csv=evaluation_csv,
        summary_csv=evaluation_summary_csv,
        summary_markdown=evaluation_summary_markdown,
        random_seed=17,
        test_size=0.25,
        split_strategy="holdout",
    )

    features = pd.read_csv(features_path)
    benchmarks = pd.read_csv(benchmark_path)
    selection_dataset = pd.read_csv(selection_dataset_path)
    evaluation_report = pd.read_csv(evaluation_csv)
    evaluation_summary = pd.read_csv(evaluation_summary_csv)

    assert len(features.index) == 4
    assert {"instance_name", "num_teams", "num_slots", "num_constraints"} <= set(features.columns)

    assert len(benchmarks.index) == 8
    assert set(benchmarks["solver_registry_name"]) == {"random_baseline", "simulated_annealing_solver"}
    assert benchmarks["objective_value"].notna().all()

    assert len(selection_dataset.index) == 4
    assert "best_solver" in selection_dataset.columns
    assert selection_dataset["best_solver"].notna().all()

    assert model_path.exists()
    assert importance_csv.exists()
    assert training_result.num_labeled_rows == 4
    assert training_result.num_validation_splits == 1

    assert evaluation_result.report_path == evaluation_csv
    assert evaluation_result.summary_csv_path == evaluation_summary_csv
    assert evaluation_result.summary_markdown_path == evaluation_summary_markdown
    assert evaluation_result.num_validation_splits == 1
    assert evaluation_result.num_test_instances >= 1
    assert 0.0 <= evaluation_result.classification_accuracy <= 1.0
    assert not evaluation_report.empty
    assert "aggregate_mean" in set(evaluation_summary["summary_row_type"])
    assert evaluation_summary_markdown.exists()
    assert "Selector Evaluation Summary" in evaluation_summary_markdown.read_text(encoding="utf-8")
