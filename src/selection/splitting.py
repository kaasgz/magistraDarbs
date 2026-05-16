# Reproducible split helpers for selector training and evaluation.

from __future__ import annotations

import math
from dataclasses import dataclass

import pandas as pd
from sklearn.model_selection import (
    RepeatedKFold,
    RepeatedStratifiedKFold,
    ShuffleSplit,
    StratifiedShuffleSplit,
)

from src.utils import SplitSettings


@dataclass(frozen=True, slots=True)
class SelectorSplit:

    # One reproducible train/test split for selector validation.
    split_id: str
    strategy: str
    repeat_index: int
    fold_index: int | None
    stratified: bool
    train_indices: tuple[int, ...]
    test_indices: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SelectorSplitPlan:

    # Resolved split plan with auditable notes.
    strategy: str
    splits: tuple[SelectorSplit, ...]
    notes: tuple[str, ...]


def build_selector_split_plan(
    target: pd.Series,
    split_settings: SplitSettings,
    random_seed: int,
) -> SelectorSplitPlan:

    # Create reproducible selector splits from configuration settings.
    normalized_target = target.astype(str).reset_index(drop=True)
    if len(normalized_target.index) < 2:
        raise ValueError("Selection dataset must contain at least two labeled rows.")

    strategy = _normalize_strategy(split_settings.strategy)
    if strategy == "holdout":
        return _build_holdout_plan(normalized_target, split_settings, random_seed)
    if strategy == "repeated_holdout":
        return _build_repeated_holdout_plan(normalized_target, split_settings, random_seed)
    if strategy == "repeated_stratified_kfold":
        return _build_repeated_kfold_plan(normalized_target, split_settings, random_seed)

    raise ValueError(
        f"Unsupported split strategy '{split_settings.strategy}'. "
        "Supported strategies: holdout, repeated_holdout, repeated_stratified_kfold."
    )


def _build_holdout_plan(
    target: pd.Series,
    split_settings: SplitSettings,
    random_seed: int,
) -> SelectorSplitPlan:

    # Build one reproducible holdout split.
    _validate_test_size(split_settings.test_size)
    stratified = _can_stratify_holdout(target, split_settings.test_size)
    splitter = (
        StratifiedShuffleSplit(n_splits=1, test_size=split_settings.test_size, random_state=random_seed)
        if stratified
        else ShuffleSplit(n_splits=1, test_size=split_settings.test_size, random_state=random_seed)
    )
    split = _iter_shuffle_splits(splitter, target, stratified)[0]
    notes = ()
    if not stratified:
        notes = ("Holdout split fell back to non-stratified sampling because class counts were too small.",)
    return SelectorSplitPlan(
        strategy="holdout",
        splits=(split,),
        notes=notes,
    )


def _build_repeated_holdout_plan(
    target: pd.Series,
    split_settings: SplitSettings,
    random_seed: int,
) -> SelectorSplitPlan:

    # Build repeated holdout splits.
    _validate_test_size(split_settings.test_size)
    repeats = split_settings.repeats if split_settings.repeats > 0 else 3
    stratified = _can_stratify_holdout(target, split_settings.test_size)
    splitter = (
        StratifiedShuffleSplit(n_splits=repeats, test_size=split_settings.test_size, random_state=random_seed)
        if stratified
        else ShuffleSplit(n_splits=repeats, test_size=split_settings.test_size, random_state=random_seed)
    )
    splits = tuple(_iter_shuffle_splits(splitter, target, stratified))
    notes = ()
    if not stratified:
        notes = (
            "Repeated holdout fell back to non-stratified sampling because class counts were too small.",
        )
    return SelectorSplitPlan(
        strategy="repeated_holdout",
        splits=splits,
        notes=notes,
    )


def _build_repeated_kfold_plan(
    target: pd.Series,
    split_settings: SplitSettings,
    random_seed: int,
) -> SelectorSplitPlan:

    # Build repeated stratified cross-validation splits when feasible.
    requested_folds = split_settings.cross_validation_folds or 3
    if requested_folds < 2:
        raise ValueError("cross_validation_folds must be at least 2 for repeated_stratified_kfold.")

    repeats = split_settings.repeats if split_settings.repeats > 0 else 3
    max_sample_folds = len(target.index)
    effective_folds = min(requested_folds, max_sample_folds)
    if effective_folds < 2:
        raise ValueError("At least two labeled rows are required for cross-validation.")

    notes: list[str] = []
    if effective_folds != requested_folds:
        notes.append(
            f"Reduced cross-validation folds from {requested_folds} to {effective_folds} because the dataset is small."
        )

    class_counts = target.value_counts()
    min_class_count = int(class_counts.min()) if not class_counts.empty else 0
    stratified = len(class_counts.index) >= 2 and min_class_count >= effective_folds

    if stratified:
        splitter = RepeatedStratifiedKFold(
            n_splits=effective_folds,
            n_repeats=repeats,
            random_state=random_seed,
        )
    else:
        splitter = RepeatedKFold(
            n_splits=effective_folds,
            n_repeats=repeats,
            random_state=random_seed,
        )
        if len(class_counts.index) < 2:
            notes.append(
                "Cross-validation fell back to non-stratified folds because only one class is present."
            )
        else:
            notes.append(
                "Cross-validation fell back to non-stratified folds because at least one class has fewer "
                f"than {effective_folds} samples."
            )

    splits: list[SelectorSplit] = []
    for split_number, (train_indices, test_indices) in enumerate(splitter.split(target, target)):
        repeat_index = split_number // effective_folds + 1
        fold_index = split_number % effective_folds + 1
        splits.append(
            SelectorSplit(
                split_id=f"{'stratified' if stratified else 'plain'}_cv_r{repeat_index:02d}_f{fold_index:02d}",
                strategy="repeated_stratified_kfold",
                repeat_index=repeat_index,
                fold_index=fold_index,
                stratified=stratified,
                train_indices=tuple(int(index) for index in train_indices),
                test_indices=tuple(int(index) for index in test_indices),
            )
        )

    return SelectorSplitPlan(
        strategy="repeated_stratified_kfold",
        splits=tuple(splits),
        notes=tuple(notes),
    )


def _iter_shuffle_splits(splitter: object, target: pd.Series, stratified: bool) -> list[SelectorSplit]:

    # Convert shuffle-split indices into typed selector split objects.
    splits: list[SelectorSplit] = []
    for split_number, (train_indices, test_indices) in enumerate(splitter.split(target, target)):
        repeat_index = split_number + 1
        strategy = "holdout" if splitter.n_splits == 1 else "repeated_holdout"
        label = "holdout" if strategy == "holdout" else f"holdout_r{repeat_index:02d}"
        splits.append(
            SelectorSplit(
                split_id=label,
                strategy=strategy,
                repeat_index=repeat_index,
                fold_index=None,
                stratified=stratified,
                train_indices=tuple(int(index) for index in train_indices),
                test_indices=tuple(int(index) for index in test_indices),
            )
        )
    return splits


def _can_stratify_holdout(target: pd.Series, test_size: float) -> bool:

    # Return whether a stratified holdout split is feasible.
    class_counts = target.value_counts()
    if len(class_counts.index) < 2:
        return False
    if int(class_counts.min()) < 2:
        return False

    num_samples = len(target.index)
    num_test = max(1, int(math.ceil(num_samples * test_size)))
    num_train = num_samples - num_test
    num_classes = len(class_counts.index)
    return num_test >= num_classes and num_train >= num_classes


def _normalize_strategy(strategy: str) -> str:

    # Normalize supported split strategy aliases.
    normalized = str(strategy).strip().casefold() or "holdout"
    aliases = {
        "cross_validation": "repeated_stratified_kfold",
        "repeated_cross_validation": "repeated_stratified_kfold",
        "repeated_cv": "repeated_stratified_kfold",
    }
    return aliases.get(normalized, normalized)


def _validate_test_size(test_size: float) -> None:

    # Validate a holdout-style test size.
    if not 0.0 < test_size < 1.0:
        raise ValueError("test_size must be between 0 and 1.")
