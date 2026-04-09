"""
Main test execution engine.

Supports all 20 tags:
  ping, os, cpu, memory, bios, firmware, bmc, disk, nvme,
  pcie, cxl, nic, thermal, power, numa, hugepages,
  stress, logs, network, all

Also supports:
  - Parallel execution across multiple hosts
  - Per-test retry with exponential back-off
  - JSON + rich console report
"""
from __future__ import annotations

import concurrent.futures
import datetime
import logging
import os
import time
from typing import Any, Dict, List, Optional

import yaml

from testforge_cli_utils.core.reporter import generate_report, display_report
from testforge_cli_utils.utils.host_check import is_host_alive, is_ssh_reachable
from testforge_cli_utils.utils.retry import retry_test

logger = logging.getLogger("testforge.executor")


# ---------------------------------------------------------------------------
# Runner registry
# ---------------------------------------------------------------------------
def _build_runner_registry() -> Dict[str, Any]:
    registry: Dict[str, Any] = {}
    try:
        from testforge_cli_utils.runner.cxl_health_check_runner import CXLHealthCheckRunner
        registry["cxl_health_check"] = CXLHealthCheckRunner
    except Exception as exc:
        logger.debug("CXLHealthCheckRunner not loaded: %s", exc)
    try:
        from testforge_cli_utils.runner.stress_runner import StressRunner
        registry["stress"] = StressRunner
    except Exception as exc:
        logger.debug("CXLHealthCheckRunner not loaded: %s", exc)
    return registry


TEST_RUNNERS = _build_runner_registry()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def timestamp() -> str:
    return datetime.datetime.now().strftime("[%Y-%m-%d %H:%M:%S]")


def load_config(config_file: str) -> Dict[str, Any]:
    with open(config_file, "r") as f:
        return yaml.safe_load(f) or {}


def write_logs(lines: List[str], path: str = "logs/results.log") -> None:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "a") as f:
        for line in lines:
            f.write(line + "\n")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def run_tests(
    config_file: Optional[str] = None,
    tag: Optional[str] = None,
    test: Optional[str] = None,
    env_file: Optional[str] = None,
) -> None:
    """Main entry point called by the CLI."""
    env: Dict[str, Any] = {}

    if env_file and os.path.exists(env_file):
        with open(env_file, "r") as f:
            env = yaml.safe_load(f) or {}

        test_type = env.get("test_type", "").lower()
        if test_type in TEST_RUNNERS:
            runner_class = TEST_RUNNERS[test_type]
            runner = runner_class(env)
            runner.run()
            return

    if not config_file:
        config_file = "examples/test_config.yaml"

    if not os.path.exists(config_file):
        raise FileNotFoundError(f"Config file not found: {config_file}")

    config = load_config(config_file)
    tests = config.get("tests", [])

    if tag:
        tests = [t for t in tests if tag in t.get("tags", [])]
    if test:
        tests = [t for t in tests if t.get("name") == test]

    if not env:
        env = config.get("env", {})

    results: List[Dict[str, Any]] = []

    # Parallel execution: if env defines multiple hosts, run them concurrently
    hosts = env.get("hosts") or ([env.get("hostname") or env.get("host")] if env.get("hostname") or env.get("host") else [None])
    max_workers = env.get("parallel_workers", 1)

    if len(hosts) > 1 and max_workers > 1:
        results = _run_parallel(tests, env, hosts, max_workers)
    else:
        results = _run_sequential(tests, env)

    display_report(results)
    generate_report(results)


def _run_sequential(tests: List[Dict[str, Any]], env: Dict[str, Any]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    for test_def in tests:
        if not test_def.get("enabled", False):
            logger.info("Skipping disabled test: %s", test_def.get("name"))
            results.append({"name": test_def.get("name"), "tags": test_def.get("tags", []), "status": "skipped", "duration": 0})
            continue

        name = test_def["name"]
        logger.info("Running test: %s", name)
        t0 = time.monotonic()

        try:
            passed = retry_test(
                lambda td=test_def: execute_test(td, env),
                retries=test_def.get("retries", 1),
                delay=test_def.get("retry_delay", 5),
            )
        except Exception as exc:
            logger.error("Test %s raised: %s", name, exc)
            passed = False

        duration = round(time.monotonic() - t0, 2)
        status = "passed" if passed else "failed"
        logger.info("Test %s %s (%.1fs)", name, status.upper(), duration)
        results.append({"name": name, "tags": test_def.get("tags", []), "status": status, "duration": duration})
    return results


def _run_parallel(
    tests: List[Dict[str, Any]],
    env: Dict[str, Any],
    hosts: List[str],
    max_workers: int,
) -> List[Dict[str, Any]]:
    """Run the same test suite against multiple hosts concurrently."""
    results: List[Dict[str, Any]] = []
    logger.info("Parallel execution: %d hosts, %d workers", len(hosts), max_workers)

    def run_for_host(host: str) -> List[Dict[str, Any]]:
        host_env = {**env, "hostname": host}
        return _run_sequential(tests, host_env)

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(run_for_host, h): h for h in hosts}
        for future in concurrent.futures.as_completed(futures):
            host = futures[future]
            try:
                host_results = future.result()
                # tag each result with host
                for r in host_results:
                    r["host"] = host
                results.extend(host_results)
            except Exception as exc:
                logger.error("Host %s execution failed: %s", host, exc)
                results.append({"name": f"host_{host}", "tags": [], "status": "failed", "duration": 0, "host": host})

    return results


# ---------------------------------------------------------------------------
# Per-test execution
# ---------------------------------------------------------------------------

def _get_hw(env: Dict[str, Any]):
    from testforge_cli_utils.utils.hardware_info import HardwareInfo
    host = env.get("hostname") or env.get("host", "localhost")
    return HardwareInfo(
        host=host,
        username=env.get("username", "root"),
        password=env.get("password"),
        key_filename=env.get("key_filename"),
    )


def execute_test(test: Dict[str, Any], env: Dict[str, Any]) -> bool:
    host = env.get("hostname") or env.get("host", "localhost")
    tags = test.get("tags", [])
    tag = tags[0] if tags else "unknown"
    logs: List[str] = []

    def log(msg: str) -> None:
        logs.append(f"{timestamp()} {msg}")
        logger.info(msg)

    log(f"=== Running Test: {test['name']} on {host} ===")

    if not is_host_alive(host):
        log(f"[FAIL] {host} is not reachable via ping")
        write_logs(logs)
        return False
    log(f"[PASS] {host} is reachable via ping")

    if tag != "ping" and not is_ssh_reachable(host):
        log(f"[FAIL] SSH port not reachable on {host}")
        write_logs(logs)
        return False

    if tag == "ping":
        write_logs(logs)
        return True

    try:
        hw = _get_hw(env)
    except Exception as exc:
        log(f"[FAIL] Cannot initialise SSH to {host}: {exc}")
        write_logs(logs)
        return False

    try:
        passed = _run_hardware_tag(tag, hw, log, env)
    except Exception as exc:
        log(f"[FAIL] Unexpected error for tag '{tag}': {exc}")
        passed = False
    finally:
        hw.close()

    write_logs(logs)
    return passed


def _run_hardware_tag(tag: str, hw, log, env: Dict[str, Any]) -> bool:
    """Dispatch to the correct checks by tag. Returns True = PASS."""

    def collect(label: str, method_name: str) -> None:
        info = getattr(hw, method_name)()
        if isinstance(info, dict):
            for k, v in info.items():
                log(f"[PASS] {label}/{k}:\n{v}")
        else:
            log(f"[PASS] {label}:\n{info}")

    # ---- simple collect-only tags ----
    collect_tags: Dict[str, List] = {
        "os":        [("OS Info",    "get_os_info"),
                      ("Kernel",     "get_kernel_info"),
                      ("Uptime",     "get_uptime")],
        "cpu":       [("CPU Info",   "get_cpu_info"),
                      ("CPU Topo",   "get_cpu_topology"),
                      ("CPU Freq",   "get_cpu_freq"),
                      ("Vuln",       "get_cpu_vulnerabilities")],
        "memory":    [("Memory",     "get_memory_info"),
                      ("ECC Status", "get_memory_ecc_status"),
                      ("ECC Errors", "get_memory_ecc_errors"),
                      ("DIMM Info",  "get_memory_dimm_info")],
        "bios":      [("BIOS Info",  "get_bios_info")],
        "firmware":  [("All FW",     "get_all_firmware_versions")],
        "bmc":       [("BMC Info",   "get_bmc_info"),
                      ("SDR",        "get_bmc_sdr"),
                      ("SEL",        "get_bmc_sel"),
                      ("SEL Errors", "get_bmc_sel_errors"),
                      ("Power",      "get_bmc_power_status"),
                      ("FRU",        "get_bmc_fru"),
                      ("LAN",        "get_bmc_lan_info")],
        "disk":      [("Disk",       "get_disk_info"),
                      ("NVMe List",  "get_nvme_list"),
                      ("SMART",      "get_disk_smart")],
        "nvme":      [("NVMe List",  "get_nvme_list"),
                      ("NVMe Health","get_nvme_health"),
                      ("NVMe Errors","get_nvme_error_log")],
        "pcie":      [("Devices",    "get_pcie_devices"),
                      ("Gen/Width",  "get_pcie_gen_summary"),
                      ("Link Status","get_pcie_link_status"),
                      ("AER",        "get_pcie_aer_detail"),
                      ("Errors",     "get_pcie_errors")],
        "cxl":       [("Devices",    "get_cxl_devices"),
                      ("Mem Info",   "get_cxl_mem_info"),
                      ("Topology",   "get_cxl_topology"),
                      ("Ports",      "get_cxl_port_info"),
                      ("Errors",     "get_cxl_error_counters"),
                      ("Latency",    "get_cxl_latency_check"),
                      ("dmesg",      "get_cxl_dmesg_events")],
        "nic":       [("NIC Info",   "get_nic_info"),
                      ("Speed",      "get_nic_speed"),
                      ("Errors",     "get_network_errors"),
                      ("ethtool",    "get_ethtool_stats")],
        "thermal":   [("Thermal",    "get_thermal_info"),
                      ("Fans",       "get_fan_info"),
                      ("Voltage",    "get_voltage_info")],
        "power":     [("Power",      "get_power_info")],
        "numa":      [("NUMA",       "get_numa_topology")],
        "hugepages": [("Hugepages",  "get_hugepages")],
    }

    if tag in collect_tags:
        for label, method in collect_tags[tag]:
            collect(label, method)
        return True

    # ---- stress tag ----
    if tag == "stress":
        from testforge_cli_utils.tests.stress.stress_tests import StressTests
        thresholds = env.get("stress_thresholds", {})
        st = StressTests(thresholds)
        stress_results: Dict[str, Any] = {}
        st.run_all(hw, stress_results)
        failed = []
        for name, r in stress_results.items():
            status = r.get("status", "FAIL")
            log(f"[{status}] Stress/{name}: {r.get('detail', '')[:120]}")
            if status == "FAIL":
                failed.append(name)
        return len(failed) == 0

    # ---- logs tag ----
    if tag == "logs":
        from testforge_cli_utils.tests.logs.log_validator import LogValidator
        lv = LogValidator()
        log_results = lv.run_all(hw)
        failed = []
        for name, r in log_results.items():
            status = r.get("status", "PASS")
            log(f"[{status}] Logs/{name}: {r.get('detail', '')}")
            if status == "FAIL":
                failed.append(name)
        return len(failed) == 0

    # ---- network tag ----
    if tag == "network":
        from testforge_cli_utils.tests.network.network_tests import NetworkTests
        net = NetworkTests(
            max_packet_loss_pct=env.get("max_packet_loss_pct", 5),
            max_latency_ms=env.get("max_latency_ms", 200),
            latency_target=env.get("latency_target", "8.8.8.8"),
        )
        net_results = net.run_all(hw)
        failed = []
        for name, r in net_results.items():
            status = r.get("status", "PASS")
            log(f"[{status}] Network/{name}: {r.get('detail', '')}")
            if status == "FAIL":
                failed.append(name)
        return len(failed) == 0

    # ---- all tag ----
    if tag == "all":
        summary = hw.get_full_health_summary()
        for label, info in summary.items():
            if isinstance(info, dict):
                for k, v in info.items():
                    log(f"[PASS] {label}/{k}:\n{v}")
            else:
                log(f"[PASS] {label}:\n{info}")
        return True

    # ---- system tag (alias for os+cpu+memory+bios+firmware) ----
    if tag == "system":
        for subtag in ["os", "cpu", "memory", "bios", "firmware"]:
            checks = collect_tags.get(subtag, [])
            for label, method in checks:
                collect(f"{subtag}/{label}", method)
        return True

    log(f"[WARN] Unknown tag '{tag}' — no checks defined")
    return True
