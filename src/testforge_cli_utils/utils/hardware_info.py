"""
HardwareInfo — collects system/hardware data from a remote host over SSH.

Covers: CPU (model, cores, freq, ECC), memory (size, speed, ECC status),
BIOS, BMC, disk/NVMe (health, SMART), firmware (BIOS, BMC, NIC, SSD),
PCIe (Gen detection, link width, AER errors), CXL, NIC (speed, errors,
packet loss), OS, thermal, power, NUMA, hugepages, dmesg log scanning.
"""
from __future__ import annotations

import logging
from typing import Dict, Optional

from testforge_cli_utils.utils.ssh_command import SSHCommand

logger = logging.getLogger("testforge.hardware_info")


class HardwareInfo:
    """
    All public methods return a stripped string or a dict.

    If a command is unavailable / requires root, the string will contain
    a clear "[UNAVAILABLE]" annotation rather than crashing the test run.
    """

    def __init__(
        self,
        host: str,
        username: str = "root",
        password: Optional[str] = None,
        key_filename: Optional[str] = None,
        port: int = 22,
    ):
        self.host = host
        self.ssh = SSHCommand(
            host=host,
            username=username,
            password=password,
            key_filename=key_filename,
            port=port,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, cmd: str, timeout: float = 60.0) -> str:
        """Run cmd, return stdout; annotate if unavailable."""
        try:
            out, err = self.ssh.run(cmd, timeout=timeout)
            if not out.strip():
                return err.strip() or "[EMPTY OUTPUT]"
            return out.strip()
        except Exception as exc:
            logger.warning("Command failed on %s: %s — %s", self.host, cmd, exc)
            return f"[UNAVAILABLE: {exc}]"

    # ------------------------------------------------------------------
    # System / OS
    # ------------------------------------------------------------------

    def get_os_info(self) -> str:
        return self._run("cat /etc/os-release")

    def get_kernel_info(self) -> str:
        return self._run("uname -a")

    def get_uptime(self) -> str:
        return self._run("uptime -p")

    # ------------------------------------------------------------------
    # CPU
    # ------------------------------------------------------------------

    def get_cpu_info(self) -> str:
        """Full lscpu output."""
        return self._run("lscpu")

    def get_cpu_topology(self) -> str:
        """Socket / core / thread / NUMA summary."""
        return self._run("lscpu | grep -E 'Socket|Core|Thread|NUMA|CPU\\(s\\)'")

    def get_cpu_model(self) -> str:
        """CPU model name and base frequency."""
        return self._run(
            "grep -m1 'model name' /proc/cpuinfo | cut -d: -f2 | xargs"
        )

    def get_cpu_freq(self) -> str:
        """Current CPU frequencies (all cores)."""
        return self._run(
            "cat /proc/cpuinfo | grep 'cpu MHz' | awk '{print $4}' | "
            "awk 'BEGIN{min=9999;max=0;sum=0;n=0} "
            "{if($1<min)min=$1; if($1>max)max=$1; sum+=$1; n++} "
            "END{printf \"min=%.0fMHz max=%.0fMHz avg=%.0fMHz cores=%d\\n\",min,max,sum/n,n}'"
        )

    def get_cpu_vulnerabilities(self) -> str:
        """Spectre/Meltdown/etc mitigations."""
        return self._run(
            "for f in /sys/devices/system/cpu/vulnerabilities/*; do "
            "  echo \"$(basename $f): $(cat $f)\"; "
            "done 2>/dev/null || echo '[VULN INFO UNAVAILABLE]'"
        )

    # ------------------------------------------------------------------
    # Memory
    # ------------------------------------------------------------------

    def get_memory_info(self) -> str:
        """Human-readable memory summary."""
        return self._run("free -h")

    def get_memory_detail(self) -> str:
        """Full /proc/meminfo."""
        return self._run("cat /proc/meminfo")

    def get_memory_dimm_info(self) -> str:
        """DMI memory device info — slot, size, speed, manufacturer."""
        return self._run("sudo dmidecode -t 17")

    def get_memory_ecc_status(self) -> str:
        """
        ECC capability and current error counters.
        Uses edac-util if available, falls back to dmidecode.
        """
        return self._run(
            "edac-util -s 0 2>/dev/null || "
            "edac-util 2>/dev/null || "
            "{ sudo dmidecode -t 16 2>/dev/null | grep -i 'error correction'; } || "
            "echo '[ECC STATUS UNAVAILABLE — install edac-utils]'"
        )

    def get_memory_ecc_errors(self) -> str:
        """ECC correctable / uncorrectable error counts from kernel EDAC."""
        return self._run(
            "grep -r '' /sys/devices/system/edac/mc/*/ce_count "
            "/sys/devices/system/edac/mc/*/ue_count 2>/dev/null | "
            "awk -F/ '{print $NF}' | sort | uniq -c || "
            "echo '[EDAC COUNTERS UNAVAILABLE]'"
        )

    # ------------------------------------------------------------------
    # BIOS / Firmware
    # ------------------------------------------------------------------

    def get_bios_info(self) -> str:
        return self._run("sudo dmidecode -t bios")

    def get_bios_version(self) -> str:
        return self._run("sudo dmidecode -s bios-version 2>/dev/null")

    def get_bios_date(self) -> str:
        return self._run("sudo dmidecode -s bios-release-date 2>/dev/null")

    def get_firmware_info(self) -> str:
        """Backward-compat alias."""
        return self._run("sudo dmidecode -t 0")

    def get_all_firmware_versions(self) -> Dict[str, str]:
        """
        Collect firmware strings from all available sources.
        Returns dict: label -> version string.
        """
        return {
            "bios_version":  self._run("sudo dmidecode -s bios-version 2>/dev/null"),
            "bios_date":     self._run("sudo dmidecode -s bios-release-date 2>/dev/null"),
            "bmc_firmware":  self._run("ipmitool mc info 2>/dev/null | grep 'Firmware Revision'"),
            "kernel":        self._run("uname -r"),
            "microcode":     self._run("grep microcode /proc/cpuinfo | head -1 | awk '{print $3}'"),
            "nvme_firmware": self._run(
                "which nvme >/dev/null 2>&1 && "
                "for d in /dev/nvme[0-9]; do "
                "  [ -e $d ] && echo -n \"$d: \" && "
                "  sudo nvme id-ctrl $d 2>/dev/null | grep -i '^fr ' | awk '{print $2}'; "
                "done || echo '[NO NVME OR nvme-cli NOT INSTALLED]'"
            ),
            "nic_firmware":  self._run(
                "for iface in $(ls /sys/class/net | grep -Ev '^(lo|virbr|docker|veth)'); do "
                "  fw=$(sudo ethtool -i $iface 2>/dev/null | grep 'firmware-version' | cut -d: -f2 | xargs); "
                "  [ -n \"$fw\" ] && echo \"$iface: $fw\"; "
                "done || echo '[NIC FW UNAVAILABLE]'"
            ),
        }

    def get_firmware_version_compare(self, component: str, expected: str) -> Dict[str, str]:
        """
        Compare actual firmware version of *component* against *expected*.
        Returns dict with actual, expected, and match (PASS/FAIL).
        """
        fw = self.get_all_firmware_versions()
        actual = fw.get(component, "[NOT FOUND]").strip()
        match = "PASS" if actual == expected else "FAIL"
        return {"component": component, "actual": actual, "expected": expected, "result": match}

    # ------------------------------------------------------------------
    # BMC / IPMI
    # ------------------------------------------------------------------

    def get_bmc_info(self) -> str:
        return self._run("ipmitool mc info")

    def get_bmc_sdr(self) -> str:
        """Full Sensor Data Repository."""
        return self._run("ipmitool sdr list full")

    def get_bmc_sdr_temperature(self) -> str:
        return self._run("ipmitool sdr type Temperature")

    def get_bmc_sdr_voltage(self) -> str:
        return self._run("ipmitool sdr type Voltage")

    def get_bmc_sdr_fan(self) -> str:
        return self._run("ipmitool sdr type Fan")

    def get_bmc_sel(self) -> str:
        """System Event Log last 50 entries."""
        return self._run("ipmitool sel list | tail -50")

    def get_bmc_sel_errors(self) -> str:
        """SEL entries filtered to errors/warnings only."""
        return self._run(
            "ipmitool sel list 2>/dev/null | "
            "grep -iE '(critical|error|warning|fail|assert|fault)' | tail -30 || "
            "echo '[NO ERROR EVENTS IN SEL]'"
        )

    def get_bmc_power_status(self) -> str:
        return self._run("ipmitool chassis power status")

    def get_bmc_lan_info(self) -> str:
        return self._run("ipmitool lan print")

    def get_bmc_fru(self) -> str:
        return self._run("ipmitool fru")

    def get_bmc_chassis_status(self) -> str:
        return self._run("ipmitool chassis status")

    # ------------------------------------------------------------------
    # Disk / NVMe
    # ------------------------------------------------------------------

    def get_disk_info(self) -> str:
        """Block device layout."""
        return self._run("lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,MODEL")

    def get_nvme_list(self) -> str:
        """NVMe device list (requires nvme-cli)."""
        return self._run(
            "nvme list 2>/dev/null || echo '[nvme-cli not installed — run: apt install nvme-cli]'"
        )

    def get_nvme_health(self) -> str:
        """
        NVMe SMART / health log for all detected drives.
        Includes: critical_warning, temperature, available_spare,
                  percentage_used, media_errors.
        """
        return self._run(
            "for dev in /dev/nvme[0-9]; do "
            "  [ -e \"$dev\" ] || continue; "
            "  echo \"=== $dev ===\"; "
            "  sudo nvme smart-log $dev 2>/dev/null | "
            "  grep -E '(critical_warning|temperature|available_spare|percentage_used|media_errors|unsafe_shutdowns)'; "
            "done || echo '[NO NVME DEVICES]'"
        )

    def get_nvme_error_log(self) -> str:
        """NVMe error log entries."""
        return self._run(
            "for dev in /dev/nvme[0-9]; do "
            "  [ -e \"$dev\" ] || continue; "
            "  echo \"=== $dev error log ===\"; "
            "  sudo nvme error-log $dev 2>/dev/null | head -40; "
            "done || echo '[NO NVME]'"
        )

    def get_disk_smart(self) -> str:
        """SMART status for SATA/SAS drives (requires smartmontools)."""
        return self._run(
            "for dev in $(lsblk -dno NAME | grep -E '^sd'); do "
            "  echo \"=== /dev/$dev ===\"; "
            "  sudo smartctl -H /dev/$dev 2>/dev/null | grep -E '(SMART overall|result)'; "
            "done || echo '[NO SATA DISKS or smartmontools not installed]'"
        )

    # ------------------------------------------------------------------
    # PCIe
    # ------------------------------------------------------------------

    def get_pcie_devices(self) -> str:
        return self._run("lspci")

    def get_pcie_verbose(self) -> str:
        return self._run("sudo lspci -vvv")

    def get_pcie_link_status(self) -> str:
        """Link speed (Gen) and link width per device."""
        return self._run(
            "sudo lspci -vvv 2>/dev/null | "
            "grep -E '(^[0-9a-fA-F]|LnkCap|LnkSta|MaxPayload|DevCtl)' | "
            "head -200"
        )

    def get_pcie_gen_summary(self) -> str:
        """
        Concise per-device: Bus, Description, LnkCap (Gen+width), LnkSta (actual).
        Useful for quickly spotting devices that negotiated below their capability.
        """
        return self._run(
            "sudo lspci -vvv 2>/dev/null | "
            "awk '"
            "/^[0-9a-fA-F]/{bus=$0} "
            "/LnkCap:/{cap=$0} "
            "/LnkSta:/{print bus\" | Cap:\"cap\" | Sta:\"$0}'"
        )

    def get_pcie_errors(self) -> str:
        """AER correctable / uncorrectable error counts."""
        return self._run(
            "sudo lspci -vvv 2>/dev/null | "
            "grep -E '(Correctable|Uncorrectable|FatalErr|NonFatal)' | head -100"
        )

    def get_pcie_aer_detail(self) -> str:
        """
        AER error detail from sysfs for all PCIe devices.
        Shows correctable + uncorrectable masks and status registers.
        """
        return self._run(
            "for d in /sys/bus/pci/devices/*/aer_dev_correctable; do "
            "  dev=$(dirname $d | xargs basename); "
            "  corr=$(cat $d 2>/dev/null); "
            "  uncorr=$(cat $(dirname $d)/aer_dev_fatal 2>/dev/null); "
            "  nonfatal=$(cat $(dirname $d)/aer_dev_nonfatal 2>/dev/null); "
            "  [ -n \"$corr\" ] && echo \"[$dev] correctable=$corr nonfatal=$nonfatal fatal=$uncorr\"; "
            "done 2>/dev/null || echo '[AER SYSFS NOT AVAILABLE]'"
        )

    def get_pcie_bandwidth(self) -> str:
        """Estimated bandwidth per slot from LnkSta."""
        return self._run(
            "sudo lspci -vvv 2>/dev/null | "
            "awk '/^[0-9a-fA-F]/{dev=$0} /LnkSta:/{print dev\" | \"$0}'"
        )

    # ------------------------------------------------------------------
    # CXL (Compute Express Link)
    # ------------------------------------------------------------------

    def get_cxl_devices(self) -> str:
        return self._run(
            "ls /sys/bus/cxl/devices 2>/dev/null || echo '[NO CXL DEVICES FOUND]'"
        )

    def get_cxl_mem_info(self) -> str:
        """CXL memory device: firmware_version, ram_size, pmem_size."""
        return self._run(
            "for d in /sys/bus/cxl/devices/mem*/; do "
            "  [ -d \"$d\" ] || continue; "
            "  echo \"=== $d ===\"; "
            "  for attr in firmware_version ram_size pmem_size state numa_node; do "
            "    v=$(cat $d/$attr 2>/dev/null); "
            "    [ -n \"$v\" ] && echo \"  $attr: $v\"; "
            "  done; "
            "done || echo '[NO CXL MEM DEVICES]'"
        )

    def get_cxl_port_info(self) -> str:
        return self._run(
            "for d in /sys/bus/cxl/devices/port*/; do "
            "  [ -d \"$d\" ] && echo \"=== $d ===\" && ls $d; "
            "done || echo '[NO CXL PORTS]'"
        )

    def get_cxl_topology(self) -> str:
        return self._run(
            "sudo lspci -d ::0502 -vvv 2>/dev/null || "
            "sudo lspci | grep -i 'CXL\\|Compute Express' || "
            "echo '[NO CXL DEVICES VIA LSPCI]'"
        )

    def get_cxl_dmesg_events(self) -> str:
        return self._run("sudo dmesg | grep -i cxl | tail -50 || echo '[NO CXL DMESG]'")

    def get_cxl_error_counters(self) -> str:
        """CXL error counters from sysfs."""
        return self._run(
            "for d in /sys/bus/cxl/devices/*/; do "
            "  for f in $d*error* $d*poison*; do "
            "    [ -f \"$f\" ] && echo \"$(basename $d)/$(basename $f): $(cat $f)\"; "
            "  done; "
            "done 2>/dev/null || echo '[NO CXL ERROR COUNTERS]'"
        )

    def get_cxl_latency_check(self) -> str:
        """
        Probe CXL memory latency using mlc or numactl if available.
        Returns latency in nanoseconds or a NOT AVAILABLE message.
        """
        return self._run(
            "which mlc >/dev/null 2>&1 && sudo mlc --latency_matrix 2>/dev/null || "
            "numactl --hardware 2>/dev/null | grep -i 'node.*distance' || "
            "echo '[LATENCY CHECK: install Intel MLC for accurate CXL latency]'"
        )

    # ------------------------------------------------------------------
    # Thermal & Power
    # ------------------------------------------------------------------

    def get_thermal_info(self) -> str:
        """All thermal zones with type and temperature in °C."""
        return self._run(
            "for z in /sys/class/thermal/thermal_zone*; do "
            "  type=$(cat $z/type 2>/dev/null); "
            "  temp=$(cat $z/temp 2>/dev/null); "
            "  echo \"$type: $((temp/1000))°C\"; "
            "done"
        )

    def get_fan_info(self) -> str:
        """Fan speeds via IPMI SDR or lm-sensors."""
        return self._run(
            "ipmitool sdr type Fan 2>/dev/null || "
            "sensors 2>/dev/null | grep -i fan || "
            "echo '[FAN INFO UNAVAILABLE]'"
        )

    def get_power_info(self) -> str:
        """System power consumption via IPMI DCMI."""
        return self._run(
            "ipmitool dcmi power reading 2>/dev/null || "
            "ipmitool sdr type 'Current' 2>/dev/null || "
            "echo '[POWER READING UNAVAILABLE]'"
        )

    def get_voltage_info(self) -> str:
        """Voltage sensor readings."""
        return self._run(
            "ipmitool sdr type Voltage 2>/dev/null || "
            "sensors 2>/dev/null | grep -i 'V\\b' || "
            "echo '[VOLTAGE INFO UNAVAILABLE]'"
        )

    # ------------------------------------------------------------------
    # Network / NIC
    # ------------------------------------------------------------------

    def get_nic_info(self) -> str:
        return self._run("ip -s link show")

    def get_nic_speed(self) -> str:
        """Speed and duplex for all non-loopback interfaces."""
        return self._run(
            "for iface in $(ls /sys/class/net | grep -Ev '^(lo|virbr|docker|veth)'); do "
            "  speed=$(cat /sys/class/net/$iface/speed 2>/dev/null || echo '?'); "
            "  duplex=$(cat /sys/class/net/$iface/duplex 2>/dev/null || echo '?'); "
            "  state=$(cat /sys/class/net/$iface/operstate 2>/dev/null || echo '?'); "
            "  echo \"$iface: ${speed}Mbps $duplex state=$state\"; "
            "done"
        )

    def get_network_errors(self) -> str:
        """Interface error/drop/missed counters."""
        return self._run(
            "ip -s link | awk '/^[0-9]+:/{iface=$2} "
            "/RX:/{getline; rx=$0} "
            "/TX:/{getline; tx=$0; "
            "print iface, \"RX:\", rx, \"TX:\", tx}'"
        )

    def get_network_latency(self, target: str = "8.8.8.8", count: int = 10) -> str:
        """
        Measure round-trip latency to *target* using ping.
        Returns min/avg/max/mdev string.
        """
        return self._run(
            f"ping -c {count} -q {target} 2>/dev/null | tail -2 || "
            f"echo '[PING TO {target} FAILED]'"
        )

    def get_network_packet_loss(self, target: str = "8.8.8.8", count: int = 20) -> str:
        """Packet loss percentage to *target*."""
        return self._run(
            f"ping -c {count} -q {target} 2>/dev/null | "
            "grep -oE '[0-9]+% packet loss' || "
            f"echo '[PACKET LOSS CHECK TO {target} FAILED]'"
        )

    def get_ethtool_stats(self) -> str:
        """ethtool driver info + stats for physical interfaces."""
        return self._run(
            "for iface in $(ls /sys/class/net | grep -Ev '^(lo|virbr|docker|veth)'); do "
            "  echo \"=== $iface ===\"; "
            "  sudo ethtool $iface 2>/dev/null | grep -E '(Speed|Duplex|Link|Port|Auto)'; "
            "done"
        )

    # ------------------------------------------------------------------
    # NUMA / Memory topology
    # ------------------------------------------------------------------

    def get_numa_topology(self) -> str:
        return self._run(
            "numactl --hardware 2>/dev/null || "
            "cat /sys/devices/system/node/node*/cpumap 2>/dev/null || "
            "echo '[NUMA INFO UNAVAILABLE]'"
        )

    def get_hugepages(self) -> str:
        return self._run(
            "grep -i huge /proc/meminfo && "
            "for hp in /sys/kernel/mm/hugepages/hugepages-*/; do "
            "  sz=$(basename $hp); "
            "  total=$(cat $hp/nr_hugepages 2>/dev/null); "
            "  free=$(cat $hp/free_hugepages 2>/dev/null); "
            "  echo \"  $sz: total=$total free=$free\"; "
            "done"
        )

    # ------------------------------------------------------------------
    # Log / dmesg validation
    # ------------------------------------------------------------------

    def get_dmesg_errors(self) -> str:
        """dmesg lines at error/warning level."""
        return self._run(
            "sudo dmesg --level=err,crit,alert,emerg 2>/dev/null | tail -100 || "
            "sudo dmesg 2>/dev/null | grep -iE '(error|fail|critical|panic|oops|bug:)' | tail -100 || "
            "echo '[DMESG ERRORS UNAVAILABLE]'"
        )

    def get_dmesg_warnings(self) -> str:
        """dmesg warning-level messages."""
        return self._run(
            "sudo dmesg --level=warn 2>/dev/null | tail -50 || "
            "echo '[DMESG WARNINGS UNAVAILABLE]'"
        )

    def get_dmesg_hardware_events(self) -> str:
        """dmesg lines mentioning hardware components."""
        return self._run(
            "sudo dmesg 2>/dev/null | "
            "grep -iE '(cxl|pcie|nvme|mce|edac|aer|ecc|corrected|uncorrected)' | "
            "tail -100 || echo '[NO HW EVENTS IN DMESG]'"
        )

    def get_mce_errors(self) -> str:
        """Machine Check Exceptions from mcelog or rasdaemon."""
        return self._run(
            "sudo mcelog --client 2>/dev/null || "
            "sudo journalctl -u rasdaemon --no-pager -n 50 2>/dev/null || "
            "sudo dmesg | grep -i 'machine check\\|mce' | tail -30 || "
            "echo '[MCE CHECK UNAVAILABLE — install mcelog or rasdaemon]'"
        )

    def get_crash_signatures(self) -> str:
        """Kernel panic / oops / crash signatures in dmesg and logs."""
        return self._run(
            "sudo dmesg 2>/dev/null | grep -iE '(kernel panic|oops|bug:|rip:|call trace|segfault)' | "
            "tail -50 || "
            "sudo journalctl -k -p err -n 50 --no-pager 2>/dev/null || "
            "echo '[NO CRASH SIGNATURES FOUND]'"
        )

    def get_system_logs(self) -> str:
        """Recent syslog / journal errors."""
        return self._run(
            "sudo journalctl -p err -n 100 --no-pager 2>/dev/null || "
            "sudo tail -100 /var/log/syslog 2>/dev/null || "
            "sudo tail -100 /var/log/messages 2>/dev/null || "
            "echo '[SYSTEM LOG UNAVAILABLE]'"
        )

    def get_bmc_sel_errors(self) -> str:
        """BMC SEL filtered to error/warning events only."""
        return self._run(
            "ipmitool sel list 2>/dev/null | "
            "grep -iE '(critical|error|warning|fail|assert|fault)' | tail -30 || "
            "echo '[NO ERROR EVENTS IN SEL]'"
        )

    # ------------------------------------------------------------------
    # Stress & reliability
    # ------------------------------------------------------------------

    def run_cpu_stress(self, duration_sec: int = 30, workers: int = 0) -> str:
        """
        Run CPU stress via stress-ng.
        *workers* = 0 means use all logical CPUs.
        Returns stress-ng exit status and metrics.
        """
        w = workers if workers > 0 else "$(nproc)"
        return self._run(
            f"which stress-ng >/dev/null 2>&1 || "
            f"{{ echo '[stress-ng not installed — run: apt install stress-ng]'; exit 0; }}; "
            f"sudo stress-ng --cpu {w} --timeout {duration_sec}s "
            f"--metrics-brief --yaml /tmp/stress_cpu.yaml 2>&1 && "
            f"cat /tmp/stress_cpu.yaml 2>/dev/null",
            timeout=duration_sec + 30,
        )

    def run_memory_stress(self, duration_sec: int = 30, workers: int = 1, vm_bytes: str = "1G") -> str:
        """
        Run memory stress via stress-ng vm stressor.
        *vm_bytes*: memory per worker (e.g. '1G', '512M').
        """
        return self._run(
            f"which stress-ng >/dev/null 2>&1 || "
            f"{{ echo '[stress-ng not installed — run: apt install stress-ng]'; exit 0; }}; "
            f"sudo stress-ng --vm {workers} --vm-bytes {vm_bytes} "
            f"--timeout {duration_sec}s --metrics-brief 2>&1",
            timeout=duration_sec + 30,
        )

    def run_io_stress(self, duration_sec: int = 30) -> str:
        """
        Run disk I/O stress via fio (sequential read/write).
        Falls back to stress-ng iomix if fio is not installed.
        """
        return self._run(
            f"if which fio >/dev/null 2>&1; then "
            f"  sudo fio --name=testforge_io --rw=randrw --bs=4k --iodepth=16 "
            f"  --numjobs=4 --runtime={duration_sec} --time_based "
            f"  --filename=/tmp/testforge_fio.tmp --size=512M "
            f"  --output-format=terse 2>&1 | tail -5; "
            f"  rm -f /tmp/testforge_fio.tmp; "
            f"elif which stress-ng >/dev/null 2>&1; then "
            f"  sudo stress-ng --iomix 2 --timeout {duration_sec}s --metrics-brief 2>&1; "
            f"else "
            f"  echo '[IO STRESS: install fio (apt install fio) or stress-ng]'; "
            f"fi",
            timeout=duration_sec + 60,
        )

    def run_memory_bandwidth_test(self) -> str:
        """
        Memory bandwidth test using stream or stress-ng stream stressor.
        Reports GB/s for copy/scale/add/triad.
        """
        return self._run(
            "if which stream >/dev/null 2>&1; then "
            "  stream 2>&1 | grep -E '(Copy|Scale|Add|Triad)'; "
            "elif which stress-ng >/dev/null 2>&1; then "
            "  sudo stress-ng --stream 1 --timeout 10s --metrics-brief 2>&1; "
            "else "
            "  echo '[BANDWIDTH TEST: install stream or stress-ng]'; "
            "fi"
        )

    # ------------------------------------------------------------------
    # Full health summary
    # ------------------------------------------------------------------

    def get_full_health_summary(self) -> Dict[str, str]:
        """All checks in one pass — used by the 'all' tag."""
        return {
            "os":                self.get_os_info(),
            "kernel":            self.get_kernel_info(),
            "uptime":            self.get_uptime(),
            "cpu":               self.get_cpu_info(),
            "cpu_topology":      self.get_cpu_topology(),
            "cpu_freq":          self.get_cpu_freq(),
            "memory":            self.get_memory_info(),
            "memory_ecc":        self.get_memory_ecc_status(),
            "memory_dimm":       self.get_memory_dimm_info(),
            "bios":              self.get_bios_info(),
            "firmware":          self.get_all_firmware_versions(),
            "bmc":               self.get_bmc_info(),
            "bmc_power":         self.get_bmc_power_status(),
            "bmc_sel_errors":    self.get_bmc_sel_errors(),
            "disk":              self.get_disk_info(),
            "nvme_list":         self.get_nvme_list(),
            "nvme_health":       self.get_nvme_health(),
            "pcie_devices":      self.get_pcie_devices(),
            "pcie_gen_summary":  self.get_pcie_gen_summary(),
            "pcie_errors":       self.get_pcie_errors(),
            "pcie_aer":          self.get_pcie_aer_detail(),
            "cxl_devices":       self.get_cxl_devices(),
            "cxl_mem":           self.get_cxl_mem_info(),
            "cxl_errors":        self.get_cxl_error_counters(),
            "nic":               self.get_nic_info(),
            "nic_speed":         self.get_nic_speed(),
            "nic_errors":        self.get_network_errors(),
            "thermal":           self.get_thermal_info(),
            "voltage":           self.get_voltage_info(),
            "power":             self.get_power_info(),
            "numa":              self.get_numa_topology(),
            "hugepages":         self.get_hugepages(),
            "dmesg_errors":      self.get_dmesg_errors(),
            "mce_errors":        self.get_mce_errors(),
            "crash_signatures":  self.get_crash_signatures(),
        }

    def close(self):
        self.ssh.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
