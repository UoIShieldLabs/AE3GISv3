# Benchmark: microsoft-surface-7 · random-idle run 6

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `9476f028774056264e0bb3c49269b67e9730142e0fd03421b00df0a179d93165`
- **Topology:** generated, random (seed 6), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 280 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1015.3 of 16605.5 MB used (6.1%) · host CPU 2.0% · Docker processes 369.0 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 390 hosts · climb: memory peaked at 91.9% at 390 hosts · 2026-10-09T05:11:06 → 2026-10-09T06:16:38

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 280 | 1 | 293 | 292 | 527.0 | 5.75 | 278.7 | 37.4 | 31.1 | 17.4 / 51.9 | 16.3 | 0.97 | 72.4 | 0.00 | 4.2 | 13.4 | – | ok |
| 330 | 1 | 344 | 343 | 692.2 | 12.77 | 441.4 | 24.7 | 20.7 | 14.7 / 51.9 | 16.1 | 0.90 | 79.3 | 0.00 | 4.1 | 13.4 | – | ok |
| 390 | 1 | 405 | 404 | 963.5 | 9.19 | 559.0 | 26.9 | 23.6 | 13.9 / 51.9 | 67.9 | 4.13 | 91.9 | 0.01 | 4.2 | 13.4 | – | ok |

Per image at 390 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 6 | 395.2 | 42.2% | 0.19 |
| `postgres:alpine` | 33 | 30.8 | 18.1% | 0.03 |
| `ae3gis.local/openplc` | 14 | 52.3 | 13.0% | 0.04 |
| `ae3gis.local/suricata` | 7 | 55.2 | 6.9% | 1.04 |
| `ae3gis.local/open-vswitch` | 22 | 11.5 | 4.5% | 0.63 |
| `kathara/base` | 122 | 1.1 | 2.3% | 0.00 |
| `ae3gis.local/vsftpd` | 31 | 3.6 | 2.0% | 0.14 |
| `ae3gis.local/nginx` | 11 | 9.8 | 1.9% | 0.14 |
| `ae3gis.local/apache` | 10 | 10.1 | 1.8% | 0.13 |
| `ae3gis.local/samba` | 8 | 10.0 | 1.4% | 0.00 |
| `ae3gis.local/malicious-client` | 25 | 2.9 | 1.3% | 0.00 |
| `httpd:alpine` | 8 | 5.5 | 0.8% | 0.00 |
| `kathara/frr` | 37 | 1.2 | 0.8% | 0.00 |
| `ae3gis.local/benign-client` | 9 | 3.0 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 7 | 3.8 | 0.5% | 0.00 |
| `ae3gis.local/wazuh-agent` | 13 | 1.9 | 0.5% | 0.01 |
| `ae3gis.local/isc-dhcp` | 20 | 1.1 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 7 | 3.1 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 6 | 3.2 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 5 | 3.2 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 4 | 3.2 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
