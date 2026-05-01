"""Configuration loader for roboweave_cloud_agent."""

from __future__ import annotations

import os
from typing import Any

import yaml


def load_config(path: str) -> dict[str, Any]:
    """Load and validate cloud_agent_params.yaml.

    Args:
        path: Path to the YAML configuration file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If the config file does not exist.
        ValueError: If the YAML is invalid or cannot be parsed.
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Configuration file not found: {path}")

    with open(path, "r") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in config file: {e}") from e

    if config is None:
        raise ValueError("Configuration file is empty")

    if not isinstance(config, dict):
        raise ValueError("Configuration must be a YAML mapping")

    return config
