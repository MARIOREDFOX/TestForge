"""
Legacy ssh.py kept for backward compatibility.
New code should use SSHCommand from ssh_command.py directly.
"""
from __future__ import annotations
import logging
from testforge_cli_utils.utils.ssh_command import SSHCommand, _PARAMIKO_AVAILABLE

logger = logging.getLogger("testforge.ssh_legacy")


def ssh_connect(host: str, username: str, password: str = None, key_filename: str = None):
    """Return a connected SSHCommand instance."""
    return SSHCommand(
        host=host,
        username=username,
        password=password,
        key_filename=key_filename,
    )


def run_ssh_command(ssh: SSHCommand, command: str):
    """Run a command via an SSHCommand instance. Returns (stdout, stderr)."""
    return ssh.run(command)
