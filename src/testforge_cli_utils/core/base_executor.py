"""Base class for all test runners."""
from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("testforge.executor")


class Executor:
    """
    Abstract base for all runner classes.

    Subclasses must implement ``run()``.
    """

    def __init__(self, env: Dict[str, Any], **kwargs: Any) -> None:
        self.env = env

    def run(self) -> None:
        raise NotImplementedError(f"{self.__class__.__name__}.run() not implemented")
