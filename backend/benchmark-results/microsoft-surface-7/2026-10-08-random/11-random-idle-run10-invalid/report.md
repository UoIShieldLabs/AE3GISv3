# Benchmark: microsoft-surface-7 · random-idle run 10

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `2c8a6d1851b04fe9809915716131e3830beec9616c320afb9f3900302ff61b78`
- **Topology:** generated, random (seed 10), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 280 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 3065.5 of 16605.5 MB used (18.5%) · host CPU 11.3% · Docker processes 2346.3 MB · Docker's disk 13.4% used
- **Outcome:** ceiling 140 hosts · climb: ceiling between 140 and 150 hosts (150 failed) · 2026-10-09T14:59:41 → 2026-10-09T17:52:41

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 280 | 1 | 293 | 292 | 2028.2 | 17.50 | 1292.0 | – | – | – / – | – | – | – | – | – | – | – | stopped: deploy took 2028s |
| 190 | 1 | 198 | 197 | 1150.2 | 11.96 | 663.9 | – | – | – / – | – | – | – | – | – | – | – | stopped: host memory 96.1% > 95.0% for 3 sweeps |
| 130 | 1 | 137 | 136 | 696.3 | 9.14 | 337.8 | 45.6 | 39.6 | 17.3 / 52.0 | – | – | – | – | 3.9 | – | – | ok |
| 150 | 1 | 158 | 157 | 774.7 | 9.56 | 416.4 | – | – | – / – | – | – | – | – | – | – | – | stopped: host memory 96.2% > 95.0% for 3 sweeps |
| 140 | 1 | 147 | 146 | 728.5 | 6.67 | 357.1 | 3.5 | -4.5 | 17.2 / 52.3 | 44.9 | 2.95 | 69.8 | 0.27 | 3.9 | 13.5 | – | ok |

Per image at 140 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 3 | 431.3 | 52.0% | 0.45 |
| `postgres:alpine` | 10 | 34.1 | 13.7% | 0.04 |
| `ae3gis.local/openplc` | 5 | 54.6 | 11.0% | 0.13 |
| `ae3gis.local/suricata` | 2 | 58.6 | 4.7% | 3.06 |
| `ae3gis.local/open-vswitch` | 9 | 12.6 | 4.6% | 1.28 |
| `ae3gis.local/nginx` | 7 | 10.0 | 2.8% | 0.00 |
| `ae3gis.local/samba` | 4 | 12.5 | 2.0% | 0.00 |
| `kathara/base` | 40 | 1.1 | 1.7% | 0.00 |
| `httpd:alpine` | 5 | 5.5 | 1.1% | 0.01 |
| `ae3gis.local/vsftpd` | 7 | 3.7 | 1.1% | 0.00 |
| `kathara/frr` | 17 | 1.1 | 0.8% | 0.00 |
| `ae3gis.local/malicious-client` | 5 | 3.3 | 0.7% | 0.00 |
| `ae3gis.local/apache` | 1 | 14.9 | 0.6% | 0.01 |
| `ae3gis.local/wazuh-agent` | 7 | 2.1 | 0.6% | 0.01 |
| `ae3gis.local/snort2` | 4 | 3.4 | 0.6% | 0.00 |
| `ae3gis.local/isc-dhcp` | 12 | 1.1 | 0.5% | 0.00 |
| `ae3gis.local/nftables` | 3 | 3.8 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 3 | 3.6 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 2 | 4.4 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 1 | 7.8 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
