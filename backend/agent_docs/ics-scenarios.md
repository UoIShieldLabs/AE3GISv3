# ICS attack-scenario labs (condensed)

The full reference is `docs/ics-scenarios/ics-scenarios-agent-guide.md` in the
repository; the presets `ics-scenario-b*` build Scenario B ready to deploy
(`read_docs presets`).

## Teaching thesis and containment
The labs reproduce, at the level of technique, attacks that cross from an IT foothold
to a physical process (Industroyer 2016, FrostyGoop 2024): legacy OT protocols have no
authentication, so **network reachability equals control**. Everything runs offline
in the lab; no real malware — every attacker action is an ordinary protocol read/write
or standard admin tooling (ssh, nmap). Weaknesses are planted (reused credentials, a
dual-homed host, no protocol auth).

## Shared architecture
| Segment | Subnet | Purdue | Switch |
|---|---|---|---|
| IT-LAN | 10.0.5.0/24 | L4 enterprise | plain |
| OT-LAN | 10.0.3.0/24 | L3/L2 supervisory | Open vSwitch with a SPAN mirror to the IDS |
| PROCESS | 10.0.1.0/24 | L1/L0 process | plain |

| Node | Role | Addresses |
|---|---|---|
| attacker | foothold, recon tools | IT 10.0.5.10 |
| fw | firewall/router IT↔OT, default-deny IT→OT except SSH to the historian | IT 10.0.5.1, OT 10.0.3.1 |
| historian | dual-homed DB + sshd, **IP forwarding off** — the pivot | IT 10.0.5.20, OT 10.0.3.20 |
| plc | field device (Modbus 502 / IEC-104 2404) | OT 10.0.3.50, PROCESS 10.0.1.50 |
| hmi | operator console (web UI) | OT 10.0.3.30 |
| ids | passive IDS on the mirror port | OT 10.0.3.40 |
| process-sim | renders the physical state (web UI) | PROCESS 10.0.1.10 |

Routing makes the pivot visible: the attacker reaches the historian over SSH on
IT-LAN without crossing the firewall; a direct scan from the attacker to the PLC goes
to `fw` and is dropped (proof of segmentation); from the historian's OT leg the PLC is
reachable with no firewall in the path (the segmentation failure the lab shows).

Planted weaknesses: reused credentials (the images default to `root:pass`), the
dual-homed historian bridging IT and OT, and an unauthenticated OT protocol.

## Attack chain (S0–S7, both scenarios)
- **S0 Baseline:** lab up clean; process-sim nominal, HMI green.
- **S1 Initial access (L4):** from the attacker's assumed foothold, host discovery on
  IT-LAN finds the historian.
- **S2 Pivot IT→OT:** SSH into the historian with reused credentials. A direct scan from
  the attacker to the PLC fails at `fw`; the same scan from the historian succeeds.
- **S3 OT discovery:** from the historian, scan OT-LAN; the field device shows its control
  port (502 for A, 2404 for B).
- **S4 Command the process (L1→L0):** one unauthenticated control command from the
  historian; process-sim diverges within a second or two.
- **S5 Loss of View (L2):** the HMI keeps showing normal while the process stays tripped.
- **S6 Recovery denial (wiper):** overwrite files on an isolated scratch volume inside one
  container only — never a host path or shared directory.
- **S7 Detection & debrief:** review the IDS output, map the chain onto Purdue, discuss
  mitigations.

## Scenario differences
- **A (Modbus/FrostyGoop):** `openplc` (Modbus 502, web 8080; no logic runs until a PLC
  program is loaded), `scadabr` console, a Modbus client on the historian. S4 writes the
  control register (FC6/FC16); S5 holds a separate status-mirror register at nominal.
  Zeek's Modbus analyzer logs the writes with the historian as source.
- **B (IEC-104/Industroyer):** `c104-server` RTU (2404, one breaker: a monitored point and
  a command point, starts closed), `c104-hmi` console, an IEC-104 client on the historian.
  S4 sends a single/double command (C_SC_NA_1 / C_DC_NA_1) opening the breaker; S5 severs
  or monopolises the HMI's 2404 session so it freezes on its last reading. Open-source IDS
  coverage of IEC-104 is thinner — itself a finding.

## Verifying a step
Use `run_in_node` from the right node (attacker for S1, historian for S3–S6), a capture
on the OT-LAN switch link or the IDS port to show the protocol traffic, and the
process-sim/HMI web UIs (`open_view` is for terminals and runs; the web UI opens from the
device in the editor).
