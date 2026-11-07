# Benchmark: microsoft-surface-7 · random-idle run 1

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 29.9.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `b14a3c4efcbf` · bench
- **Environment fingerprint:** `33e9ba4c2d41a1e0c353447beb0781c483a431470f4d022dd281d82544c121f1`
- **Topology:** generated, random (seed 1), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 100 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 880.7 of 16605.5 MB used (5.3%) · host CPU 0.6% · Docker processes 241.8 MB · Docker's disk 13.6% used
- **Outcome:** ceiling 490 hosts · climb: ceiling between 490 and 500 hosts (500 failed) · 2026-10-25T20:45:06 → 2026-10-25T21:27:09

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 107 | 106 | 33.7 | 2.51 | 20.7 | 18.8 | 12.1 | 15.0 / 56.6 | 2.5 | 0.08 | 17.7 | 0.00 | 4.4 | 13.7 | – | ok |
| 200 | 1 | 209 | 208 | 73.5 | 2.31 | 41.1 | 22.6 | 12.0 | 18.0 / 51.8 | 3.9 | 0.14 | 35.2 | 0.00 | 4.9 | 13.7 | – | ok |
| 400 | 1 | 416 | 415 | 183.8 | 5.40 | 116.8 | 24.0 | 12.1 | 19.3 / 56.6 | 7.6 | 0.24 | 67.5 | 0.00 | 5.2 | 13.8 | – | ok |
| 500 | 1 | 521 | 520 | 277.2 | 5.92 | 190.9 | – | – | – / – | – | – | – | – | – | – | – | stopped: memory stalls 18.6% > 10.0% for 3 sweeps |
| 450 | 1 | 470 | 469 | 237.4 | 5.81 | 155.6 | 23.9 | 11.9 | 20.0 / 54.6 | 9.0 | 0.28 | 77.4 | 0.16 | 4.9 | 13.8 | – | ok |
| 490 | 1 | 510 | 509 | 266.9 | 6.54 | 180.3 | 23.1 | 11.8 | 19.0 / 54.3 | 9.9 | 0.33 | 80.9 | 0.01 | 5.0 | 13.8 | – | ok |

Per image at 490 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 12 | 407.4 | 50.4% | 0.37 |
| `postgres:alpine` | 47 | 35.6 | 17.2% | 0.03 |
| `ae3gis.local/suricata` | 15 | 56.0 | 8.7% | 0.57 |
| `ae3gis.local/openplc` | 15 | 53.7 | 8.3% | 0.02 |
| `ae3gis.local/open-vswitch` | 24 | 12.7 | 3.1% | 0.48 |
| `ae3gis.local/samba` | 22 | 10.4 | 2.4% | 0.00 |
| `ae3gis.local/vsftpd` | 42 | 3.7 | 1.6% | 0.07 |
| `kathara/base` | 143 | 1.1 | 1.6% | 0.00 |
| `ae3gis.local/nginx` | 11 | 9.7 | 1.1% | 0.08 |
| `httpd:alpine` | 19 | 5.5 | 1.1% | 0.00 |
| `ae3gis.local/malicious-client` | 26 | 3.1 | 0.8% | 0.00 |
| `ae3gis.local/apache` | 6 | 10.6 | 0.7% | 0.08 |
| `kathara/frr` | 42 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 15 | 3.1 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 13 | 3.5 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 10 | 3.9 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 10 | 3.3 | 0.3% | 0.00 |
| `ae3gis.local/isc-dhcp` | 23 | 1.1 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 5 | 4.4 | 0.2% | 0.00 |
| `ae3gis.local/benign-client` | 5 | 3.6 | 0.2% | 0.00 |
| `ae3gis.local/wazuh-agent` | 5 | 2.8 | 0.1% | 0.01 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
