# Scenario B3 — classroom walkthrough (Industroyer, four ways in)

A shorter, more intuitive companion to the detailed B2 case study. B3 keeps B2's faithful Stage-2
(IEC-104 trip / M_ME collapse / wiper / manual recovery) but rebuilds **Stage 1** so every IT→OT hop is
a **different** technique with a **different** credential — the "chain of distinct weaknesses" thesis made
literal. The long-form narrative stays in
[`scenario-b2-classroom-walkthrough.md`](./scenario-b2-classroom-walkthrough.md); use B3 when you want a
clean, teachable intrusion.

**What you demonstrate.** The attacker starts on a compromised IoT sensor and crosses
`iot → fileserver → gateway → historian → ew`, then trips the breaker:

| Hop | Weakness (distinct) | Credential (distinct) |
|---|---|---|
| iot → fileserver | a **default-cred spray that fails**, then a **writable SMB share** → drop our SSH key → key login | an SSH key *we* plant (no password) |
| fileserver → gateway | a **reused file-transfer service account** over the sanctioned SFTP channel | `svc-ft` |
| gateway → historian | **secrets in a database** (dump the creds table) | `histadmin` (dumped) |
| historian → ew | **SSH key sprawl** (the OT engineering key) | the stolen OT key |
| ew → rtu | **unauthenticated IEC-104** (reachability = control) | none needed |

The key teaching contrast: the spray **fails** (SSH is hardened), so SMB is the real vector; and credential
reuse is featured at exactly **one** hop (the service account), not as the lazy default everywhere.

Benign, offline, container-only, ARM64-native.

---

## Part 0 — Before class

B3 uses its **own image versions** (B2's are untouched). Build/publish from `AE3GIS-containers`, or confirm
they're on `tollan`:

| Image | Version | B3 role |
|---|---|---|
| `tollan/malicious-client` | v0.11 | iot: carries the dropped SSH key + a spray wordlist in /opt/ics |
| `tollan/smb` | v0.3 | fileserver: hardened root SSH, a guest-writable home-dir share (SMB key-drop), the `svc-ft` push config |
| `tollan/ftp-server` | v0.6 | gateway: the `svc-ft` service account + the reporting DB config |
| `tollan/mariadb` | v0.5 | historian: `histadmin` account + a creds table that yields it + the OT key |
| `tollan/benign-client` | v0.12 | ew: trusts the OT key; clean ssh config |

Reused unchanged from B2: `c104-server:v0.2`, `c104-hmi:v0.3`, `process-sim:v0.4`, `zeek`, `nftables`,
`open-vswitch`.

```bash
# in AE3GIS-containers (needs docker login to the tollan namespace)
scripts/publish.sh smb ftp-server mariadb malicious-client benign-client
```

> **Lab-only secrets by design:** distinct weak/planted credentials per host (`f1l3S3rv!`, `Tr4nsf3r!`,
> `H1st0r!an`, a throwaway SSH key). Teaching artifacts for an offline lab — never reused anywhere real.

---

## Part 1–3 — Start, load, deploy

1. `./start.sh`, open the UI.
2. **Presets → Use preset** *ICS Scenario B3 — Industroyer (four ways in)* → **Add & sync** `tollan`
   (required for the OT SPAN) → **Deploy**. Four subnets, 15 nodes; all cards green.
3. **CHECK** (optional): from `iot`, `nmap -Pn -p22 10.0.4.20` and `-p2404 10.0.3.50` are both **filtered**
   — only the fileserver crosses into the DMZ.

## Part 4 — Run the tutorial

Open **More → Tutorials… → Industroyer — four ways into the plant**. Press **Configure lab** once (arms the
two firewalls, starts Zeek + the background telemetry and nightly file push), then walk with **Next step**.
Every command has a one-line explainer right above it; the single `iot` terminal walks the chain, and the
recovery/detection cells run on `rtu`/`ids`.

Narration beats:
- **Hop 1** — the spray **fails** ("guessing isn't the way") → the SMB share **is** ("misconfig beats a
  hardened password"). Show the key-drop then the passwordless login.
- **Hop 2** — one **service account**, found in a config, abused over the **sanctioned** path — the only
  flow the firewall allows into the DMZ.
- **Hop 3** — a **database** hands over the historian's maintenance login.
- **Hop 4** — **key sprawl**: the OT engineering key, stored on the historian, trusted by the EW.
- **Trip / loss of control / wiper / recovery** — identical to B2: HMI + `process-sim` collapse, sustained
  commanding, the wiper blinds the HMI, evict + **local RTU** recovery, degraded-but-restored.
- **Detection** — only TCP to 2404; the tell is the **source** (the EW), not the protocol.

## Part 5 — Reset

**Destroy** → clean idle topology; **Deploy** to run again. The tutorial stays saved with the topology.

---

## Gotchas
- **Configure lab before the attack** — the firewall rules and Zeek are armed there, not baked.
- **Sync `tollan`** before deploying (the OT SPAN depends on the `ownBridge` label).
- SSH-chained cells show "sent", not live run-status (OSC-133 doesn't survive ssh); the sustained payload
  runs in the background and the recovery cell's `pkill` evicts it.
- The canvas busy-node highlight lags ~1–2 s (the live view samples once a second) — inherent, not a bug.
