# Stuxnet Kill Chain — Verification Steps

Use these steps after deploying the **"Stuxnet ICS Attack (Single site)"** preset to confirm each phase is producing the expected artifacts, processes, and network behaviour.

---

## Prerequisites

1. Load the **"Stuxnet ICS Attack (Single site)"** preset from the UI
2. Click **Deploy** and wait for all containers to show green status indicators
3. Open the **Stuxnet Kill Chain** scenario in the ScenarioPanel

---

## Phase 0 — Environment Setup

Run Phase 0 from the ScenarioPanel, then verify:

**Firewall rules — UI Firewall panel**
- IT-router: 7 rules, last rule is DROP
- dmz-router: 6 rules, last rule is DROP
- scada-router: 4 rules, last rule is DROP

**Firewall rules — terminal into IT-router:**
```sh
iptables -S AE3GIS-FW
```
Expect 7 lines starting with `-A AE3GIS-FW`.

**PLC daemon — terminal into plc-1:**
```sh
tail -f /plc/status.log
```
Expect a new line every 3 seconds:
```
2026-03-09T14:22:01 | DEVICE=Centrifuge_PLC_UF-320 | RPM=1064 | PRESSURE=97psi | VIBRATION=0.15g | MODE=normal
```

**PLC daemon — terminal into plc-2:**
```sh
cat /plc/setpoints.conf
tail -5 /plc/status.log
```
Expect `VALVE_A_POSITION=42`, `FEED_RATE_KG_H=1.4`, `MODE=normal`.

---

## Phase 1 — Initial Access

Run Phase 1, then terminal into **IT-ws-1**:

```sh
# File artifacts
cat /tmp/.infected
ls /tmp/.stuxnet/
ls /tmp/.usb/

# C2 beacon process
ps aux | grep nc

# Beacon log — expect FAIL entries (fileserv not listening yet)
tail -f /tmp/.stuxnet/beacon.log
```

**Expected:** `BEACON FAIL — C2 unreachable 10.0.1.50:4444` every ~10 seconds.

---

## Phase 2 — Lateral Movement

Run Phase 2, then:

**Terminal into IT-fileserv:**
```sh
ps aux | grep nc                       # nc listener on :4444
ls /srv/files/                         # .infected and .stuxnet/ present
cat /tmp/stolen_creds.txt
cat /etc/cron.d/stuxnet_persist
```

**Back on IT-ws-1 — watch beacon transition:**
```sh
tail -f /tmp/.stuxnet/beacon.log
```
Within 10 seconds: `BEACON OK — C2 connected to 10.0.1.50:4444`

This is the observable network change — Wireshark on IT-switch shows SYN→RST becoming a full TCP handshake on port 4444.

---

## Phase 3 — Pivot to DMZ

Run Phase 3, then terminal into **dmz-historian**:

```sh
ls /opt/historian/                     # .stuxnet_tools/ and .backdoor present
cat /opt/historian/.backdoor
cat /tmp/scada_reachability.txt        # probe results to SCADA:102
ps aux | grep nc                       # pivot listener on :9001
```

**Note on network IOC:** The reachability probe file shows whether SCADA hosts responded. Even if they show UNREACHABLE (nothing listening on port 102), the SYN packets still crossed the dmz-router — observable on Wireshark as outbound connections *from* the historian to SCADA, which is the anomalous direction for an OPC historian.

---

## Phase 4 — SCADA Compromise

Run Phase 4, then:

**Terminal into eng-ws:**
```sh
ls /opt/step7/projects/                # .infected.s7p present
cat /tmp/historian_response.txt        # empty or "nc: connect failed" — blocked by scada-router
cat /tmp/plc_reachability.txt          # PLCs reachable intra-subnet
```

**Terminal into hmi-1:**
```sh
tail -f /hmi/display.log
```
Expect every 5 seconds: `PLC1: CENTRIFUGE_RPM=1064 ... STATUS=normal` (hardcoded defaults — PLCs not listening on :9900 yet).

---

## Phase 5 — PLC Manipulation

This is the core test. Open **two terminals simultaneously**.

**Terminal A — plc-1 (ground truth):**
```sh
tail -f /plc/status.log
```
Within 3 seconds of Phase 5 running, RPM jumps to `1410`, PRESSURE to `130psi`, MODE becomes `COMPROMISED`.

**Terminal B — hmi-1 (the lie):**
```sh
tail -f /hmi/display.log
```
Still shows `CENTRIFUGE_RPM=1064 PRESSURE=97psi STATUS=normal` — the spoof listener is answering.

**Confirm spoof listener on plc-1:**
```sh
ps aux | grep nc                       # nc -l -p 9900 running
cat /plc/setpoints.conf                # CENTRIFUGE_RPM_SETPOINT=1410
```

**Manually query the spoof listener from any SCADA host:**
```sh
nc 10.0.10.200 9900
# Returns: CENTRIFUGE_RPM=1064 PRESSURE=97psi VIBRATION=0.12g STATUS=normal
```

**Repeat for plc-2:**
```sh
# On plc-2
tail -f /plc/status.log               # VALVE_A=97% VALVE_B=98% FEED_RATE=8.9kg/h

# From hmi-1
nc 10.0.10.201 9900                   # Returns: VALVE_A=42% VALVE_B=68% STATUS=normal
```

---

## Quick Smoke Test (All Phases)

Run this after all phases are deployed to hit the key IOCs in one pass:

```sh
# === IT-ws-1 ===
cat /tmp/.infected
ps aux | grep nc

# === IT-fileserv ===
ps aux | grep nc | grep 4444

# === dmz-historian ===
ls /opt/historian/.backdoor

# === plc-1 — THE critical discrepancy ===
echo "=== TRUTH (status.log) ===" && tail -2 /plc/status.log
echo "=== HMI SEES (port 9900) ===" && nc -w1 10.0.10.200 9900
```

**Pass condition:** `status.log` shows `MODE=COMPROMISED` / `RPM=1410` while port 9900 returns `STATUS=normal` / `RPM=1064`.

---

## Student IOC Hunting Targets

| Location | Command | What to find |
|----------|---------|--------------|
| IT-ws-1 | `cat /tmp/.infected` | Infection timestamp marker |
| IT-ws-1 | `ls /tmp/.stuxnet/` | Credential cache, payload binary |
| IT-ws-1 | `ps aux \| grep nc` | Background beacon process |
| IT-fileserv | `ps aux \| grep nc` | C2 relay listener on :4444 |
| IT-fileserv | `cat /etc/cron.d/stuxnet_persist` | Persistence cron artifact |
| dmz-historian | `ls /opt/historian/` | Backdoor and toolkit files |
| dmz-historian | `cat /tmp/scada_reachability.txt` | Evidence of SCADA probing |
| eng-ws | `ls /opt/step7/projects/` | Infected Step7 project |
| plc-1 / plc-2 | `cat /plc/setpoints.conf` | Manipulated setpoints |
| plc-1 / plc-2 | `ps aux \| grep nc` | Spoofing listener on :9900 |
| hmi-1 | `diff` `/hmi/display.log` vs `/plc/status.log` | Discrepancy between truth and display |

## Defensive Response Options (Students)

Students can apply corrective firewall rules via the UI Firewall panel on any router to block attacker lateral movement between phases:

- **Block C2 beacon:** Add DROP rule on IT-router blocking `10.0.1.100 → 10.0.1.50:4444`
- **Isolate historian:** Add DROP rule on dmz-router blocking `10.0.2.10 → 10.0.10.0/24` (cuts off pivot)
- **Block HMI spoofing:** Add DROP rule on scada-router or on the SCADA switch blocking intra-subnet `10.0.10.100 → 10.0.10.200:9900`
