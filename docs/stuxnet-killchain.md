# Stuxnet Kill Chain Emulation — How It Works

Educational ICS attack scenario modeled after the Stuxnet worm. Runs across three isolated network segments (IT LAN → DMZ → SCADA) using real iptables firewall rules, background daemon processes, and cross-subnet network traffic to produce all four categories of observable evidence: file artifacts, running processes, network traffic, and system state changes.

---

## Network Architecture

| Subnet | CIDR | Router | Key Hosts |
|--------|------|--------|-----------|
| IT LAN | 10.0.1.0/24 | IT-router (10.0.1.1) | IT-ws-1 (.100), IT-ws-2 (.101), IT-fileserv (.50) |
| DMZ | 10.0.2.0/24 | dmz-router (10.0.2.1) | dmz-historian (.10), dmz-jumpbox (.11) |
| SCADA | 10.0.10.0/24 | scada-router (10.0.10.1) | hmi-1 (.100), eng-ws (.101), plc-1 (.200), plc-2 (.201) |

Cross-subnet traffic passes through routers (PtP links on `10.255.0.0/24`), so the routers are the real enforcement point for iptables FORWARD rules.

---

## Phase 0: Environment Setup

**Scripts:** `setup_fw_it.sh`, `setup_fw_dmz.sh`, `setup_fw_scada.sh`, `plc_daemon.sh`

### Firewall Initialization

Each router script creates the `AE3GIS-FW` iptables chain (the same chain the UI Firewall panel reads and writes) and wires it into the FORWARD table. This means rules applied by scripts are visible in the UI and can be modified by students as a defensive response.

**IT-router policy** — IT LAN may reach the DMZ historian on HTTP/HTTPS/1911 only. No IT→SCADA direct path. DMZ cannot initiate connections back into IT.

**DMZ-router policy** — Only the historian (10.0.2.10) may reach SCADA, and only on ports 102 (ISO-TSAP/S7comm) and 1911 (Wonderware OPC). All other DMZ→SCADA and SCADA→IT traffic is dropped.

**SCADA-router policy** — Mirrors DMZ-router for inbound historian queries. Everything else dropped (OT air-gap).

### PLC Simulation Daemon

`plc_daemon.sh` uses the `TARGET_ID` environment variable (injected by the backend at exec time) to write device-specific setpoints to `/plc/setpoints.conf`, then starts a background loop that appends one status line to `/plc/status.log` every 3 seconds.

The loop re-reads `setpoints.conf` on every iteration using shell dot-source (`. /plc/setpoints.conf`). This means Phase 5's setpoint changes are reflected in the log within 3 seconds — no daemon restart required.

**plc-1 (Centrifuge UF-320)** normal state:
```
RPM=1064 | PRESSURE=97psi | VIBRATION=0.15g | MODE=normal
```

**plc-2 (Valve VF-210)** normal state:
```
VALVE_A=42% | VALVE_B=68% | FEED_RATE=1.4kg/h | MODE=normal
```

---

## Phase 1: Initial Access (USB Drop)

**Script:** `phase1_usb_drop.sh` on **IT-ws-1**

Simulates a USB-borne malware infection. Creates:

- `/tmp/.usb/autorun.inf` — simulated USB autorun entry
- `/tmp/.stuxnet/payload.bin` — malware marker (fake binary header)
- `/tmp/.stuxnet/creds.cache` — fake NTLM hashes for `engineer1`, `admin`, `svc_historian` (simulating an LSASS credential dump)
- `/tmp/.infected` — infection timestamp marker

Then starts a **C2 beacon** in the background: every 10 seconds it attempts `nc -w2 10.0.1.50 4444`. Before Phase 2, IT-fileserv isn't listening so every attempt produces a `SYN→RST` (BEACON FAIL in the log). After Phase 2 starts the relay, connections succeed.

**Why this is realistic:** Stuxnet spread via USB autorun and used stolen certificates and LSASS credential dumps to move laterally.

---

## Phase 2: Lateral Movement

**Script:** `phase2_lateral_movement.sh` on **IT-fileserv**

Simulates worm spread from the workstation to the file server using stolen credentials. Creates:

- `/srv/files/.infected` and `/srv/files/.stuxnet/` — worm spread markers on shared storage
- `/tmp/stolen_creds.txt` — full credential set harvested from IT-ws-1 via C2 channel
- `/etc/cron.d/stuxnet_persist` — persistence artifact (file only, not an active cron entry)

Starts a **C2 relay listener**: `while true; do nc -l -p 4444; done`. Once running, the Phase 1 beacon on IT-ws-1 transitions from `SYN→RST` to a full TCP handshake — observable on Wireshark as a change from connection-refused to connection-established traffic.

---

## Phase 3: Pivot to DMZ

**Script:** `phase3_dmz_pivot.sh` on **dmz-historian**

Simulates the attacker using stolen `svc_historian` credentials to reach the data historian in the DMZ. Creates:

- `/opt/historian/.stuxnet_tools/` — attacker toolkit drop
- `/tmp/historian_data.csv` — simulated exfiltrated ICS historian records (fake tag values)
- `/opt/historian/.backdoor` — webshell/persistence stub marker

Then **probes SCADA hosts** on port 102 via `nc -w2`. These connections cross the dmz-router and are technically **allowed** by the firewall (historian→SCADA:102 is a permitted rule). However, the direction is anomalous: normally the historian receives inbound OPC queries from SCADA; it does not initiate outbound connections to SCADA. This is the IOC students should detect.

Starts a **pivot relay listener** on port 9001 for future SCADA-directed tunneling.

---

## Phase 4: SCADA Compromise

### 4A — Engineering Station (`phase4_eng_compromise.sh` on eng-ws)

Creates an infected Siemens Step7 project file at `/opt/step7/projects/.infected.s7p` (simulating Stuxnet's actual technique of replacing OB1 organization blocks via a DLL proxy into `s7otbxdx.dll`).

Then **attempts to reach the historian** on `10.0.2.10:1911`. This connection crosses the scada-router, which drops it (no rule permits SCADA→IT traffic). The result is a dropped SYN with no reply — visible on Wireshark as a one-sided connection attempt. This shows the attacker is trying to call back out through the air-gap.

Also probes plc-1 and plc-2 on port 102 (intra-subnet, no router hop — succeeds).

### 4B — HMI Workstation (`phase4_hmi_spoof.sh` on hmi-1)

Starts the **HMI monitoring daemon**: a background loop that queries each PLC on port 9900 every 5 seconds and writes results to `/hmi/display.log`. Before Phase 5 starts the spoof listener on the PLCs, port 9900 is closed and all connections fail. The daemon falls back to hardcoded normal defaults, so `/hmi/display.log` shows normal readings from the start.

---

## Phase 5: PLC Manipulation

**Script:** `phase5_plc_manipulate.sh` on **plc-1** and **plc-2**

The script uses `TARGET_ID` to apply the correct attack per device.

### Setpoint Injection

Overwrites `/plc/setpoints.conf` with dangerous values:

**plc-1 (centrifuge over-speed attack):**
```
CENTRIFUGE_RPM_SETPOINT: 1064 → 1410  (at the structural failure limit)
PRESSURE_LIMIT_PSI:       97  → 130
VIBRATION_LIMIT:         0.15 → 0.95
OPERATING_MODE:        normal → COMPROMISED
```

**plc-2 (valve overpressure attack):**
```
VALVE_A_POSITION:  42 → 97  (nearly fully open)
VALVE_B_POSITION:  68 → 98
FEED_RATE_KG_H:   1.4 → 8.9  (6× normal)
OPERATING_MODE: normal → COMPROMISED
```

Because the daemon loop re-reads `setpoints.conf` on every tick, `/plc/status.log` starts reflecting dangerous values within 3 seconds — without any daemon restart.

### HMI Spoofing Listener

Starts a listener on port 9900: `while true; do printf 'CENTRIFUGE_RPM=1064 ... STATUS=normal\n' | nc -l -p 9900; done`

The Phase 4 HMI daemon on hmi-1 connects to this port every 5 seconds and receives the fake-normal values. `/hmi/display.log` continues to show normal readings even as `/plc/status.log` shows dangerous ones.

### The Core Learning Moment

| What you look at | What you see |
|------------------|--------------|
| `/hmi/display.log` on hmi-1 | `RPM=1064 STATUS=normal` — nothing wrong |
| `/plc/status.log` on plc-1 | `RPM=1410 MODE=COMPROMISED` — rotor failure imminent |
| `/plc/setpoints.conf` on plc-1 | Modified setpoints with dangerous values |
| `ps aux` on plc-1 | `nc -l -p 9900` spoofing listener |

This directly mirrors Stuxnet's documented behaviour: the worm intercepted calls from the Siemens WinCC HMI software to the STEP 7 runtime to mask the true PLC state from operators.

---

## Script Mount Paths (reference)

| Container type | Host directory | Mount point in container |
|----------------|---------------|--------------------------|
| `router` | `backend/scripts/router/` | `/scripts/router/` |
| `workstation` | `backend/scripts/workstation/` | `/scripts/workstation/` |
| `plc`, `file-server`, `web-server` | `backend/scripts/server/` | `/scripts/server/` |

## Environment Variables Available in Scripts

The backend injects topology context as environment variables at exec time:

| Variable | Value |
|----------|-------|
| `TARGET_ID` | Container ID of the container running the script (e.g. `plc-1`) |
| `TARGET_IP` | IP address of that container |
| `TARGET_TYPE` | Container type (e.g. `plc`) |
| `CONTAINER_{NAME}_IP` | IP of any container in the topology |
| `TOPO_NAME` | Topology name |

`plc_daemon.sh` and `phase5_plc_manipulate.sh` both use `TARGET_ID` to apply the correct per-device configuration without needing separate scripts.
