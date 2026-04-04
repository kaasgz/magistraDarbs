"""Tests for benchmark execution across instances and solvers."""

from __future__ import annotations

import csv
import importlib
import json
from pathlib import Path

import pytest

from src.demo.generate_demo_instances import generate_demo_instances
from src.experiments.benchmark_report import benchmark_report


benchmark_module = importlib.import_module("src.experiments.run_benchmarks")


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
FIXED_TIMESTAMP = "2026-04-04T12:00:00+00:00"


def test_run_benchmarks_writes_traceable_results_and_summary(tmp_path: Path) -> None:
    """The benchmark runner should write one traceable row per instance-solver pair."""

    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "first.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (input_dir / "sample_robinx_missing_sections.xml").write_text(
        (FIXTURES_DIR / "sample_robinx_missing_sections.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    output_csv = tmp_path / "benchmark_results.csv"
    summary_json = tmp_path / "benchmark_run_summary.json"
    benchmark_module.run_benchmarks(
        instance_folder=str(input_dir),
        solver_names=["random_baseline", "simulated_annealing_solver"],
        time_limit_seconds=1,
        random_seed=7,
        output_csv=output_csv,
        run_summary_path=summary_json,
    )

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    summary = json.loads(summary_json.read_text(encoding="utf-8"))

    assert reader.fieldnames == [
        "instance_name",
        "solver_name",
        "solver_registry_name",
        "objective_value",
        "runtime_seconds",
        "feasible",
        "status",
        "random_seed",
        "configured_time_limit_seconds",
        "timestamp",
        "is_synthetic",
        "instance_source_path",
        "solver_metadata_json",
        "error_message",
    ]
    assert len(rows) == 4
    assert {row["solver_registry_name"] for row in rows} == {
        "random_baseline",
        "simulated_annealing_solver",
    }
    assert {row["solver_name"] for row in rows} == {
        "random_baseline",
        "simulated_annealing_baseline",
    }
    assert {row["instance_name"] for row in rows} == {
        "SampleRobinX",
        "sample_robinx_missing_sections",
    }
    assert {row["random_seed"] for row in rows} == {"7"}
    assert {row["configured_time_limit_seconds"] for row in rows} == {"1"}
    assert {row["is_synthetic"] for row in rows} == {"False"}
    assert all(row["timestamp"] for row in rows)
    assert all(row["instance_source_path"] for row in rows)
    assert all(row["solver_metadata_json"] for row in rows)

    assert summary["results"]["num_input_xml_files"] == 2
    assert summary["results"]["num_solvers"] == 2
    assert summary["results"]["num_requested_runs"] == 4
    assert summary["results"]["num_benchmark_rows"] == 4
    assert summary["results"]["num_failed_solver_runs"] == 0
    assert summary["results"]["validation_issue_count"] == 0
    assert summary["outputs"]["benchmark_results_csv"] == output_csv.as_posix()
    assert summary["outputs"]["run_summary"] == summary_json.as_posix()


def test_run_benchmarks_continues_when_one_solver_fails(tmp_path: Path, monkeypatch, caplog) -> None:
    """A failing solver run should be recorded and should not stop other runs."""

    input_dir = tmp_path / "instances"
    input_dir.mkdir()
    (input_dir / "sample.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    original_get_solver = benchmark_module.get_solver

    def failing_get_solver(name: str, **kwargs: object) -> object:
        if name == "failing_solver":
            class _FailingSolver:
                def solve(self, instance: object, time_limit_seconds: int = 60, random_seed: int = 42) -> object:
                    raise RuntimeError("simulated failure")

            return _FailingSolver()

        return original_get_solver(name, **kwargs)

    monkeypatch.setattr(benchmark_module, "get_solver", failing_get_solver)
    caplog.set_level("INFO")

    output_csv = tmp_path / "benchmark_results.csv"
    summary_json = tmp_path / "benchmark_run_summary.json"
    benchmark_module.run_benchmarks(
        instance_folder=str(input_dir),
        solver_names=["random_baseline", "failing_solver"],
        time_limit_seconds=1,
        random_seed=7,
        output_csv=output_csv,
        run_summary_path=summary_json,
    )

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    summary = json.loads(summary_json.read_text(encoding="utf-8"))

    assert len(rows) == 2
    assert {row["solver_registry_name"] for row in rows} == {"random_baseline", "failing_solver"}
    failed_row = next(row for row in rows if row["solver_registry_name"] == "failing_solver")
    assert failed_row["solver_name"] == "failing_solver"
    assert failed_row["feasible"] == "False"
    assert failed_row["status"] == "FAILED:RuntimeError"
    assert failed_row["objective_value"] == ""
    assert failed_row["error_message"] == "simulated failure"
    assert "failed on instance" in caplog.text

    assert summary["results"]["num_failed_solver_runs"] == 1
    assert summary["results"]["num_completed_solver_runs"] == 1


def test_run_benchmarks_rejects_empty_solver_list(tmp_path: Path) -> None:
    """At least one solver must be selected for a benchmark run."""

    input_dir = tmp_path / "instances"
    input_dir.mkdir()

    with pytest.raises(ValueError, match="At least one solver name"):
        benchmark_module.run_benchmarks(
            instance_folder=str(input_dir),
            solver_names=[],
        )


def test_run_benchmarks_smoke_test_on_tiny_synthetic_batch(tmp_path: Path) -> None:
    """A tiny synthetic batch should run end-to-end and produce a readable report."""

    input_dir = tmp_path / "demo_instances"
    manifest_path = tmp_path / "demo_manifest.json"
    output_csv = tmp_path / "benchmark_results.csv"
    summary_json = tmp_path / "benchmark_run_summary.json"

    generate_demo_instances(
        output_folder=input_dir,
        manifest_path=manifest_path,
        instance_count=2,
        random_seed=5,
        difficulty_level="easy",
        generation_timestamp=FIXED_TIMESTAMP,
    )
    benchmark_module.run_benchmarks(
        instance_folder=str(input_dir),
        solver_names=["random_baseline"],
        time_limit_seconds=1,
        random_seed=5,
        output_csv=output_csv,
        run_summary_path=summary_json,
    )

    with output_csv.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    report = benchmark_report(output_csv)

    assert len(rows) == 2
    assert {row["solver_registry_name"] for row in rows} == {"random_baseline"}
    assert {row["is_synthetic"] for row in rows} == {"True"}
    assert "Rows: 2" in report
    assert "Validation issues: 0" in report


def test_run_benchmarks_rejects_mixed_real_and_synthetic_subtrees(tmp_path: Path) -> None:
    """A mixed raw folder should be rejected instead of benchmarked silently."""

    raw_dir = tmp_path / "data" / "raw"
    real_dir = raw_dir / "real"
    synthetic_dir = raw_dir / "synthetic"
    real_dir.mkdir(parents=True)
    synthetic_dir.mkdir(parents=True)
    (real_dir / "sample.xml").write_text(
        (FIXTURES_DIR / "sample_robinx.xml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    generate_demo_instances(
        output_folder=synthetic_dir,
        manifest_path=tmp_path / "data" / "processed" / "demo_manifest.json",
        instance_count=1,
        random_seed=5,
        generation_timestamp=FIXED_TIMESTAMP,
    )

    with pytest.raises(ValueError, match="mixes real and synthetic XML subfolders"):
        benchmark_module.run_benchmarks(
            instance_folder=str(raw_dir),
            solver_names=["random_baseline"],
            time_limit_seconds=1,
            random_seed=5,
            output_csv=tmp_path / "benchmark_results.csv",
        )
