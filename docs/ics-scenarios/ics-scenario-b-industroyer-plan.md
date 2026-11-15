# Scenario B (revised) — IEC-104 / Industroyer, Purdue-aligned

**Project:** AE3GIS · **Platform:** Kathará / AE3GIS lab · **Audience:** an implementing/reviewing agent

---

## 0. Status and how to use this

This is a **design reference to implement and refine, not a finalized spec.** It captures the agreed shape of the revised Scenario B so another agent can build the topology, the container behaviour, and the tutorial cells. Treat every concrete value here — IP addresses, IEC-104 object numbers, exact commands — as a **working baseline you may change**, as long as the behaviour each step is meant to demonstrate is preserved. Where something is genuinely open, it is called out in Section 9. Research current tool/library details as needed (the IEC-104 stack, Samba SMBv1 config, Zeek) rather than treating the snippets here as authoritative.

This revision **supersedes the Scenario B portion** of `ics-scenarios-agent-guide.md` (which used a flat IT/OT topology with a dual-homed historian pivot and no DMZ). The shared conventions in that guide and in `ics-dockerfiles-build-guide.md` still apply; the topology and attack chain below replace the old Scenario B.

---

## 1. What this models, and fidelity notes

A Purdue-aligned reproduction of an **Industroyer-style** attack (2016 Ukraine grid): an attacker starting on the enterprise IT network crosses a DMZ into the OT network and issues a legitimate **IEC-104** control command that opens a substation breaker, then denies recovery. The thesis is unchanged: **unauthenticated OT protocols mean reachability equals control.**

This is an educational lab — no real malware, fully offline, all weaknesses planted or simulated. Deliberate simplifications a presenter should disclose:

- **Initial access is simplified.** Real Industroyer followed spearphishing, stolen credentials and long dwell time in a Windows environment. Here it's an assumed foothold on an IoT device plus an SMBv1 weak-config hop. SMBv1 is modelled as a **weak Samba configuration with weak/reused credentials**, not the EternalBlue kernel exploit.
- **Faithful core.** The final act — issuing an IEC-104 control command to trip a breaker — *is* what Industroyer did. It did **not** reprogram PLC logic (that's Stuxnet/TRITON); we deliberately avoid that.
- **Not modelled:** Industroyer's multi-protocol payloads, its SIPROTEC relay DoS (CVE-2015-5374), and its wiper. "Loss of control" is represented by a software re-trip loop.
- **Scale:** one RTU and one breaker, versus many in the real incident.
- **Hosts:** Linux stand-ins throughout; Windows-specific tradecraft is represented by equivalent weak configs, not executed.
- The IT→DMZ→OT pivot chain is a *representative* path, not Industroyer's literal tradecraft.

---

## 2. Purdue topology

### 2.1 Zones → segments

| Purdue level | Zone | Segment (baseline CIDR) |
|---|---|---|
| L4/L5 | Enterprise IT | IT-LAN 10.0.5.0/24 |
| L3.5 | Industrial DMZ (IDMZ) | DMZ-LAN 10.0.4.0/24 |
| L3/L2 | Operations / Supervisory (OT) | OT-LAN 10.0.3.0/24 |
| L1/L0 | Control / Process | PROCESS 10.0.1.0/24 |

No direct IT↔OT path exists; everything crosses the DMZ. The DMZ is flanked by two firewall boundaries.

### 2.2 Nodes and interfaces (baseline)

| Node | Zone | Container (suggested) | eth0 | eth1 | Role |
|---|---|---|---|---|---|
| `iot` | IT | IoT stand-in + attacker toolkit | IT-LAN 10.0.5.10 | — | attacker's assumed foothold |
| `it-fileserver` | IT | Samba (SMBv1 enabled) | IT-LAN 10.0.5.30 | — | weak IT file server; the one host allowed to reach the DMZ gateway |
| `fw-it` | boundary | firewall (nftables) | IT-LAN 10.0.5.1 | DMZ-LAN 10.0.4.1 | enforces IT↔DMZ |
| `gateway` | DMZ | file-transfer broker (SFTP/SMB) | DMZ-LAN 10.0.4.20 | — | IT-facing DMZ entry point |
| `historian` | DMZ | historian DB (MariaDB/InfluxDB) + collector | DMZ-LAN 10.0.4.30 | — | collects OT data; holds a reused OT credential |
| `fw-ot` | boundary | firewall (nftables) | DMZ-LAN 10.0.4.2 | OT-LAN 10.0.3.1 | enforces DMZ↔OT |
| `ew` | OT | engineering workstation | OT-LAN 10.0.3.15 | — | attacker's OT foothold; runs the attacker's IEC-104 client |
| `hmi` | OT | IEC-104 client console (web UI) | OT-LAN 10.0.3.30 | — | operator console + legitimate IEC-104 master |
| `ids` | OT | Zeek | OT-LAN 10.0.3.40 | — | passive monitor on the OT switch mirror |
| `ot-sw` | OT | open-vswitch | OT-LAN | — | managed switch; SPAN/mirror to `ids` |
| `rtu` | OT→Process | c104-server (IEC-104, 2404) | OT-LAN 10.0.3.50 | PROCESS 10.0.1.50 | the field device; actuates the breaker, serves telemetry |
| `process-sim` | Process | custom physics engine (web UI) | PROCESS 10.0.1.10 | — | Level 0 ground truth (see Section 3) |

Interface count: only `fw-it`, `fw-ot`, and `rtu` are dual-homed. Plain collision domains suffice for IT-LAN, DMZ-LAN and PROCESS; OT-LAN needs the managed `ot-sw` so the passive IDS receives a mirror of OT traffic.

Realization note: the two firewall boundaries may be two firewall containers (shown here) or one multi-homed firewall enforcing both — implementer's choice.

### 2.3 Firewall policy and allowed flows

Both firewalls default-deny. The allowed flows are deliberately the *only* ones, and they define the attack path:

- **FW-IT:** permit `it-fileserver → gateway` on the file-transfer port only. Deny all other IT→DMZ, and all IT→OT.
- **FW-OT:** permit `historian → OT` for its data-collection role. Deny `gateway → OT` and everything else DMZ→OT.
- Within a segment there is no firewall (e.g., `ew → rtu:2404` is intra-OT and open; `gateway → historian` is intra-DMZ and open).

This is what forces the chain through both DMZ hosts: IT can only reach the gateway; only the historian can reach OT.

### 2.4 Planted weaknesses (the teachable failures)

1. **SMBv1 + weak/reused credentials** on `it-fileserver`.
2. **Over-broad DMZ internals:** intra-DMZ lateral movement (`gateway → historian`) is unrestricted, and the historian's DMZ→OT rule is broader than a data feed needs — it can reach the EW over SSH, not just a telemetry port.
3. **Reused service-account credential** stored on the historian (e.g., in a DB/backup config) that the EW trusts — the "secret sprawl" moment.
4. **Unauthenticated IEC-104** on the RTU: any well-formed command on 2404 is executed.
5. Reused OS credentials across hosts (lab convention).

---

## 3. Process and telemetry model (give `process-sim` a real role)

`process-sim` is the **Level 0 physics engine**, not a passive display. Suggested behaviour:

- It maintains the true physical state of a simple feeder/substation: breaker position → feeder energized or de-energized, load served, and derived measurements (e.g., line current, bus voltage).
- It is **coupled to the RTU** so that the breaker's position actually drives the physics, and the telemetry the RTU reports upward is **sourced from `process-sim`**, not hardcoded. Implementer picks the coupling direction — e.g., `process-sim` polls the RTU's breaker state over the PROCESS link and computes the resulting current/voltage/load, which the RTU then exposes as IEC-104 monitored points; or the RTU drives `process-sim` directly. Either way, opening the breaker must propagate to both the HMI's readings and the `process-sim` projector.
- It exposes a **projector web UI** showing physical reality (energized/dark, powered %, current) — distinct from the HMI, which shows the control state.

Baseline IEC-104 object model on the RTU (reuse the existing scenario's numbering for familiarity; adjust freely):

- **Common address (CA):** 47.
- **Breaker command:** IOA 12, `C_SC_NA_1` (single command); value false = OPEN, true = CLOSE.
- **Breaker status (monitored):** IOA 11, `M_SP_NA_1` (or `M_DP_NA_1`).
- **Optional measured values:** `M_ME_*` points for current/voltage sourced from `process-sim`, so the HMI shows the electrical quantities collapsing, not just a breaker flag. Recommended as an enrichment (Section 9).

Because this is the Industroyer ending (a protocol command, not a logic change), the HMI honestly reflects the breaker state — there is no Loss-of-View deception here. The meaningful contrast is **control state (HMI) vs physical consequence (process-sim)**.

---

## 4. Normal operations (baseline, A0)

Establish and project the healthy state before the attack:

- Start Zeek on `ids` (capturing the OT-LAN mirror).
- `process-sim` projector shows the feeder **energized** / city powered; HMI shows breaker **CLOSED**.
- Optionally, the operator performs an authorized open/close **from the HMI** (the legitimate IEC-104 master) to show normal control and that the monitoring/telemetry path works. This is the reference the attack is later contrasted against.

---

## 5. Attack chain (step by step)

Each act lists goal → action → representative terminal intent → observable. Commands are baseline; the implementer may adapt them. Unless noted, phishing and other out-of-scope tradecraft are **narrated, not executed.**

- **A1 — Initial foothold (IT, L4).** *Goal:* orient on the enterprise network. The attacker has a shell on `iot`. Actions: print identity (`hostname; ip -o -4 addr show`), then a ping sweep (`nmap -sn 10.0.5.0/24`) to find IT hosts, including `it-fileserver`. *Observable:* the file server is discovered.

- **A2 — Compromise the IT file server (IT).** *Goal:* take the host that can reach the DMZ. Actions: identify the SMB service, confirm SMBv1 is accepted, and authenticate with weak/reused credentials (e.g., `smbclient`/mount, or an SMB client script). *Observable:* a session/foothold on `it-fileserver`. *Weakness:* SMBv1 + weak creds.

- **A3 — Cross into the DMZ (IT→DMZ).** *Goal:* reach the DMZ. From `it-fileserver`, connect to `gateway` over the permitted file-transfer flow and obtain a session on it. *Observable:* foothold on the DMZ gateway. *Note:* this is the only IT→DMZ path FW-IT allows.

- **A4 — Loot credentials from the historian (within DMZ).** *Goal:* obtain a credential OT will accept. From `gateway`, discover `historian` and move to it (intra-DMZ). On the historian, locate the reused service-account secret (e.g., `grep -ri password /etc` over a DB/backup config, or a saved connection profile). *Observable:* a credential the EW trusts. *Weakness:* secret sprawl + unrestricted intra-DMZ movement.

- **A5 — Pivot into OT (DMZ→OT).** *Goal:* reach an OT host. Show the boundary first: a direct attempt from `gateway` to OT is dropped by FW-OT. Then, from `historian` (whose data-collection rule reaches OT), authenticate to `ew` over SSH with the looted credential (e.g., `sshpass -p <looted> ssh root@10.0.3.15`). *Observable:* a CLI on the EW — inside OT, past both firewalls. *Weakness:* overprivileged historian→OT path + reused credential.

- **A6 — Reach the RTU (OT).** *Goal:* confirm control reach. From `ew`, probe the RTU's IEC-104 port (`nmap -Pn -p 2404 10.0.3.50`). Intra-OT, so it's open. *Observable:* 2404 reachable; the unauthenticated control surface is exposed.

- **A7 — Trip the breaker (L1→L0).** *Goal:* cause the physical effect. From the EW CLI, run the attacker's own IEC-104 client to send a single command (CA 47, IOA 12, value=OPEN). Representative:
  ```
  python3  # c104 client: connect 10.0.3.50:2404, station CA=47,
           # point IOA=12 C_SC_NA_1, value=False, transmit ACTIVATION
  ```
  *Observable:* the RTU opens the breaker; `process-sim` de-energizes the feeder (projector goes dark, current → 0); the HMI shows OPEN. Same command type the operator uses, so nothing looks malformed.

- **A8 — Recovery and loss of control.** *Goal:* deny recovery. The operator closes the breaker **from the HMI** — it works briefly (process-sim re-energizes). Then the attacker runs a **re-trip loop** on the EW: poll breaker state via IEC-104 interrogation and re-open whenever it reads closed. Re-running the operator's close now snaps straight back to OPEN. *Observable:* the operator can no longer hold the breaker closed — the Industroyer effect. The loop runs until stopped (Ctrl-C).

- **A9 — Detection and debrief (IDS).** On `ids`, show Zeek's `conn.log` filtered to the RTU's control port — the whole attack appears only as **plain TCP to 2404** (no IEC-104 analyzer loaded), indistinguishable at that layer from a routine poll. Representative: `grep -v '^#' conn.log | awk '$6==2404{...}' | tail`.

  Debrief points (talk through; optional live extensions):
  - A loaded IEC-104 analyzer *would* decode the `C_SC_NA_1` open command — but it still looks like **authorized control**, so protocol parsing alone doesn't flag it.
  - Even at the TCP layer, the malicious command originates from the **EW**, a host that does not normally command the RTU. **Context/behavioural detection** (an unexpected source talking to the RTU) is the realistic defensive win — a good contrast to protocol-blind monitoring.

**Reset:** stop the loop, operator closes from the HMI, exit the shells back out to `iot`.

---

## 6. Detection summary (scope for the build)

- **Ship live:** Zeek on the OT-LAN mirror, and the `conn.log` view in A9 (option (a)).
- **Debrief/optional extension:** the IEC-104-analyzer view (option (b)) and the context-detection point. Not required as a live step; include if the analyzer builds cleanly on both arches (see the build guide's multi-arch caveats).

---

## 7. Containment and safety

Offline only; no real malware; all weaknesses planted/simulated. No wiper step (the re-trip loop replaces recovery-denial and writes nothing). If any destructive element is ever added, it must write only to an isolated scratch volume inside one container, never a host or shared path.

---

## 8. Narrative cast (quick reference)

- **Attacker path:** `iot` → `it-fileserver` → `gateway` → `historian` → `ew` → `rtu`.
- **Operator (defender side):** `hmi` — normal ops, recovery close, where loss of control is felt.
- **Physical truth:** `process-sim` — reacts to the breaker and sources the telemetry.
- **Monitoring:** `ids` (Zeek).

---

## 9. Open decisions / room for improvement

For the reviewing/implementing agent to resolve or refine:

- **Final foothold host:** baseline is the EW (attacker runs their own IEC-104 client there; its engineering software is unused). Pending advisor confirmation; if a dedicated SCADA/control host is preferred as the IEC-104 origin, relabel the final OT foothold accordingly and keep the EW as a present OT asset.
- **One firewall vs two.** Baseline shows two boundary firewalls; a single multi-homed firewall is acceptable.
- **Telemetry richness.** Recommended enrichment: add `M_ME_*` measured values from `process-sim` so the HMI shows current/voltage collapsing, not just a breaker flag.
- **Historian loot form.** Baseline is a reused service-account password in a config/backup file; an SSH private key the EW trusts is an equally valid variant.
- **process-sim physics fidelity.** How detailed the electrical model is (simple energized/dark + load %, or richer) is open.
- **IoT foothold realism.** The IoT stand-in carries the attacker toolkit (nmap, SMB client, SSH, IEC-104 client); a real IoT device would need these staged. Note or refine as desired.
- **Detection depth.** Whether to wire the IEC-104 analyzer for a live option (b) or keep it a debrief point.
- **IP plan / object numbers.** All baseline; adjust to lab conventions.

---

## 10. Relationship to other docs

- Supersedes the Scenario B portion of `ics-scenarios-agent-guide.md` (flat-topology version).
- Container build guidance (base images, packages, multi-arch publishing) remains in `ics-dockerfiles-build-guide.md`; note the added/changed images this scenario implies: an IoT stand-in, an SMBv1 Samba file server, a DMZ file-transfer gateway, a second firewall, and the historian now as a DMZ data collector rather than a dual-homed pivot.
