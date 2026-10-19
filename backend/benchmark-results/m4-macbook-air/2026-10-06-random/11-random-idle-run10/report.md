# Benchmark: m4-macbook-air · random-idle run 10

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 10), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 370 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 916.1 of 16746.1 MB used (5.5%) · host CPU 0.3% · Docker processes 254.7 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 580 hosts · climb: memory peaked at 90.3% at 580 hosts · 2026-10-06T09:21:26 → 2026-10-06T09:49:30

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 370 | 1 | 385 | 384 | 73.4 | 4.03 | 62.0 | 24.3 | 15.7 | 14.6 / 51.6 | 46.5 | 3.48 | 62.4 | 0.00 | 4.0 | 55.3 | – | ok |
| 500 | 1 | 521 | 520 | 134.6 | 7.23 | 112.4 | 22.4 | 15.2 | 13.3 / 51.6 | 49.7 | 3.63 | 81.8 | 0.04 | 3.9 | 56.0 | – | ok |
| 550 | 1 | 572 | 571 | 171.5 | 8.77 | 137.4 | 20.8 | 14.9 | 12.6 / 51.6 | 50.6 | 3.63 | 87.3 | 0.23 | 3.8 | 56.3 | – | ok |
| 580 | 1 | 602 | 601 | 188.9 | 8.73 | 153.1 | 20.1 | 14.3 | 12.7 / 48.9 | 51.0 | 3.64 | 90.3 | 0.03 | 4.0 | 56.7 | – | ok |

Per image at 580 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 7 | 393.6 | 36.0% | 0.37 |
| `postgres:alpine` | 48 | 28.6 | 17.9% | 0.03 |
| `ae3gis.local/openplc` | 21 | 48.8 | 13.4% | 0.01 |
| `ae3gis.local/open-vswitch` | 33 | 20.9 | 9.0% | 0.37 |
| `ae3gis.local/suricata` | 10 | 57.7 | 7.5% | 0.36 |
| `kathara/base` | 173 | 1.2 | 2.7% | 0.00 |
| `ae3gis.local/samba` | 22 | 7.7 | 2.2% | 0.00 |
| `ae3gis.local/nginx` | 19 | 8.5 | 2.1% | 0.06 |
| `ae3gis.local/apache` | 17 | 8.5 | 1.9% | 0.06 |
| `ae3gis.local/vsftpd` | 38 | 3.4 | 1.7% | 0.05 |
| `kathara/frr` | 64 | 1.2 | 1.0% | 0.00 |
| `httpd:alpine` | 14 | 5.1 | 0.9% | 0.00 |
| `ae3gis.local/isc-dhcp` | 47 | 1.1 | 0.7% | 0.00 |
| `ae3gis.local/snort2` | 19 | 2.7 | 0.7% | 0.00 |
| `ae3gis.local/wazuh-agent` | 18 | 2.0 | 0.5% | 0.00 |
| `ae3gis.local/iptables` | 12 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 12 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 12 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 8 | 2.9 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 8 | 2.7 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
