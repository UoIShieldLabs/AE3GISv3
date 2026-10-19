# Benchmark: m4-macbook-air · random-idle run 7

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 7), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 340 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 930.3 of 16746.1 MB used (5.5%) · host CPU 0.3% · Docker processes 254.6 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 700 hosts · climb: memory peaked at 90.4% at 700 hosts · 2026-10-06T07:35:51 → 2026-10-06T08:20:12

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 340 | 1 | 354 | 353 | 63.2 | 2.97 | 54.7 | 20.1 | 15.7 | 9.4 / 51.6 | 47.1 | 3.53 | 48.7 | 0.00 | 2.9 | 54.5 | – | ok |
| 560 | 1 | 582 | 581 | 161.6 | 7.31 | 141.1 | 19.6 | 15.4 | 10.7 / 51.6 | 50.1 | 3.63 | 79.5 | 0.06 | 2.8 | 55.4 | – | ok |
| 630 | 1 | 655 | 654 | 206.1 | 10.93 | 181.5 | 18.5 | 14.8 | 10.2 / 49.3 | 51.6 | 3.67 | 89.3 | 0.35 | 2.9 | 55.9 | – | ok |
| 650 | 1 | 677 | 676 | 282.8 | 29.24 | 197.2 | 16.4 | 13.4 | 10.3 / 51.6 | 52.4 | 3.68 | 85.5 | 0.10 | 3.0 | 56.0 | – | ok |
| 700 | 1 | 728 | 727 | 276.6 | 32.81 | 233.9 | 16.3 | 12.8 | 10.3 / 40.7 | 52.7 | 3.67 | 90.4 | 0.42 | 3.1 | 56.4 | – | ok |

Per image at 700 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 5 | 381.3 | 25.4% | 0.42 |
| `ae3gis.local/openplc` | 31 | 41.1 | 17.0% | 0.01 |
| `postgres:alpine` | 44 | 28.1 | 16.5% | 0.03 |
| `ae3gis.local/suricata` | 16 | 52.7 | 11.3% | 0.40 |
| `ae3gis.local/open-vswitch` | 39 | 18.2 | 9.5% | 0.39 |
| `kathara/base` | 213 | 1.2 | 3.4% | 0.00 |
| `ae3gis.local/samba` | 29 | 7.6 | 2.9% | 0.00 |
| `ae3gis.local/vsftpd` | 66 | 3.2 | 2.9% | 0.05 |
| `ae3gis.local/nginx` | 19 | 8.6 | 2.2% | 0.06 |
| `ae3gis.local/apache` | 15 | 8.4 | 1.7% | 0.07 |
| `httpd:alpine` | 26 | 4.8 | 1.7% | 0.00 |
| `ae3gis.local/isc-dhcp` | 63 | 1.1 | 1.0% | 0.00 |
| `kathara/frr` | 56 | 1.2 | 0.9% | 0.00 |
| `ae3gis.local/benign-client` | 21 | 2.6 | 0.7% | 0.00 |
| `ae3gis.local/iptables` | 19 | 2.6 | 0.7% | 0.00 |
| `ae3gis.local/snort2` | 18 | 2.6 | 0.6% | 0.00 |
| `ae3gis.local/snort3` | 17 | 2.6 | 0.6% | 0.00 |
| `ae3gis.local/nftables` | 15 | 2.7 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 8 | 3.6 | 0.4% | 0.00 |
| `ae3gis.local/wazuh-agent` | 8 | 2.3 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
