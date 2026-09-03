#!/usr/bin/env bash
# Single entry point. Kathara runs unprivileged against the Docker daemon, so
# there is no sudoers setup and no host-namespace gymnastics — this works the
# same on Linux and macOS (Apple silicon included).
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if ! docker info >/dev/null 2>&1; then
  echo "Docker does not appear to be running. Start Docker Desktop / the daemon and retry." >&2
  exit 1
fi

echo "Starting AE3GIS (frontend :3000, backend :8000)..."
exec docker compose up --build
