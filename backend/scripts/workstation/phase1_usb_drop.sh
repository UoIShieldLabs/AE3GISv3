#!/bin/sh
# Phase 1: Initial Access — simulated USB malware drop on IT-ws-1
# Creates USB drop artifacts, a fake credential cache, and starts a C2 beacon
# that polls IT-fileserv:4444 every 10 seconds.

echo "=== Phase 1: Initial Access (USB Drop) ==="
echo "Target: IT Engineer Workstation (IT-ws-1, 10.0.1.100)"
echo "Time:   $(date -u +%Y-%m-%dT%H:%M:%S)"

# Simulated USB autorun artifact
mkdir -p /tmp/.usb
cat > /tmp/.usb/autorun.inf << 'EOF'
[AutoRun]
open=setup.exe
icon=setup.exe,1
label=USB Storage
EOF

# Malware staging directory
mkdir -p /tmp/.stuxnet

# Simulated payload binary marker
echo "MZ STUXNET_PAYLOAD_V2.1 s7otbxdx.dll frxrefapi.dll" > /tmp/.stuxnet/payload.bin

# Simulated LSASS credential dump (fake NTLM hashes — not real credentials)
cat > /tmp/.stuxnet/creds.cache << 'EOF'
; Credential cache — dumped from lsass.exe via Mimikatz
; Format: username:domain:LM_hash:NTLM_hash
engineer1:FACILITY:aad3b435b51404eeaad3b435b51404ee:8846f7eaee8fb117ad06bdd830b7586c
admin:FACILITY:aad3b435b51404eeaad3b435b51404ee:f4dcf4b06ad2d3dc6f95dea9fd5a9c4a
svc_historian:FACILITY:aad3b435b51404eeaad3b435b51404ee:2b5760d5e30c72f03c7a4a7a29ab5cf0
EOF

# Infection marker
echo "INFECTED=$(date -u +%Y-%m-%dT%H:%M:%S) PAYLOAD=stuxnet-v2.1 SOURCE=USB VECTOR=autorun" > /tmp/.infected

echo ""
echo "Artifacts created:"
ls -la /tmp/.usb/
ls -la /tmp/.stuxnet/

# Stop any existing beacon
pkill -f "beacon.log" 2>/dev/null || true
sleep 1

# C2 beacon: polls IT-fileserv:4444 every 10s
# Before Phase 2, IT-fileserv isn't listening — beacon.log shows FAIL entries
# After Phase 2 starts the relay, connections succeed — observable on Wireshark
(
  while true; do
    TS=$(date -u +%Y-%m-%dT%H:%M:%S)
    if nc -w2 10.0.1.50 4444 </dev/null >/dev/null 2>&1; then
      echo "$TS BEACON OK — C2 connected to 10.0.1.50:4444" >> /tmp/.stuxnet/beacon.log
    else
      echo "$TS BEACON FAIL — C2 unreachable 10.0.1.50:4444" >> /tmp/.stuxnet/beacon.log
    fi
    sleep 10
  done
) &

BEACON_PID=$!
echo $BEACON_PID > /tmp/.stuxnet/beacon.pid
echo ""
echo "C2 beacon started (PID $BEACON_PID) — polling 10.0.1.50:4444 every 10s"
echo "Infection marker: $(cat /tmp/.infected)"
echo ""
echo "IOC hunting: ps aux | grep nc  |  ls /tmp/.stuxnet/  |  cat /tmp/.infected"
