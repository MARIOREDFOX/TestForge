# TestForge Architecture

## Overview

TestForge is a CLI-driven hardware/system-level test automation framework
designed for validating CXL, PCIe, BMC, firmware, and general platform health.

```
testforge run --tag pcie --env examples/env.yaml
testforge probe 192.168.1.10 --check cxl
```

---

## Directory Layout

```
src/testforge_cli_utils/
├── cli.py                     # Click entry point — run, probe, version
├── __init__.py
│
├── core/
│   ├── base_executor.py       # Abstract Executor base class
│   ├── executor.py            # Tag-based test dispatch & reporting
│   ├── loader.py              # Protocol module loader
│   ├── logger.py              # Centralised logging (rich + file)
│   └── reporter.py            # JSON report + console table
│
├── protocols/
│   ├── pcie.py                # PCIe link / error helpers
│   ├── cxl.py                 # CXL device enumeration helpers
│   └── bmc/
│       ├── ipmi.py            # IPMI/ipmitool helpers
│       └── redfish.py         # Redfish REST client
│
├── runner/
│   └── cxl_health_check_runner.py   # Multi-host CXL health runner
│
├── tests/
│   └── health/
│       └── health.py          # HealthTests — ping + SSH + CXL/PCIe checks
│
├── config/
│   └── config_loader.py       # YAML loader with validation
│
└── utils/
    ├── hardware_info.py        # All SSH-based hardware queries
    ├── host_check.py           # Ping / port reachability
    ├── ssh_command.py          # Lazy paramiko wrapper (fixes import error)
    ├── ssh.py                  # Legacy shim (backward compat)
    ├── retry.py                # Exponential back-off retry
    └── parser.py               # YAML helpers
```

---

## Supported Test Tags

| Tag        | What it collects                                           |
|------------|------------------------------------------------------------|
| `ping`     | ICMP reachability only                                     |
| `os`       | OS release, kernel version, uptime                         |
| `cpu`      | lscpu, socket/core/thread topology                         |
| `memory`   | free -h, DMI DIMM info                                     |
| `bios`     | dmidecode BIOS/UEFI details                               |
| `firmware` | BIOS version/date, BMC FW, kernel, microcode, NVMe FW     |
| `bmc`      | ipmitool mc info, SDR, SEL, power status, FRU, LAN        |
| `disk`     | lsblk with model/FSTYPE                                   |
| `pcie`     | lspci, link speed/width, AER errors, bandwidth            |
| `cxl`      | /sys/bus/cxl, lspci class 0502, dmesg CXL events          |
| `nic`      | ip link, speed/duplex, error counters                      |
| `thermal`  | thermal zones (°C), fan speeds                            |
| `power`    | IPMI DCMI power reading                                    |
| `numa`     | numactl --hardware, node/CPU mapping                       |
| `hugepages`| /proc/meminfo huge + /sys/kernel/mm/hugepages              |
| `all`      | All of the above in one pass                              |

---

## The `paramiko` Import Fix

**Problem:** `ssh_command.py` did `import paramiko` at module level.
The CLI entry point imports `cli.py → executor.py → hardware_info.py → ssh_command.py`,
so the entire CLI crashed on startup if paramiko wasn't installed.

**Fix:** wrap the import in `try/except`. The `_PARAMIKO_AVAILABLE` flag is set
at import time. `SSHCommand.__init__` raises a clear `RuntimeError` with install
instructions if paramiko is missing — only when you actually try to connect,
not on startup.

**paramiko is now an optional extra:**

```bash
pip install testforge-cli-utils          # core only (no SSH)
pip install testforge-cli-utils[ssh]     # core + paramiko
pip install paramiko                     # or install paramiko separately
```

---

## Adding a New Test Tag

1. Add hardware query method(s) to `HardwareInfo` in `utils/hardware_info.py`
2. Add the tag → method mapping in `executor.py:_run_hardware_tag()`
3. Add example entry in `examples/test_config.yaml`
4. Add unit test in `tests/test_executor.py`

## Adding a New Runner

1. Create `runner/my_runner.py` extending `Executor`
2. Register in `executor.py:TEST_RUNNERS` dict
3. Set `test_type: my_runner` in your `env.yaml`
