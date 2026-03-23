#!/bin/sh
# Phase 3: Pivot to DMZ — dmz-historian compromise
# Attacker uses stolen historian credentials to deploy a toolkit on the data historian.
# Probes SCADA hosts on port 102 (allowed by dmz-router FW rules) — observable as
# anomalous outbound connections FROM the historian (not normal inbound queries).

echo "=== Phase 3: Pivot to DMZ ==="
echo "Target: Data Historian (dmz-historian, 10.0.2.10)"
echo "Time:   $(date -u +%Y-%m-%dT%H:%M:%S)"

# Attacker toolkit staged on the historian
mkdir -p /opt/historian/.stuxnet_tools
cat > /opt/historian/.stuxnet_tools/README << 'EOF'
; Stuxnet stage-2 toolkit
; Modules: network scanner, S7comm fuzzer, OPC DA pivot relay
; Version: 2.1.4319.24782
; Deployed via svc_historian credentials (NTLM pass-the-hash)
EOF

# Simulated historian DB dump (fake ICS tag values exfiltrated from SCADA)
cat > /tmp/historian_data.csv << 'EOF'
timestamp,tag,value,quality,unit
2026-03-09T12:00:00,UF320.RPM.Setpoint,1064,Good,rpm
2026-03-09T12:00:00,UF320.RPM.Actual,1061,Good,rpm
2026-03-09T12:00:00,UF320.Pressure,96.8,Good,psi
2026-03-09T12:00:00,UF320.Vibration,0.12,Good,g
2026-03-09T12:00:00,VF210.Valve_A,42.0,Good,%
2026-03-09T12:00:00,VF210.Valve_B,68.0,Good,%
2026-03-09T12:00:00,VF210.FeedRate,1.41,Good,kg/h
2026-03-09T12:03:00,UF320.RPM.Setpoint,1064,Good,rpm
2026-03-09T12:03:00,UF320.RPM.Actual,1063,Good,rpm
2026-03-09T12:03:00,UF320.Pressure,97.1,Good,psi
2026-03-09T12:03:00,UF320.Vibration,0.11,Good,g
EOF

# Backdoor / webshell persistence marker
cat > /opt/historian/.backdoor << 'EOF'
; Historian backdoor — PHP webshell (stub marker)
; Location: /opt/historian/web/health.php?cmd=<base64_encoded_cmd>
; Auth bypass: X-Forwarded-For: 127.0.0.1
INSTALLED=2026-03-09T12:00:00
PERSISTENCE=httpd_module_injection
C2_ENDPOINT=10.0.1.50:4444
EOF

echo ""
echo "Toolkit deployed:    /opt/historian/.stuxnet_tools/"
echo "DB exfil written:    /tmp/historian_data.csv"
echo "Backdoor installed:  /opt/historian/.backdoor"

# Probe SCADA hosts for reachability via port 102 (crosses dmz-router)
# These connections are ALLOWED by the FW (historian → SCADA:102) but anomalous
# because outbound initiation from the historian is not normal historian behaviour
echo ""
echo "Probing SCADA network (port 102 — allowed by FW, but anomalous direction)..."
{
  echo "# SCADA reachability probe"
  echo "# Source: dmz-historian (10.0.2.10)"
  echo "# Time:   $(date -u +%Y-%m-%dT%H:%M:%S)"
  for HOST_LABEL in "10.0.10.100:hmi-1" "10.0.10.101:eng-ws" "10.0.10.200:plc-1" "10.0.10.201:plc-2"; do
    HOST=$(echo "$HOST_LABEL" | cut -d: -f1)
    LABEL=$(echo "$HOST_LABEL" | cut -d: -f2)
    if nc -w2 "$HOST" 102 </dev/null >/dev/null 2>&1; then
      echo "$HOST:102 REACHABLE ($LABEL)"
    else
      echo "$HOST:102 UNREACHABLE ($LABEL)"
    fi
  done
} | tee /tmp/scada_reachability.txt

# Stop any existing pivot listener
pkill -f "nc -l.*9001\|nc -l -p 9001" 2>/dev/null || true
sleep 1

# SCADA pivot relay on port 9001 — will relay future connections toward SCADA
(
  while true; do
    nc -l -p 9001 2>/dev/null
  done
) &

PIVOT_PID=$!
echo $PIVOT_PID > /opt/historian/.stuxnet_tools/pivot.pid
echo ""
echo "SCADA pivot listener started on :9001 (PID $PIVOT_PID)"
echo ""
echo "IOC hunting: ps aux | grep nc  |  ls /opt/historian/  |  cat /tmp/scada_reachability.txt"
echo "Anomaly: historian (10.0.2.10) initiating outbound SYN to SCADA:102 — not normal OPC polling"
