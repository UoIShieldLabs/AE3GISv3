# Benchmark: m4-macbook-air · random-idle run 1

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 1), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 100 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 893.7 of 16746.1 MB used (5.3%) · host CPU 0.4% · Docker processes 258.4 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 490 hosts · climb: memory peaked at 90.7% at 490 hosts · 2026-10-06T04:23:21 → 2026-10-06T05:15:09

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 107 | 106 | 14.3 | 4.33 | 6.2 | 26.7 | 15.7 | 20.3 / 60.5 | 3.2 | 0.13 | 23.1 | 0.00 | 4.4 | 53.5 | – | ok |
| 200 | 1 | 209 | 208 | 36.5 | 1.44 | 17.8 | 30.5 | 15.3 | 19.0 / 57.1 | 23.1 | 1.67 | 46.6 | 0.00 | 5.3 | 54.5 | – | ok |
| 350 | 1 | 365 | 364 | 76.8 | 4.09 | 53.1 | 29.2 | 15.5 | 19.6 / 60.6 | 46.9 | 3.46 | 73.5 | 0.00 | 5.1 | 55.8 | – | ok |
| 420 | 1 | 438 | 437 | 110.4 | 5.53 | 78.9 | 28.0 | 13.8 | 21.1 / 60.6 | 47.5 | 3.47 | 86.3 | 0.04 | 5.6 | 56.7 | – | ok |
| 440 | 1 | 458 | 457 | 120.1 | 5.68 | 86.8 | 27.2 | 14.0 | 20.2 / 60.6 | 48.0 | 3.47 | 89.0 | 0.05 | 5.4 | 56.8 | – | ok |
| 450 | 1 | 470 | 469 | 139.6 | 7.04 | 102.7 | 25.8 | 13.2 | 19.9 / 60.6 | 48.6 | 3.50 | 88.3 | 0.03 | 5.4 | 56.8 | – | ok |
| 470 | 1 | 490 | 489 | 155.8 | 8.06 | 114.0 | 25.3 | 13.2 | 19.0 / 57.4 | 49.0 | 3.53 | 89.9 | 0.91 | 5.5 | 57.1 | – | ok |
| 480 | 1 | 500 | 499 | 167.0 | 8.38 | 121.0 | 24.1 | 13.0 | 18.8 / 57.3 | 51.0 | 3.66 | 89.5 | 0.09 | 5.4 | 57.1 | – | ok |
| 490 | 1 | 510 | 509 | 177.8 | 9.73 | 127.8 | 24.2 | 12.8 | 18.5 / 56.7 | 50.1 | 3.62 | 90.7 | 0.02 | 5.4 | 57.2 | – | ok |

Per image at 490 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 12 | 387.8 | 49.3% | 0.23 |
| `postgres:alpine` | 52 | 28.4 | 15.6% | 0.02 |
| `ae3gis.local/suricata` | 16 | 58.8 | 10.0% | 0.38 |
| `ae3gis.local/openplc` | 15 | 50.4 | 8.0% | 0.01 |
| `ae3gis.local/open-vswitch` | 29 | 21.4 | 6.6% | 0.38 |
| `kathara/base` | 144 | 1.2 | 1.8% | 0.00 |
| `ae3gis.local/samba` | 20 | 7.8 | 1.7% | 0.00 |
| `ae3gis.local/vsftpd` | 44 | 3.4 | 1.6% | 0.05 |
| `ae3gis.local/nginx` | 11 | 8.8 | 1.0% | 0.06 |
| `httpd:alpine` | 15 | 4.9 | 0.8% | 0.00 |
| `ae3gis.local/apache` | 7 | 8.5 | 0.6% | 0.06 |
| `kathara/frr` | 47 | 1.2 | 0.6% | 0.00 |
| `ae3gis.local/snort3` | 15 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 13 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 11 | 3.0 | 0.3% | 0.00 |
| `ae3gis.local/isc-dhcp` | 26 | 1.2 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 11 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 8 | 2.7 | 0.2% | 0.00 |
| `ae3gis.local/nftables` | 6 | 2.7 | 0.2% | 0.00 |
| `ae3gis.local/wazuh-agent` | 8 | 2.0 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
