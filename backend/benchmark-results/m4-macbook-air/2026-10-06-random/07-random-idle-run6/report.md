# Benchmark: m4-macbook-air · random-idle run 6

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 6), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 350 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 930.1 of 16746.1 MB used (5.5%) · host CPU 1.0% · Docker processes 254.9 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 490 hosts · climb: memory peaked at 90.1% at 490 hosts · 2026-10-06T07:16:15 → 2026-10-06T07:34:32

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 350 | 1 | 365 | 364 | 69.6 | 3.04 | 56.3 | 25.6 | 15.6 | 16.3 / 51.6 | 46.3 | 3.44 | 62.6 | 0.00 | 4.0 | 55.1 | – | ok |
| 470 | 1 | 490 | 489 | 126.4 | 6.07 | 103.4 | 26.0 | 15.2 | 17.0 / 52.0 | 48.5 | 3.53 | 87.8 | 0.14 | 4.1 | 56.0 | – | ok |
| 490 | 1 | 510 | 509 | 144.6 | 6.87 | 115.0 | 24.4 | 14.9 | 16.3 / 51.7 | 50.4 | 3.65 | 90.1 | 0.15 | 4.2 | 56.2 | – | ok |

Per image at 490 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 11 | 375.2 | 49.8% | 0.44 |
| `postgres:alpine` | 38 | 28.2 | 12.9% | 0.03 |
| `ae3gis.local/openplc` | 20 | 44.6 | 10.8% | 0.01 |
| `ae3gis.local/suricata` | 14 | 53.6 | 9.1% | 0.37 |
| `ae3gis.local/open-vswitch` | 25 | 18.6 | 5.6% | 0.33 |
| `kathara/base` | 162 | 1.2 | 2.3% | 0.00 |
| `ae3gis.local/samba` | 20 | 7.7 | 1.9% | 0.00 |
| `ae3gis.local/vsftpd` | 39 | 3.2 | 1.5% | 0.05 |
| `ae3gis.local/nginx` | 12 | 8.6 | 1.2% | 0.06 |
| `ae3gis.local/apache` | 10 | 8.4 | 1.0% | 0.06 |
| `kathara/frr` | 48 | 1.2 | 0.7% | 0.00 |
| `httpd:alpine` | 9 | 4.9 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 13 | 2.6 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 11 | 2.9 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 12 | 2.6 | 0.4% | 0.00 |
| `ae3gis.local/isc-dhcp` | 26 | 1.1 | 0.4% | 0.00 |
| `ae3gis.local/wazuh-agent` | 14 | 2.0 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 9 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 9 | 2.5 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 8 | 2.6 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
