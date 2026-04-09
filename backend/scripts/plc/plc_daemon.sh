#!/bin/sh
# Phase 0: PLC simulation daemon
# Writes device-specific setpoints to /plc/setpoints.conf and starts a background
# loop that appends one status line every 3 seconds.  The loop re-reads
# setpoints.conf on every iteration so Phase 5 setpoint changes are reflected
# immediately in /plc/status.log without restarting the daemon.

mkdir -p /plc

# Write initial setpoints based on which PLC this container is
case "$TARGET_ID" in
  plc-1)
    cat > /plc/setpoints.conf << 'EOF'
DEVICE=Centrifuge_PLC_UF-320
CENTRIFUGE_RPM_SETPOINT=1064
CENTRIFUGE_RPM_MAX=1410
PRESSURE_LIMIT_PSI=97
VIBRATION_LIMIT=0.15
OPERATING_MODE=normal
EOF
    ;;
  plc-2)
    cat > /plc/setpoints.conf << 'EOF'
DEVICE=Valve_PLC_VF-210
VALVE_A_POSITION=42
VALVE_B_POSITION=68
FEED_RATE_KG_H=1.4
OPERATING_MODE=normal
EOF
    ;;
  *)
    echo "ERROR: unrecognised TARGET_ID '$TARGET_ID' (expected plc-1 or plc-2)" >&2
    exit 1
    ;;
esac

echo "Initial setpoints for $TARGET_ID:"
cat /plc/setpoints.conf

# Stop any previously running daemon instance
if [ -f /plc/daemon.pid ]; then
  kill "$(cat /plc/daemon.pid)" 2>/dev/null || true
  rm -f /plc/daemon.pid
fi

# Capture TARGET_ID for the daemon subshell
_TARGET_ID="$TARGET_ID"

# Start daemon loop in background.  The subshell inherits the environment, and
# the dot-source re-reads the file each tick so Phase 5 mutations are visible.
(
  while true; do
    . /plc/setpoints.conf
    TS=$(date -u +%Y-%m-%dT%H:%M:%S)
    case "$_TARGET_ID" in
      plc-1)
        echo "$TS | DEVICE=$DEVICE | RPM=$CENTRIFUGE_RPM_SETPOINT | PRESSURE=${PRESSURE_LIMIT_PSI}psi | VIBRATION=${VIBRATION_LIMIT}g | MODE=$OPERATING_MODE" >> /plc/status.log
        ;;
      plc-2)
        echo "$TS | DEVICE=$DEVICE | VALVE_A=${VALVE_A_POSITION}% | VALVE_B=${VALVE_B_POSITION}% | FEED_RATE=${FEED_RATE_KG_H}kg/h | MODE=$OPERATING_MODE" >> /plc/status.log
        ;;
    esac
    sleep 3
  done
) &

DAEMON_PID=$!
echo $DAEMON_PID > /plc/daemon.pid
echo "PLC daemon started for $TARGET_ID (PID $DAEMON_PID)"
echo "Streaming to /plc/status.log every 3s"
