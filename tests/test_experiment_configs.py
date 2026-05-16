# Tests for YAML-configured experiment and selection workflows.

from __future__ import annotations

import csv
import sys
from pathlib import Path

import pandas as pd

from src.features.build_feature_table import build_feature_table_from_config
from src.experiments.run_benchmarks import run_benchmarks_from_config
from src.selection import (
    analyze_selector_errors_from_config,
    build_selection_dataset_from_config,
    evaluate_selector_from_config,
    run_ablation_study_from_config,
    train_selector_from_config,
)


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"


def test_build_feature_table_from_config_uses_yaml_values(tmp_path: Path) -> None:

    # Feature-table generation should load its inputs and outputs from YAML config.
    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "sample.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    output_csv = tmp_path / "features.csv"
    summary_json = tmp_path / "features_run_summary.json"
    config_path = tmp_path / "feature_config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  instance_folder: {input_dir.as_posix()}",
                f"  output_csv: {output_csv.as_posix()}",
                f"  run_summary: {summary_json.as_posix()}",
                "run:",
                "  random_seed: 9",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    written_path = build_feature_table_from_config(config_path)

    assert written_path == output_csv
    assert output_csv.exists()
    assert summary_json.exists()


def test_run_benchmarks_from_config_uses_yaml_values(tmp_path: Path) -> None:

    # Benchmark execution should load its inputs and outputs from YAML config.
    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "sample.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    output_csv = tmp_path / "benchmark_results.csv"
    summary_json = tmp_path / "benchmark_run_summary.json"
    config_path = tmp_path / "benchmark_config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  instance_folder: {input_dir.as_posix()}",
                f"  output_csv: {output_csv.as_posix()}",
                f"  run_summary: {summary_json.as_posix()}",
                "run:",
                "  random_seed: 9",
                "  time_limit_seconds: 1",
                "solvers:",
                "  selected:",
                "    - random_baseline",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    written_path = run_benchmarks_from_config(config_path)

    assert written_path == output_csv
    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["instance_name"] == "SampleRobinX"
    assert rows[0]["solver_name"] == "random_baseline"
    assert summary_json.exists()


def test_run_benchmarks_from_config_supports_timefold_solver_settings(tmp_path: Path) -> None:

    # Benchmark YAML should forward per-solver settings to the Timefold wrapper.
    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "tiny.xml").write_text(
        "\n".join(
            [
                "<Instance name=\"TinyTimefold\">",
                "  <MetaData>",
                "    <Name>TinyTimefold</Name>",
                "    <RoundRobinMode>single</RoundRobinMode>",
                "  </MetaData>",
                "  <Teams>",
                "    <Team id=\"T1\" name=\"Team 1\" />",
                "    <Team id=\"T2\" name=\"Team 2\" />",
                "  </Teams>",
                "  <Slots>",
                "    <Slot id=\"S1\" name=\"Round 1\" />",
                "  </Slots>",
                "</Instance>",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    adapter_path = tmp_path / "fake_timefold_adapter.py"
    adapter_path.write_text(
        "\n".join(
            [
                "from __future__ import annotations",
                "",
                "import argparse",
                "import json",
                "from pathlib import Path",
                "",
                "parser = argparse.ArgumentParser()",
                "parser.add_argument('--input', required=True)",
                "parser.add_argument('--output', required=True)",
                "parser.add_argument('--time-limit-seconds', dest='time_limit_seconds', required=True)",
                "parser.add_argument('--random-seed', dest='random_seed', required=True)",
                "args = parser.parse_args()",
                "",
                "input_path = Path(args.input)",
                "output_path = Path(args.output)",
                "payload = json.loads(input_path.read_text(encoding='utf-8'))",
                "meeting = payload['modelInput']['meetings'][0]",
                "slot = payload['modelInput']['slots'][0]",
                "result = {",
                "    'status': 'SOLVED',",
                "    'feasible': True,",
                "    'objectiveValue': 1.0,",
                "    'runtimeSeconds': 0.1,",
                "    'schedule': [{'meetingId': meeting['id'], 'slotId': slot['id']}],",
                "}",
                "output_path.write_text(json.dumps(result), encoding='utf-8')",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    output_csv = tmp_path / "benchmark_results.csv"
    summary_json = tmp_path / "benchmark_run_summary.json"
    config_path = tmp_path / "benchmark_config.yaml"
    config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  instance_folder: {input_dir.as_posix()}",
                f"  output_csv: {output_csv.as_posix()}",
                f"  run_summary: {summary_json.as_posix()}",
                "run:",
                "  random_seed: 9",
                "  time_limit_seconds: 60",
                "solvers:",
                "  selected:",
                "    - timefold",
                "  settings:",
                "    timefold:",
                f"      executable_path: {Path(sys.executable).as_posix()}",
                "      command_arguments:",
                f"        - {adapter_path.as_posix()}",
                "      time_limit_seconds: 2",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    written_path = run_benchmarks_from_config(config_path)

    assert written_path == output_csv
    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 1
    assert rows[0]["instance_name"] == "TinyTimefold"
    assert rows[0]["solver_name"] == "timefold"
    assert rows[0]["solver_registry_name"] == "timefold"
    assert rows[0]["configured_time_limit_seconds"] == "2"
    assert rows[0]["feasible"] == "True"
    assert rows[0]["error_message"] == ""
    assert summary_json.exists()


def test_selector_pipeline_can_run_from_selector_config(tmp_path: Path) -> None:

    # Selection dataset building, training, evaluation, and error analysis should honor YAML config.
    features_csv = tmp_path / "features.csv"
    benchmarks_csv = tmp_path / "benchmark_results.csv"
    selection_dataset_csv = tmp_path / "selection_dataset.csv"
    selection_summary_json = tmp_path / "selection_dataset_run_summary.json"
    model_output = tmp_path / "selector.joblib"
    importance_csv = tmp_path / "feature_importance.csv"
    training_summary_json = tmp_path / "selector_training_run_summary.json"
    evaluation_report_csv = tmp_path / "selector_evaluation.csv"
    evaluation_summary_csv = tmp_path / "selector_evaluation_summary.csv"
    evaluation_summary_markdown = tmp_path / "selector_evaluation_summary.md"
    evaluation_summary_json = tmp_path / "selector_evaluation_run_summary.json"
    ablation_summary_csv = tmp_path / "selector_ablation_summary.csv"
    ablation_plot = tmp_path / "selector_ablation.png"
    ablation_report_markdown = tmp_path / "selector_ablation.md"
    ablation_summary_json = tmp_path / "selector_ablation_run_summary.json"
    error_output_dir = tmp_path / "error_analysis"
    error_summary_json = tmp_path / "selector_error_analysis_run_summary.json"
    config_path = tmp_path / "selector_config.yaml"

    pd.DataFrame(
        [
            {
                "instance_name": f"inst_{index}",
                "num_teams": 4 if index < 6 else 8,
                "num_slots": 3 if index < 6 else 7,
                "num_hard_constraints": 2 if index < 6 else 6,
                "num_soft_constraints": 1 if index < 6 else 4,
                "constraints_per_team": 0.5 if index < 6 else 1.5,
                "objective_name": "compact" if index % 2 == 0 else "balanced",
                "objective_present": bool(index % 2),
            }
            for index in range(12)
        ]
    ).to_csv(features_csv, index=False)

    benchmark_rows: list[dict[str, object]] = []
    for index in range(12):
        instance_name = f"inst_{index}"
        solver_a_best = index < 6
        benchmark_rows.extend(
            [
                {
                    "instance_name": instance_name,
                    "solver_name": "solver_a",
                    "objective_value": 1.0 if solver_a_best else 9.0,
                    "runtime_seconds": 1.0 + 0.01 * index,
                    "feasible": True,
                    "status": "OPTIMAL",
                },
                {
                    "instance_name": instance_name,
                    "solver_name": "solver_b",
                    "objective_value": 9.0 if solver_a_best else 1.0,
                    "runtime_seconds": 1.1 + 0.01 * index,
                    "feasible": True,
                    "status": "OPTIMAL",
                },
            ]
        )
    pd.DataFrame(benchmark_rows).to_csv(benchmarks_csv, index=False)

    config_path.write_text(
        "\n".join(
            [
                "paths:",
                f"  features_csv: {features_csv.as_posix()}",
                f"  benchmark_results_csv: {benchmarks_csv.as_posix()}",
                f"  selection_dataset_csv: {selection_dataset_csv.as_posix()}",
                f"  selection_dataset_run_summary: {selection_summary_json.as_posix()}",
                f"  model_output: {model_output.as_posix()}",
                f"  feature_importance_csv: {importance_csv.as_posix()}",
                f"  training_run_summary: {training_summary_json.as_posix()}",
                f"  evaluation_report_csv: {evaluation_report_csv.as_posix()}",
                f"  evaluation_summary_csv: {evaluation_summary_csv.as_posix()}",
                f"  evaluation_summary_markdown: {evaluation_summary_markdown.as_posix()}",
                f"  evaluation_run_summary: {evaluation_summary_json.as_posix()}",
                f"  ablation_summary_csv: {ablation_summary_csv.as_posix()}",
                f"  ablation_plot: {ablation_plot.as_posix()}",
                f"  ablation_report_markdown: {ablation_report_markdown.as_posix()}",
                f"  ablation_run_summary: {ablation_summary_json.as_posix()}",
                f"  error_analysis_output_dir: {error_output_dir.as_posix()}",
                f"  error_analysis_run_summary: {error_summary_json.as_posix()}",
                "run:",
                "  random_seed: 7",
                "  time_limit_seconds: 60",
                "solvers:",
                "  selected:",
                "    - solver_a",
                "    - solver_b",
                "split:",
                "  strategy: repeated_stratified_kfold",
                "  test_size: 0.25",
                "  cross_validation_folds: 3",
                "  repeats: 2",
                "selector:",
                "  model_choice: random_forest",
                "dataset:",
                "  include_solver_objectives: true",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    selection_dataset_path = build_selection_dataset_from_config(config_path)
    training_result = train_selector_from_config(config_path)
    ablation_result = run_ablation_study_from_config(config_path)
    evaluation_result = evaluate_selector_from_config(config_path)
    error_result = analyze_selector_errors_from_config(config_path)

    selection_dataset = pd.read_csv(selection_dataset_path)

    assert selection_dataset_path == selection_dataset_csv
    assert selection_dataset_csv.exists()
    assert selection_summary_json.exists()
    assert list(selection_dataset.columns[:6]) == [
        "instance_name",
        "num_teams",
        "num_slots",
        "num_hard_constraints",
        "num_soft_constraints",
        "constraints_per_team",
    ]
    assert "best_solver" in selection_dataset.columns
    assert training_result.model_name == "random_forest"
    assert training_result.model_path == model_output
    assert model_output.exists()
    assert importance_csv.exists()
    assert training_summary_json.exists()
    assert ablation_result.summary_csv_path == ablation_summary_csv
    assert ablation_summary_csv.exists()
    assert ablation_plot.exists()
    assert ablation_report_markdown.exists()
    assert ablation_summary_json.exists()
    assert evaluation_result.report_path == evaluation_report_csv
    assert evaluation_report_csv.exists()
    assert evaluation_summary_csv.exists()
    assert evaluation_summary_markdown.exists()
    assert evaluation_summary_json.exists()
    assert error_result.output_dir == error_output_dir
    assert error_result.hard_instances_csv.exists()
    assert error_result.confusion_plot.exists()
    assert error_summary_json.exists()
