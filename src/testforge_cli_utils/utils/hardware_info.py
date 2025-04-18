import subprocess

from testforge_cli_utils.utils.ssh_command import SSHCommand


class HardwareInfo:
    def __init__(self, host):
        self.ssh = SSHCommand(host)

    def run_cmd(self, cmd):
        stdout, _ = self.ssh.run(cmd)
        return stdout.strip()

    def get_cpu_info(self):
        return self.run_cmd("lscpu")

    def get_memory_info(self):
        return self.run_cmd("free -h")

    def get_bios_info(self):
        return self.run_cmd("sudo dmidecode -t bios")

    def get_bmc_info(self):
        return self.run_cmd("ipmitool mc info")

    def get_disk_info(self):
        return self.run_cmd("lsblk")

    def get_firmware_info(self):
        return self.run_cmd("sudo dmidecode -t 0")
