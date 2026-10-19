# Benchmark: m4-macbook-air · random-idle run 9

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 9), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 370 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 954.1 of 16746.1 MB used (5.7%) · host CPU 0.3% · Docker processes 260.5 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 540 hosts · climb: memory peaked at 90.3% at 540 hosts · 2026-10-06T08:44:46 → 2026-10-06T09:20:07

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 370 | 1 | 385 | 384 | 74.8 | 3.63 | 63.0 | 26.5 | 15.7 | 16.8 / 53.9 | 47.0 | 3.47 | 67.6 | 0.00 | 3.5 | 54.9 | – | ok |
| 470 | 1 | 490 | 489 | 128.5 | 6.87 | 104.3 | 24.9 | 15.1 | 15.7 / 51.8 | 48.6 | 3.52 | 85.1 | 0.04 | 3.8 | 55.8 | – | ok |
| 500 | 1 | 521 | 520 | 150.4 | 7.24 | 136.6 | 23.6 | 15.0 | 15.1 / 51.8 | 52.4 | 3.69 | 88.9 | 0.05 | 3.9 | 56.0 | – | ok |
| 520 | 1 | 541 | 540 | 166.6 | 7.58 | 132.9 | 22.5 | 14.4 | 14.7 / 51.9 | 51.1 | 3.64 | 89.2 | 0.19 | 3.8 | 56.1 | – | ok |
| 540 | 1 | 561 | 560 | 197.5 | 9.39 | 146.6 | 21.7 | 14.0 | 14.4 / 51.5 | 51.7 | 3.65 | 90.3 | 0.05 | 3.7 | 56.1 | – | ok |

Per image at 540 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 8 | 399.6 | 39.6% | 0.50 |
| `postgres:alpine` | 39 | 28.6 | 13.8% | 0.03 |
| `ae3gis.local/openplc` | 21 | 51.5 | 13.4% | 0.02 |
| `ae3gis.local/suricata` | 13 | 59.8 | 9.6% | 0.47 |
| `ae3gis.local/open-vswitch` | 37 | 19.6 | 9.0% | 0.43 |
| `kathara/base` | 158 | 1.2 | 2.4% | 0.00 |
| `ae3gis.local/samba` | 21 | 8.0 | 2.1% | 0.00 |
| `ae3gis.local/apache` | 19 | 8.5 | 2.0% | 0.08 |
| `ae3gis.local/vsftpd` | 45 | 3.4 | 1.9% | 0.06 |
| `ae3gis.local/nginx` | 14 | 8.7 | 1.5% | 0.16 |
| `httpd:alpine` | 15 | 5.1 | 0.9% | 0.00 |
| `kathara/frr` | 58 | 1.2 | 0.9% | 0.00 |
| `ae3gis.local/isc-dhcp` | 36 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/iptables` | 15 | 2.7 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 15 | 2.7 | 0.5% | 0.00 |
| `ae3gis.local/nftables` | 12 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/wazuh-agent` | 14 | 2.0 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 10 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/firehol` | 7 | 3.0 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 4 | 2.6 | 0.1% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
