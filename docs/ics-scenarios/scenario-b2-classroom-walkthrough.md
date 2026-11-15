# Scenario B2 — classroom walkthrough (Purdue / DMZ Industroyer)

A direct, step-by-step guide to **set up, deploy, and present** the revised Scenario B — a
Purdue-aligned IEC-104 / Industroyer lab with an Industrial DMZ and two firewalls. The design
rationale is in [`ics-scenario-b-industroyer-plan.md`](./ics-scenario-b-industroyer-plan.md); this is
the operator's script for running it live. The simpler flat-topology Scenario B
([`scenario-b-classroom-walkthrough.md`](./scenario-b-classroom-walkthrough.md)) still ships as a
beginner on-ramp — B2 is the advanced version.

**What you demonstrate:** defense-in-depth that *held* against every direct path — two firewalls, a
DMZ, no office→plant route — yet was defeated by a **chain of weak links**. An attacker on an IT IoT
box hops `iot → it-fileserver (SMBv1 + reused creds) → gateway → historian (loots a reused OT
credential) → ew`, lands inside OT past both firewalls, and sends **one legitimate IEC-104 command**
that trips a breaker — then denies recovery. No exploit, no malware; every action is standard admin
tooling (`nmap`, `smbclient`, `ssh`) or an ordinary IEC-104 client. The lab runs **fully offline
inside Kathará**.

> This preset uses **rebuilt `tollan/*` images** (see Part 0). Pre-warm them well before class — the
> first sync and deploy are slow, and the `tollan/smb` image compiles Samba from source.

---

## Part 0 — Before class (do this ahead of time)

**This scenario depends on updated container images.** Build and publish these from the
`AE3GIS-containers` repo (then let AE3GIS pull them), or confirm they are already on the `tollan`
namespace:

| Image | New version | Change |
|---|---|---|
| `tollan/malicious-client` | v0.9 | adds `smbclient` (the IoT attacker box) |
| `tollan/smb` | v0.2 | adds `sshpass`/`ssh` + a reused SMB credential (`root/pass`) |
| `tollan/ftp-server` | v0.4 | adds `sshpass`/`ssh` (DMZ gateway pivot) |
| `tollan/mariadb` | v0.3 | adds `sshpass`/`ssh` + a planted `/etc/ot-collector/collector.conf` (lootable OT credential) |
| `tollan/process-sim` | v0.3 | richer projector: ENERGIZED/DARK + powered % · current · voltage |

```bash
# in AE3GIS-containers (needs docker login to the tollan namespace)
scripts/publish.sh malicious-client smb ftp-server mariadb process-sim
```

The `smb` build is the slow one (Samba from source on ubuntu:16.04). Image sync and first deploy are
also slow (Docker Hub anonymous pulls are rate-limited; the OVS/tools images build locally). Run
Parts 1–3 **once the day before**, leave it saved, then `Destroy`/`Deploy` just before presenting.

---

## Part 1 — Start AE3GIS and open the UI

1. In the project root: `./start.sh` (frontend **:3000**, backend **:8000**), or
   `cd frontend && npm run dev` for the Vite dev server on **:5173**.
2. Open the UI → the **Topology library**. The title-bar **Deploy / status** area is your
   "is it running" indicator all session; click the status badge for job steps and logs.

## Part 2 — Load the scenario and add its registry

1. Library page → **Presets** → **Use preset** *ICS Scenario B2 — IEC-104 / Industroyer (Purdue +
   DMZ)*. It opens as four subnets — IT-LAN `10.0.5.0/24`, DMZ-LAN `10.0.4.0/24`, OT-LAN
   `10.0.3.0/24`, PROCESS `10.0.1.0/24` — with 15 nodes.
2. A banner appears: *"This scenario uses images from Docker Hub namespace `tollan` — not added
   yet."* Click **Add & sync**. Syncing is **required** here: the OT switch's SPAN mirror to the IDS
   only works once the `tollan/open-vswitch` image's labels are known.
3. The images banner then lists anything to build or pull — click **Build now** to pre-warm, or let
   **Deploy** handle it.

**CHECK:** run **Layout → Purdue** (or `L`) — the subnets stack IT → DMZ → OT → PROCESS top to
bottom, with the firewalls in the DMZ band.

## Part 3 — Deploy and verify it's up

1. Top bar → **Deploy**. Watch the badge step through `validate → images → plan → deploy → verify`.
2. **CHECK it's live:** every device card turns green. Click the badge for per-step logs if anything
   stalls.
3. **CHECK segmentation + routing (optional, convincing):** double-click `iot` → terminal →
   `nmap -Pn -p 2404 10.0.3.50` is **filtered** (office can't reach the plant). On `historian`,
   `ip route` shows `default via 10.0.4.1`; after the tutorial's setup cell, `nmap -Pn -p 2404
   10.0.3.50` from `historian` is **open**.
4. **CHECK the SPAN works (optional):** on the `ot-sw ↔ ids` link (or the `ids` node) → **Start
   capture**; you should see HMI↔RTU IEC-104 traffic the IDS is mirrored.

---

## Part 4 — Run the tutorial

Open **More → Tutorials… → Industroyer across the Purdue model** (or ⌘K → "Tutorials"). It's a
notebook of Markdown notes + command cells; **Run step** / **Next step** types each command into the
target node's own terminal. Running needs a **deployed** lab with **no unsaved edits** (click **Save**
first if a Run button is greyed out).

> **How the cells chain:** each command is typed into the node's terminal. The attack cells all run in
> the **`iot`** terminal — once a cell SSHes into the next host, the cells that follow run **there**.
> So the single `iot` terminal walks the whole chain `iot → it-fileserver → gateway → historian → ew`.
> The **setup** cells run on `fw-it`, `fw-ot` and `ids`; the **detection** cell runs on `ids`.

The tutorial's own Markdown narrates every act; the structure is:

| Act | Where | What it shows |
|---|---|---|
| 1 Setup | `fw-it`, `fw-ot`, `ids` | arm the two allowed firewall flows; start Zeek on the OT SPAN |
| 2 Baseline | HMI / process-sim web UIs | breaker CLOSED, feeder ENERGIZED; operator controls from the HMI |
| 3 Foothold | `iot` | identity + ping-sweep the office LAN → finds `it-fileserver` |
| 4 File server | `iot` | `smbclient` to the SMBv1 share with reused creds, then SSH shell on it |
| 5 Into the DMZ | `iot`→`it-fileserver` | direct plant scan **dropped**; SFTP/SSH pivot to the `gateway` |
| 6 Loot | `iot`→`gateway`→`historian` | read `collector.conf` → a reused OT credential |
| 7 Pivot to OT | `iot`→`historian` | historian's over-broad OT rule → SSH to the `ew` |
| 8 Reach RTU | `iot`→`ew` | `breaker status` → CLOSED; the control port is open from here |
| 9 Trip | `iot`→`ew` | `breaker open` → HMI flips OPEN·red, process-sim goes DARK |
| 10 Loss of control | `iot`→`ew` + HMI | operator closes from HMI; attacker re-trip loop overrides every close |
| 11 Detection | `ids` | the trip shows only as TCP to `:2404`; the tell is the **source** (the EW) |

---

## Part 5 — Present it

Baseline first. **SHOW** both views: select `process-sim` → **Open web UI** (ENERGIZED · 100% · ~420 A
· 11 kV) and `hmi` → **Open web UI** (breaker CLOSED · green); fullscreen the dock for the projector.

Then walk the tutorial in order. Narration beats:

- **Setup/baseline** — SAY: "Textbook segmentation: a DMZ, two firewalls, *no* office→plant path. Only
  two narrow flows are allowed." Click **Open/Close** on the HMI to show normal authorized control.
- **The chain (acts 3–7)** — each pivot is one weak link: an SMBv1 file server, a reused password, an
  over-broad historian rule, a looted credential. SAY at the dropped scan: **"The firewall is doing its
  job — from here."** At the EW shell: **"…but the attacker went *around* it, not through it."**
- **Trip (act 9)** — SHOW the **HMI flip to OPEN** and the **feeder go DARK (0%)**. SAY: **"No exploit.
  A legitimate protocol command. The protocol has no authentication, so reachability *is* control."**
- **Loss of control (act 10)** — run the loop, then **click Close on the HMI**: it snaps back to OPEN.
  SAY: **"The operator has lost control."** Press **Ctrl-C** in the `iot` terminal to stop; Close holds
  again.
- **Detection (act 11)** — the control shows only as TCP to `:2404`, sourced from the **EW**. Contrast
  protocol-blind monitoring with context/behavioural detection (which host should *ever* command the
  RTU?).

A long step (the re-trip loop) keeps running while you talk — leave its tab open and **Ctrl-C** when
done.

## Part 6 — Reset

**Destroy** (top bar) returns to a clean, idle topology; captures/runs are stopped first. **Deploy**
again for the next run. Your tutorial stays saved with the topology.

---

## Confirm before class (pre-checks + gotchas)

1. **Images are rebuilt and published.** The chain needs `smbclient` on `iot`, `sshpass`/`ssh` on the
   `smb`/`ftp-server`/`mariadb` hosts, and the planted `collector.conf` on the historian — all from
   the updated image versions in Part 0. If a pivot cell fails with "command not found", the node is
   running an old image; re-sync `tollan` and redeploy.
2. **Sync `tollan` before deploying** — the OT SPAN to the IDS depends on it (the `ownBridge` label).
   Without it the IDS sees nothing and act 11 is empty.
3. **The firewall rules are inserted by the tutorial's setup cells**, not baked — run act 1 before the
   attack, or the DMZ-crossing pivots will be dropped. (Re-running them after a `Destroy`/`Deploy` is
   required each run.)
4. **Showing the process / HMI view.** One click: inspector → **Open web UI** (`process-sim` port
   8000, `hmi` 8080); the backend relays the page to the dock iframe. Fullscreen for the projector.
5. **Run gating.** A greyed-out **Run** button means the lab isn't deployed or you have unsaved edits —
   click **Save**. The tutorial always runs the *deployed* topology.
6. **IEC-104 detection depth.** This Zeek has no IEC-104 analyzer (the community Spicy analyzers don't
   yet build against Zeek LTS), so live detection is "TCP to 2404" only. That gap — and the fact that
   even a decoded command is *valid* — is itself the finding; the realistic defensive win is
   context/behavioural detection (an unexpected source commanding the RTU).
7. **Slow `smb` rebuild fallback.** If you skip rebuilding `tollan/smb`, the `it-fileserver → gateway`
   pivot (act 5) has no `sshpass`; type the one `ssh root@10.0.4.20` password (`pass`) by hand when
   prompted in that terminal.
