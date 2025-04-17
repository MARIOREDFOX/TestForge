import subprocess

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip()

def get_cpu_info():
    return run_cmd("lscpu")

def get_memory_info():
    return run_cmd("free -h")

def get_bios_info():
    return run_cmd("sudo dmidecode -t bios")

def get_bmc_info():
    return run_cmd("ipmitool mc info")

def get_disk_info():
    return run_cmd("lsblk")

def get_firmware_info():
    return run_cmd("sudo dmidecode -t 0")

