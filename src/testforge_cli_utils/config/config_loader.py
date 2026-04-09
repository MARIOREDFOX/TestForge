"""YAML config loader with schema validation hints."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict

import yaml

logger = logging.getLogger("testforge.config")


def load_config(path: str) -> Dict[str, Any]:
    """
    Load a YAML config file and return its contents as a dict.

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError if the file cannot be parsed.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config not found: {path}")
    try:
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ValueError(f"Config must be a YAML mapping, got: {type(data)}")
        return data
    except yaml.YAMLError as exc:
        raise ValueError(f"YAML parse error in {path}: {exc}") from exc


def load_env(path: str) -> Dict[str, Any]:
    """Load an environment YAML file. Returns empty dict if path is None/missing."""
    if not path or not os.path.exists(path):
        logger.debug("Env file not found or not specified: %s", path)
        return {}
    return load_config(path)
