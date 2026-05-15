"""Tests for the full run-all pipeline orchestrator."""

from __future__ import annotations

from pathlib import Path

from src.demo.generate_demo_instances import generate_demo_instances
from src.experiments.run_all_pipeline import main, run_all_pipeline


FIXED_TIMESTAMP = "2026-04-04T12:00:00+00:00"


def test_run_all_pipeline_executes_core_steps_and_prints_progress(
    tmp_path: Path,
    capsys,
) -> None:
    """The orchestration helper should run the core pipeline in the documented order."""

    input_dir = tmp_path / "instances"
    manifest_path = tmp_path / "data" / "processed" / "pipeline_manifest.json"
    feature_config_path = tmp_path / "feature_config.yaml"
    benchmark_config_path = tmp_path / "benchmark_config.yaml"
    selector_config_path = tmp_path / "selector_config.yaml"
    pipeline_config_path = tmp_path / "pipeline_config.yaml"

    inventory_csv = tmp_path / "data" / "processed" / "real_dataset_inventory.csv"
    features_csv = tmp_path / "data" / "processed" / "features.csv"
    benchmark_csv = tmp_path / "data" / "results" / "benchmark_results.csv"
    selection_dataset_csv = tmp_path / "data" / "processed" / "selection_dataset.csv"
    model_path = tmp_path / "data" / "results" / "selector.joblib"
    importance_csv = tmp_path / "data" / "results" / "feature_importance.csv"
    evaluation_csv = tmp_path / "data" / "results" / "selector_evaluation.csv"
    evaluation_summary_csv = tmp_path / "data" / "results" / "selector_evaluation_summary.csv"
    evaluation_summary_markdown = tmp_path / "data" / "results" / "selector_evaluation_summary.md"

    generate_demo_instances(
        output_folder=input_dir,
        manifest_path=manifest_path,
        instance_count=4,
        random_seed=17,
        difficulty_level="easy",
        generation_timestamp=FIXED_TIMESTAMP,
    )

    feature_config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  instance_folder: {input_dir.as_posix()}",
                f"  output_csv: {features_csv.as_posix()}",
                "run:",
                "  random_seed: 17",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    benchmark_config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  instance_folder: {input_dir.as_posix()}",
                f"  output_csv: {benchmark_csv.as_posix()}",
                "run:",
                "  random_seed: 17",
                "  time_limit_seconds: 1",
                "solvers:",
                "  selected:",
                "    - random_baseline",
                "    - simulated_annealing_solver",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    selector_config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  features_csv: {features_csv.as_posix()}",
                f"  benchmark_results_csv: {benchmark_csv.as_posix()}",
                f"  selection_dataset_csv: {selection_dataset_csv.as_posix()}",
                f"  model_output: {model_path.as_posix()}",
                f"  feature_importance_csv: {importance_csv.as_posix()}",
                f"  evaluation_report_csv: {evaluation_csv.as_posix()}",
                f"  evaluation_summary_csv: {evaluation_summary_csv.as_posix()}",
                f"  evaluation_summary_markdown: {evaluation_summary_markdown.as_posix()}",
                "run:",
                "  random_seed: 17",
                "split:",
                "  strategy: holdout",
                "  test_size: 0.25",
                "  repeats: 1",
                "selector:",
                "  model_choice: random_forest",
                "dataset:",
                "  include_solver_objectives: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    pipeline_config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  feature_config: {feature_config_path.as_posix()}",
                f"  benchmark_config: {benchmark_config_path.as_posix()}",
                f"  selector_config: {selector_config_path.as_posix()}",
                f"  inventory_input_folder: {input_dir.as_posix()}",
                f"  inventory_output_csv: {inventory_csv.as_posix()}",
                "run:",
                "  include_inventory: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = run_all_pipeline(config_path=pipeline_config_path)
    output = capsys.readouterr().out

    assert result.inventory_csv == inventory_csv
    assert result.features_csv == features_csv
    assert result.benchmark_csv == benchmark_csv
    assert result.selection_dataset_csv == selection_dataset_csv
    assert result.model_path == model_path
    assert result.feature_importance_csv == importance_csv
    assert result.evaluation_report_csv == evaluation_csv
    assert result.evaluation_summary_csv == evaluation_summary_csv
    assert result.evaluation_summary_markdown == evaluation_summary_markdown

    assert inventory_csv.exists()
    assert features_csv.exists()
    assert benchmark_csv.exists()
    assert selection_dataset_csv.exists()
    assert model_path.exists()
    assert importance_csv.exists()
    assert evaluation_csv.exists()
    assert evaluation_summary_csv.exists()
    assert evaluation_summary_markdown.exists()

    assert "[1/6] Build dataset inventory..." in output
    assert "[2/6] Build feature table..." in output
    assert "[3/6] Run benchmarks..." in output
    assert "[4/6] Build selection dataset..." in output
    assert "[5/6] Train selector..." in output
    assert "[6/6] Evaluate selector..." in output
    assert "Pipeline completed successfully." in output


def test_run_all_pipeline_main_fails_gracefully_for_missing_config(
    tmp_path: Path,
    capsys,
) -> None:
    """The CLI entrypoint should stop cleanly on a critical configuration error."""

    missing_config_path = tmp_path / "missing_pipeline_config.yaml"

    exit_code = main(["--config", str(missing_config_path)])
    output = capsys.readouterr().out

    assert exit_code == 1
    assert "Pipeline failed" in output
