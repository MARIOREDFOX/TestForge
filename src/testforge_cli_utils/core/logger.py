"""
Centralised logging configuration for TestForge.

Call configure_logging() once at startup (cli.py does this).
All other modules just do:  logger = logging.getLogger("testforge.<module>")
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import sys
from typing import Optional


def configure_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rich_output: bool = True,
) -> None:
    """
    Set up root testforge logger.

    Args:
        level: 'DEBUG', 'INFO', 'WARNING', 'ERROR'
        log_file: If given, also write to this file.
        rich_output: Use rich for pretty console output when available.
    """
    root = logging.getLogger("testforge")
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    root.handlers.clear()

    fmt = "%(asctime)s [%(levelname)-8s] %(name)s — %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"

    # Console handler
    console_handler: logging.Handler
    if rich_output:
        try:
            from rich.logging import RichHandler
            console_handler = RichHandler(
                rich_tracebacks=True,
                show_path=False,
                log_time_format="[%H:%M:%S]",
            )
            console_handler.setFormatter(logging.Formatter("%(message)s"))
        except ImportError:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
    else:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(fmt, datefmt=datefmt))

    root.addHandler(console_handler)

    # File handler
    if log_file:
        os.makedirs(os.path.dirname(log_file) if os.path.dirname(log_file) else ".", exist_ok=True)
        fh = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        fh.setFormatter(logging.Formatter(fmt, datefmt=datefmt))
        root.addHandler(fh)


# Module-level convenience functions (backward compatible)
_logger = logging.getLogger("testforge")


def log_event(message: str) -> None:
    _logger.info(message)


def log_error(message: str) -> None:
    _logger.error(message)


def log_warning(message: str) -> None:
    _logger.warning(message)
