# Helpers for loading simple YAML experiment configuration files.

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml


_MISSING = object()


def load_yaml_config(config_path: str | Path) -> dict[str, Any]:

    # Load a YAML configuration file into a dictionary.
    #
    # Args:
    # config_path: Path to a YAML file.
    #
    # Returns:
    # Parsed configuration data as a dictionary.
    #
    # Raises:
    # ValueError: If the YAML file does not contain a mapping at the top level.
    #
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle)

    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"Configuration root must be a mapping: {path}")
    return data


def get_config_value(
    config: Mapping[str, Any],
    dotted_key: str,
    default: object = _MISSING,
) -> Any:

    # Read a nested configuration value using dotted-key lookup.
    current: Any = config
    for part in dotted_key.split("."):
        if not isinstance(current, Mapping) or part not in current:
            if default is _MISSING:
                raise ValueError(f"Configuration is missing required key '{dotted_key}'.")
            return default
        current = current[part]
    return current


def get_config_path(
    config: Mapping[str, Any],
    dotted_key: str,
    default: object = _MISSING,
) -> Path:

    # Read a path-like configuration value and coerce it to ``Path``.
    value = get_config_value(config, dotted_key, default=default)
    if value is None:
        raise ValueError(f"Configuration key '{dotted_key}' must not be null.")
    if not isinstance(value, (str, Path)):
        raise ValueError(f"Configuration key '{dotted_key}' must be a path string.")
    return Path(value)


def get_config_string_list(
    config: Mapping[str, Any],
    dotted_key: str,
    default: object = _MISSING,
) -> list[str]:

    # Read a list of non-empty strings from a configuration mapping.
    value = get_config_value(config, dotted_key, default=default)
    if not isinstance(value, list):
        raise ValueError(f"Configuration key '{dotted_key}' must be a list.")

    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(
                f"Configuration key '{dotted_key}' must contain only non-empty strings."
            )
        items.append(item.strip())
    return items
