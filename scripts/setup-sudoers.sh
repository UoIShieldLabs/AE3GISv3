#!/usr/bin/env bash
# One-time setup: lets the AE3GIS backend run `containerlab deploy/destroy`
# and clean up persistent storage without a password prompt.
#
# Safe to re-run — it always writes a fresh copy of the same rules, so
# running it twice just overwrites the file with identical content.

set -euo pipefail

CLAB_PATH="$(command -v containerlab || true)"
if [ -z "$CLAB_PATH" ]; then
    echo "containerlab not found on PATH. Install it first, then re-run this script."
    exit 1
fi

RM_PATH="$(command -v rm)"
SUDOERS_FILE="/etc/sudoers.d/ae3gis-containerlab"
CURRENT_USER="$(whoami)"

TMP_FILE="$(mktemp)"
cat > "$TMP_FILE" << RULES
$CURRENT_USER ALL=(ALL) NOPASSWD: $CLAB_PATH
$CURRENT_USER ALL=(ALL) NOPASSWD: $RM_PATH
RULES

# Validate before installing — visudo -c refuses to accept a broken file.
if ! sudo visudo -c -f "$TMP_FILE" >/dev/null 2>&1; then
    echo "Generated sudoers rules failed validation, aborting. Contents:"
    cat "$TMP_FILE"
    rm -f "$TMP_FILE"
    exit 1
fi

sudo install -m 0440 "$TMP_FILE" "$SUDOERS_FILE"
rm -f "$TMP_FILE"

echo "Installed $SUDOERS_FILE for user '$CURRENT_USER':"
cat "$SUDOERS_FILE"
echo
echo "Verifying (should print the containerlab version with no password prompt)..."
sudo containerlab version
