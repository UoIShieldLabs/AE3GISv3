#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if ! sudo -n containerlab version >/dev/null 2>&1; then
    echo "First-time setup: granting this user passwordless sudo for containerlab."
    echo "You'll be asked for your password once — after this, it won't ask again."
    ./scripts/setup-sudoers.sh
fi

python3 frontend/src/components/dynamicFrontendGenerator.py

docker compose up --build
