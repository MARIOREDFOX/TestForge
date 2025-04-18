import paramiko

def ssh_connect(host, username, password):
    """Connect to a remote host via SSH."""
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username=username, password=password)
    return ssh

def run_ssh_command(ssh, command):
    """Run a command on the remote server."""
    stdin, stdout, stderr = ssh.exec_command(command)
    return stdout.read().decode(), stderr.read().decode()

