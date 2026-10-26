# Benchmark: microsoft-surface-7 · random-idle run 2

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 29.9.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `b14a3c4efcbf` · bench
- **Environment fingerprint:** `33e9ba4c2d41a1e0c353447beb0781c483a431470f4d022dd281d82544c121f1`
- **Topology:** generated, random (seed 2), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 340 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 937.4 of 16605.5 MB used (5.6%) · host CPU 13.2% · Docker processes 232.0 MB · Docker's disk 13.6% used
- **Outcome:** ceiling 630 hosts · climb: ceiling between 630 and 640 hosts (640 failed) · 2026-10-25T21:28:34 → 2026-10-25T22:52:25

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 340 | 1 | 354 | 353 | 169.3 | 4.78 | 107.2 | 21.0 | 12.2 | 16.4 / 56.6 | 20.4 | 0.20 | 50.4 | 0.00 | 3.3 | 13.7 | – | ok |
| 540 | 1 | 561 | 560 | 315.3 | 7.47 | 243.5 | 19.3 | 12.0 | 14.5 / 52.0 | 22.7 | 0.30 | 73.1 | 0.00 | 3.6 | 13.8 | – | ok |
| 640 | 1 | 665 | 664 | 427.8 | 12.15 | 316.8 | – | – | – / – | – | – | – | – | – | – | – | stopped: memory stalls 14.0% > 10.0% for 3 sweeps |
| 590 | 1 | 612 | 611 | 376.1 | 8.72 | 274.3 | 18.9 | 11.9 | 14.6 / 52.0 | 23.9 | 0.34 | 79.5 | 0.01 | 3.8 | 13.8 | – | ok |
| 630 | 1 | 655 | 654 | 407.0 | 9.56 | 321.7 | 18.5 | 11.9 | 13.7 / 51.9 | 25.1 | 0.40 | 82.8 | 0.06 | 3.7 | 13.8 | – | ok |

Per image at 630 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 9 | 402.5 | 40.2% | 0.30 |
| `postgres:alpine` | 46 | 34.4 | 17.6% | 0.02 |
| `ae3gis.local/openplc` | 22 | 52.5 | 12.8% | 0.02 |
| `ae3gis.local/suricata` | 15 | 55.2 | 9.2% | 0.49 |
| `ae3gis.local/open-vswitch` | 31 | 11.9 | 4.1% | 0.46 |
| `kathara/base` | 190 | 1.1 | 2.2% | 0.00 |
| `ae3gis.local/samba` | 19 | 10.1 | 2.1% | 0.00 |
| `ae3gis.local/vsftpd` | 47 | 3.7 | 1.9% | 0.08 |
| `ae3gis.local/apache` | 17 | 9.5 | 1.8% | 0.09 |
| `ae3gis.local/malicious-client` | 42 | 3.0 | 1.4% | 0.00 |
| `ae3gis.local/nginx` | 10 | 9.6 | 1.1% | 0.09 |
| `httpd:alpine` | 17 | 5.4 | 1.0% | 0.00 |
| `kathara/frr` | 60 | 1.1 | 0.8% | 0.00 |
| `ae3gis.local/snort3` | 19 | 3.0 | 0.6% | 0.00 |
| `ae3gis.local/firehol` | 13 | 3.8 | 0.6% | 0.00 |
| `ae3gis.local/snort2` | 14 | 3.3 | 0.5% | 0.00 |
| `ae3gis.local/isc-dhcp` | 40 | 1.1 | 0.5% | 0.00 |
| `ae3gis.local/iptables` | 14 | 3.1 | 0.5% | 0.00 |
| `ae3gis.local/nftables` | 12 | 3.5 | 0.5% | 0.00 |
| `ae3gis.local/benign-client` | 9 | 3.4 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 9 | 2.2 | 0.2% | 0.01 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
