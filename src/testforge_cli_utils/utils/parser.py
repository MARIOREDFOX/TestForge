"""YAML / config parsing utilities."""
from __future__ import annotations

import yaml
from typing import Any, Dict


def parse_yaml(file_path: str) -> Dict[str, Any]:
    """Parse a YAML file and return its contents."""
    with open(file_path, "r") as f:
        return yaml.safe_load(f) or {}
