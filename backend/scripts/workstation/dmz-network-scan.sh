#!/bin/bash
#
# dmz-network-scan.sh — Scan a target network (typically the DMZ) for vulnerable services.
#
# Args (all optional; env vars are used as fallback):
#   $1  SCAN_CIDR  — CIDR range to scan (e.g. 10.0.2.0/24)
#
# Env vars injected automatically by the topology (build_topology_env):
#   SUBNET_DMZ_NETWORK_CIDR, SUBNET_DMZ_CIDR, etc.
#
# Falls back to parsing ~/routes.txt (written by router-nmap.sh) if no CIDR supplied.

SCAN_CIDR="${1:-${SUBNET_DMZ_NETWORK_CIDR:-${SUBNET_DMZ_CIDR:-}}}"

echo "Nmaping hosts on the DMZ network..."

if [[ -z "$SCAN_CIDR" ]]; then
    if [[ -f ~/routes.txt ]]; then
        echo "No CIDR supplied — using routes from ~/routes.txt"
        cat ~/routes.txt
        # Extract first non-default, non-local route that looks like a subnet
        SCAN_CIDR=$(grep -Eo '([0-9]{1,3}\.){3}[0-9]{1,3}/[0-9]+' ~/routes.txt \
                    | grep -v '^0\.0\.0\.0\|^127\.' | head -1)
    fi
fi

if [[ -z "$SCAN_CIDR" ]]; then
    echo "[!] No scan target found. Pass as \$1, set SUBNET_DMZ_NETWORK_CIDR, or run router-nmap.sh first."
    exit 1
fi

echo "Scanning $SCAN_CIDR ..."
nmap -sV -O --script=vuln "$SCAN_CIDR" -T5
echo "Scan complete. Check the output above for open vulnerable services on the network."
