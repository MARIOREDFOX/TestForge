"""
Test result reporter — writes JSON, pretty console table, and appends to
the run log.
"""
from __future__ import annotations

import json
import os
import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger("testforge.reporter")


def generate_report(results: List[Dict[str, Any]], output_path: str = "logs/test_report.json") -> None:
    """Write results as a JSON report file."""
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
    report = {
        "generated_at": datetime.datetime.now().isoformat(),
        "total": len(results),
        "passed": sum(1 for r in results if r.get("status") == "passed"),
        "failed": sum(1 for r in results if r.get("status") == "failed"),
        "skipped": sum(1 for r in results if r.get("status") == "skipped"),
        "tests": results,
    }
    with open(output_path, "w") as f:
        json.dump(report, f, indent=4)
    logger.info("Report written to %s", output_path)


def display_report(results: List[Dict[str, Any]]) -> None:
    """Pretty-print a summary table to stdout."""
    try:
        from rich.table import Table
        from rich.console import Console

        console = Console()
        table = Table(title="TestForge Results", show_lines=True)
        table.add_column("Test", style="cyan")
        table.add_column("Tag")
        table.add_column("Status", justify="center")
        table.add_column("Duration (s)", justify="right")

        for r in results:
            status = r.get("status", "unknown")
            colour = {"passed": "green", "failed": "red", "skipped": "yellow"}.get(status, "white")
            table.add_row(
                r.get("name", "?"),
                ", ".join(r.get("tags", [])),
                f"[{colour}]{status.upper()}[/{colour}]",
                str(r.get("duration", "?")),
            )

        console.print(table)
        passed = sum(1 for r in results if r.get("status") == "passed")
        console.print(f"\n[bold]Total: {len(results)}  Passed: {passed}  Failed: {len(results)-passed}[/bold]")

    except ImportError:
        # plain fallback
        print("\n--- TestForge Results ---")
        for r in results:
            print(f"  [{r.get('status','?').upper():8s}] {r.get('name','?')}")
        passed = sum(1 for r in results if r.get("status") == "passed")
        print(f"Total: {len(results)}  Passed: {passed}  Failed: {len(results)-passed}\n")
