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

# Captures and traffic runs record which code produced them. The backend
# container sees only ./backend (no .git), so pass the commit in. Set
# AE3GIS_HOST_LABEL to name this machine in run results (e.g. "mac-studio").
if git rev-parse HEAD >/dev/null 2>&1; then
  export AE3GIS_GIT_COMMIT="${AE3GIS_GIT_COMMIT:-$(git rev-parse HEAD)}"
  if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
    export AE3GIS_GIT_DIRTY=true
  fi
fi

if [ -z "${AE3GIS_INSTRUCTOR_PASSWORD:-}" ] && [ -z "${AE3GIS_INSTRUCTOR_TOKEN:-}" ]; then
  echo "Note: accounts are off, so anyone who can reach :3000 or :8000 has full access."
  echo "      For a class, set AE3GIS_INSTRUCTOR_PASSWORD (see README, \"Accounts\")."
fi

echo "Starting AE3GIS (frontend :3000, backend :8000)..."
exec docker compose up --build
