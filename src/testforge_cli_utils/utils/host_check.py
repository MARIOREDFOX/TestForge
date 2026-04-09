"""Host reachability helpers."""
from __future__ import annotations

import subprocess
import logging
import socket

logger = logging.getLogger("testforge.host_check")


def is_host_alive(host: str, count: int = 2, timeout: int = 5) -> bool:
    """
    Return True if *host* responds to ping.
    Uses a short timeout so CI runs don't hang.
    """
    if not host:
        logger.warning("is_host_alive called with empty host")
        return False
    try:
        result = subprocess.run(
            ["ping", "-c", str(count), "-W", str(timeout), host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout * count + 5,
        )
        alive = result.returncode == 0
        logger.debug("Ping %s -> %s", host, "ALIVE" if alive else "DEAD")
        return alive
    except Exception as exc:
        logger.warning("Ping failed for %s: %s", host, exc)
        return False


def is_port_open(host: str, port: int, timeout: float = 5.0) -> bool:
    """Return True if *host*:*port* is accepting TCP connections."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def is_ssh_reachable(host: str, port: int = 22, timeout: float = 5.0) -> bool:
    """Return True if SSH port is open on *host*."""
    return is_port_open(host, port, timeout)
