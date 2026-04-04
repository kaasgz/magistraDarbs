"""Experiment orchestration code."""

from src.experiments.benchmark_report import benchmark_report
from src.experiments.reporting import DEFAULT_OUTPUT_DIR, ThesisArtifactResult, generate_thesis_artifacts
from src.experiments.benchmark_validation import (
    BenchmarkValidationError,
    BenchmarkValidationIssue,
    ensure_valid_benchmark_results,
    validate_benchmark_results,
)
from src.experiments.metrics import (
    average_objective_by_solver,
    average_runtime_by_solver,
    best_solver_per_instance,
    single_best_solver,
    virtual_best_solver,
)
from src.experiments.run_benchmarks import run_benchmarks, run_benchmarks_from_config

__all__ = [
    "DEFAULT_OUTPUT_DIR",
    "BenchmarkValidationError",
    "BenchmarkValidationIssue",
    "ThesisArtifactResult",
    "average_objective_by_solver",
    "average_runtime_by_solver",
    "benchmark_report",
    "best_solver_per_instance",
    "ensure_valid_benchmark_results",
    "generate_thesis_artifacts",
    "run_benchmarks",
    "run_benchmarks_from_config",
    "single_best_solver",
    "validate_benchmark_results",
    "virtual_best_solver",
]
