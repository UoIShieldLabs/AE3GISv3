# Benchmark: microsoft-surface-7 · random-idle run 9

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `704de102e05249dc78e3ef4356455b5c320a16e8822c258dbe8d26d816384402`
- **Topology:** generated, random (seed 9), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 240 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1095.7 of 16605.5 MB used (6.6%) · host CPU 3.0% · Docker processes 407.5 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 410 hosts · climb: memory peaked at 91.5% at 410 hosts · 2026-10-09T09:50:31 → 2026-10-09T12:21:17

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 240 | 1 | 251 | 250 | 501.0 | 8.55 | 271.9 | 30.6 | 26.9 | 15.1 / 56.7 | 17.7 | 1.03 | 55.4 | 0.00 | 4.2 | 13.4 | – | ok |
| 360 | 1 | 375 | 374 | 975.8 | 12.99 | 556.7 | 21.6 | 18.1 | 14.3 / 52.0 | 25.2 | 1.57 | 75.5 | 0.00 | 3.7 | 13.4 | – | ok |
| 420 | 1 | 438 | 437 | 1303.1 | 12.43 | 758.3 | – | – | – / – | – | – | – | – | – | – | – | stopped: host memory 95.5% > 95.0% for 3 sweeps |
| 390 | 1 | 405 | 404 | 1195.1 | 10.76 | 661.4 | 28.7 | 26.0 | 13.8 / 52.3 | 23.0 | 1.25 | 85.6 | 0.04 | 3.7 | 13.4 | – | ok |
| 410 | 1 | 428 | 427 | 1253.7 | 19.88 | 806.8 | 26.2 | 23.5 | 13.3 / 52.3 | 32.5 | 1.97 | 91.5 | 0.09 | 3.8 | 13.4 | – | ok |

Per image at 410 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 4 | 392.8 | 27.6% | 0.14 |
| `ae3gis.local/openplc` | 22 | 52.7 | 20.4% | 0.03 |
| `postgres:alpine` | 32 | 30.6 | 17.2% | 0.04 |
| `ae3gis.local/suricata` | 12 | 55.2 | 11.6% | 0.67 |
| `ae3gis.local/open-vswitch` | 27 | 11.5 | 5.5% | 0.50 |
| `ae3gis.local/samba` | 17 | 10.7 | 3.2% | 0.01 |
| `ae3gis.local/apache` | 13 | 10.2 | 2.3% | 0.10 |
| `kathara/base` | 100 | 1.1 | 1.9% | 0.00 |
| `ae3gis.local/nginx` | 10 | 9.7 | 1.7% | 0.11 |
| `ae3gis.local/vsftpd` | 26 | 3.5 | 1.6% | 0.09 |
| `ae3gis.local/malicious-client` | 29 | 2.9 | 1.5% | 0.00 |
| `httpd:alpine` | 13 | 5.5 | 1.3% | 0.01 |
| `kathara/frr` | 38 | 1.2 | 0.8% | 0.00 |
| `ae3gis.local/iptables` | 11 | 3.3 | 0.6% | 0.00 |
| `ae3gis.local/isc-dhcp` | 29 | 1.1 | 0.6% | 0.00 |
| `ae3gis.local/snort3` | 11 | 2.8 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 8 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 7 | 3.4 | 0.4% | 0.00 |
| `ae3gis.local/wazuh-agent` | 11 | 2.0 | 0.4% | 0.01 |
| `ae3gis.local/nftables` | 5 | 3.0 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 3 | 3.3 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
