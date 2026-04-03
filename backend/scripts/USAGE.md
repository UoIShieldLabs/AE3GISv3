# Using Container Scripts

## Overview

The `/backend/scripts` directory provides a centralized location for scripts that containers can access as **read-only**. Scripts are automatically mounted into each container based on its type during deployment.

## Directory Structure

```
backend/scripts/
├── workstation/          # Scripts for workstation containers
├── server/               # Scripts for web-server and file-server containers
├── plc/                  # Scripts for PLC containers
├── router/               # Scripts for router containers
├── firewall/             # Scripts for firewall containers
└── switch/               # Scripts for switch containers
```

## How It Works

1. **Automatic Mounting**: When you deploy a topology, each container automatically gets a read-only mount to its type-specific script directory
2. **Container Path**: Inside a container, scripts are accessible at `/scripts/{type}/`
3. **Read-Only**: Containers cannot write to, modify, or delete scripts
4. **Type Mapping**: 
   - `workstation` → `/scripts/workstation/`
   - `web-server`, `file-server` → `/scripts/server/`
   - `plc` → `/scripts/plc/`
   - `router` → `/scripts/router/`
   - `firewall` → `/scripts/firewall/`
   - `switch` → `/scripts/switch/`

## Example Usage

### In a Workstation Container

```bash
# List available scripts
ls -la /scripts/workstation/

# Execute a script
bash /scripts/workstation/init.sh

# Run a Python script
python /scripts/workstation/setup.py
```

### In a Server Container

```bash
# Run a server initialization script
bash /scripts/server/init.sh

# Verify script is read-only
touch /scripts/server/test.txt  # This will fail - permission denied
```

### In a PLC Container

```bash
# Start the PLC daemon
bash /scripts/plc/plc_daemon.sh

# Run the PLC manipulation phase script
bash /scripts/plc/phase5_plc_manipulate.sh
```

### In a Router Container

```bash
# Execute router setup script
bash /scripts/router/init.sh

# Run routing configuration
python /scripts/router/routes.py
```

## Adding New Scripts

1. **Create your script** in the appropriate directory:
   ```bash
   echo '#!/bin/bash' > backend/scripts/workstation/my-script.sh
   echo 'echo "Hello from workstation"' >> backend/scripts/workstation/my-script.sh
   ```

2. **Make it executable** on the host:
   ```bash
   chmod 755 backend/scripts/workstation/my-script.sh
   ```

3. **Deploy your topology** - the new script will automatically be available in containers

## Permissions

All script directories are configured with:
- **755** permissions on directories (readable and executable)
- **755** permissions on scripts (readable and executable)
- **Mounted as read-only** in containers (`:ro` flag)

This ensures:
- Scripts are accessible to all containers
- Containers cannot modify the scripts
- Users inside containers have predictable, safe access

## Adding More Container Types

To add scripts for a new container type:

1. Create a new directory: `backend/scripts/my-type/`
2. Update the `_SCRIPT_TYPE_MAP` in `backend/services/clab_generator.py`:
   ```python
   _SCRIPT_TYPE_MAP = {
       # ... existing mappings ...
       "my-type": "my-type",  # Add this line
   }
   ```
3. Add your scripts to `backend/scripts/my-type/`
4. Make them executable: `chmod 755 backend/scripts/my-type/*.sh backend/scripts/my-type/*.py`

## Debugging

If scripts don't appear in a container:

1. **Check the logs** during deployment for script mounting status
2. **Verify permissions** on the host:
   ```bash
   ls -la backend/scripts/
   ls -la backend/scripts/workstation/
   ```
3. **Confirm container type** matches the mapping in `_SCRIPT_TYPE_MAP`
4. **Check read-only flag**: Scripts should be mounted with `:ro` suffix in the YAML

## Integration with Persistence

Scripts are separate from persistent storage:
- **Scripts** (`/scripts/*`): Read-only, centralized, reusable
- **Persistent storage** (`/data/*` or custom paths): Read-write, per-container, topology-specific

Both can be used together - scripts can initialize persistent data directories.
