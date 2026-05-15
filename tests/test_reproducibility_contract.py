"""Regression checks for the documented final thesis reproduction contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.utils.config import load_yaml_config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FINAL_SOLVER_PORTFOLIO = [
    "random_baseline",
    "cpsat_solver",
    "simulated_annealing_solver",
    "timefold",
]
CANONICAL_COMMANDS = [
    r".\.venv\Scripts\python.exe -m src.experiments.generate_synthetic_dataset --n 180 --seeds 42,43,44 --output-root data\raw\synthetic\study",
    r".\.venv\Scripts\python.exe -m src.experiments.run_real_pipeline_current --config configs\real_pipeline_current.yaml",
    r".\.venv\Scripts\python.exe -m src.experiments.build_solver_compatibility_matrix",
    r".\.venv\Scripts\python.exe -m src.experiments.run_synthetic_study --config configs\synthetic_study.yaml",
    r".\.venv\Scripts\python.exe -m src.selection.build_selection_dataset_full",
    r".\.venv\Scripts\python.exe -m src.selection.train_selector --full-dataset",
    r".\.venv\Scripts\python.exe -m src.selection.evaluate_selector --full-dataset",
    r".\.venv\Scripts\python.exe -m src.experiments.thesis_report",
    r".\.venv\Scripts\python.exe -m src.thesis.generate_assets",
]


def test_final_configs_match_reproducibility_contract() -> None:
    """Final YAML configs should keep the documented thesis paths, seeds, and split."""

    real = _load_config("real_pipeline_current.yaml")
    synthetic = _load_config("synthetic_study.yaml")
    selector = _load_config("selector_config.yaml")

    assert real["paths"] == {
        "instance_folder": "data/raw/real",
        "processed_dir": "data/processed/real_pipeline_current",
        "results_dir": "data/results/real_pipeline_current",
    }
    assert real["run"]["random_seed"] == 42
    assert real["run"]["time_limit_seconds"] == 60
    assert real["solvers"]["settings"]["timefold"]["executable_path"] is None
    assert _split_settings(real) == ("repeated_stratified_kfold", 0.25, 3, 3)

    assert synthetic["paths"] == {
        "dataset_root": "data/raw/synthetic/study",
        "processed_dir": "data/processed/synthetic_study",
        "results_dir": "data/results/synthetic_study",
    }
    assert synthetic["run"]["seeds"] == [42, 43, 44]
    assert synthetic["run"]["time_limit_seconds"] == 60
    assert synthetic["solvers"]["selected"] == FINAL_SOLVER_PORTFOLIO
    assert synthetic["solvers"]["settings"]["timefold"]["executable_path"] is None
    assert _split_settings(synthetic) == ("repeated_stratified_kfold", 0.25, 3, 3)

    assert selector["paths"]["synthetic_features_csv"] == "data/processed/synthetic_study/features.csv"
    assert selector["paths"]["synthetic_benchmark_results_csv"] == (
        "data/results/synthetic_study/benchmark_results.csv"
    )
    assert selector["paths"]["real_features_csv"] == "data/processed/real_pipeline_current/features.csv"
    assert selector["paths"]["real_benchmark_results_csv"] == (
        "data/results/real_pipeline_current/benchmark_results.csv"
    )
    assert selector["paths"]["full_selection_dataset_csv"] == "data/processed/selection_dataset_full.csv"
    assert selector["paths"]["full_combined_benchmark_results_csv"] == (
        "data/results/full_selection/combined_benchmark_results.csv"
    )
    assert selector["paths"]["full_model_output"] == (
        "data/results/full_selection/random_forest_selector.joblib"
    )
    assert selector["run"]["random_seed"] == 42
    assert selector["selector"]["model_choice"] == "random_forest"
    assert _split_settings(selector) == ("repeated_stratified_kfold", 0.25, 3, 3)


def test_reproduction_docs_publish_the_same_canonical_sequence() -> None:
    """README, guide, and audit should expose one identical final command order."""

    docs = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "docs" / "reproduction_guide.md",
        PROJECT_ROOT / "docs" / "reproducibility_audit.md",
    ]

    for path in docs:
        text = path.read_text(encoding="utf-8")
        for command in CANONICAL_COMMANDS:
            assert command in text, f"{path.name} is missing canonical command: {command}"


def test_reproducibility_audit_records_known_limits() -> None:
    """The audit should state the practical limits instead of overstating exact repeatability."""

    text = (PROJECT_ROOT / "docs" / "reproducibility_audit.md").read_text(encoding="utf-8")

    assert "requirements.txt" in text
    assert "does not download" in text
    assert "not_configured" in text
    assert "54 XML files" in text
    assert "180 synthetic instances" in text
    assert "3 folds, 3 repeats" in text


def _load_config(name: str) -> dict[str, Any]:
    """Load one repository config by filename."""

    return load_yaml_config(PROJECT_ROOT / "configs" / name)


def _split_settings(config: dict[str, Any]) -> tuple[str, float, int, int]:
    """Return the split contract as a compact tuple."""

    split = config["split"]
    return (
        split["strategy"],
        float(split["test_size"]),
        int(split["cross_validation_folds"]),
        int(split["repeats"]),
    )
