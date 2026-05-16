# Algorithm selection components with lazy exports.

from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = [
    "AblationStudyResult",
    "ErrorAnalysisResult",
    "SelectorEvaluationResult",
    "SelectorTrainingResult",
    "analyze_selector_errors",
    "analyze_selector_errors_from_config",
    "build_selection_dataset",
    "build_selection_dataset_full",
    "build_selection_dataset_from_config",
    "build_full_selection_dataset",
    "evaluate_selector",
    "evaluate_full_selector",
    "evaluate_full_selector_from_config",
    "evaluate_selector_from_config",
    "run_ablation_study",
    "run_ablation_study_from_config",
    "train_selector",
    "train_full_selector_from_config",
    "train_selector_from_config",
]

_LAZY_EXPORTS = {
    "AblationStudyResult": ("src.selection.ablation_study", "AblationStudyResult"),
    "run_ablation_study": ("src.selection.ablation_study", "run_ablation_study"),
    "run_ablation_study_from_config": ("src.selection.ablation_study", "run_ablation_study_from_config"),
    "build_selection_dataset": ("src.selection.build_selection_dataset", "build_selection_dataset"),
    "build_selection_dataset_full": (
        "src.selection.build_selection_dataset_full",
        "build_selection_dataset_full",
    ),
    "build_selection_dataset_from_config": (
        "src.selection.build_selection_dataset",
        "build_selection_dataset_from_config",
    ),
    "build_full_selection_dataset": ("src.selection.build_selection_dataset", "build_full_selection_dataset"),
    "SelectorEvaluationResult": ("src.selection.evaluate_selector", "SelectorEvaluationResult"),
    "evaluate_full_selector": ("src.selection.evaluate_selector", "evaluate_full_selector"),
    "evaluate_full_selector_from_config": ("src.selection.evaluate_selector", "evaluate_full_selector_from_config"),
    "evaluate_selector": ("src.selection.evaluate_selector", "evaluate_selector"),
    "evaluate_selector_from_config": ("src.selection.evaluate_selector", "evaluate_selector_from_config"),
    "SelectorTrainingResult": ("src.selection.train_selector", "SelectorTrainingResult"),
    "train_selector": ("src.selection.train_selector", "train_selector"),
    "train_full_selector_from_config": ("src.selection.train_selector", "train_full_selector_from_config"),
    "train_selector_from_config": ("src.selection.train_selector", "train_selector_from_config"),
    "ErrorAnalysisResult": ("src.selection.error_analysis", "ErrorAnalysisResult"),
    "analyze_selector_errors": ("src.selection.error_analysis", "analyze_selector_errors"),
    "analyze_selector_errors_from_config": (
        "src.selection.error_analysis",
        "analyze_selector_errors_from_config",
    ),
}


def __getattr__(name: str) -> Any:

    # Load selection exports lazily to keep lightweight imports cheap.
    if name not in _LAZY_EXPORTS:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module_name, attribute_name = _LAZY_EXPORTS[name]
    module = import_module(module_name)
    value = getattr(module, attribute_name)
    globals()[name] = value
    return value
