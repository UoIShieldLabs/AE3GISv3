#!/bin/sh
# Phase 4B: SCADA Compromise — HMI Workstation monitoring daemon
# Starts a background loop that queries PLCs on port 9900 every 5s and writes
# results to /hmi/display.log.  PLCs aren't listening on 9900 yet (Phase 5 starts
# the spoof listener), so the HMI falls back to hardcoded normal defaults.
# After Phase 5 the HMI will receive — and log — the spoofed "normal" values,
# masking the dangerous setpoints that /plc/status.log shows.

echo "=== Phase 4: SCADA Compromise — HMI Workstation ==="
echo "Target: HMI Workstation (hmi-1, 10.0.10.100)"
echo "Time:   $(date -u +%Y-%m-%dT%H:%M:%S)"

mkdir -p /hmi

# Stop any existing HMI daemon
pkill -f "hmi_monitor\|display.log" 2>/dev/null || true
sleep 1

# HMI monitoring daemon
# Queries plc-1 and plc-2 on port 9900 each cycle.
# If the port is closed: uses fallback defaults that look normal.
# Once Phase 5 starts the spoofing listener on :9900, the HMI receives
# the fake-normal values and logs them — masking the real dangerous state.
(
  while true; do
    TS=$(date -u +%Y-%m-%dT%H:%M:%S)

    PLC1_DATA=$(nc -w2 10.0.10.200 9900 2>/dev/null)
    if [ -z "$PLC1_DATA" ]; then
      PLC1_DATA="CENTRIFUGE_RPM=1064 PRESSURE=97psi VIBRATION=0.12g STATUS=normal"
    fi

    PLC2_DATA=$(nc -w2 10.0.10.201 9900 2>/dev/null)
    if [ -z "$PLC2_DATA" ]; then
      PLC2_DATA="VALVE_A=42% VALVE_B=68% FEED_RATE=1.4kg/h STATUS=normal"
    fi

    echo "$TS | PLC1: $PLC1_DATA" >> /hmi/display.log
    echo "$TS | PLC2: $PLC2_DATA" >> /hmi/display.log

    sleep 5
  done
) &

HMI_PID=$!
echo $HMI_PID > /hmi/daemon.pid
echo ""
echo "HMI monitoring daemon started (PID $HMI_PID)"
echo "Display log: /hmi/display.log  (updates every 5s)"
echo ""
echo "Before Phase 5: HMI shows hardcoded normal defaults"
echo "After Phase 5:  HMI receives spoofed normal values from plc :9900 listener"
echo "Ground truth:   /plc/status.log on each PLC shows real (dangerous) values"
echo ""
echo "IOC hunting: diff <(tail -1 /hmi/display.log) vs tail -1 /plc/status.log on plc-1"
