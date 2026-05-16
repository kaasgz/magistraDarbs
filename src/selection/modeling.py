# Shared selector dataset-preparation and modeling helpers.

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from src.selection.feature_groups import feature_group_for_column
from src.utils import ensure_parent_directory


TARGET_COLUMN = "best_solver"
INSTANCE_COLUMN = "instance_name"
LEAKAGE_COLUMN_PREFIXES = (
    "objective_",
    "benchmark_",
    "label_",
    "target_",
    "dataset_",
    "source_",
    "solver_",
    "scoring_",
    "selected_",
    "true_",
    "single_best_",
    "virtual_best_",
    "prediction_",
    "regret_",
    "delta_",
    "improvement_",
)
LEAKAGE_COLUMN_NAMES = {
    "dataset_type",
    "is_synthetic",
    "source_kind",
    "source_type",
    "dataset_source",
    "source_dataset",
    "instance_source_path",
    "instance_path",
    "xml_path",
    "file_path",
    "source_path",
    "source_file",
    "raw_file",
    "generator_seed",
    "generation_seed",
    "random_seed",
    "seed",
    "solver_name",
    "solver_registry_name",
    "solver_support_status",
    "support_status",
    "scoring_status",
    "modeling_scope",
    "scoring_notes",
    "objective_value",
    "objective_value_valid",
    "objective_sense",
    "runtime_seconds",
    "feasible",
    "status",
    "error_message",
}
BENCHMARK_DERIVED_PREFIXES = LEAKAGE_COLUMN_PREFIXES


@dataclass(frozen=True, slots=True)
class PreparedSelectionData:

    # Selection dataset columns prepared for leakage-safe training.
    features: pd.DataFrame
    target: pd.Series
    instance_names: pd.Series
    feature_columns: tuple[str, ...]
    excluded_columns: tuple[str, ...]


def prepare_selection_data(dataset: pd.DataFrame) -> PreparedSelectionData:

    # Return labeled selector data with leakage-prone columns excluded.
    if INSTANCE_COLUMN not in dataset.columns:
        raise ValueError("Selection dataset must contain an 'instance_name' column.")
    if TARGET_COLUMN not in dataset.columns:
        raise ValueError("Selection dataset must contain a 'best_solver' column.")

    labeled = dataset[dataset[TARGET_COLUMN].notna()].copy()
    if labeled.empty:
        raise ValueError("Selection dataset does not contain any labeled rows.")
    if len(labeled.index) < 2:
        raise ValueError("Selection dataset must contain at least two labeled rows.")

    feature_columns = tuple(
        column
        for column in labeled.columns
        if column not in {INSTANCE_COLUMN, TARGET_COLUMN}
        and not is_leakage_column(column)
    )
    if not feature_columns:
        raise ValueError("Selection dataset does not contain usable feature columns.")

    excluded_columns = tuple(
        column for column in labeled.columns if column not in {INSTANCE_COLUMN, TARGET_COLUMN, *feature_columns}
    )
    return PreparedSelectionData(
        features=labeled.loc[:, list(feature_columns)].copy(),
        target=labeled[TARGET_COLUMN].astype(str).copy(),
        instance_names=labeled[INSTANCE_COLUMN].astype(str).copy(),
        feature_columns=feature_columns,
        excluded_columns=excluded_columns,
    )


def is_leakage_column(column: object) -> bool:

    # Return whether a column is unsafe as a pre-solving structural feature.
    normalized = str(column).strip().casefold()
    return normalized in LEAKAGE_COLUMN_NAMES or normalized.startswith(LEAKAGE_COLUMN_PREFIXES)


def build_selector_pipeline(
    model_name: str,
    random_seed: int,
    dataset: pd.DataFrame,
) -> Pipeline:

    # Build one selector training pipeline for mixed-type structural features.
    preprocessor = _build_preprocessor(dataset)

    if model_name == "random_forest":
        estimator = RandomForestClassifier(
            n_estimators=200,
            random_state=random_seed,
            class_weight="balanced",
            n_jobs=1,
        )
    else:
        raise ValueError(f"Unsupported selector model '{model_name}'.")

    return Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", estimator),
        ]
    )


def save_feature_importance(pipeline: Pipeline, output_path: str | Path | None) -> Path | None:

    # Save feature importance values when the estimator exposes them.
    if output_path is None:
        return None

    classifier = pipeline.named_steps["classifier"]
    if not hasattr(classifier, "feature_importances_"):
        return None

    preprocessor = pipeline.named_steps["preprocessor"]
    original_columns = _original_feature_columns(preprocessor)
    if hasattr(preprocessor, "get_feature_names_out"):
        feature_names = list(preprocessor.get_feature_names_out())
    else:
        feature_names = [f"feature_{index}" for index in range(len(classifier.feature_importances_))]

    importance = pd.DataFrame(
        {
            "feature": feature_names,
            "source_feature": [
                _resolve_source_feature_name(
                    transformed_feature_name=name,
                    original_columns=original_columns,
                )
                for name in feature_names
            ],
            "importance": classifier.feature_importances_,
        }
    )
    importance["feature_group"] = importance["source_feature"].map(feature_group_for_column)
    importance = importance.sort_values(
        by=["importance", "source_feature", "feature"],
        ascending=[False, True, True],
        kind="mergesort",
    ).reset_index(drop=True)
    importance.insert(0, "importance_rank", range(1, len(importance.index) + 1))

    path = ensure_parent_directory(output_path)
    importance.to_csv(path, index=False)
    return path


def _build_preprocessor(dataset: pd.DataFrame) -> ColumnTransformer:

    # Build a preprocessing transformer for numeric and categorical features.
    categorical_columns = [
        column
        for column in dataset.columns
        if str(dataset[column].dtype) in {"object", "string", "category"}
    ]
    numeric_columns = [column for column in dataset.columns if column not in categorical_columns]

    return ColumnTransformer(
        transformers=[
            (
                "numeric",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="median")),
                    ]
                ),
                numeric_columns,
            ),
            (
                "categorical",
                Pipeline(
                    steps=[
                        ("imputer", SimpleImputer(strategy="most_frequent")),
                        ("encoder", OneHotEncoder(handle_unknown="ignore", sparse_output=False)),
                    ]
                ),
                categorical_columns,
            ),
        ],
        remainder="drop",
    )


def _original_feature_columns(preprocessor: ColumnTransformer) -> tuple[str, ...]:

    # Return the original input feature columns seen by the fitted preprocessor.
    columns: list[str] = []
    for _, _, transformer_columns in preprocessor.transformers_:
        if transformer_columns == "drop":
            continue
        if isinstance(transformer_columns, str):
            columns.append(transformer_columns)
            continue
        columns.extend(str(column) for column in transformer_columns)
    return tuple(columns)


def _resolve_source_feature_name(
    *,
    transformed_feature_name: str,
    original_columns: tuple[str, ...],
) -> str:

    # Map one transformed model feature name back to its source feature column.
    raw_name = transformed_feature_name
    if "__" in raw_name:
        _, raw_name = raw_name.split("__", maxsplit=1)

    if raw_name in original_columns:
        return raw_name

    matching_columns = [
        column
        for column in original_columns
        if raw_name.startswith(f"{column}_")
    ]
    if not matching_columns:
        return raw_name
    return max(matching_columns, key=len)
