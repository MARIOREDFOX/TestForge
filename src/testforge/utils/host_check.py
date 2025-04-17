import subprocess

def is_host_alive(host):
    try:
        result = subprocess.run(['ping', '-c', '2', host], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception as e:
        return False

