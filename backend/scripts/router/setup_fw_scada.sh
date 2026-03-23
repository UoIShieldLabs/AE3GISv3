#!/bin/sh
# Phase 0: scada-router firewall initialization
# SCADA network is air-gapped except for inbound historian queries on ICS ports.
# All other forwarded traffic is dropped.

FW_CHAIN="AE3GIS-FW"
IPT=$(command -v iptables 2>/dev/null || command -v iptables-nft 2>/dev/null)

if [ -z "$IPT" ]; then
    echo "ERROR: iptables not found in container" >&2
    exit 1
fi

echo "Applying scada-router firewall rules at $(date)..."

$IPT -N $FW_CHAIN 2>/dev/null || true
$IPT -C FORWARD -j $FW_CHAIN 2>/dev/null || $IPT -I FORWARD 1 -j $FW_CHAIN
$IPT -F $FW_CHAIN

# Rule 1: Allow established/related return traffic
$IPT -A $FW_CHAIN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Rule 2: Historian → SCADA: ISO-TSAP / S7comm
$IPT -A $FW_CHAIN -s 10.0.2.10 -d 10.0.10.0/24 -p tcp --dport 102 -j ACCEPT

# Rule 3: Historian → SCADA: Wonderware OPC DA
$IPT -A $FW_CHAIN -s 10.0.2.10 -d 10.0.10.0/24 -p tcp --dport 1911 -j ACCEPT

# Rule 4: Default deny all other forwarded traffic (OT air-gap enforcement)
$IPT -A $FW_CHAIN -j DROP

echo "scada-router firewall rules applied successfully."
echo "Active rules in $FW_CHAIN:"
$IPT -S $FW_CHAIN
