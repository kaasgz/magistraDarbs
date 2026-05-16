
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.experiments.full_benchmark import DEFAULT_FULL_SOLVER_PORTFOLIO
from src.experiments.run_thesis_pipeline import main, run_thesis_pipeline


FIXED_TIMESTAMP = "2026-04-19T12:00:00+00:00"


def test_run_thesis_pipeline_produces_thesis_ready_artifacts(
    tmp_path: Path,
    capsys,
) -> None:

    dataset_folder = tmp_path / "data" / "raw" / "synthetic" / "generated"
    processed_dir = tmp_path / "data" / "processed" / "thesis_pipeline"
    results_dir = tmp_path / "data" / "results" / "thesis_pipeline"

    result = run_thesis_pipeline(
        dataset_size=4,
        time_limit_seconds=1,
        seed=37,
        dataset_folder=dataset_folder,
        processed_dir=processed_dir,
        results_dir=results_dir,
        difficulty="easy",
        generation_timestamp=FIXED_TIMESTAMP,
        split_strategy="holdout",
        test_size=0.25,
        repeats=1,
    )
    output = capsys.readouterr().out

    assert result.generated_dataset is True
    assert result.num_instances == 4
    assert result.metadata_csv.exists()
    assert result.features_csv.exists()
    assert result.benchmark_csv.exists()
    assert result.selection_dataset_csv.exists()
    assert result.model_path.exists()
    assert result.feature_importance_csv is not None
    assert result.feature_importance_csv.exists()
    assert result.evaluation_report_csv.exists()
    assert result.evaluation_summary_csv.exists()
    assert result.evaluation_summary_markdown.exists()
    assert result.summary_report.exists()
    assert result.run_summary_json.exists()

    benchmarks = pd.read_csv(result.benchmark_csv)
    selection_dataset = pd.read_csv(result.selection_dataset_csv)

    assert set(benchmarks["solver_registry_name"]) == set(DEFAULT_FULL_SOLVER_PORTFOLIO)
    assert "solver_support_status" in benchmarks.columns
    assert len(benchmarks.index) == 4 * len(DEFAULT_FULL_SOLVER_PORTFOLIO)
    assert len(selection_dataset.index) == 4
    assert selection_dataset["best_solver"].notna().all()
    assert 0.0 <= result.selector_accuracy <= 1.0

    summary_text = result.summary_report.read_text(encoding="utf-8")
    assert "Thesis Experiment Pipeline Summary" in summary_text
    assert "Benchmark results" in summary_text
    assert "Top Feature Importance" in summary_text
    assert "[1/7] Ensure synthetic dataset..." in output
    assert "[7/7] Write thesis summary report..." in output
    assert "Thesis pipeline completed successfully." in output


def test_thesis_pipeline_cli_fails_cleanly_for_invalid_dataset_size(
    tmp_path: Path,
    capsys,
) -> None:

    exit_code = main(
        [
            "--dataset-size",
            "1",
            "--dataset-folder",
            str(tmp_path / "generated"),
            "--processed-dir",
            str(tmp_path / "processed"),
            "--results-dir",
            str(tmp_path / "results"),
        ]
    )
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Thesis pipeline failed" in output
    assert "dataset_size must be at least 2" in output
