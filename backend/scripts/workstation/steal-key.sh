#!/bin/bash

# Usage:
# ./copy-ssh-key.sh <destination_directory>

DEST="$HOME/stolen_keys"
KEY_DIR="$HOME/.ssh"
KEY_NAME="id_ed25519"

# Create destination directory if it doesn't exist
mkdir -p "$DEST"

# Copy keys
cp "$KEY_DIR/$KEY_NAME" "$DEST/"
cp "$KEY_DIR/$KEY_NAME.pub" "$DEST/"

echo "SSH key copied to: $DEST"
echo ""
echo "Private key:"
echo "$DEST/$KEY_NAME"
echo ""
echo "Public key:"
echo "$DEST/$KEY_NAME.pub"