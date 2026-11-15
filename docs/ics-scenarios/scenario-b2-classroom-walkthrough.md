# Scenario B2 — classroom walkthrough (Industroyer case study)

A step-by-step guide to **set up, deploy, and present** the B2 scenario: a faithful case study of the
2016 Ukraine / **Industroyer (CrashOverride)** incident, structured on the **ICS Cyber Kill Chain**.
The locked design is in
[`ics-scenario-b2-industroyer-locked-spec.md`](./ics-scenario-b2-industroyer-locked-spec.md); this is
the operator's script for running it live. The simpler flat-topology Scenario B
([`scenario-b-classroom-walkthrough.md`](./scenario-b-classroom-walkthrough.md)) still ships as a
beginner on-ramp — B2 is the advanced, case-study version.

**What you demonstrate.** Two stages, treated differently on purpose:

- **Stage 1 — Intrusion (representative).** An external adversary crosses an internet edge, enterprise
  IT, an industrial DMZ, and into OT — `external → iot → it-fileserver → gateway → historian → ew` —
  using **four real techniques** (weak-cred spray, SMBv1, MariaDB credential extraction, SSH-key theft)
  stitched by reused credentials. Defense-in-depth *held* against every direct path; a **chain of weak
  links** crossed it anyway.
- **Stage 2 — ICS Attack (faithful).** A staged **IEC-104 payload** on the EW trips the breaker and
  **sustains** the trip (loss of control); a symbolic **wiper** blinds the HMI (loss of view); recovery
  is **manual, on-site at the RTU**. The ending is the accurate 2016 outcome — recovered, but degraded.

Everything is benign, offline, container-only, ARM64-native: no real malware, no compiled-payload RCE.
The "payload" is an ordinary IEC-104 client that narrates the real protocol; the "wiper" only touches a
scratch directory inside one container.

> This preset uses **rebuilt `tollan/*` images** (Part 0). Pre-warm them well before class.

---

## Part 0 — Before class (do this ahead of time)

**This scenario depends on updated container images.** Build/publish these from the `AE3GIS-containers`
repo (then let AE3GIS pull them), or confirm they are already on the `tollan` namespace:

| Image | Version | Change |
|---|---|---|
| `tollan/malicious-client` | v0.10 | `external`/`iot`: adds a staged IEC-104 payload + symbolic wiper in `/opt/ics`, `openssh-client` |
| `tollan/mariadb` | v0.4 | historian: seeds a `telemetry` DB with a planted `ot_credentials` table + a lootable OT SSH key; carries the payload for the EW drop |
| `tollan/ftp-server` | v0.5 | gateway: adds `mariadb-client` + a planted DB-report config (`/etc/filebroker/report.cnf`) |
| `tollan/benign-client` | v0.11 | EW: adds `openssh-client`/`sshpass` + trusts the OT engineering SSH key |
| `tollan/c104-server` | v0.2 | RTU: adds `M_ME` current/voltage measured values + a local `breaker` CLI (manual recovery) |
| `tollan/c104-hmi` | v0.3 | HMI: shows current/voltage; Flask runs as a child so the wiper can kill it; carries a dummy SCADA project |
| `tollan/process-sim` | v0.4 | projector reads current/voltage from the RTU; adds a `feeder` CLI readout |

```bash
# in AE3GIS-containers (needs docker login to the tollan namespace)
scripts/publish.sh malicious-client mariadb ftp-server benign-client c104-server c104-hmi process-sim
```

`tollan/smb` (v0.2, the slow Samba-from-source image) is **unchanged** — no rebuild needed. Image sync
and first deploy are slow (Docker Hub anonymous pulls are rate-limited); run Parts 1–3 **once the day
before**, then `Destroy`/`Deploy` just before presenting.

> **Lab-only secrets, by design.** The images deliberately bake weak secrets (`root/pass`, a throwaway
> OT SSH keypair, a DB creds table). These are planted teaching weaknesses for an offline lab — never
> reuse them anywhere real; naive secret scanners will flag the committed key on purpose.

---

## Part 1 — Start AE3GIS and open the UI

1. Project root: `./start.sh` (frontend **:3000**, backend **:8000**), or `cd frontend && npm run dev`
   (**:5173**).
2. Open the UI → **Topology library**. The title-bar **Deploy / status** area is your "is it running"
   indicator all session; click the status badge for job steps and logs.

## Part 2 — Load the scenario and add its registry

1. Library → **Presets** → **Use preset** *ICS Scenario B2 — Industroyer case study (Purdue + DMZ)*. It
   opens as five subnets — EDGE `198.51.100.0/24`, IT-LAN `10.0.5.0/24`, DMZ-LAN `10.0.4.0/24`, OT-LAN
   `10.0.3.0/24`, PROCESS `10.0.1.0/24` — with 17 nodes.
2. A banner appears: *"This scenario uses images from Docker Hub namespace `tollan` — not added yet."*
   Click **Add & sync**. Syncing is **required**: the OT switch's SPAN mirror to the IDS only works once
   the `tollan/open-vswitch` image's labels are known.
3. The images banner lists anything to build/pull — click **Build now** to pre-warm, or let **Deploy**
   handle it.

**CHECK:** run **Layout → Purdue** (or `L`) — EDGE/IT → DMZ → OT → PROCESS stack top to bottom, firewalls
in the boundary bands.

## Part 3 — Deploy and verify it's up

1. Top bar → **Deploy**. Watch the badge step through `validate → images → plan → deploy → verify`.
2. **CHECK it's live:** all 17 device cards turn green.
3. **CHECK segmentation (optional, convincing):** from `iot`'s terminal, `nmap -Pn -p 2404 10.0.3.50` is
   **filtered** (office can't reach the plant). `fw-it` carries three legs (`ip -o -4 addr` → IT, DMZ,
   EDGE) — it is both the IT/DMZ firewall and the internet perimeter.
4. **CHECK the SPAN (optional):** `ids` node → **Start capture** → you should see HMI↔RTU IEC-104
   traffic mirrored.

---

## Part 4 — Run the tutorial

Open **More → Tutorials… → Industroyer — an ICS kill-chain case study** (or ⌘K → "Tutorials"). Running
needs a **deployed** lab with **no unsaved edits** (click **Save** if a Run button is greyed out).

**One click to arm the lab:** press **Configure lab** at the top of the panel. It runs four headless
setup steps (perimeter + firewall rules on `fw-it`/`fw-ot`, Zeek on `ids`, the C2 listener on
`external`) and starts the **background traffic** (historian telemetry, the IT→DMZ file push, and the
IoT C2 beacon). Watch the canvas light up.

> **How the cells chain:** each command is typed into a node's terminal. The Stage-1/Stage-2 attack
> cells all run in the **`external`** terminal — once a cell SSHes onward, the cells that follow run on
> the next host, so the single terminal walks `external → iot → it-fileserver → gateway → historian →
> ew`. The **recovery** cell runs on `rtu` (on-site, local), and the **detection** cell on `ids`.

| Act | Where | What it shows |
|---|---|---|
| Configure lab | headless | arm perimeter + firewall flows, start Zeek, background traffic + C2 |
| Baseline (A0) | HMI / process-sim / `process-sim feeder` | breaker CLOSED, feeder ENERGIZED (100% · 420 A · 11 kV) |
| ① Foothold | `external` | weak-cred spray → SSH to the internet-exposed `iot`; tools staged; C2 beacon |
| ② SMBv1 | `external`→`iot` | office scan finds `it-fileserver`; plant scan **filtered**; `smbclient` + SSH pivot |
| Cross to DMZ | →`it-fileserver` | SSH to `gateway` over the one permitted IT→DMZ flow |
| ③ DB extraction | →`gateway` | dump the historian's `ot_credentials` table with the broker's DB creds |
| ④ SSH-key theft | →`historian` | loot the OT engineering key; **drop** the payload; key-login to `ew` |
| Trip | →`ew` | staged payload: interrogation → `C_SC_NA_1` OFF → HMI OPEN·red, current/voltage collapse, feeder DARK |
| Loss of control | `ew` + HMI | sustained range-mode commanding; the operator's HMI Close snaps back to OPEN |
| Loss of view | `ew`→HMI | the wiper destroys the SCADA project + kills the HMI service; its web UI goes down |
| Recovery | `ew` + `rtu` | evict the payload (isolate EW), then operate the breaker **locally at the RTU** |
| Detection | `ids` | the attack shows only as TCP to `:2404`; the tell is **action-type × source** (the EW) |

---

## Part 5 — Present it

Baseline first. **SHOW** both views: `process-sim` → **Open web UI** (ENERGIZED · 420 A · 11 kV) and
`hmi` → **Open web UI** (breaker CLOSED · green, with live current/voltage). Fullscreen the dock for the
projector. Narration beats:

- **Faithful vs. modeled** — open with the honesty contract (the tutorial's first cell): faithful = the
  breaker trip, sustained commanding, the wiper, manual recovery, external C2; modeled = initial access
  and lateral movement, one live protocol, Linux SCADA stand-ins.
- **Stage 1** — each hop is one real technique and one weak link. At the filtered plant scan: **"The
  firewall is doing its job — from here."** At the EW key-login: **"…they went *around* it, not through
  it."**
- **Trip** — SHOW the **HMI flip to OPEN** and both the HMI's and `process-sim`'s **current/voltage
  collapse to 0**. SAY: **"No exploit. A legitimate protocol command. No authentication, so reachability
  *is* control."**
- **Loss of control** — after the sustained-commanding cell, **click Close on the HMI**: it snaps back
  to OPEN. **"You can't out-click the malware."**
- **Loss of view** — run the wiper; the **HMI web UI dies** while `process-sim` (the out-of-band
  god-view) still shows the truth. The RTU is untouched — faithful.
- **Recovery** — evict the payload, then the **local RTU** cell re-energizes. **"You don't race ICS
  malware from the HMI — you remove it and fall back to manual."** End on the degraded-but-recovered
  note.
- **Detection** — the whole attack is only TCP to `:2404`, sourced from the **EW** — a host that reads
  the RTU but never commands it. Context, not protocol decoding.

## Part 6 — Reset

**Destroy** (top bar) returns to a clean, idle topology; captures/runs/background traffic are stopped
first. **Deploy** again for the next run. Your tutorial stays saved with the topology.

---

## Confirm before class (pre-checks + gotchas)

1. **All seven images are rebuilt/published** (Part 0). If a Stage-1 cell fails with "command not
   found", or the payload/wiper is missing, a node is on an old image — re-sync `tollan` and redeploy.
2. **Sync `tollan` before deploying** — the OT SPAN depends on it (`ownBridge` label); without it the
   IDS sees nothing and the detection act is empty.
3. **Press Configure lab before the attack** — the perimeter/firewall rules and Zeek are armed there,
   not baked. Re-run it after every `Destroy`/`Deploy`.
4. **Web UIs:** inspector → **Open web UI** (`process-sim` 8000, `hmi` 8080); the backend relays the
   page to the dock iframe. After the wiper, the HMI page stops responding — that's the point.
5. **SSH-chained cells show "sent", not live run-status** (OSC-133 markers don't survive an ssh). The
   sustained-commanding payload runs in the **background** on the EW; the recovery cell's `pkill`
   evicts it. If you launched it in the foreground instead, press **Ctrl-C** to stop it.
6. **IEC-104 detection depth.** This Zeek has no IEC-104 analyzer, so detection is "TCP to 2404" only —
   and even a decoded command is *valid*. That gap is the finding: the realistic win is
   context/behavioural detection (an unexpected source commanding the RTU).
7. **Local recovery** runs on the `rtu` node (`BREAKER_RTU=127.0.0.1 breaker close`) — the RTU image
   carries the `breaker` CLI for exactly this on-site manual step.
