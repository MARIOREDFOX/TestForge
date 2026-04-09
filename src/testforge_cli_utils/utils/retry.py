"""Retry utility with exponential back-off and jitter."""
from __future__ import annotations

import time
import random
import logging
from typing import Callable, TypeVar, Optional, Tuple

logger = logging.getLogger("testforge.retry")

T = TypeVar("T")


def retry_test(
    func: Callable[[], T],
    retries: int = 3,
    delay: float = 5.0,
    backoff: float = 2.0,
    jitter: float = 0.5,
    exceptions: Tuple[type, ...] = (Exception,),
) -> T:
    """
    Call *func* up to *retries* times.

    On each failure the sleep is  delay * backoff^attempt  plus random jitter.

    Args:
        func: Zero-argument callable to execute.
        retries: Maximum number of attempts.
        delay: Base sleep seconds between attempts.
        backoff: Multiplier applied to delay after each failure.
        jitter: Maximum random seconds added to each sleep.
        exceptions: Exception types that trigger a retry.

    Returns:
        The return value of *func* on success.

    Raises:
        The last exception if all attempts fail.
    """
    current_delay = delay
    last_exc: Optional[Exception] = None

    for attempt in range(1, retries + 1):
        try:
            return func()
        except exceptions as exc:
            last_exc = exc
            if attempt == retries:
                logger.error("All %d attempts failed: %s", retries, exc)
                raise

            sleep_time = current_delay + random.uniform(0, jitter)
            logger.warning(
                "Attempt %d/%d failed (%s). Retrying in %.1fs …",
                attempt, retries, exc, sleep_time,
            )
            time.sleep(sleep_time)
            current_delay *= backoff

    raise last_exc  # type: ignore[misc]
