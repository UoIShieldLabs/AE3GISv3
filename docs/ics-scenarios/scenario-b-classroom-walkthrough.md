# Scenario B — classroom walkthrough (IEC‑104 / Industroyer)

A direct, step‑by‑step guide to **set up, deploy, and present** Scenario B with the
scenario runner. Design, node roles and the full attack chain are in
[`ics-scenarios-agent-guide.md`](./ics-scenarios-agent-guide.md); this is the operator's
script for running it live in front of a class.

**What you demonstrate:** an IT foothold pivots through a dual‑homed host into the OT
network and sends one *unauthenticated, perfectly legal* IEC‑104 command that opens a
breaker — no exploit, no malware. The lab runs **fully offline inside Kathará**; every
step is standard admin tooling (`nmap`, `ssh`) or an ordinary protocol client. The one
"destructive" step writes only to a scratch path **inside a single container** — the
runner adds no host mounts, so containment holds.

> **Read "Confirm before class" (last section) first.** Two things depend on your
> `tollan/*` images (the exact IEC‑104 client call, and how you show the process view),
> and you should pre‑warm images well before students arrive.

---

## Part 0 — Before class (do this ahead of time)

Image sync and the first deploy are slow (Docker Hub anonymous pulls are rate‑limited,
and the OVS/tools images build locally). Run Parts 1–3 **once the day before**, leave the
scenario authored and saved, then `Destroy` and re‑`Deploy` just before presenting.

---

## Part 1 — Start AE3GIS and open the UI

1. In the project root: `./start.sh` (brings up frontend **:3000**, backend **:8000**).
2. Open **http://localhost:3000** → the **Topology library**.

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

## Part 4 — Author the scenario in the runner

The **Scenario runner** turns the attack chain into click‑through steps, each showing its
command and live output. Open it: **More → Scenario runner…** (or ⌘K → "Scenario runner").

> **How the runner executes:** each step runs **one command directly inside the node you
> pick** (`docker exec`), streaming its output. It does *not* carry a shell session
> between steps. So the SSH pivot below is run from `attacker` to *demonstrate* that reuse
> works; the OT actions are then authored to run **on the `historian` node directly**,
> which is exactly where the real attacker would be running them.

Click **New scenario**, name it *Industroyer walkthrough*, then **+ Phase** and **Add
step** to build the phases below. For each step pick the **node** and type the **command**.

> Steps marked **«image»** depend on the client your `tollan/c104-*` images ship — put the
> real invocation in (see "Confirm before class"). Everything else is standard tooling.

**Phase 1 — Recon & boundary (S1–S2)**
| # | Node | Command | Teaches |
|---|------|---------|---------|
| 1 | `attacker` | `nmap -sn 10.0.5.0/24` | finds the historian at `10.0.5.20` on IT‑LAN |
| 2 | `attacker` | `nmap -Pn -p 2404 10.0.3.50` | **blocked at the firewall** — segmentation holds from IT |
| 3 | `attacker` | `sshpass -p pass ssh -o StrictHostKeyChecking=no root@10.0.5.20 'hostname; ip -o addr show'` | reused creds → lands on the historian; shows it is dual‑homed (**«image»**: needs `sshpass`+creds in the attacker image, else narrate and skip to Phase 2) |

**Phase 2 — Reach & command the process (S3–S4)**
| # | Node | Command | Teaches |
|---|------|---------|---------|
| 1 | `historian` | `nmap -Pn -p 2404 10.0.3.50` | from the historian the RTU **is** reachable — no firewall in the path |
| 2 | `historian` | **«image»** IEC‑104 control: send a single/double command (C_SC_NA_1 / C_DC_NA_1) to the breaker IOA on `10.0.3.50:2404`, state → **open** | *one legal command* trips the breaker — the thesis |

**Phase 3 — Loss of View (S5)**
| # | Node | Command | Teaches |
|---|------|---------|---------|
| 1 | `historian` | **«image»** sever/monopolize the HMI's `2404` session to the RTU | the HMI freezes on its last reading while the process stays tripped |

**Phase 4 — Recovery denial, contained (S6)**
| # | Node | Command | Teaches |
|---|------|---------|---------|
| 1 | `historian` | `mkdir -p /scratch && dd if=/dev/zero of=/scratch/eng_backup.img bs=1M count=20 && rm -f /scratch/eng_backup.img` | models wiping recovery tooling — **writes only inside this container's own layer**, never a host or shared path |

**Phase 5 — Detection & debrief (S7)**
| # | Node | Command | Teaches |
|---|------|---------|---------|
| 1 | `ids` | **«image»** read the Zeek logs (e.g. `cat /usr/local/zeek/logs/current/conn.log \| tail`) | the recon is visible; **IEC‑104 parsing is thin** in open tooling — the detectability gap is itself a finding |

**Then click Save** (top bar). The scenario is stored with the topology. The **Run
phase** / **Run step** buttons enable only when the lab is **deployed** and there are **no
unsaved edits** — the runner executes what was deployed.

---

## Part 5 — Present it

Baseline first. **SHOW** the process view: select `process-sim` → inspector →
**Web UI → Open web UI** (its page loads in the dock; fullscreen the dock for the
projector). Do the same for `hmi`. Breaker closed, city powered, HMI green.

Walk the phases in order. For each, click **Run phase** (or **Run step** per row): a tab
opens with the command, its **streamed output** and an **exit** badge.

- **Phase 1** — SAY: "Our foothold is on IT." Step 2 times out/filtered → **"segmentation
  is doing its job from here."** Step 3 lands on the historian and prints two IPs →
  **"…but this host has a foot in both networks."**
- **Phase 2** — the same scan from the historian succeeds. Then the control command. SHOW
  the **process view flip** to breaker‑open / city dark. SAY: **"No exploit. A legitimate
  protocol command. The protocol has no authentication, so reachability *is* control."**
- **Phase 3** — run the session‑sever step; SHOW the HMI **still green** beside the dark
  process view: *loss of view.*
- **Phase 4** — the contained wiper; note the write stays inside the container.
- **Phase 5** — open the IDS output; contrast IEC‑104's thin coverage with Modbus (A).

If a long step (Phase 3) needs to keep running while you talk, leave its tab open — it
streams until it exits or hits the per‑step cap; use **Stop** on the tab when done.

## Part 6 — Reset

**Destroy** (top bar) returns to a clean, idle topology; captures/runs are stopped first.
**Deploy** again for the next run. The scenario you authored stays saved with the topology.

---

## Confirm before class (the two image‑dependent pieces + gotchas)

1. **The IEC‑104 client calls (Phase 2 step 2, Phase 3, and the Zeek read).** These are
   the **«image»** rows. Open a terminal on `plc` / `historian` / `ids` and confirm the
   actual client binary and syntax your `tollan/c104-server`, `c104-hmi` and `zeek` images
   ship, then paste the real command into those steps. The guide's §7/§9 is the reference.
2. **Showing the process / HMI view.** Now one‑click: inspector → **Open web UI**
   (the preset sets `process-sim`'s port to 8000 and `hmi`'s to 8080). The backend
   relays the node's page to the dock iframe. For a node whose port differs or isn't
   set, fill **Web UI → Port** in the inspector first. (The relay suits the simple
   Flask pages here; a complex app would still want an out‑of‑band port‑forward.)
3. **Tooling presence.** `nmap` must be in the `attacker` image; `sshpass` + reused creds
   are needed for Phase 1 step 3 (else narrate the pivot and run Phase 2 on `historian`
   directly — the demo still lands). Confirm the Zeek log path.
4. **Pre‑warm.** First registry sync + first deploy are slow; do Parts 1–3 ahead of time.
5. **Run gating.** If a **Run** button is greyed out: the lab isn't deployed, or you have
   unsaved edits — click **Save**. The runner always runs the *deployed* topology.
6. **Fragility.** Per the guide, the IEC‑104 session‑sever (Phase 3) is the most delicate
   step to run live — rehearse it and keep a recorded fallback.
