#!/bin/sh
# Phase 0: dmz-router firewall initialization
# Only the historian (10.0.2.10) may reach SCADA on ICS protocol ports.
# No other DMZ host may reach SCADA, and SCADA cannot route back to IT via DMZ.

FW_CHAIN="AE3GIS-FW"
IPT=$(command -v iptables 2>/dev/null || command -v iptables-nft 2>/dev/null)

if [ -z "$IPT" ]; then
    echo "ERROR: iptables not found in container" >&2
    exit 1
fi

echo "Applying dmz-router firewall rules at $(date)..."

$IPT -N $FW_CHAIN 2>/dev/null || true
$IPT -C FORWARD -j $FW_CHAIN 2>/dev/null || $IPT -I FORWARD 1 -j $FW_CHAIN
$IPT -F $FW_CHAIN

# Rule 1: Allow established/related return traffic
$IPT -A $FW_CHAIN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Rule 2: Historian → SCADA: ISO-TSAP / S7comm (Siemens protocol port)
$IPT -A $FW_CHAIN -s 10.0.2.10 -d 10.0.10.0/24 -p tcp --dport 102 -j ACCEPT

# Rule 3: Historian → SCADA: Wonderware OPC DA
$IPT -A $FW_CHAIN -s 10.0.2.10 -d 10.0.10.0/24 -p tcp --dport 1911 -j ACCEPT

# Rule 4: Block all other DMZ → SCADA traffic
$IPT -A $FW_CHAIN -s 10.0.2.0/24 -d 10.0.10.0/24 -j DROP

# Rule 5: Block SCADA → IT routing through DMZ
$IPT -A $FW_CHAIN -s 10.0.10.0/24 -d 10.0.1.0/24 -j DROP

# Rule 6: Default deny
$IPT -A $FW_CHAIN -j DROP

echo "dmz-router firewall rules applied successfully."
echo "Active rules in $FW_CHAIN:"
$IPT -S $FW_CHAIN
