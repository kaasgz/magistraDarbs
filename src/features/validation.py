"""Validation helpers for extracted structural features."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from src.features.manifest import feature_names


@dataclass(frozen=True, slots=True)
class FeatureValidationIssue:
    """One validation issue found in a feature mapping."""

    code: str
    feature_name: str
    message: str


class FeatureValidationError(ValueError):
    """Raised when extracted features fail basic validation checks."""


def validate_feature_names(names: Sequence[str]) -> list[FeatureValidationIssue]:
    """Return duplicate feature-name issues for the provided sequence."""

    counts = Counter(names)
    return [
        FeatureValidationIssue(
            code="duplicate_feature_name",
            feature_name=name,
            message=f"Feature name '{name}' appears {count} times.",
        )
        for name, count in sorted(counts.items())
        if count > 1
    ]


def validate_feature_values(features: Mapping[str, object]) -> list[FeatureValidationIssue]:
    """Return issues related to numeric validity and ratio bounds."""

    issues: list[FeatureValidationIssue] = []
    for name, value in features.items():
        if isinstance(value, bool):
            continue

        if isinstance(value, (int, float)):
            numeric_value = float(value)
            if not math.isfinite(numeric_value):
                issues.append(
                    FeatureValidationIssue(
                        code="non_finite_numeric_value",
                        feature_name=name,
                        message=f"Feature '{name}' has non-finite numeric value {value!r}.",
                    )
                )
                continue

            if name.startswith("num_") or name.startswith("number_of_") or name.endswith("_count"):
                if numeric_value < 0:
                    issues.append(
                        FeatureValidationIssue(
                            code="negative_count_value",
                            feature_name=name,
                            message=f"Feature '{name}' has negative count value {value!r}.",
                        )
                    )

            if name.startswith("ratio_") and not (0.0 <= numeric_value <= 1.0):
                issues.append(
                    FeatureValidationIssue(
                        code="invalid_ratio_value",
                        feature_name=name,
                        message=f"Feature '{name}' should be in [0, 1] but is {value!r}.",
                    )
                )

    return issues


def ensure_valid_features(features: Mapping[str, object]) -> None:
    """Raise when a feature mapping fails basic consistency checks."""

    issues = [
        *validate_feature_names(list(features.keys())),
        *validate_feature_values(features),
    ]

    expected_names = feature_names()
    if tuple(features.keys()) != expected_names:
        missing = [name for name in expected_names if name not in features]
        unexpected = [name for name in features if name not in expected_names]
        if missing:
            issues.append(
                FeatureValidationIssue(
                    code="missing_feature_definition",
                    feature_name=",".join(missing),
                    message=f"Missing expected features: {', '.join(missing)}.",
                )
            )
        if unexpected:
            issues.append(
                FeatureValidationIssue(
                    code="unexpected_feature_definition",
                    feature_name=",".join(unexpected),
                    message=f"Unexpected extracted features: {', '.join(unexpected)}.",
                )
            )

    if not issues:
        return

    message = "; ".join(issue.message for issue in issues)
    raise FeatureValidationError(message)
