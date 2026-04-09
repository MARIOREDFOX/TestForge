"""TestForge CLI entry point."""
from __future__ import annotations

import sys
import click

from testforge_cli_utils.core.logger import configure_logging

ALL_TAGS = [
    "all", "system", "ping", "os", "cpu", "memory", "bios",
    "firmware", "bmc", "disk", "nvme", "pcie", "cxl",
    "nic", "network", "thermal", "power", "numa",
    "hugepages", "stress", "logs",
]


@click.group()
@click.option("--log-level", default="INFO", show_default=True,
              type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"], case_sensitive=False))
@click.option("--log-file", default="logs/testforge.log", show_default=True)
@click.pass_context
def cli(ctx, log_level, log_file):
    """TestForge — Hardware/System-Level Test Automation CLI."""
    configure_logging(level=log_level, log_file=log_file)
    ctx.ensure_object(dict)


@cli.command()
@click.argument("host", required=False, default=None)
@click.option("--tag", default=None, type=click.Choice(ALL_TAGS), help="Filter by tag.")
@click.option("--test", default=None, help="Run one test by name.")
@click.option("--env", default=None, help="Path to environment YAML.")
@click.option("--config-file", default="examples/test_config.yaml", show_default=True)
def run(host, tag, test, env, config_file):
    """
    Run tests.

    \b
    Examples:
      testforge run --env examples/env.yaml --tag pcie
      testforge run 192.168.1.10 --tag cxl
      testforge run 192.168.1.10 --tag system
      testforge run 192.168.1.10 --tag stress
    """
    from testforge_cli_utils.core.executor import run_tests

    # Allow: testforge run <host> --tag X  (shorthand without env file)
    if host and not env:
        import tempfile, yaml, os
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump({"hostname": host, "username": "root"}, tmp)
        tmp.close()
        env = tmp.name

    run_tests(config_file=config_file, tag=tag, test=test, env_file=env)


@cli.command()
def version():
    """Display version."""
    click.echo("TestForge v0.3.0")


@cli.command()
@click.argument("host")
@click.option("--username", default="root", show_default=True)
@click.option("--password", default=None)
@click.option("--key-file", default=None)
@click.option("--check", default="all", type=click.Choice(ALL_TAGS))
def probe(host, username, password, key_file, check):
    """
    Quick one-shot hardware probe without a config file.

    \b
    Examples:
      testforge probe 192.168.1.10 --check pcie
      testforge probe 192.168.1.10 --check cxl
      testforge probe 192.168.1.10 --check stress
    """
    from testforge_cli_utils.utils.host_check import is_host_alive
    from testforge_cli_utils.utils.hardware_info import HardwareInfo
    from testforge_cli_utils.core.executor import _run_hardware_tag

    if not is_host_alive(host):
        click.echo(f"[FAIL] {host} is not reachable.", err=True)
        sys.exit(1)

    click.echo(f"[OK] {host} reachable — running check: {check}\n")
    hw = HardwareInfo(host=host, username=username, password=password, key_filename=key_file)
    logs = []

    try:
        env = {"hostname": host, "username": username, "password": password}
        _run_hardware_tag(check, hw, lambda msg: (logs.append(msg), click.echo(msg)), env)
    except Exception as exc:
        click.echo(f"[ERROR] {exc}", err=True)
        sys.exit(1)
    finally:
        hw.close()


@cli.command()
@click.argument("host")
@click.option("--username", default="root", show_default=True)
@click.option("--password", default=None)
@click.option("--output", default="logs/fw_snapshot.json", show_default=True)
def fw_snapshot(host, username, password, output):
    """
    Save a firmware version snapshot for *host*.

    Use this before a firmware upgrade, then run fw-compare after.
    """
    from testforge_cli_utils.utils.hardware_info import HardwareInfo
    from testforge_cli_utils.tests.firmware.firmware_tests import FirmwareTests
    hw = HardwareInfo(host=host, username=username, password=password)
    try:
        fw = FirmwareTests()
        versions = fw.snapshot(hw, output)
        click.echo(f"Firmware snapshot saved to {output}")
        for k, v in versions.items():
            click.echo(f"  {k:20s}: {v}")
    finally:
        hw.close()


@cli.command()
@click.argument("host")
@click.option("--username", default="root", show_default=True)
@click.option("--password", default=None)
@click.option("--before", required=True, help="Path to before-snapshot JSON.")
def fw_compare(host, username, password, before):
    """
    Compare current firmware versions against a before-snapshot.

    \b
    Example:
      testforge fw-snapshot 192.168.1.10 --output before.json
      # ... perform firmware upgrade ...
      testforge fw-compare  192.168.1.10 --before before.json
    """
    from testforge_cli_utils.utils.hardware_info import HardwareInfo
    from testforge_cli_utils.tests.firmware.firmware_tests import FirmwareTests
    hw = HardwareInfo(host=host, username=username, password=password)
    try:
        fw = FirmwareTests()
        results = fw.compare_snapshots(before, hw)
        changed = [k for k, v in results.items() if v.get("changed")]
        unchanged = [k for k, v in results.items() if not v.get("changed")]
        click.echo(f"\nFirmware comparison — {host}")
        click.echo(f"Changed ({len(changed)}):   {', '.join(changed) or 'none'}")
        click.echo(f"Unchanged ({len(unchanged)}): {', '.join(unchanged)}")
        for k, v in results.items():
            marker = "✓ CHANGED" if v["changed"] else "  same"
            click.echo(f"  {marker:12s} {k:20s}: {v['before']} → {v['after']}")
    finally:
        hw.close()


if __name__ == "__main__":
    cli()
