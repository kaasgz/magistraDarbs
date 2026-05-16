# Helpers for reproducible experiment configuration and artifact metadata.

from __future__ import annotations

import json
import math
import platform
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.utils.config import (
    _MISSING,
    get_config_path,
    get_config_string_list,
    get_config_value,
)


@dataclass(frozen=True, slots=True)
class SplitSettings:

    # Selector split configuration loaded from YAML.
    strategy: str
    test_size: float
    cross_validation_folds: int | None
    repeats: int


def get_compat_value(
    config: dict[str, Any],
    dotted_keys: list[str],
    default: object = _MISSING,
) -> Any:

    # Read the first available value from a list of compatible config keys.
    for dotted_key in dotted_keys:
        try:
            return get_config_value(config, dotted_key)
        except ValueError:
            continue

    if default is _MISSING:
        joined = ", ".join(dotted_keys)
        raise ValueError(f"Configuration is missing all supported keys: {joined}")
    return default


def get_compat_path(
    config: dict[str, Any],
    dotted_keys: list[str],
    default: object = _MISSING,
) -> Path:

    # Read the first available path from a list of compatible config keys.
    for dotted_key in dotted_keys:
        try:
            return get_config_path(config, dotted_key)
        except ValueError:
            continue

    if default is _MISSING:
        joined = ", ".join(dotted_keys)
        raise ValueError(f"Configuration is missing all supported path keys: {joined}")
    if isinstance(default, Path):
        return default
    if isinstance(default, str):
        return Path(default)
    raise ValueError("Default path value must be a string or Path.")


def get_compat_string_list(
    config: dict[str, Any],
    dotted_keys: list[str],
    default: object = _MISSING,
) -> list[str]:

    # Read the first available non-empty string list from compatible keys.
    for dotted_key in dotted_keys:
        try:
            return get_config_string_list(config, dotted_key)
        except ValueError:
            continue

    if default is _MISSING:
        joined = ", ".join(dotted_keys)
        raise ValueError(f"Configuration is missing all supported list keys: {joined}")
    if not isinstance(default, list):
        raise ValueError("Default list value must be a list of strings.")
    return [str(item) for item in default]


def get_random_seed(config: dict[str, Any], default: int = 42) -> int:

    # Read the experiment random seed from a config mapping.
    return int(get_compat_value(config, ["run.random_seed", "random_seed"], default))


def get_time_limit_seconds(config: dict[str, Any], default: int = 60) -> int:

    # Read the configured solver time limit from a config mapping.
    return int(get_compat_value(config, ["run.time_limit_seconds", "time_limit_seconds"], default))


def get_selected_solvers(config: dict[str, Any], default: list[str]) -> list[str]:

    # Read the configured solver portfolio from a config mapping.
    return get_compat_string_list(config, ["solvers.selected", "selected_solvers"], default)


def get_solver_settings_by_name(config: dict[str, Any]) -> dict[str, dict[str, object]]:

    # Read optional per-solver constructor settings from a config mapping.
    raw_value = get_compat_value(config, ["solvers.settings", "solver_settings"], {})
    if raw_value in ({}, None):
        return {}
    if not isinstance(raw_value, dict):
        raise ValueError("Configuration key 'solvers.settings' must be a mapping of solver settings.")

    settings: dict[str, dict[str, object]] = {}
    for solver_name, solver_settings in raw_value.items():
        normalized_name = str(solver_name).strip()
        if not normalized_name:
            raise ValueError("Solver setting names must be non-empty strings.")
        if solver_settings is None:
            settings[normalized_name] = {}
            continue
        if not isinstance(solver_settings, dict):
            raise ValueError(
                f"Configuration key 'solvers.settings.{normalized_name}' must be a mapping."
            )
        settings[normalized_name] = {str(key): value for key, value in solver_settings.items()}
    return settings


def get_include_solver_objectives(config: dict[str, Any], default: bool = True) -> bool:

    # Read the selection-dataset objective-column toggle.
    return bool(
        get_compat_value(
            config,
            ["dataset.include_solver_objectives", "include_solver_objectives"],
            default,
        )
    )


def get_model_choice(config: dict[str, Any], default: str = "random_forest") -> str:

    # Read the selector model family from config.
    return str(get_compat_value(config, ["selector.model_choice", "model_choice"], default)).strip()


def get_split_settings(config: dict[str, Any]) -> SplitSettings:

    # Read selector split settings from config.
    strategy = str(get_compat_value(config, ["split.strategy"], "holdout")).strip().casefold() or "holdout"
    test_size = float(get_compat_value(config, ["split.test_size", "test_size"], 0.25))
    raw_folds = get_compat_value(config, ["split.cross_validation_folds"], None)
    cross_validation_folds = int(raw_folds) if raw_folds is not None else None
    repeats = int(get_compat_value(config, ["split.repeats"], 1))
    return SplitSettings(
        strategy=strategy,
        test_size=test_size,
        cross_validation_folds=cross_validation_folds,
        repeats=repeats,
    )


def ensure_directory(path: str | Path) -> Path:

    # Create one directory path safely and return it.
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def ensure_parent_directory(path: str | Path) -> Path:

    # Create the parent directory for a file path safely and return the file path.
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    return file_path


def default_run_summary_path(output_path: str | Path) -> Path:

    # Derive a deterministic run-summary JSON path from an output artifact path.
    path = Path(output_path)
    if path.suffix:
        return path.with_name(f"{path.stem}_run_summary.json")
    return path / "run_summary.json"


def write_run_summary(
    summary_path: str | Path,
    *,
    stage_name: str,
    config_path: str | Path | None,
    config: dict[str, Any] | None,
    settings: dict[str, Any],
    inputs: dict[str, Any],
    outputs: dict[str, Any],
    results: dict[str, Any],
) -> Path:

    # Write one JSON run summary with lightweight reproducibility metadata.
    output_path = ensure_parent_directory(summary_path)
    payload = {
        "stage_name": stage_name,
        "generated_at": _timestamp_now(),
        "config_path": Path(config_path).as_posix() if config_path is not None else None,
        "settings": _json_safe_value(settings),
        "inputs": _json_safe_value(inputs),
        "outputs": _json_safe_value(outputs),
        "results": _json_safe_value(results),
        "config_snapshot": _json_safe_value(config) if config is not None else None,
        "environment": {
            "python_version": sys.version.split()[0],
            "platform": platform.platform(),
        },
    }
    output_path.write_text(
        json.dumps(payload, indent=2),
        encoding="utf-8",
    )
    return output_path


def _json_safe_value(value: Any) -> Any:

    # Convert nested values into JSON-safe primitives.
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_value(item) for item in value]
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return value
    if isinstance(value, (int, str)):
        return value

    item_method = getattr(value, "item", None)
    if callable(item_method):
        try:
            return _json_safe_value(item_method())
        except (TypeError, ValueError):
            pass

    return str(value)


def _timestamp_now() -> str:

    # Return the current timestamp as an ISO string.
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
