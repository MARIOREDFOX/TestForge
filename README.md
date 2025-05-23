# TestForge

**TestForge** is a modular, CLI-based hardware/system-level test automation framework for validating technologies like CXL, PCIe, BMC, and firmware.

## Features

- Modular protocol support (CXL, IPMI/Redfish, PCIe)
- YAML-based configuration
- Rich CLI interface
- Scalable and pip-installable

## Installation
```bash
git clone https://github.com/MARIOREDFOX/TestForge.git
cd testforge
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
testforge version
```

## Setup Testing Linux Machine
```text
✅ 1. Find the Local IP of the Target Linux Machine
On that machine, run:
ip a | grep inet
You’ll see something like: 192.168.1.101

✅ 2. Ensure SSH is Running
Run on the target:
sudo systemctl status sshd
sudo apt update
sudo apt install openssh-server -y
sudo systemctl enable ssh
sudo systemctl start ssh
If it’s not active:
sudo systemctl start sshd
sudo systemctl status ssh

✅ 3. Set Up SSH Passwordless Login (From your TestForge Machine)
On the machine where you're running testforge, do:
ssh-keygen -t rsa -b 4096 -C "testforge@localhost"
ssh-copy-id marieinfa@192.168.1.101
After this, test it:
ssh marieinfa@192.168.1.101
It should login without prompting for a password

✅ 4. On your TestForge Host: Generate SSH Key run below
ssh-keygen
ssh-copy-id <username>@<target-ip>
Test the Connection
ssh <username>@<target-ip>


Note:
Check Linux Target's Firewall / SSH Access
run:
sudo ufw status
sudo ufw allow ssh
sudo systemctl status ssh
sudo systemctl status ssh
sudo systemctl start ssh

```

## 📁 Project Structure

```text
testforge/
├── src/
│   └── testforge/
│       ├── cli.py
│       ├── core/
│       │   ├── executor.py
│       │   ├── loader.py
│       │   ├── reporter.py
│       │   └── logger.py
│       ├── protocols/
│       │   ├── __init__.py
│       │   ├── bmc/
│       │   │   ├── redfish.py
│       │   │   └── ipmi.py
│       │   ├── cxl.py
│       │   └── pcie.py
│       ├── tests/
│       │   ├── __init__.py
│       │   ├── firmware/
│       │   ├── stress/
│       │   ├── health/
│       │   └── regression/
│       ├── config/
│       │   └── config_loader.py
│       ├── utils/
│       │   ├── ssh.py
│       │   ├── retry.py
│       │   └── parser.py
├── tests/
│   └── test_executor.py
├── examples/
│   ├── env.yaml
│   └── test_config.yaml
├── docs/
│   └── architecture.md
├── LICENSE
├── README.md
├── setup.py
├── setup.cfg
└── pyproject.toml
```
## Usage

```bash
pip install testforge-cli-utils
testforge version
testforge run --env examples/env.yaml
testforge run --tag all --env examples/env.yaml --config-file examples/test_config.yaml

python3 -m unittest discover tests

Running it in local create these two files test_config.yaml & env.yaml:
(.venv) marieinfa@marieinfa-mba TestForge % testforge run --tag all --env env.yaml --config-file test_config.yaml
Running test: check_all_health with env: {'hostname': '192.168.1.6', 'username': 'mark'}
[2025-04-20 13:31:22] === Running Test: check_all_health on 192.168.1.6 ===
[2025-04-20 13:31:34] [FAIL] 192.168.1.6 is not reachable.
Test check_all_health failed


(.venv) marieinfa@marieinfa-mba TestForge % cat examples/env.yaml
hostname: <ipaddress>
username: <username>

(.venv) marieinfa@marieinfa-mba TestForge % cat examples/test_config.yaml
tests:
  - name: check_ping
    enabled: true
    tags: [ping]

  - name: check_all_health
    enabled: true
    tags: [all]
```
## License
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

## PYPI
[![PyPI version](https://badge.fury.io/py/testforge-cli-utils.svg)](https://badge.fury.io/py/testforge-cli-utils)

