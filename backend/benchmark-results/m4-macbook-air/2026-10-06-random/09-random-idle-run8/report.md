# Benchmark: m4-macbook-air · random-idle run 8

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 8), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 480 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 917.3 of 16746.1 MB used (5.5%) · host CPU 0.4% · Docker processes 253.4 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 530 hosts · climb: memory peaked at 91.2% at 530 hosts · 2026-10-06T08:21:40 → 2026-10-06T08:43:26

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 480 | 1 | 500 | 499 | 113.6 | 5.44 | 106.7 | 26.4 | 15.6 | 15.3 / 60.6 | 50.0 | 3.59 | 84.4 | 0.04 | 3.5 | 55.6 | – | ok |
| 510 | 1 | 531 | 530 | 153.2 | 7.95 | 127.0 | 23.7 | 14.3 | 16.0 / 58.7 | 50.9 | 3.62 | 89.3 | 0.07 | 3.6 | 55.8 | – | ok |
| 530 | 1 | 551 | 550 | 175.8 | 8.27 | 137.6 | 23.1 | 13.9 | 15.7 / 54.8 | 51.9 | 3.62 | 91.2 | 0.46 | 3.6 | 56.0 | – | ok |

Per image at 530 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 10 | 387.1 | 44.9% | 0.62 |
| `ae3gis.local/suricata` | 20 | 55.9 | 13.0% | 0.42 |
| `postgres:alpine` | 35 | 28.0 | 11.3% | 0.03 |
| `ae3gis.local/openplc` | 20 | 47.6 | 11.0% | 0.01 |
| `ae3gis.local/open-vswitch` | 34 | 20.1 | 7.9% | 0.39 |
| `kathara/base` | 160 | 1.2 | 2.2% | 0.00 |
| `ae3gis.local/vsftpd` | 43 | 3.3 | 1.7% | 0.05 |
| `ae3gis.local/apache` | 14 | 8.6 | 1.4% | 0.06 |
| `ae3gis.local/samba` | 15 | 7.8 | 1.3% | 0.00 |
| `ae3gis.local/nginx` | 9 | 8.9 | 0.9% | 0.07 |
| `kathara/frr` | 62 | 1.2 | 0.9% | 0.00 |
| `ae3gis.local/isc-dhcp` | 48 | 1.2 | 0.6% | 0.00 |
| `httpd:alpine` | 10 | 4.9 | 0.6% | 0.00 |
| `ae3gis.local/firehol` | 15 | 2.9 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 10 | 2.9 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 10 | 2.8 | 0.3% | 0.00 |
| `ae3gis.local/snort2` | 9 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 9 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 11 | 2.0 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 7 | 2.7 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
