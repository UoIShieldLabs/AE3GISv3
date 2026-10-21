# Benchmark: microsoft-surface-7 · random-idle run 10

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `20c8b9e23b2c` · bench
- **Environment fingerprint:** `80bcc0f7cf6416d6093c854bced92b36fd9c47bcd0cf66b50bbcf2bab60c304b`
- **Topology:** generated, random (seed 10), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 280 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1013.7 of 16605.5 MB used (6.1%) · host CPU 3.5% · Docker processes 364.9 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 440 hosts · climb: memory peaked at 90.8% at 440 hosts · 2026-10-11T07:00:40 → 2026-10-11T10:09:05

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 280 | 1 | 293 | 292 | 750.7 | 9.07 | 402.5 | 30.9 | 28.8 | 13.0 / 51.8 | 19.1 | 1.17 | 53.5 | 0.00 | 3.3 | 13.4 | – | ok |
| 380 | 1 | 395 | 394 | 1223.5 | 14.23 | 696.3 | 25.3 | 24.8 | 10.8 / 51.7 | 27.3 | 1.69 | 76.9 | 0.00 | 3.7 | 13.5 | – | ok |
| 430 | 1 | 448 | 447 | 1450.3 | 17.52 | 867.6 | 25.4 | 25.7 | 10.1 / 51.7 | 47.0 | 2.81 | 87.6 | 0.01 | 3.4 | 13.5 | – | ok |
| 460 | 1 | 480 | 479 | 1617.4 | 11.75 | 1099.4 | – | – | – / – | – | – | – | – | – | – | – | stopped: host memory 95.1% > 95.0% for 3 sweeps |
| 440 | 1 | 458 | 457 | 1513.6 | 19.86 | 910.7 | 24.4 | 25.6 | 9.4 / 45.3 | 53.7 | 3.33 | 90.8 | 0.22 | 3.4 | 13.5 | – | ok |

Per image at 440 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 3 | 330.7 | 23.1% | 0.32 |
| `postgres:alpine` | 31 | 28.4 | 20.6% | 0.04 |
| `ae3gis.local/openplc` | 14 | 46.5 | 15.2% | 0.05 |
| `ae3gis.local/suricata` | 8 | 52.1 | 9.7% | 0.95 |
| `ae3gis.local/open-vswitch` | 23 | 11.7 | 6.2% | 0.67 |
| `ae3gis.local/samba` | 18 | 10.4 | 4.4% | 0.00 |
| `ae3gis.local/apache` | 14 | 10.3 | 3.4% | 0.14 |
| `kathara/base` | 131 | 1.1 | 3.3% | 0.00 |
| `ae3gis.local/nginx` | 14 | 9.2 | 3.0% | 0.15 |
| `ae3gis.local/vsftpd` | 28 | 3.5 | 2.3% | 0.09 |
| `ae3gis.local/malicious-client` | 25 | 2.9 | 1.7% | 0.00 |
| `httpd:alpine` | 11 | 5.5 | 1.4% | 0.02 |
| `kathara/frr` | 46 | 1.1 | 1.2% | 0.00 |
| `ae3gis.local/snort2` | 14 | 3.0 | 1.0% | 0.00 |
| `ae3gis.local/isc-dhcp` | 36 | 1.1 | 0.9% | 0.00 |
| `ae3gis.local/iptables` | 7 | 3.0 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 7 | 2.9 | 0.5% | 0.00 |
| `ae3gis.local/wazuh-agent` | 12 | 1.6 | 0.5% | 0.01 |
| `ae3gis.local/nftables` | 6 | 2.9 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 5 | 3.2 | 0.4% | 0.00 |
| `ae3gis.local/benign-client` | 5 | 2.9 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
