# Benchmark: microsoft-surface-7 · random-idle run 4

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `704de102e05249dc78e3ef4356455b5c320a16e8822c258dbe8d26d816384402`
- **Topology:** generated, random (seed 4), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 240 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1014.9 of 16605.5 MB used (6.1%) · host CPU 1.6% · Docker processes 360.3 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 360 hosts · climb: ceiling between 360 and 370 hosts (370 failed) · 2026-10-09T02:32:15 → 2026-10-09T04:07:14

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 240 | 1 | 251 | 250 | 374.5 | 6.30 | 188.8 | 36.3 | 29.3 | 18.5 / 56.7 | 16.4 | 0.93 | 60.9 | 0.00 | 5.0 | 13.4 | – | ok |
| 330 | 1 | 344 | 343 | 643.2 | 6.25 | 367.5 | 26.0 | 18.9 | 17.7 / 54.3 | 21.9 | 1.26 | 82.2 | 0.00 | 4.6 | 13.4 | – | ok |
| 370 | 1 | 385 | 384 | 795.4 | 16.35 | 540.1 | – | – | – / – | – | – | – | – | – | – | – | stopped: memory stalls 12.3% > 10.0% for 3 sweeps |
| 350 | 1 | 365 | 364 | 711.0 | 6.27 | 365.5 | 33.5 | 26.1 | 18.3 / 54.6 | 24.2 | 1.39 | 86.4 | 0.03 | 4.5 | 13.4 | – | ok |
| 360 | 1 | 375 | 374 | 677.1 | 6.23 | 374.9 | 26.0 | 17.3 | 18.1 / 54.1 | 79.3 | 4.73 | 88.7 | 0.03 | 4.5 | 13.4 | – | ok |

Per image at 360 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 9 | 381.4 | 50.6% | 0.64 |
| `postgres:alpine` | 30 | 29.2 | 12.9% | 0.04 |
| `ae3gis.local/openplc` | 16 | 50.7 | 12.0% | 0.05 |
| `ae3gis.local/suricata` | 11 | 54.5 | 8.8% | 1.10 |
| `ae3gis.local/open-vswitch` | 27 | 11.4 | 4.5% | 0.75 |
| `ae3gis.local/samba` | 15 | 9.8 | 2.2% | 0.00 |
| `kathara/base` | 93 | 1.1 | 1.5% | 0.00 |
| `ae3gis.local/vsftpd` | 27 | 3.5 | 1.4% | 0.11 |
| `ae3gis.local/malicious-client` | 29 | 2.9 | 1.2% | 0.00 |
| `ae3gis.local/apache` | 7 | 10.2 | 1.0% | 0.17 |
| `ae3gis.local/nginx` | 4 | 11.1 | 0.7% | 0.13 |
| `kathara/frr` | 35 | 1.1 | 0.6% | 0.00 |
| `ae3gis.local/iptables` | 12 | 2.9 | 0.5% | 0.00 |
| `httpd:alpine` | 6 | 5.4 | 0.5% | 0.01 |
| `ae3gis.local/firehol` | 8 | 3.3 | 0.4% | 0.00 |
| `ae3gis.local/isc-dhcp` | 24 | 1.1 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 7 | 2.9 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 7 | 2.8 | 0.3% | 0.00 |
| `ae3gis.local/snort3` | 3 | 3.1 | 0.1% | 0.00 |
| `ae3gis.local/nftables` | 2 | 3.2 | 0.1% | 0.00 |
| `ae3gis.local/wazuh-agent` | 3 | 2.0 | 0.1% | 0.01 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
