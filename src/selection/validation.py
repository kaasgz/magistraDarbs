"""Shared validation workflow for selector training and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score

from src.selection.modeling import PreparedSelectionData, build_selector_pipeline
from src.selection.splitting import SelectorSplit, SelectorSplitPlan, build_selector_split_plan
from src.utils import SplitSettings


@dataclass(frozen=True, slots=True)
class SelectorValidationResult:
    """Out-of-sample selector predictions with split-level metrics."""

    split_plan: SelectorSplitPlan
    predictions: pd.DataFrame
    split_summary: pd.DataFrame


def run_selector_validation(
    prepared_data: PreparedSelectionData,
    *,
    model_name: str,
    random_seed: int,
    split_settings: SplitSettings,
) -> SelectorValidationResult:
    """Train and evaluate the selector across reproducible validation splits."""

    split_plan = build_selector_split_plan(
        prepared_data.target,
        split_settings=split_settings,
        random_seed=random_seed,
    )

    prediction_rows: list[dict[str, object]] = []
    split_rows: list[dict[str, object]] = []
    for split in split_plan.splits:
        x_train = prepared_data.features.iloc[list(split.train_indices)].copy()
        x_test = prepared_data.features.iloc[list(split.test_indices)].copy()
        y_train = prepared_data.target.iloc[list(split.train_indices)].copy()
        y_test = prepared_data.target.iloc[list(split.test_indices)].copy()
        instance_names = prepared_data.instance_names.iloc[list(split.test_indices)].copy()

        pipeline = build_selector_pipeline(
            model_name=model_name,
            random_seed=random_seed,
            dataset=x_train,
        )
        pipeline.fit(x_train, y_train)
        predictions = pd.Series(
            pipeline.predict(x_test),
            index=instance_names.index,
            dtype="string",
        )

        accuracy = float(accuracy_score(y_test, predictions))
        balanced_accuracy = _compute_balanced_accuracy(y_test, predictions)
        split_rows.append(
            _split_summary_row(
                split=split,
                num_train_rows=len(x_train.index),
                num_test_rows=len(x_test.index),
                num_train_classes=int(y_train.nunique()),
                num_test_classes=int(y_test.nunique()),
                accuracy=accuracy,
                balanced_accuracy=balanced_accuracy,
            )
        )
        for index in predictions.index:
            prediction_rows.append(
                {
                    "split_id": split.split_id,
                    "split_strategy": split.strategy,
                    "repeat_index": split.repeat_index,
                    "fold_index": split.fold_index,
                    "stratified_split": split.stratified,
                    "instance_name": str(instance_names.loc[index]),
                    "true_best_solver": str(y_test.loc[index]),
                    "predicted_solver": str(predictions.loc[index]),
                    "is_correct_prediction": bool(predictions.loc[index] == y_test.loc[index]),
                }
            )

    prediction_frame = (
        pd.DataFrame(prediction_rows)
        .sort_values(by=["split_id", "instance_name"], ascending=[True, True], kind="mergesort")
        .reset_index(drop=True)
    )
    split_summary = (
        pd.DataFrame(split_rows)
        .sort_values(by=["repeat_index", "fold_index", "split_id"], kind="mergesort")
        .reset_index(drop=True)
    )
    return SelectorValidationResult(
        split_plan=split_plan,
        predictions=prediction_frame,
        split_summary=split_summary,
    )


def aggregate_metric(values: pd.Series) -> float | None:
    """Return the mean of one metric column, ignoring missing values."""

    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if numeric.empty:
        return None
    return float(numeric.mean())


def metric_standard_deviation(values: pd.Series) -> float | None:
    """Return the sample standard deviation of one metric column when available."""

    numeric = pd.to_numeric(values, errors="coerce").dropna()
    if len(numeric.index) < 2:
        return None
    return float(numeric.std(ddof=1))


def summarize_label_distribution(values: Sequence[object]) -> str | None:
    """Return a stable label summary when all values agree."""

    normalized = [str(value).strip() for value in values if value is not None and str(value).strip()]
    if not normalized:
        return None
    unique = sorted(set(normalized))
    if len(unique) == 1:
        return unique[0]
    return None


def _compute_balanced_accuracy(y_true: pd.Series, y_pred: Sequence[str]) -> float | None:
    """Compute balanced accuracy when the test labels span multiple classes."""

    if y_true.nunique() < 2:
        return None
    return float(balanced_accuracy_score(y_true, y_pred))


def _split_summary_row(
    *,
    split: SelectorSplit,
    num_train_rows: int,
    num_test_rows: int,
    num_train_classes: int,
    num_test_classes: int,
    accuracy: float,
    balanced_accuracy: float | None,
) -> dict[str, object]:
    """Build one auditable validation-split summary row."""

    return {
        "split_id": split.split_id,
        "split_strategy": split.strategy,
        "repeat_index": split.repeat_index,
        "fold_index": split.fold_index,
        "stratified_split": split.stratified,
        "num_train_rows": num_train_rows,
        "num_test_rows": num_test_rows,
        "num_train_classes": num_train_classes,
        "num_test_classes": num_test_classes,
        "classification_accuracy": accuracy,
        "balanced_accuracy": balanced_accuracy,
    }
