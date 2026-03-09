#!/bin/sh
# Phase 4A: SCADA Compromise — Engineering Station (eng-ws)
# Injects a fake Siemens Step7 project with embedded payload.
# Attempts to reach the historian (blocked by scada-router FW) — observable as
# dropped SYN packets, showing the attacker is trying to call back out.
# Probes PLCs on port 102 (intra-subnet, allowed).

echo "=== Phase 4: SCADA Compromise — Engineering Station ==="
echo "Target: Engineering Station (eng-ws, 10.0.10.101)"
echo "Time:   $(date -u +%Y-%m-%dT%H:%M:%S)"

# Infected Siemens Step7 project file (simulated OB1 replacement)
mkdir -p /opt/step7/projects
cat > /opt/step7/projects/.infected.s7p << 'EOF'
; Siemens STEP 7 Project — COMPROMISED
; Injected payload: OB1 organization block replacement
; Stuxnet technique: intercept S7_Get_Object / S7_Set_Object via DLL proxy
[PROJECT]
Name=Centrifuge_Control_v3
Version=3.1.0
TargetPLC=S7-315-2DP
[PAYLOAD]
Module=s7otbxdx.dll:StuxnetProxy
Intercept=S7_Get_Object,S7_Set_Object
Manipulate=output_rpm_setpoint
TriggerCondition=centrifuge_count>=163
EOF

# Simulated payload binary staged for PLC injection
mkdir -p /tmp/.stuxnet
echo "MZ STUXNET_PLC_PAYLOAD s7otbxdx.dll mrxcls.sys mrxnet.sys" > /tmp/.stuxnet/plc_payload.bin

echo ""
echo "Infected Step7 project: /opt/step7/projects/.infected.s7p"
echo "PLC payload staged:     /tmp/.stuxnet/plc_payload.bin"

# Attempt to reach historian — this crosses scada-router which drops the traffic
# Students see SYN packets with no reply (dropped by FW, not RST)
echo ""
echo "Attempting historian query on 10.0.2.10:1911 (expect: blocked by scada-router)..."
nc -w3 10.0.2.10 1911 </dev/null > /tmp/historian_response.txt 2>&1
echo "Result (connection dropped by firewall):"
cat /tmp/historian_response.txt

# Probe PLCs on port 102 — intra-subnet, no router hop, always succeeds
echo ""
echo "Probing PLCs on port 102 (intra-subnet — no firewall hop)..."
{
  echo "# PLC reachability probe"
  echo "# Source: eng-ws (10.0.10.101)"
  echo "# Time:   $(date -u +%Y-%m-%dT%H:%M:%S)"
  if nc -w2 10.0.10.200 102 </dev/null >/dev/null 2>&1; then
    echo "10.0.10.200:102 REACHABLE (plc-1 Centrifuge)"
  else
    echo "10.0.10.200:102 UNREACHABLE (plc-1 Centrifuge)"
  fi
  if nc -w2 10.0.10.201 102 </dev/null >/dev/null 2>&1; then
    echo "10.0.10.201:102 REACHABLE (plc-2 Valve)"
  else
    echo "10.0.10.201:102 UNREACHABLE (plc-2 Valve)"
  fi
} | tee /tmp/plc_reachability.txt

echo ""
echo "IOC hunting: ls /opt/step7/projects/  |  cat /tmp/historian_response.txt"
echo "Network: eng-ws attempting 10.0.10.101→10.0.2.10:1911 — dropped SYN visible on Wireshark"
