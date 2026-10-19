# ICS Attack-Scenario Lab — Implementation Reference

**Project:** AE3GIS · **Platform:** Kathará (Docker-based network emulation) · **Audience:** an implementing agent with access to the AE3GIS lab

---

## 0. How to use this document

This is a reference for building and running two ICS attack scenarios in the AE3GIS Kathará lab. It describes the agreed design: the shared topology, what each node does, and the ordered steps of each scenario. It is deliberately not a line-by-line script. Where it says to write a client, a PLC program, or a simulator, implement it with whatever library and style fits, and research current tool details (pymodbus APIs, the IEC-104 stack, OpenPLC's program format, ScadaBR's data-source UI, Zeek's ICS analyzers) as needed. The AE3GIS container repo (`UoIShieldLabs/ae3gis-containers`) provides most base images; the Dockerfiles can be extended, and new containers can be added where noted. Treat IP addresses, register numbers, and command shapes as a working baseline you may adjust, as long as the behaviour each step is meant to demonstrate is preserved.

The two scenarios share one topology and one attack chain. Only the OT protocol and the two containers that speak it change. Build Scenario A (Modbus) first; it reuses the most existing components. Scenario B (IEC-104) is the same lab with the field device, console, and client swapped.

---

## 1. Purpose and containment

The lab reproduces, at the level of technique, two real attacks that cross from an IT foothold down to a physical process: the 2016 Ukraine grid attack (Industroyer) and the 2024 Lviv heating attack (FrostyGoop). The teaching thesis is that both worked for the same reason: legacy OT control protocols have no authentication, so network reachability equals control.

This is an educational lab. It implements the attacks, not the defenses; the mitigations are discussed in the debrief, not configured in the topology. Keep it within these boundaries:

- Runs fully offline inside Kathará, with no bridge to any real or external network.
- No real malware. Every attacker action is an ordinary, legitimate ICS client operation (protocol reads/writes) or standard admin tooling (ssh, nmap). The point is that no exploit is needed, because the protocols are unauthenticated by design.
- All weaknesses are planted or simulated (reused credentials, a dual-homed host, no protocol auth), not live CVEs against real software.
- The "wiper" step writes only to an isolated scratch volume inside a single container, never a mounted host path or shared lab directory.
- The lab resets to a clean baseline with `kathara lclean && kathara lstart`.

---

## 2. The two scenarios at a glance

| | Scenario A | Scenario B |
|---|---|---|
| Reference incident | FrostyGoop (Lviv, Jan 2024) | Industroyer / CrashOverride (Ukraine, Dec 2016) |
| OT protocol | Modbus TCP (port 502) | IEC 60870-5-104 (port 2404) |
| Field device container | `openplc` | custom `c104-server` |
| Operator console container | `scadabr` | custom `c104-hmi` |
| Attacker command tool | `pymodbus` (or equivalent) | `c104` / lib60870 client |
| Physical effect | heating output forced off | breaker opened, outage |
| Loss of View mechanism | spoof the status register the HMI reads | sever/hijack the HMI's protocol session |
| Open-source IDS coverage | strong (mature Modbus analyzers) | thinner (IEC-104 needs an add-on) |

Everything else is identical between them.

---

## 3. Shared architecture

### 3.1 Segments (Kathará collision domains)

| Segment | Subnet | Purdue level | Switch |
|---|---|---|---|
| IT-LAN | 10.0.5.0/24 | L4 Enterprise | plain collision domain |
| OT-LAN | 10.0.3.0/24 | L3/L2 Supervisory | managed (`open-vswitch`) with a SPAN/mirror port to the IDS |
| PROCESS | 10.0.1.0/24 | L1/L0 Process | plain collision domain |

A Kathará collision domain is a learning bridge, so it will not copy unicast traffic to a passive IDS port. OT-LAN therefore needs an explicit managed switch (the repo's `open-vswitch`) with port mirroring to the IDS. IT-LAN and PROCESS can be ordinary collision domains. If mirroring proves troublesome, the fallback is to run the IDS inline as the OT gateway, but the SPAN approach is cleaner.

### 3.2 Nodes and interfaces

Same for both scenarios; only the PLC and HMI images differ.

| Node | Container (A / B) | eth0 | eth1 | Notes |
|---|---|---|---|---|
| `attacker` | `malicious-client` | IT-LAN 10.0.5.10 | — | foothold; nmap and recon tooling; default route via `fw` |
| `fw` | `nftables` | IT-LAN 10.0.5.1 | OT-LAN 10.0.3.1 | routes and filters IT↔OT; default-deny IT→OT, allow only SSH to the historian |
| `historian` | dedicated node: a historian DB (InfluxDB or MySQL) + sshd | IT-LAN 10.0.5.20 | OT-LAN 10.0.3.20 | dual-homed pivot; **IP forwarding OFF**; carries the scenario's client library |
| `plc` | `openplc` / `c104-server` | OT-LAN 10.0.3.50 | PROCESS 10.0.1.50 | dual-homed field device; serves the OT protocol on the OT leg |
| `hmi` | `scadabr` / `c104-hmi` | OT-LAN 10.0.3.30 | — | operator console; default route via `fw` |
| `ids` | `suricata` + `zeek` | OT-LAN 10.0.3.40 | — | attaches to the OVS mirror port; passive |
| `process-sim` | custom Flask app | PROCESS 10.0.1.10 | — | reads the PLC's true output; renders the physical state for the projector |

Interface-count rule for whoever wires it: `attacker`, `hmi`, `ids`, `process-sim` have one NIC each; `fw`, `historian`, `plc` have two. Give raw-socket/forwarding nodes `NET_ADMIN`.

### 3.3 Routing (this makes the pivot demonstrable)

- `attacker` and `historian` both sit on IT-LAN, so the attacker reaches the historian over SSH **without crossing the firewall**. This is intended.
- The firewall only sits on the path from IT-LAN toward OT-LAN. IT hosts' default route points at `fw` (10.0.5.1), so a direct attempt from `attacker` to the PLC at 10.0.3.50 travels to `fw` and is dropped there. That dropped scan is the visible proof of segmentation.
- The historian has its own leg inside OT-LAN, so from the historian the PLC is reachable with no firewall in the path. This is the segmentation failure the lab exists to show.
- Keep IP forwarding **off** on the historian. The attacker lands on it over SSH and runs the OT tools locally from its OT interface. If forwarding were on, the historian would silently become a second router around the firewall and blur the lesson.

### 3.4 Planted weaknesses

1. **Reused credentials** across hosts (the repo images default to `root:pass`), enabling the SSH pivot.
2. **Dual-homed historian** bridging IT and OT, bypassing the firewall.
3. **Unauthenticated OT protocol** on the field device: it executes any well-formed request on its port. No exploit, no CVE.

---

## 4. The register / view model (enables Loss of View)

For the operator-deception step to work, the value the HMI *displays* must be a separate point from the value that *actuates* the process. Design the field device with two points:

- **Control/output point** — the attacker writes this to cause the physical effect; `process-sim` reads this as ground truth.
- **Status-mirror point** — what the HMI displays. Under normal operation it tracks the control point so the two agree.

With the points decoupled, the attacker acts on the control point and then separately holds the status-mirror point at "normal," so the console keeps showing a healthy process while the real one is tripped. If decoupling turns out to be awkward on a given device (see the OpenPLC note in 6.1), the fallback is to disrupt the HMI-to-device polling so the console freezes on its last-good reading. Scenario A uses the two-register spoof as primary; Scenario B uses the severed-session approach because IEC-104 is session-based.

---

## 5. Shared attack chain (S0–S7)

Each step is stated as goal → what happens. Protocol-specific details are in Sections 6 and 7.

- **S0 — Baseline.** Bring the lab up clean. Project two views: `process-sim` showing the physical state nominal, and the HMI showing green. This is the reference for the run.
- **S1 — Initial access (L4).** The attacker starts on the IT host with an assumed foothold (phishing is narrated, not executed) and runs host discovery on IT-LAN to locate the historian.
- **S2 — Pivot IT→OT.** The attacker SSHes into the dual-homed historian with reused credentials. Demonstrate the boundary: a direct scan from the attacker to the PLC fails at the firewall, while the same scan from the historian succeeds. All OT-facing actions now originate from the historian.
- **S3 — OT discovery.** From the historian, scan OT-LAN and identify the field device by its open control port (502 for A, 2404 for B).
- **S4 — Command the process (L1→L0).** From the historian, issue one unauthenticated control command with a legitimate client library. The `process-sim` diverges from nominal within a second or two.
- **S5 — Loss of View (L2).** Make the HMI keep showing normal while the process stays tripped (mechanism per scenario). The projector and the console now disagree.
- **S6 — Recovery denial (wiper).** On the compromised control host, overwrite files on an isolated scratch volume inside that one container, modelling destruction of recovery/engineering tooling. Never touch a host path or shared directory.
- **S7 — Detection & debrief.** Review the IDS output, then map the chain onto the Purdue model and discuss the real-world mitigations.

---

## 6. Scenario A — Modbus / FrostyGoop

### 6.1 Components and setup

- **Field device — `openplc` (10.0.3.50).** OpenPLC serves Modbus TCP on 502 and a web editor on 8080. Important: OpenPLC runs no logic until a PLC program is loaded and started through the web UI, so it does not auto-start. Prepare a small program that exposes the two Modbus points from Section 4: a control point (coil or holding register) representing the heating output, and a separate status-mirror register the HMI reads. For a hands-off demo, arrange for the program to be loaded and running at baseline (export it and script the load, or document the one-time UI step), and make sure the status-mirror register is independently writable rather than recomputed from the control point every scan, or the LOV spoof in S5 will not hold.
- **Operator console — `scadabr` (10.0.3.30).** ScadaBR's installer is interactive, so complete the install once and commit the result as a ready image rather than installing at runtime. Configure a Modbus-IP data source pointing at `openplc:502` and bind a display data point to the status-mirror register. Add a simple graphical view showing heat on/off or temperature.
- **Attacker tooling.** Put a Modbus client (pymodbus or equivalent) on the historian. The `malicious-client` image does not ship one, so install it in the historian image or a venv.
- **process-sim (10.0.1.10).** Poll the PLC's control point over Modbus (a function-code-3 read of the control register) and render the physical state (for example, supply temperature falling once the output is zeroed). Expose the web view to the host for the projector.

### 6.2 Step specifics

- **S3.** From the historian, scanning OT-LAN reveals `openplc` with 502 (and 8080) open.
- **S4.** Use the Modbus client to write the control register, setting the heating output to zero (a write-single-register / write-multiple-registers call, FC6/FC16). `process-sim` shows the temperature dropping. The HMI may also react here; that is expected until S5 corrects the operator's view.
- **S5.** Send a second write to the status-mirror register, holding it at the nominal value. Because the display point and the control point are separate, ScadaBR keeps reporting normal while the process stays off.
- **S7.** Zeek has a mature Modbus analyzer, so the register writes appear in `modbus.log` with the historian as the source; Suricata surfaces the earlier nmap/ICMP recon. This clean detection is the point of comparison with Scenario B.

### 6.3 Verification checkpoints

Baseline shows heat on and the HMI green. After S4, `process-sim` shows the process tripping. After S5, `process-sim` still shows it tripped while ScadaBR shows normal. The IDS log contains the Modbus writes attributed to the historian's IP.

---

## 7. Scenario B — IEC-104 / Industroyer

### 7.1 Components and setup

- **Field device — custom `c104-server` (10.0.3.50).** No off-the-shelf IEC-104 device exists in the repo, so build a small one around an open IEC-104 stack (lib60870 or the `c104` Python library). Model it as a substation RTU exposing IEC-104 on TCP 2404, with one breaker object: a monitored point reporting breaker state (closed/open) that both the HMI and `process-sim` read, and a command point that accepts a control command to change that state. Start closed.
- **Operator console — custom `c104-hmi` (10.0.3.30).** An IEC-104 client that subscribes to the RTU and displays the breaker point (green when closed). A minimal web or terminal view is fine.
- **Attacker tooling.** Put an IEC-104 client library on the historian for issuing the command in S4.
- **process-sim (10.0.1.10).** Read the RTU's monitored point via IEC-104 interrogation and render breaker state and a "powered %" for the city.

### 7.2 Step specifics

- **S3.** From the historian, scanning OT-LAN reveals the RTU with 2404 open.
- **S4.** Use the IEC-104 client to send a control command (single/double command, e.g. C_SC_NA_1 / C_DC_NA_1) to the breaker's information object address, switching it to open. `process-sim` shows the breaker open and the powered percentage dropping to zero.
- **S5.** Because IEC-104 is session-based, blind the operator by severing or hijacking the HMI's connection to the RTU (disrupt or monopolize the 2404 session) so the console stops updating and holds its last reading. The city reads dark on the projector while the HMI still shows the breaker green.
- **S7.** IEC-104 coverage in open-source tooling is thinner than Modbus: Zeek needs an add-on analyzer to parse it and Suricata's visibility is limited. The recon alerts still fire. The detectability gap versus Scenario A is itself a finding. (Verify the current state of Zeek/Suricata IEC-104 support when writing the debrief.)

### 7.3 Verification checkpoints

Baseline shows the breaker closed and the city powered, HMI green. After S4, `process-sim` shows the blackout. After S5, the HMI still shows green while `process-sim` shows the city dark. The IEC-104 session handling is the most fragile part to run live, so confirm a clean repeatable run and keep a recorded fallback.

---

## 8. Build and run order

1. **Images.** Build/commit the shared images. Complete ScadaBR's interactive install and commit it (Scenario A). Prepare and export the OpenPLC program so the device comes up with logic running (Scenario A). Build the `c104-server` and `c104-hmi` images (Scenario B). Add the Modbus / IEC-104 client libraries to the historian image.
2. **Topology.** Lay down the Kathará `lab.conf` wiring the three collision domains per Section 3, with per-node `.startup` files carrying service start-up (the repo images are GNS3-oriented, so startup moves into `.startup`). Configure the `open-vswitch` node on OT-LAN with a mirror port to the IDS. Grant `NET_ADMIN` where needed. Set the default routes and keep historian forwarding off.
3. **Select the scenario** by choosing the `plc`/`hmi` images and the `process-sim` render mode.
4. **Run.** `kathara lstart`, verify S0 on the projector, then walk S1→S7.
5. **Reset between runs.** `kathara lclean && kathara lstart` returns a clean baseline.

---

## 9. What the implementing agent should decide or research

- Exact register map for OpenPLC (addresses, coil vs holding register) and how to keep the status-mirror register independently writable.
- The OpenPLC program-load approach for a hands-off baseline (scripted import vs documented one-time UI step).
- The IEC-104 server/client implementation details: library choice, object/IOA layout, and the cleanest way to sever the HMI session for S5.
- The `open-vswitch` mirror configuration in the Kathará context, or the inline-IDS fallback.
- Current Zeek/Suricata ICS analyzer coverage, for accurate S7 claims.
- The attacker command execution style: run tools interactively on the historian (baseline) or via an SSH port-forward from the attacker box, whichever demonstrates better.

---

## 10. Reference incidents

- **Industroyer / CrashOverride** (Ukraine, Dec 2016): unauthenticated IEC-104 commands opened substation breakers; roughly an hour-long outage affecting part of Kyiv. Associated wiper tooling prolonged recovery.
- **FrostyGoop** (Lviv, Jan 2024): unauthenticated Modbus register writes against heating controllers left around 600 buildings without heat for roughly two days.

Both are attributed to the same class of root cause — an unauthenticated OT protocol reachable across a weak IT/OT boundary — which is the lab's thesis. The implementing agent should verify specifics against current public reporting (for example Dragos, ESET, and CISA material) where accuracy matters for the debrief.
