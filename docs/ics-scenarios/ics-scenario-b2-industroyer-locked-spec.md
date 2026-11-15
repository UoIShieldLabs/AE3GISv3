# Scenario B2 — Industroyer case study (LOCKED design)

**Project:** AE3GIS · **Platform:** AE3GIS / Kathará-style lab · **Audience of this doc:** an implementing/reviewing agent
**Purpose of the demo:** a *faithful case study* of the **2016 Ukraine (Industroyer/CrashOverride)** incident for a **knowledgeable audience**, that also **showcases the AE3GIS platform** for cyber scenarios.

---

## 0. Status

This is the **locked design** agreed in discussion. It refines the existing `ics-scenario-b2-industroyer-purdue.json` build and **supersedes two things in it**: the `breaker open` wrapper (→ replaced by a staged IEC-104 payload) and the naive `while: breaker open` recovery-denial (→ replaced by the faithful sustained-commanding + wiper + manual-recovery arc below). The topology, firewall policy, and loot/weakness model from the JSON and from `ics-scenario-b-industroyer-plan.md` still stand except where noted. Concrete values (IPs, IOAs, commands) remain a working baseline.

**Hardware constraint that shaped decisions:** the demo runs on **Apple Silicon (ARM64)**. Everything must be ARM64-native; **no compiled-payload RCE sits on the critical path** (see §3).

---

## 1. Framing and the honesty contract

Structure the whole demo on the **ICS Cyber Kill Chain** (the Dragos model from the talk): **Stage 1 — Intrusion** and **Stage 2 — ICS Attack**, treated differently on purpose.

For a knowledgeable audience, ship an explicit **"faithful vs. modeled" slide** up front and let the lab own it:

- **Faithful to the incident:** the IEC-104 breaker trip via a legitimate control command; the unauthenticated-protocol thesis (reachability = control); attacker **staging a config** before the ICS attack; **sustained commanding** as denial of control; a **wiper** destroying SCADA tooling as denial of view / denial of recovery; **manual on-site recovery**; command-and-control (C2) back to an external node.
- **Modeled / representative (our tradecraft, not Industroyer's):** initial access and lateral movement (real Industroyer used spearphishing + Windows dwell; we model the *shape* of an IT→OT crossing); a single **live** protocol (IEC-104), others narrated; Linux stand-ins for Windows SCADA/engineering hosts.

**Accuracy caveat to state aloud:** in the real 2016 event the wiper's impact was limited and power returned in ~an hour via manual ops — the *capability* was scarier than the realized damage.

**Out of scope (mention, don't demo):** the **SIPROTEC relay DoS (CVE-2015-5374)** — one slide bullet noting it was the only true *exploit* in the kit; cut from the live demo because it's orthogonal to the breaker-trip through-line and its recovery-degradation lesson is already carried by the wiper.

---

## 2. Topology changes from the current B2 build

### 2.1 New external attacker / C2 node
Add an **external (internet/edge) node** that is the actual adversary. It reaches the **internet-exposed IoT device**, compromises it (default/weak creds), and the attacker **stages tooling** onto the IoT host after popping it (this resolves the "why does a sensor have nmap" problem — narrate the staging).

**Make the external node double as C2:** the staged implant beacons back to it (HTTPS-style; Tor narrated). This represents Industroyer's **main backdoor + C2** component for almost no extra cost and keeps the adversary present throughout, not just at t=0.

Topology: an edge/internet segment with a narrated IoT exposure. A perimeter firewall is **optional** — implementer's call; don't rabbit-hole it.

### 2.2 Every node must have a real purpose
Design principle: **no node exists solely to enable the attack.** Each has a legitimate operational role — shown as background traffic where cheap, narrated otherwise — and the story is that the attacker **leveraged existing useful infrastructure**.

| Node | Legitimate purpose (the reason it exists) | Attacker's use |
|---|---|---|
| `external` | The adversary + their C2 server | Origin of the intrusion; implant beacons home here |
| `iot` | Real building/IoT device (badge reader, HVAC/environmental sensor, IP camera) that POSTs telemetry to an IT service | Internet-exposed soft entry; tool-staging host |
| `it-fileserver` | Corporate SMB file share; legitimately **pushes files to the DMZ gateway** (nightly report/engineering-file export) — which is *why* FW-IT permits that one flow | SMB foothold; stepping stone to the DMZ |
| `gateway` | Sanctioned IT↔OT **file-transfer broker** (textbook IDMZ) | DMZ entry; pivot to historian |
| `historian` | **Data historian** collecting OT telemetry from the RTU for business reporting; holds a reused OT credential because historians genuinely need one to poll — and its DMZ→OT rule exists for that poll | Loot trove (DB creds + SSH key); its over-broad OT rule is the pivot into OT |
| `ew` | **Engineering workstation**: engineers configure/diagnose the RTU from here (legit **reads**, not control) | Control-capable OT foothold; where the ICS payload is dropped and run |
| `hmi` | **Operator console** + legitimate IEC-104 master (the normal control path) | Wiper target (denial of view) |
| `ids` | Passive OT security monitoring (Zeek) | — (defender) |
| `ot-sw` | Managed switch with SPAN mirror to IDS | — |
| `rtu` | Field device: actuates the breaker, serves telemetry | Target of the IEC-104 control command; untouched by the wiper |
| `process-sim` | Level-0 physics — the real feeder/substation ground truth | Audience's god-view of physical reality |

**Background traffic to run live (lights up the canvas in the A0 baseline):** `historian → rtu` telemetry poll (already present), `hmi` operator polling, `it-fileserver → gateway` file push, `iot` sensor telemetry POST. **Narrate** the rarer flows (EW engineering reads, business queries to the historian).

---

## 3. Stage 1 — Intrusion (manual, step-by-step, "representative")

Kept **manual and narrated** on purpose: the audience should see each hop, and it's explicitly representative tradecraft. Chain: `external → iot → it-fileserver → gateway → historian → ew`.

**Four distinct techniques** (real where feasible, all **ARM64-safe**), with credential reuse as connective tissue:

1. **IoT foothold — default/weak creds** (small password spray). Also fixes the previously hand-waved "attacker already has a shell." One spray only — do **not** brute-force every hop (slow and shallow on stage).
2. **iot → it-fileserver — weak-cred / misconfigured SMB.** *Decision:* fell back from a SambaCry RCE because a compiled-payload RCE on ARM64 is the most fragile thing possible in a live demo. (Note for the record: the chosen **Samba 4.5.9 is genuinely SambaCry-vulnerable, CVE-2017-7494**, fixed in 4.5.10 — keep a real ARM64 SambaCry as an **optional, off-critical-path** stretch flex only if built and tested well in advance.)
3. **gateway → historian — MariaDB credential extraction** (dump a creds table). Arch-agnostic, real; this is a "real exploitation" anchor for the platform showcase.
4. **historian → ew — SSH private-key / client-cert theft** (the OT key the EW trusts), used over the historian's over-broad OT rule. Arch-agnostic, real; the strongest "secret sprawl" beat.

The historian is the **loot trove** (DB creds + the SSH key). Exact which-loot-sits-where and the precise hop wiring are build details.

**Firewall rationale stays tied to legitimate function:** FW-IT permits `it-fileserver → gateway` (the file push); FW-OT permits `historian → OT` (the telemetry poll), deliberately **over-broad** (whole subnet, not just a telemetry port) — that over-breadth is the planted mistake the pivot exploits.

---

## 4. Stage 2 — ICS Attack (faithful, autonomous where it matters)

Replace the `breaker open` wrapper. The attacker **drops a payload + config on the EW and launches it**; the payload does the Industroyer work itself but prints every protocol step (autonomous *and* explainable).

**Config staging (faithful — the real 104 module "requires manual staging"):** a `104.cfg` on the EW naming target `10.0.3.50:2404`, common address `CA=47`, target `IOA=12`, and a mode. Teaching beat: the attacker already knew the substation's addressing — which is *why* all the recon mattered.

**Payload behavior (loud; expose the real IEC-104 on the wire):**
- Connect to 2404; send **general interrogation `C_IC_NA_1`** → read breaker state (`M_SP_NA_1`, IOA 11).
- Issue **`C_SC_NA_1`** (single command), IOA 12, value = OFF (ACTIVATION) to trip the breaker.
- Print each ASDU as it goes: type ID, CA, IOA, cause-of-transmission, con/ack.
- **Range mode:** enumerate the configured IOA range and **sustain** the open commands across it — this models the real 104 module and ties to the deck's **Range / Shift / Sequence** modes. (This replaces the naive `while: breaker open`; it is the same sustained-commanding idea, dressed to look like the real payload.)

**Optional cheap multi-protocol nod:** on launch, print a module roster — `101: no serial targets, skip · 61850: skip · OPC: skip · 104: 1 target → engage` — to communicate Industroyer's framework/vendor-independent nature without building three more stacks. Clearly stubbed = honest.

Build note: bake the payload into the attacker/`malicious-client` toolkit and have Stage 1 end by **copying it onto the EW** (a literal "drop the payload" beat). RTU already speaks real `c104`; `CA 47 / IOA 12 (C_SC_NA_1) / IOA 11 status` are consistent with the existing spec.

---

## 5. Denial of control → denial of view → recovery (the faithful arc)

**No Local/Remote toggle** (rejected as a software gimmick with no basis in the incident). The faithful sequence:

1. **Loss of control.** The payload **sustains range-mode open commands** from the EW. The operator closes the breaker from the HMI; it **snaps straight back to OPEN**. They cannot out-click the malware.
2. **Loss of view.** A **wiper** fires on the **HMI** (operator console): it destroys files in a dummy SCADA project/config directory, **kills the HMI service so it won't restart**, and is **loud about enumerating the ICS files it clobbers**. The operator is now blind. The **RTU/field devices are untouched** (faithful — the real wiper was a Windows executable aimed at SCADA/engineering hosts, not embedded field devices). **process-sim is the audience's out-of-band god-view** — the operator does *not* have it; don't let the framing imply they "switched screens."
3. **Recovery = evict + go local.** Responders identify the rogue source (the **EW**), **kill the payload / isolate the EW** (this is what stops the sustained commands — represents cutting off the compromised host), and then, **because the HMI is destroyed**, operate the breaker **locally at the RTU** to re-energize. The wipe is what *forces* manual on-site operation — this is the causal link that makes the manual-RTU step necessary rather than a convenience.

**Lesson:** you don't beat ICS malware by racing it from the HMI — you remove it and fall back to manual. **Ending tone:** response succeeds but operations are degraded to blind/manual — the accurate 2016 outcome (hopeful but costly).

**Wiper safety:** writes **only to an isolated scratch volume inside the one container**, never a host or shared path.

---

## 6. Detection debrief (refined)

- Zeek on the OT SPAN; `conn.log` shows the whole attack only as **plain TCP to 2404** (no IEC-104 analyzer loaded).
- **Sharper lesson than "unknown source":** the EW *legitimately* talks to the RTU for engineering **reads** — so the anomaly is not the source alone, it's that the EW issued a **control command** (breaker open), which it never does; **operators issue control from the HMI**. Detection is about **action type × source**, i.e. context, not protocol decoding alone. Even a loaded 104 analyzer would see a *valid* command.

---

## 7. Component roster vs. the real malware (for the debrief slide)

| Industroyer component | In this demo |
|---|---|
| Main backdoor + C2 | External node as C2; staged implant beacons home (narrated) |
| Additional backdoor | Narrated (optional) |
| Launcher | The "drop + launch payload on EW" beat |
| Port scanner | The nmap recon beats in Stage 1 |
| IEC-104 payload | **Live** — staged config, interrogation, `C_SC_NA_1`, range-mode sustained commanding |
| IEC-101 / 61850 / OPC DA payloads | Narrated / roster-stub line |
| Data wiper | **Live (symbolic, scratch-volume only)** on the HMI |
| SIPROTEC DoS (CVE-2015-5374) | **Not demoed** — one slide bullet (only true exploit in the kit) |

---

## 8. Open build details (not design decisions)
- Exact hop wiring and which credential/key sits on which host.
- `c104-server` needs to expose interrogation + the breaker status/control points for the loud payload output; add a couple of measured values (`M_ME_*`) if you want the HMI/physics to show current/voltage collapsing, not just a flag.
- `process-sim` should expose a terminal/CLI readout of feeder state (energized/dark, %, A, kV) in addition to its web UI.
- Wiper implementation specifics (which dummy dir, which "extensions" to enumerate for effect) and the scratch-volume mount.
- Whether to run the optional SambaCry stretch and/or the multi-protocol roster line.

---

## 9. Relationship to other docs
- Refines `ics-scenario-b2-industroyer-purdue.json` (the current build); supersedes its `breaker open` wrapper and `while`-loop recovery-denial.
- Builds on `ics-scenario-b-industroyer-plan.md` (topology, firewall policy, weakness model) — still valid except as noted here.
- Container build guidance stays in `ics-dockerfiles-build-guide.md`; new/changed images this implies: an **external/C2 node**, a **staged IEC-104 payload** in the attacker toolkit, a **wiper** behavior on the HMI image, MariaDB cred-dump + SSH-key loot on the historian image, and a Local-mode-free `c104-server` that honors interrogation and a verbose control path.
