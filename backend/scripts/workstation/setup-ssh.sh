#!/bin/bash

# Usage:
# ./setup-ssh-key.sh user host port
# Example:
# ./setup-ssh-key.sh root 192.168.1.50 22

USER=$1
HOST=$2
PORT=${3:-22}

KEY="$HOME/.ssh/id_ed25519"

if [ -z "$USER" ] || [ -z "$HOST" ]; then
  echo "Usage: $0 <user> <host> [port]"
  exit 1
fi

echo "Target: $USER@$HOST:$PORT"

# Generate SSH key if it doesn't exist
if [ ! -f "$KEY" ]; then
  echo "No SSH key found. Generating new key..."
  ssh-keygen -t ed25519 -f "$KEY" -N "" -C "auto-generated-key"
else
  echo "SSH key already exists."
fi

# Ensure ssh-copy-id exists
if ! command -v ssh-copy-id &> /dev/null; then
  echo "ssh-copy-id not found. Install it first."
  exit 1
fi

echo "Copying SSH key to remote host..."

ssh-copy-id -i "$KEY.pub" -p "$PORT" "$USER@$HOST"

if [ $? -eq 0 ]; then
  echo ""
  echo "Key installed successfully."
  echo "You can now login with:"
  echo "ssh -p $PORT $USER@$HOST"
else
  echo "Failed to install key."
fi