"""
SSH command execution utility.

paramiko is an optional dependency. When it is not installed the module still
imports cleanly; an ImportError is only raised at *runtime* when you try to
actually open a connection. This is what causes the traceback you reported:

    ModuleNotFoundError: No module named 'paramiko'

The fix: wrap the import in a try/except and raise a clear, actionable error
only when SSHCommand.__init__ is called without paramiko present.
"""
from __future__ import annotations

import time
import logging
from typing import Optional, Tuple

logger = logging.getLogger("testforge.ssh")

try:
    import paramiko
    _PARAMIKO_AVAILABLE = True
except ImportError:
    _PARAMIKO_AVAILABLE = False


class SSHCommand:
    """
    Thin wrapper around paramiko that provides:
    - Lazy connection (connect on first use, not on import)
    - Key-based auth with password fallback
    - Configurable timeout and retry
    - Context-manager support  (``with SSHCommand(...) as ssh:``)
    """

    def __init__(
        self,
        host: str,
        username: str = "root",
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = 22,
        timeout: float = 30.0,
        connect_retries: int = 3,
    ):
        if not _PARAMIKO_AVAILABLE:
            raise RuntimeError(
                "paramiko is not installed. "
                "Run: pip install paramiko\n"
                "Then re-run your testforge command."
            )

        self.host = host
        self.username = username
        self.password = password
        self.key_filename = key_filename
        self.port = port
        self.timeout = timeout
        self.connect_retries = connect_retries
        self._client = None  # lazy

    def _ensure_connected(self):
        if self._client is not None:
            try:
                transport = self._client.get_transport()
                if transport and transport.is_active():
                    return
            except Exception:
                pass
            self._client = None

        last_err = None
        for attempt in range(1, self.connect_retries + 1):
            try:
                client = paramiko.SSHClient()
                client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                connect_kwargs = dict(
                    hostname=self.host,
                    port=self.port,
                    username=self.username,
                    timeout=self.timeout,
                    allow_agent=True,
                    look_for_keys=True,
                )
                if self.key_filename:
                    connect_kwargs["key_filename"] = self.key_filename
                if self.password:
                    connect_kwargs["password"] = self.password

                client.connect(**connect_kwargs)
                self._client = client
                logger.debug("SSH connected to %s (attempt %d)", self.host, attempt)
                return
            except Exception as exc:
                last_err = exc
                logger.warning(
                    "SSH connect attempt %d/%d to %s failed: %s",
                    attempt, self.connect_retries, self.host, exc,
                )
                if attempt < self.connect_retries:
                    time.sleep(2 ** attempt)

        raise ConnectionError(
            f"Cannot SSH to {self.host}:{self.port} after {self.connect_retries} attempts: {last_err}"
        )

    def run(self, command: str, timeout: float = 60.0):
        """Execute command. Returns (stdout, stderr) strings."""
        self._ensure_connected()
        logger.debug("SSH[%s] $ %s", self.host, command)
        stdin, stdout, stderr = self._client.exec_command(command, timeout=timeout)
        out = stdout.read().decode(errors="replace")
        err = stderr.read().decode(errors="replace")
        stdout.channel.recv_exit_status()  # wait for completion
        return out, err

    def close(self):
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
