# Benchmark: microsoft-surface-7 · random-idle run 5

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `a3fb37a56895634ac8915147b0d14ff988bcd622cf412d89b18c746622ea9efa`
- **Topology:** generated, random (seed 5), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 250 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1013.1 of 16605.5 MB used (6.1%) · host CPU 1.7% · Docker processes 364.7 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 400 hosts · climb: memory peaked at 91.0% at 400 hosts · 2026-10-09T04:10:11 → 2026-10-09T05:08:35

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 250 | 1 | 263 | 262 | 389.8 | 5.20 | 208.9 | 35.8 | 30.0 | 16.9 / 52.1 | 14.2 | 0.83 | 64.5 | 0.00 | 3.8 | 13.4 | – | ok |
| 330 | 1 | 344 | 343 | 631.3 | 17.06 | 346.4 | 20.9 | 14.8 | 17.0 / 51.8 | 23.6 | 1.32 | 76.6 | 0.01 | 4.4 | 13.4 | – | ok |
| 400 | 1 | 416 | 415 | 886.5 | 11.24 | 565.9 | 21.3 | 17.5 | 14.3 / 43.6 | 49.7 | 2.95 | 91.0 | 0.02 | 4.5 | 13.5 | – | ok |

Per image at 400 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 8 | 338.5 | 45.5% | 0.29 |
| `postgres:alpine` | 35 | 29.1 | 17.1% | 0.08 |
| `ae3gis.local/openplc` | 15 | 43.5 | 11.0% | 0.03 |
| `ae3gis.local/suricata` | 9 | 50.6 | 7.7% | 0.79 |
| `ae3gis.local/open-vswitch` | 19 | 11.7 | 3.7% | 0.67 |
| `kathara/base` | 104 | 1.1 | 1.9% | 0.00 |
| `ae3gis.local/samba` | 10 | 11.3 | 1.9% | 0.05 |
| `ae3gis.local/vsftpd` | 29 | 3.5 | 1.7% | 0.11 |
| `ae3gis.local/apache` | 10 | 9.9 | 1.7% | 0.17 |
| `ae3gis.local/nginx` | 8 | 9.6 | 1.3% | 0.15 |
| `ae3gis.local/malicious-client` | 26 | 2.8 | 1.2% | 0.00 |
| `httpd:alpine` | 12 | 5.4 | 1.1% | 0.02 |
| `kathara/frr` | 42 | 1.1 | 0.8% | 0.00 |
| `ae3gis.local/snort2` | 16 | 2.8 | 0.8% | 0.00 |
| `ae3gis.local/isc-dhcp` | 25 | 1.1 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 8 | 3.4 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 9 | 2.9 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 9 | 2.9 | 0.4% | 0.00 |
| `ae3gis.local/benign-client` | 8 | 2.8 | 0.4% | 0.00 |
| `ae3gis.local/wazuh-agent` | 10 | 1.8 | 0.3% | 0.01 |
| `ae3gis.local/nftables` | 4 | 3.4 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
