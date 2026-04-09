"""
Unit tests — no real hardware required (all SSH mocked).
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch


# ============================================================
# Retry
# ============================================================
class TestRetry(unittest.TestCase):
    def test_succeeds_first_attempt(self):
        from testforge_cli_utils.utils.retry import retry_test
        self.assertEqual(retry_test(lambda: "ok", retries=3), "ok")

    def test_retries_then_succeeds(self):
        from testforge_cli_utils.utils.retry import retry_test
        calls = {"n": 0}
        def flaky():
            calls["n"] += 1
            if calls["n"] < 3:
                raise RuntimeError("not yet")
            return "done"
        self.assertEqual(retry_test(flaky, retries=3, delay=0), "done")

    def test_raises_after_max(self):
        from testforge_cli_utils.utils.retry import retry_test
        with self.assertRaises(RuntimeError):
            retry_test(lambda: (_ for _ in ()).throw(RuntimeError("boom")), retries=2, delay=0)


# ============================================================
# Host check
# ============================================================
class TestHostCheck(unittest.TestCase):
    @patch("subprocess.run")
    def test_alive(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)
        from testforge_cli_utils.utils.host_check import is_host_alive
        self.assertTrue(is_host_alive("1.2.3.4"))

    @patch("subprocess.run")
    def test_dead(self, mock_run):
        mock_run.return_value = MagicMock(returncode=1)
        from testforge_cli_utils.utils.host_check import is_host_alive
        self.assertFalse(is_host_alive("1.2.3.4"))

    def test_empty_host(self):
        from testforge_cli_utils.utils.host_check import is_host_alive
        self.assertFalse(is_host_alive(""))


# ============================================================
# SSH import fix
# ============================================================
class TestSSHImportFix(unittest.TestCase):
    def test_imports_without_paramiko(self):
        import sys
        real = sys.modules.pop("paramiko", None)
        sys.modules.pop("testforge_cli_utils.utils.ssh_command", None)
        try:
            import testforge_cli_utils.utils.ssh_command as m
            self.assertFalse(m._PARAMIKO_AVAILABLE)
        finally:
            if real:
                sys.modules["paramiko"] = real
            sys.modules.pop("testforge_cli_utils.utils.ssh_command", None)

    def test_raises_clear_error(self):
        import sys
        real = sys.modules.pop("paramiko", None)
        sys.modules.pop("testforge_cli_utils.utils.ssh_command", None)
        try:
            import testforge_cli_utils.utils.ssh_command as m
            m._PARAMIKO_AVAILABLE = False
            with self.assertRaises(RuntimeError) as ctx:
                m.SSHCommand("host")
            self.assertIn("paramiko", str(ctx.exception).lower())
        finally:
            if real:
                sys.modules["paramiko"] = real
            sys.modules.pop("testforge_cli_utils.utils.ssh_command", None)


# ============================================================
# HardwareInfo (mocked SSH)
# ============================================================
def _make_hw(return_value="mocked output"):
    from testforge_cli_utils.utils import hardware_info as hi
    hw = hi.HardwareInfo.__new__(hi.HardwareInfo)
    hw.host = "mock"
    mock_ssh = MagicMock()
    mock_ssh.run.return_value = (return_value, "")
    hw.ssh = mock_ssh
    return hw


class TestHardwareInfo(unittest.TestCase):
    def test_get_cpu_info(self):
        self.assertEqual(_make_hw().get_cpu_info(), "mocked output")

    def test_get_pcie_devices(self):
        self.assertEqual(_make_hw().get_pcie_devices(), "mocked output")

    def test_get_cxl_devices(self):
        self.assertEqual(_make_hw().get_cxl_devices(), "mocked output")

    def test_get_nvme_list(self):
        self.assertEqual(_make_hw().get_nvme_list(), "mocked output")

    def test_get_nvme_health(self):
        self.assertEqual(_make_hw().get_nvme_health(), "mocked output")

    def test_get_memory_ecc_status(self):
        self.assertEqual(_make_hw().get_memory_ecc_status(), "mocked output")

    def test_get_dmesg_errors(self):
        self.assertEqual(_make_hw().get_dmesg_errors(), "mocked output")

    def test_get_crash_signatures(self):
        self.assertEqual(_make_hw().get_crash_signatures(), "mocked output")

    def test_unavailable_on_exception(self):
        from testforge_cli_utils.utils import hardware_info as hi
        hw = hi.HardwareInfo.__new__(hi.HardwareInfo)
        hw.host = "mock"
        mock_ssh = MagicMock()
        mock_ssh.run.side_effect = Exception("refused")
        hw.ssh = mock_ssh
        self.assertIn("[UNAVAILABLE", hw.get_cpu_info())

    def test_firmware_version_compare_pass(self):
        hw = _make_hw()
        hw.get_all_firmware_versions = lambda: {"bios_version": "2.7.0"}
        result = hw.get_firmware_version_compare("bios_version", "2.7.0")
        self.assertEqual(result["result"], "PASS")

    def test_firmware_version_compare_fail(self):
        hw = _make_hw()
        hw.get_all_firmware_versions = lambda: {"bios_version": "2.6.0"}
        result = hw.get_firmware_version_compare("bios_version", "2.7.0")
        self.assertEqual(result["result"], "FAIL")


# ============================================================
# Log validator
# ============================================================
class TestLogValidator(unittest.TestCase):
    def test_no_errors(self):
        from testforge_cli_utils.tests.logs.log_validator import LogValidator, _scan, CRITICAL_PATTERNS
        hits = _scan("Normal boot message\nAll good here", CRITICAL_PATTERNS)
        self.assertEqual(hits, [])

    def test_detects_kernel_panic(self):
        from testforge_cli_utils.tests.logs.log_validator import _scan, CRITICAL_PATTERNS
        hits = _scan("[ 1234.5] Kernel panic - not syncing: VFS", CRITICAL_PATTERNS)
        self.assertTrue(len(hits) > 0)

    def test_detects_mce(self):
        from testforge_cli_utils.tests.logs.log_validator import _scan, CRITICAL_PATTERNS
        hits = _scan("mce: [Hardware Error]: Machine check events logged", CRITICAL_PATTERNS)
        self.assertTrue(len(hits) > 0)

    def test_warns_on_correctable(self):
        from testforge_cli_utils.tests.logs.log_validator import _scan, WARNING_PATTERNS
        hits = _scan("EDAC mc0: 1 correctable error", WARNING_PATTERNS)
        self.assertTrue(len(hits) > 0)


# ============================================================
# Network tests
# ============================================================
class TestNetworkTests(unittest.TestCase):
    def test_packet_loss_pass(self):
        from testforge_cli_utils.tests.network.network_tests import NetworkTests
        nt = NetworkTests(max_packet_loss_pct=5)
        hw = MagicMock()
        hw.get_network_packet_loss.return_value = "2% packet loss"
        passed, detail = nt.test_packet_loss(hw)
        self.assertTrue(passed)

    def test_packet_loss_fail(self):
        from testforge_cli_utils.tests.network.network_tests import NetworkTests
        nt = NetworkTests(max_packet_loss_pct=5)
        hw = MagicMock()
        hw.get_network_packet_loss.return_value = "20% packet loss"
        passed, detail = nt.test_packet_loss(hw)
        self.assertFalse(passed)

    def test_latency_pass(self):
        from testforge_cli_utils.tests.network.network_tests import NetworkTests
        nt = NetworkTests(max_latency_ms=200)
        hw = MagicMock()
        hw.get_network_latency.return_value = "rtt min/avg/max/mdev = 0.5/1.2/3.0/0.1 ms"
        passed, detail = nt.test_latency(hw)
        self.assertTrue(passed)

    def test_latency_fail(self):
        from testforge_cli_utils.tests.network.network_tests import NetworkTests
        nt = NetworkTests(max_latency_ms=50)
        hw = MagicMock()
        hw.get_network_latency.return_value = "rtt min/avg/max/mdev = 80.0/120.5/200.0/5.0 ms"
        passed, detail = nt.test_latency(hw)
        self.assertFalse(passed)


# ============================================================
# Firmware tests
# ============================================================
class TestFirmwareTests(unittest.TestCase):
    def test_compare_pass(self):
        from testforge_cli_utils.tests.firmware.firmware_tests import FirmwareTests
        ft = FirmwareTests(expected={"bios_version": "2.7.0"})
        hw = MagicMock()
        hw.get_all_firmware_versions.return_value = {"bios_version": "2.7.0"}
        results = ft.run_all(hw)
        self.assertEqual(results["bios_version"]["status"], "PASS")

    def test_compare_fail(self):
        from testforge_cli_utils.tests.firmware.firmware_tests import FirmwareTests
        ft = FirmwareTests(expected={"bios_version": "2.8.0"})
        hw = MagicMock()
        hw.get_all_firmware_versions.return_value = {"bios_version": "2.7.0"}
        results = ft.run_all(hw)
        self.assertEqual(results["bios_version"]["status"], "FAIL")

    def test_minimum_version_pass(self):
        from testforge_cli_utils.tests.firmware.firmware_tests import FirmwareTests
        ft = FirmwareTests()
        hw = MagicMock()
        hw.get_all_firmware_versions.return_value = {"bios_version": "3.0.0"}
        results = ft.validate_minimum_versions(hw, {"bios_version": "2.0.0"})
        self.assertEqual(results["bios_version"]["status"], "PASS")

    def test_minimum_version_fail(self):
        from testforge_cli_utils.tests.firmware.firmware_tests import FirmwareTests
        ft = FirmwareTests()
        hw = MagicMock()
        hw.get_all_firmware_versions.return_value = {"bios_version": "1.5.0"}
        results = ft.validate_minimum_versions(hw, {"bios_version": "2.0.0"})
        self.assertEqual(results["bios_version"]["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
