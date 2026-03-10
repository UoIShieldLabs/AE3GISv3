# AE3GIS Deployment Guide

**Audience:** System administrators and instructors setting up the AE3GIS server.

---

## 1. Prerequisites

| Requirement | Minimum Version | Notes |
|-------------|-----------------|-------|
| Linux host | Any modern distro | Ubuntu 22.04+ or RHEL 9+ recommended |
| Docker Engine | 24.0+ | [Install guide](https://docs.docker.com/engine/install/) |
| Docker Compose | v2 (plugin) | `docker compose` (not `docker-compose`) |
| ContainerLab | 0.54+ | [Install guide](https://containerlab.dev/install/) |
| Open ports | 3000, 8000 | Frontend (:3000), backend API (:8000) |
| Disk space | 10 GB+ | For Docker images and topology data |

ContainerLab must be installed on the **host** (not just inside Docker). The backend container runs privileged with `network_mode: host` and calls `sudo containerlab` on the host daemon.

---

## 2. Installation

```bash
git clone https://github.com/your-org/AE3GISv2.git
cd AE3GISv2
cp .env.example .env   # if provided, or create .env manually
```

---

## 3. Environment Variables

Create a `.env` file in the project root before starting the stack. The backend reads these at startup.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AE3GIS_INSTRUCTOR_TOKEN` | **Yes** | `test` | Bearer token for instructor login. **Change this before production.** |
| `AE3GIS_DB_PATH` | No | `/app/data/ae3gis.db` | SQLite database path inside the backend container |
| `AE3GIS_CLAB_WORKDIR` | No | `/app/clab-workdir` | Directory where ContainerLab YAML files and persistent data are written |
| `AE3GIS_HOST_SCRIPTS_DIR` | No | `${PWD}/backend/scripts` | **Host** absolute path to the scripts directory. Must match the in-container bind mount path exactly — ContainerLab resolves bind mounts against the host daemon. |

Example `.env`:

```ini
AE3GIS_INSTRUCTOR_TOKEN=change-me-before-production
AE3GIS_HOST_SCRIPTS_DIR=/home/deploy/AE3GISv2/backend/scripts
```

> **Security note:** `AE3GIS_INSTRUCTOR_TOKEN` is the only credential protecting the instructor interface. Use a long random string (e.g. `openssl rand -hex 32`).

---

## 4. Start the Stack

```bash
docker compose up --build -d
```

This starts two services:

| Service | Port | Description |
|---------|------|-------------|
| `frontend` | 3000 | Nginx-served React SPA |
| `backend` | 8000 | FastAPI application |

The backend service runs with:
- `network_mode: host` — required so ContainerLab can manage host network namespaces
- `pid: host` — required for network namespace access via `/proc`
- `privileged: true` — required for Docker socket access and ContainerLab operations
- `restart: unless-stopped` — auto-restarts after host reboot

Check logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

---

## 5. Sudoers Configuration

The backend calls `sudo containerlab` to deploy and destroy topologies. The user running the backend container process must be allowed to do this without a password prompt.

### Why this is needed

ContainerLab requires root to create network namespaces, virtual interfaces, and manage Docker networks. The backend runs as a non-root user inside the container, escalating via `sudo`.

### Configuration steps

1. Find the user running the backend process (typically `root` inside the container since it's privileged, but check your setup):

   ```bash
   docker compose exec backend whoami
   ```

2. Find the ContainerLab binary path on the **host**:

   ```bash
   which containerlab
   # e.g. /usr/bin/containerlab
   ```

3. Edit sudoers safely:

   ```bash
   sudo visudo -f /etc/sudoers.d/ae3gis
   ```

4. Add one of the following stanzas:

   **Restrictive (recommended for production):**
   ```
   # Allow ae3gis backend to run containerlab without password
   root ALL=(ALL) NOPASSWD: /usr/bin/containerlab deploy *, /usr/bin/containerlab destroy *, /usr/bin/containerlab inspect *
   ```

   **Permissive (acceptable for isolated lab environments):**
   ```
   root ALL=(ALL) NOPASSWD: /usr/bin/containerlab
   ```

5. Verify it works from inside the container:

   ```bash
   docker compose exec backend sudo containerlab version
   ```

   You should see ContainerLab version output with no password prompt.

> **Note:** If the backend container runs as `root` (default for privileged containers), the sudoers entry should use `root` as the user. Adjust to match `whoami` output above.

---

## 6. Persistent Data

Two named Docker volumes store data that survives container restarts and rebuilds:

| Volume | Mount point | Contents |
|--------|-------------|----------|
| `ae3gis-db` | `/app/data` | SQLite database (`ae3gis.db`) — all topologies, classroom sessions, student slots |
| `ae3gis-clab` | `/app/clab-workdir` | ContainerLab YAML files, persistent container bind mounts |

### Backup

```bash
# Back up the database
docker run --rm -v ae3gis-db:/data -v $(pwd):/backup alpine \
  tar czf /backup/ae3gis-db-$(date +%Y%m%d).tar.gz -C /data .
```

### Reset (destructive)

> **Warning:** This permanently deletes all saved topologies, classroom sessions, and student data.

```bash
# Stop the stack first
docker compose down

# Remove volumes
docker volume rm ae3gis-db ae3gis-clab

# Restart — volumes are recreated empty
docker compose up -d
```

---

## 7. Verifying the Deployment

Perform this smoke test after initial setup:

1. **Open the UI:** Navigate to `http://<server-ip>:3000`
2. **Log in:** Select the Instructor tab, enter your `AE3GIS_INSTRUCTOR_TOKEN`, click Log In
3. **Create a topology:** Click New, give it a name, right-click the canvas to add a site
4. **Save:** Click Save — the dirty indicator (pencil icon) should disappear
5. **Deploy:** Click Deploy — the status pill should transition to `deploying` then `deployed`
6. **Check status dots:** Container nodes should turn green within a few seconds
7. **Open a terminal:** Click a running container node — a terminal tab should open at the bottom of the screen
8. **Destroy:** Click Destroy — containers should turn red

If any step fails, check the [Troubleshooting](#9-troubleshooting) section.

---

## 8. CI/CD

The repository includes `.github/workflows/deploy.yml` which automates deployment on push to `main`.

The workflow:
1. SSHs into the production server using a stored secret
2. Pulls the latest code (`git pull`)
3. Runs `docker compose up --build -d`

Required GitHub secrets:
- `DEPLOY_HOST` — server hostname or IP
- `DEPLOY_USER` — SSH username
- `DEPLOY_KEY` — SSH private key

No environment variables are managed by CI — `.env` must be present on the server before the first deploy.

---

## 9. Troubleshooting

### Docker socket permission denied

**Symptom:** Backend logs show `Permission denied: '/var/run/docker.sock'`

**Fix:** Ensure the backend service has `privileged: true` and the socket is mounted:
```yaml
volumes:
  - /var/run/docker.sock:/var/run/docker.sock
```

### "Failed to lookup link" error on deploy

**Symptom:** Deploy fails with `Failed to lookup link` in ContainerLab output.

**Cause:** Stale Docker bridge metadata from a previous failed deployment.

**Fix:** This is automatically self-healed by the backend (`clab_manager.py`). If it persists, manually remove stale bridges:
```bash
docker network prune
```

### Sudoers not working inside container

**Symptom:** `sudo: a password is required` in backend logs during deploy.

**Fix:** Confirm the sudoers entry matches the actual user:
```bash
docker compose exec backend id
# e.g. uid=0(root) ...
```
Then ensure your sudoers entry uses `root ALL=(ALL) NOPASSWD: ...`.

### Port conflicts

**Symptom:** `docker compose up` fails with `bind: address already in use` on port 3000 or 8000.

**Fix:** Stop conflicting services, or change the host port mapping in `docker-compose.yml`:
```yaml
ports:
  - "3001:80"   # frontend on 3001 instead
```

### Management subnet overlap

**Symptom:** Deploy fails with `address already in use` for Docker networks.

**Fix:** The backend automatically retries with different subnets (up to 4 attempts using deterministic `/24` subnets from `100.64.0.0/10`). If all attempts fail, check for conflicting Docker networks:
```bash
docker network ls
docker network rm <conflicting-network>
```

### Database locked

**Symptom:** API returns 500 errors with `database is locked`.

**Fix:** Only one backend instance should run at a time. Check for stale processes:
```bash
docker compose ps
docker compose restart backend
```
