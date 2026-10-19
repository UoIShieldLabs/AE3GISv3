# Benchmark: microsoft-surface-7 · random-idle run 2

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `9476f028774056264e0bb3c49269b67e9730142e0fd03421b00df0a179d93165`
- **Topology:** generated, random (seed 2), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 320 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 978.7 of 16605.5 MB used (5.9%) · host CPU 2.0% · Docker processes 351.7 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 410 hosts · climb: memory peaked at 90.7% at 410 hosts · 2026-10-08T23:03:12 → 2026-10-09T01:37:01

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 320 | 1 | 334 | 333 | 708.7 | 7.86 | 363.3 | 33.3 | 28.7 | 15.4 / 56.7 | 70.2 | 4.19 | 70.2 | 0.00 | 3.4 | 13.4 | – | ok |
| 380 | 1 | 395 | 394 | 1004.0 | 18.81 | 581.7 | 24.8 | 20.6 | 14.5 / 52.7 | 85.1 | 4.75 | 84.1 | 0.00 | 3.7 | 13.4 | – | ok |
| 400 | 1 | 416 | 415 | 1099.6 | 53.17 | 629.0 | 24.8 | 21.0 | 14.3 / 52.8 | 82.7 | 4.96 | 78.0 | 0.01 | 3.8 | 13.4 | – | ok |
| 440 | 1 | 458 | 457 | 976.7 | 8.64 | 595.0 | – | – | – / – | – | – | – | – | – | – | – | stopped: host memory 95.2% > 95.0% for 3 sweeps |
| 420 | 1 | 438 | 437 | 745.9 | 7.92 | 502.4 | – | – | – / – | – | – | – | – | – | – | – | stopped: host memory 95.2% > 95.0% for 3 sweeps |
| 410 | 1 | 428 | 427 | 776.0 | 6.91 | 464.9 | 18.5 | 14.6 | 12.2 / 45.7 | 80.7 | 4.92 | 90.7 | 0.10 | 3.8 | 13.4 | – | ok |

Per image at 410 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 6 | 321.8 | 36.9% | 0.42 |
| `postgres:alpine` | 31 | 29.1 | 17.2% | 0.04 |
| `ae3gis.local/openplc` | 17 | 42.7 | 13.8% | 0.04 |
| `ae3gis.local/suricata` | 13 | 46.7 | 11.6% | 1.01 |
| `ae3gis.local/open-vswitch` | 17 | 11.2 | 3.6% | 0.78 |
| `ae3gis.local/apache` | 14 | 9.6 | 2.6% | 0.13 |
| `kathara/base` | 122 | 1.1 | 2.5% | 0.00 |
| `ae3gis.local/vsftpd` | 35 | 3.5 | 2.4% | 0.11 |
| `ae3gis.local/samba` | 8 | 9.9 | 1.5% | 0.00 |
| `ae3gis.local/malicious-client` | 24 | 2.8 | 1.3% | 0.00 |
| `ae3gis.local/nginx` | 6 | 9.1 | 1.0% | 0.18 |
| `kathara/frr` | 45 | 1.1 | 1.0% | 0.00 |
| `httpd:alpine` | 9 | 5.5 | 0.9% | 0.01 |
| `ae3gis.local/firehol` | 10 | 3.4 | 0.6% | 0.00 |
| `ae3gis.local/iptables` | 10 | 2.8 | 0.5% | 0.00 |
| `ae3gis.local/nftables` | 9 | 2.8 | 0.5% | 0.00 |
| `ae3gis.local/isc-dhcp` | 23 | 1.1 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 9 | 2.8 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 8 | 2.8 | 0.4% | 0.00 |
| `ae3gis.local/benign-client` | 6 | 3.6 | 0.4% | 0.00 |
| `ae3gis.local/wazuh-agent` | 6 | 1.9 | 0.2% | 0.01 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
