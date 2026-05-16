# Coverage-aware tests for thesis benchmark reports.

from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.experiments.thesis_report import generate_thesis_benchmark_report


def test_thesis_report_separates_coverage_support_and_valid_objectives(tmp_path: Path) -> None:

    # Reports should not treat feasible coverage as objective-comparable quality.
    synthetic_benchmark_csv = tmp_path / "synthetic_benchmark_results.csv"
    real_benchmark_csv = tmp_path / "real_benchmark_results.csv"
    synthetic_summary_csv = tmp_path / "synthetic_selector_summary.csv"
    real_summary_csv = tmp_path / "real_selector_summary.csv"
    compatibility_matrix_csv = tmp_path / "solver_compatibility_matrix.csv"
    output_dir = tmp_path / "reports"

    pd.DataFrame(
        [
            _benchmark_row(
                instance_name="synthetic_1",
                solver_name="solver_a",
                objective=10.0,
                feasible=True,
                support="supported",
                scoring="supported_feasible_run",
                objective_valid=True,
            ),
            _benchmark_row(
                instance_name="synthetic_1",
                solver_name="solver_b",
                objective=1.0,
                feasible=True,
                support="partially_supported",
                scoring="partially_modeled_run",
                objective_valid=False,
            ),
        ]
    ).to_csv(synthetic_benchmark_csv, index=False)
    pd.DataFrame(
        [
            _benchmark_row(
                instance_name="real_1",
                solver_name="solver_a",
                objective=20.0,
                feasible=True,
                support="supported",
                scoring="supported_feasible_run",
                objective_valid=True,
                synthetic=False,
            ),
            _benchmark_row(
                instance_name="real_1",
                solver_name="solver_b",
                objective=None,
                feasible=False,
                support="not_configured",
                scoring="not_configured",
                status="NOT_CONFIGURED",
                objective_valid=False,
                synthetic=False,
            ),
        ]
    ).to_csv(real_benchmark_csv, index=False)
    _write_evaluation_summary(synthetic_summary_csv, selected=10.0, virtual_best=10.0)
    _write_evaluation_summary(real_summary_csv, selected=20.0, virtual_best=20.0)
    pd.DataFrame(
        [
            {
                "instance_name": "real_1",
                "solver_name": "solver_a",
                "support_status": "supported",
                "unsupported_constraint_families": "",
                "notes": "fully modeled fixture",
            },
            {
                "instance_name": "real_1",
                "solver_name": "solver_b",
                "support_status": "not_configured",
                "unsupported_constraint_families": "",
                "notes": "missing executable fixture",
            },
        ]
    ).to_csv(compatibility_matrix_csv, index=False)

    result = generate_thesis_benchmark_report(
        output_dir=output_dir,
        synthetic_benchmark_csv=synthetic_benchmark_csv,
        real_benchmark_csv=real_benchmark_csv,
        synthetic_evaluation_summary_csv=synthetic_summary_csv,
        real_evaluation_summary_csv=real_summary_csv,
        compatibility_matrix_csv=compatibility_matrix_csv,
    )

    solver_comparison = pd.read_csv(result.solver_comparison_csv)
    support_summary = pd.read_csv(result.solver_support_summary_csv)
    selector_vs_baselines = pd.read_csv(result.selector_vs_baselines_csv)
    summary_markdown = result.summary_markdown.read_text(encoding="utf-8")

    synthetic_solver_b = solver_comparison[
        (solver_comparison["result_scope"] == "synthetic")
        & (solver_comparison["solver_registry_name"] == "solver_b")
    ].iloc[0]
    real_solver_b_support = support_summary[
        (support_summary["result_scope"] == "real")
        & (support_summary["solver_registry_name"] == "solver_b")
        & (support_summary["solver_support_status"] == "not_configured")
    ].iloc[0]
    real_solver_a = solver_comparison[
        (solver_comparison["result_scope"] == "real")
        & (solver_comparison["solver_registry_name"] == "solver_a")
    ].iloc[0]

    assert result.solver_support_summary_csv.exists()
    assert result.solver_support_summary_markdown.exists()
    assert set(solver_comparison["result_scope"]) == {"synthetic", "real"}
    assert int(synthetic_solver_b["num_instances_feasible"]) == 1
    assert int(synthetic_solver_b["num_instances_valid_feasible"]) == 0
    assert float(synthetic_solver_b["feasible_coverage_ratio"]) == 1.0
    assert float(synthetic_solver_b["valid_feasible_coverage_ratio"]) == 0.0
    assert pd.isna(synthetic_solver_b["average_objective_valid_feasible"])
    assert int(real_solver_b_support["num_valid_feasible_runs"]) == 0
    assert int(real_solver_a["compatibility_supported_instances"]) == 1
    assert set(selector_vs_baselines["result_scope"]) == {"synthetic", "real"}
    assert "Valid feasible coverage" in summary_markdown
    assert "unsupported, failed, and not-configured" in summary_markdown


def _benchmark_row(
    *,
    instance_name: str,
    solver_name: str,
    objective: float | None,
    feasible: bool,
    support: str,
    scoring: str,
    objective_valid: bool,
    status: str = "FEASIBLE",
    synthetic: bool = True,
) -> dict[str, object]:

    # Build one benchmark row with scoring-contract metadata.
    return {
        "instance_name": instance_name,
        "solver_name": solver_name,
        "solver_registry_name": solver_name,
        "objective_value": objective,
        "objective_sense": "lower_is_better",
        "objective_value_valid": objective_valid,
        "runtime_seconds": 1.0,
        "feasible": feasible,
        "status": status,
        "solver_support_status": support,
        "scoring_status": scoring,
        "is_synthetic": synthetic,
    }


def _write_evaluation_summary(path: Path, *, selected: float, virtual_best: float) -> None:

    # Write a minimal selector summary fixture.
    pd.DataFrame(
        [
            {
                "summary_row_type": "split",
                "split_strategy": "holdout",
                "classification_accuracy": 1.0,
                "balanced_accuracy": None,
                "average_selected_objective": selected,
                "average_virtual_best_objective": virtual_best,
                "average_single_best_objective": selected,
                "regret_vs_virtual_best": selected - virtual_best,
                "delta_vs_single_best": 0.0,
                "single_best_solver_name": "solver_a",
            },
            {
                "summary_row_type": "aggregate_mean",
                "split_strategy": "holdout",
                "classification_accuracy": 1.0,
                "balanced_accuracy": None,
                "average_selected_objective": selected,
                "average_virtual_best_objective": virtual_best,
                "average_single_best_objective": selected,
                "regret_vs_virtual_best": selected - virtual_best,
                "delta_vs_single_best": 0.0,
                "single_best_solver_name": "solver_a",
            },
            {
                "summary_row_type": "aggregate_std",
                "split_strategy": "holdout",
                "classification_accuracy": 0.0,
                "balanced_accuracy": None,
            },
        ]
    ).to_csv(path, index=False)
