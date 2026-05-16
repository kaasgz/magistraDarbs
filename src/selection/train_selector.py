# Train a first algorithm selection model from the selection dataset.
#
# This module keeps the selector model simple but makes its validation workflow
# more explicit and reproducible:
#
# - benchmark-derived columns such as ``objective_*`` are excluded from training
# features to reduce leakage risk
# - validation splits are created by a shared split helper used by both training
# and evaluation
# - the saved model is fitted on the full labeled dataset after validation so the
# artifact can be reused later without silently depending on one holdout split

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import joblib
import pandas as pd
from sklearn.metrics import confusion_matrix

from src.selection.modeling import (
    build_selector_pipeline,
    prepare_selection_data,
    save_feature_importance,
)
from src.selection.validation import aggregate_metric, run_selector_validation
from src.utils import (
    SplitSettings,
    default_run_summary_path,
    ensure_parent_directory,
    get_compat_path,
    get_model_choice,
    get_random_seed,
    get_split_settings,
    load_yaml_config,
    write_run_summary,
)


LOGGER = logging.getLogger(__name__)
DEFAULT_CONFIG_PATH = Path("configs/selector_config.yaml")
DEFAULT_DATASET_PATH = Path("data/processed/selection_dataset.csv")
DEFAULT_MODEL_PATH = Path("data/results/random_forest_selector.joblib")
DEFAULT_IMPORTANCE_PATH = Path("data/results/random_forest_feature_importance.csv")
DEFAULT_FULL_DATASET_PATH = Path("data/processed/selection_dataset_full.csv")
DEFAULT_FULL_MODEL_PATH = Path("data/results/full_selection/random_forest_selector.joblib")
DEFAULT_FULL_IMPORTANCE_PATH = Path("data/results/full_selection/feature_importance.csv")
DEFAULT_FULL_TRAINING_SUMMARY_PATH = Path("data/results/full_selection/selector_training_run_summary.json")


@dataclass(slots=True)
class SelectorTrainingResult:

    # Summary of one selector training run.
    model_name: str
    model_path: Path
    feature_importance_path: Path | None
    accuracy: float
    balanced_accuracy: float | None
    confusion_matrix: pd.DataFrame
    num_train_rows: int
    num_test_rows: int
    num_labeled_rows: int
    num_validation_splits: int
    split_strategy: str


def train_selector(
    dataset_csv: str | Path = DEFAULT_DATASET_PATH,
    model_path: str | Path = DEFAULT_MODEL_PATH,
    feature_importance_csv: str | Path = DEFAULT_IMPORTANCE_PATH,
    random_seed: int = 42,
    test_size: float = 0.25,
    model_name: str = "random_forest",
    *,
    split_strategy: str = "holdout",
    cross_validation_folds: int | None = None,
    repeats: int = 1,
    config_path: str | Path | None = None,
    config: dict[str, Any] | None = None,
    run_summary_path: str | Path | None = None,
) -> SelectorTrainingResult:

    # Train a baseline algorithm selector from a selection dataset.
    dataset_path = Path(dataset_csv)
    model_output_path = Path(model_path)
    importance_output_path = Path(feature_importance_csv)

    dataset = pd.read_csv(dataset_path)
    prepared_data = prepare_selection_data(dataset)
    split_settings = SplitSettings(
        strategy=split_strategy,
        test_size=test_size,
        cross_validation_folds=cross_validation_folds,
        repeats=repeats,
    )

    validation_result = run_selector_validation(
        prepared_data,
        model_name=model_name,
        random_seed=random_seed,
        split_settings=split_settings,
    )
    split_summary = validation_result.split_summary
    pooled_predictions = validation_result.predictions

    accuracy = aggregate_metric(split_summary["classification_accuracy"])
    balanced_accuracy = aggregate_metric(split_summary["balanced_accuracy"])
    if accuracy is None:
        raise ValueError("Selector validation did not produce any accuracy values.")

    confusion = _build_confusion_matrix(pooled_predictions)

    final_pipeline = build_selector_pipeline(
        model_name=model_name,
        random_seed=random_seed,
        dataset=prepared_data.features,
    )
    final_pipeline.fit(prepared_data.features, prepared_data.target)

    ensure_parent_directory(model_output_path)
    joblib.dump(final_pipeline, model_output_path)
    importance_path = save_feature_importance(
        pipeline=final_pipeline,
        output_path=importance_output_path,
    )

    num_train_rows = int(round(float(split_summary["num_train_rows"].mean())))
    num_test_rows = int(round(float(split_summary["num_test_rows"].mean())))

    LOGGER.info("Selector model: %s", model_name)
    LOGGER.info("Validation strategy: %s", validation_result.split_plan.strategy)
    LOGGER.info("Validation splits: %d", len(split_summary.index))
    LOGGER.info("Labeled rows: %d", len(prepared_data.target.index))
    LOGGER.info("Mean classification accuracy: %.4f", accuracy)
    if balanced_accuracy is None:
        LOGGER.info("Mean balanced accuracy: not applicable")
    else:
        LOGGER.info("Mean balanced accuracy: %.4f", balanced_accuracy)
    LOGGER.info("Validation confusion matrix:\n%s", confusion.to_string())
    LOGGER.info("Saved trained model to %s", model_output_path)
    if importance_path is not None:
        LOGGER.info("Saved feature importance to %s", importance_path)

    result = SelectorTrainingResult(
        model_name=model_name,
        model_path=model_output_path,
        feature_importance_path=importance_path,
        accuracy=accuracy,
        balanced_accuracy=balanced_accuracy,
        confusion_matrix=confusion,
        num_train_rows=num_train_rows,
        num_test_rows=num_test_rows,
        num_labeled_rows=len(prepared_data.target.index),
        num_validation_splits=len(split_summary.index),
        split_strategy=validation_result.split_plan.strategy,
    )
    summary_path = Path(run_summary_path) if run_summary_path is not None else default_run_summary_path(model_output_path)
    write_run_summary(
        summary_path,
        stage_name="selector_training",
        config_path=config_path,
        config=config,
        settings={
            "random_seed": random_seed,
            "model_name": model_name,
            "split_strategy": validation_result.split_plan.strategy,
            "test_size": test_size,
            "cross_validation_folds": cross_validation_folds,
            "repeats": repeats,
            "split_notes": list(validation_result.split_plan.notes),
        },
        inputs={
            "selection_dataset_csv": dataset_path,
        },
        outputs={
            "model_output": model_output_path,
            "feature_importance_csv": importance_path,
            "run_summary": summary_path,
        },
        results={
            "accuracy": result.accuracy,
            "balanced_accuracy": result.balanced_accuracy,
            "num_train_rows": result.num_train_rows,
            "num_test_rows": result.num_test_rows,
            "num_labeled_rows": result.num_labeled_rows,
            "num_validation_splits": result.num_validation_splits,
            "dataset_type_counts": _dataset_type_counts(dataset),
            "feature_columns": list(prepared_data.feature_columns),
            "excluded_columns": list(prepared_data.excluded_columns),
            "confusion_matrix": result.confusion_matrix.to_dict(),
        },
    )
    LOGGER.info("Saved selector-training run summary to %s", summary_path)
    return result


def train_selector_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> SelectorTrainingResult:

    # Train the selector using values loaded from a YAML configuration file.
    config = load_yaml_config(config_path)
    split_settings = get_split_settings(config)
    model_path = get_compat_path(config, ["paths.model_output"], DEFAULT_MODEL_PATH)
    summary_path = get_compat_path(
        config,
        ["paths.training_run_summary", "paths.run_summary", "paths.run_summary_path"],
        default_run_summary_path(model_path),
    )
    return train_selector(
        dataset_csv=get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_DATASET_PATH),
        model_path=model_path,
        feature_importance_csv=get_compat_path(config, ["paths.feature_importance_csv"], DEFAULT_IMPORTANCE_PATH),
        random_seed=get_random_seed(config, 42),
        test_size=split_settings.test_size,
        model_name=get_model_choice(config, "random_forest"),
        split_strategy=split_settings.strategy,
        cross_validation_folds=split_settings.cross_validation_folds,
        repeats=split_settings.repeats,
        config_path=config_path,
        config=config,
        run_summary_path=summary_path,
    )


def train_full_selector_from_config(config_path: str | Path = DEFAULT_CONFIG_PATH) -> SelectorTrainingResult:

    # Train the selector on the combined synthetic/real selection dataset.
    config = load_yaml_config(config_path)
    split_settings = get_split_settings(config)
    model_path = get_compat_path(config, ["paths.full_model_output"], DEFAULT_FULL_MODEL_PATH)
    summary_path = get_compat_path(
        config,
        ["paths.full_training_run_summary"],
        DEFAULT_FULL_TRAINING_SUMMARY_PATH,
    )
    return train_selector(
        dataset_csv=get_compat_path(config, ["paths.full_selection_dataset_csv"], DEFAULT_FULL_DATASET_PATH),
        model_path=model_path,
        feature_importance_csv=get_compat_path(
            config,
            ["paths.full_feature_importance_csv"],
            DEFAULT_FULL_IMPORTANCE_PATH,
        ),
        random_seed=get_random_seed(config, 42),
        test_size=split_settings.test_size,
        model_name=get_model_choice(config, "random_forest"),
        split_strategy=split_settings.strategy,
        cross_validation_folds=split_settings.cross_validation_folds,
        repeats=split_settings.repeats,
        config_path=config_path,
        config=config,
        run_summary_path=summary_path,
    )


def build_argument_parser() -> argparse.ArgumentParser:

    # Create the command-line parser for selector training.
    parser = argparse.ArgumentParser(
        description="Train a baseline algorithm selection model.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the selector YAML configuration file.",
    )
    parser.add_argument(
        "--dataset",
        default=None,
        help="Path to the selection dataset CSV.",
    )
    parser.add_argument(
        "--full-dataset",
        action="store_true",
        help="Train on data/processed/selection_dataset_full.csv and write full_selection outputs.",
    )
    parser.add_argument(
        "--model-output",
        default=None,
        help="Output path for the trained model.",
    )
    parser.add_argument(
        "--importance-output",
        default=None,
        help="Output path for feature importance CSV.",
    )
    parser.add_argument(
        "--random-seed",
        type=int,
        default=None,
        help="Random seed used for splitting and training.",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=None,
        help="Fraction of labeled rows reserved for testing in holdout-style strategies.",
    )
    parser.add_argument(
        "--model-name",
        default=None,
        help="Selector model family. Version 1 supports: random_forest.",
    )
    parser.add_argument(
        "--split-strategy",
        default=None,
        help="Data split strategy: holdout, repeated_holdout, or repeated_stratified_kfold.",
    )
    parser.add_argument(
        "--cross-validation-folds",
        type=int,
        default=None,
        help="Number of folds for repeated_stratified_kfold.",
    )
    parser.add_argument(
        "--repeats",
        type=int,
        default=None,
        help="Number of validation repeats for repeated strategies.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:

    # Run selector training from the command line.
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    try:
        config = load_yaml_config(args.config)
        split_settings = get_split_settings(config)
        if args.full_dataset:
            default_dataset_path = get_compat_path(
                config,
                ["paths.full_selection_dataset_csv"],
                DEFAULT_FULL_DATASET_PATH,
            )
            default_model_path = get_compat_path(config, ["paths.full_model_output"], DEFAULT_FULL_MODEL_PATH)
            default_importance_path = get_compat_path(
                config,
                ["paths.full_feature_importance_csv"],
                DEFAULT_FULL_IMPORTANCE_PATH,
            )
            default_run_summary = get_compat_path(
                config,
                ["paths.full_training_run_summary"],
                DEFAULT_FULL_TRAINING_SUMMARY_PATH,
            )
        else:
            default_dataset_path = get_compat_path(config, ["paths.selection_dataset_csv"], DEFAULT_DATASET_PATH)
            default_model_path = get_compat_path(config, ["paths.model_output"], DEFAULT_MODEL_PATH)
            default_importance_path = get_compat_path(
                config,
                ["paths.feature_importance_csv"],
                DEFAULT_IMPORTANCE_PATH,
            )
            default_run_summary = get_compat_path(
                config,
                ["paths.training_run_summary", "paths.run_summary", "paths.run_summary_path"],
                default_run_summary_path(args.model_output or default_model_path),
            )

        resolved_model_path = args.model_output or default_model_path
        result = train_selector(
            dataset_csv=args.dataset or default_dataset_path,
            model_path=resolved_model_path,
            feature_importance_csv=args.importance_output or default_importance_path,
            random_seed=(
                args.random_seed
                if args.random_seed is not None
                else get_random_seed(config, 42)
            ),
            test_size=(
                args.test_size
                if args.test_size is not None
                else split_settings.test_size
            ),
            model_name=args.model_name or get_model_choice(config, "random_forest"),
            split_strategy=(args.split_strategy or split_settings.strategy),
            cross_validation_folds=(
                args.cross_validation_folds
                if args.cross_validation_folds is not None
                else split_settings.cross_validation_folds
            ),
            repeats=(
                args.repeats
                if args.repeats is not None
                else split_settings.repeats
            ),
            config_path=args.config,
            config=config,
            run_summary_path=default_run_summary,
        )
    except (FileNotFoundError, ValueError, pd.errors.EmptyDataError) as exc:
        print(f"Failed to train selector: {exc}", file=sys.stderr)
        return 1

    print(f"Selector model saved to {result.model_path}")
    return 0


def _build_confusion_matrix(predictions: pd.DataFrame) -> pd.DataFrame:

    # Build one confusion matrix from pooled out-of-sample predictions.
    labels = sorted(
        {
            *predictions["true_best_solver"].astype(str),
            *predictions["predicted_solver"].astype(str),
        }
    )
    if not labels:
        return pd.DataFrame()
    if len(labels) == 1:
        only_label = labels[0]
        return pd.DataFrame(
            [[len(predictions.index)]],
            index=[only_label],
            columns=[only_label],
        )
    return pd.DataFrame(
        confusion_matrix(predictions["true_best_solver"], predictions["predicted_solver"], labels=labels),
        index=labels,
        columns=labels,
    )


def _dataset_type_counts(dataset: pd.DataFrame) -> dict[str, int]:

    # Return source counts when the dataset carries synthetic/real labels.
    if "dataset_type" not in dataset.columns:
        return {}
    counts = dataset["dataset_type"].dropna().astype(str).value_counts().sort_index()
    return {str(dataset_type): int(count) for dataset_type, count in counts.items()}


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "DEFAULT_DATASET_PATH",
    "DEFAULT_FULL_DATASET_PATH",
    "DEFAULT_FULL_IMPORTANCE_PATH",
    "DEFAULT_FULL_MODEL_PATH",
    "DEFAULT_IMPORTANCE_PATH",
    "DEFAULT_MODEL_PATH",
    "SelectorTrainingResult",
    "build_selector_pipeline",
    "train_selector",
    "train_selector_from_config",
    "train_full_selector_from_config",
]


if __name__ == "__main__":
    raise SystemExit(main())
