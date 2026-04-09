#!/bin/sh
# Phase 0: IT-router firewall initialization
# Applies ICS-realistic segmentation rules — IT LAN may reach DMZ historian
# but cannot directly reach SCADA. DMZ cannot initiate connections into IT.

FW_CHAIN="AE3GIS-FW"
IPT=$(command -v iptables 2>/dev/null || command -v iptables-nft 2>/dev/null)

if [ -z "$IPT" ]; then
    echo "ERROR: iptables not found in container" >&2
    exit 1
fi

echo "Applying IT-router firewall rules at $(date)..."

# Create managed chain and wire it into FORWARD (top of chain)
$IPT -N $FW_CHAIN 2>/dev/null || true
$IPT -C FORWARD -j $FW_CHAIN 2>/dev/null || $IPT -I FORWARD 1 -j $FW_CHAIN

# Flush any existing managed rules
$IPT -F $FW_CHAIN

# Rule 1: Allow established/related return traffic
$IPT -A $FW_CHAIN -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT

# Rule 2: IT LAN → DMZ historian: HTTP
$IPT -A $FW_CHAIN -s 10.0.1.0/24 -d 10.0.2.0/24 -p tcp --dport 80 -j ACCEPT

# Rule 3: IT LAN → DMZ historian: HTTPS
$IPT -A $FW_CHAIN -s 10.0.1.0/24 -d 10.0.2.0/24 -p tcp --dport 443 -j ACCEPT

# Rule 4: IT LAN → historian: Wonderware/OSIsoft OPC port
$IPT -A $FW_CHAIN -s 10.0.1.0/24 -d 10.0.2.10 -p tcp --dport 1911 -j ACCEPT

# Rule 5: Block IT → SCADA (no direct IT-to-OT path)
$IPT -A $FW_CHAIN -s 10.0.1.0/24 -d 10.0.10.0/24 -j DROP

# Rule 6: Block DMZ → IT initiation (DMZ should not talk back to IT)
$IPT -A $FW_CHAIN -s 10.0.2.0/24 -d 10.0.1.0/24 -j DROP

# Rule 7: Default deny everything else
$IPT -A $FW_CHAIN -j DROP

echo "IT-router firewall rules applied successfully."
echo "Active rules in $FW_CHAIN:"
$IPT -S $FW_CHAIN
