# Container Scripts Directory

This directory contains scripts that containers can read and execute. Scripts are mounted as **read-only** volumes into containers.

## Structure

- `workstation/` - Scripts for workstation containers
- `server/` - Scripts for web-server and file-server containers
- `plc/` - Scripts for PLC containers
- `router/` - Scripts for router containers
- `firewall/` - Scripts for firewall containers
- `switch/` - Scripts for switch containers

## Usage

Scripts in these directories are automatically mounted into containers at `/scripts/{type}/` based on the container type. For example:

- A `workstation` container will have `/scripts/workstation/` mounted and readable
- A `plc` container will have `/scripts/plc/` mounted and readable
- A `router` container will have `/scripts/router/` mounted and readable

Containers can execute these scripts:
```bash
/scripts/workstation/init.sh
python /scripts/server/setup.py
/scripts/plc/plc_daemon.sh
```

## Permissions

All script directories are **read-only** for containers. Containers cannot modify, delete, or write to these directories.

## Adding New Scripts

1. Create your script in the appropriate subdirectory
2. Make sure it has execute permissions on the host: `chmod 755 script.sh`
3. Containers will automatically have access to it
