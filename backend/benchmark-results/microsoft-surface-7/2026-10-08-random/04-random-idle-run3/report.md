# Benchmark: microsoft-surface-7 · random-idle run 3

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `9476f028774056264e0bb3c49269b67e9730142e0fd03421b00df0a179d93165`
- **Topology:** generated, random (seed 3), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 280 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1001.4 of 16605.5 MB used (6.0%) · host CPU 1.2% · Docker processes 357.8 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 350 hosts · climb: memory peaked at 93.3% at 350 hosts · 2026-10-09T01:39:38 → 2026-10-09T02:29:27

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 280 | 1 | 293 | 292 | 455.7 | 5.82 | 234.7 | 41.5 | 30.2 | 22.4 / 56.2 | 15.3 | 0.86 | 79.3 | 0.45 | 4.5 | 13.4 | – | ok |
| 310 | 1 | 324 | 323 | 540.2 | 4.77 | 306.5 | 26.5 | 17.2 | 20.3 / 53.6 | 21.8 | 1.28 | 80.7 | 0.01 | 4.4 | 13.4 | – | ok |
| 350 | 1 | 365 | 364 | 645.5 | 7.15 | 354.1 | 25.9 | 17.2 | 19.1 / 54.4 | 20.9 | 1.15 | 93.3 | 1.83 | 4.1 | 13.4 | – | ok |

Per image at 350 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 10 | 388.8 | 55.8% | 0.26 |
| `ae3gis.local/openplc` | 16 | 52.8 | 12.1% | 0.03 |
| `postgres:alpine` | 24 | 29.7 | 10.2% | 0.03 |
| `ae3gis.local/suricata` | 9 | 55.5 | 7.2% | 0.65 |
| `ae3gis.local/open-vswitch` | 21 | 11.7 | 3.5% | 0.48 |
| `kathara/base` | 95 | 1.1 | 1.5% | 0.00 |
| `ae3gis.local/samba` | 9 | 11.1 | 1.4% | 0.00 |
| `ae3gis.local/vsftpd` | 26 | 3.5 | 1.3% | 0.08 |
| `ae3gis.local/malicious-client` | 26 | 3.0 | 1.1% | 0.00 |
| `ae3gis.local/apache` | 7 | 10.7 | 1.1% | 0.10 |
| `ae3gis.local/nginx` | 7 | 9.7 | 1.0% | 0.08 |
| `httpd:alpine` | 9 | 5.6 | 0.7% | 0.00 |
| `kathara/frr` | 32 | 1.1 | 0.5% | 0.00 |
| `ae3gis.local/isc-dhcp` | 26 | 1.1 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 8 | 3.3 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 7 | 3.7 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 7 | 3.6 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 8 | 2.9 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 5 | 3.9 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 5 | 3.3 | 0.2% | 0.00 |
| `ae3gis.local/wazuh-agent` | 8 | 1.8 | 0.2% | 0.01 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
