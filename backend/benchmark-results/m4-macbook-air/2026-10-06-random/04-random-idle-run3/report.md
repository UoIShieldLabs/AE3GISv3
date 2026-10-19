# Benchmark: m4-macbook-air · random-idle run 3

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 3), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 390 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 931.6 of 16746.1 MB used (5.6%) · host CPU 0.3% · Docker processes 262.9 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 450 hosts · climb: memory peaked at 91.2% at 450 hosts · 2026-10-06T06:01:39 → 2026-10-06T06:13:44

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 390 | 1 | 405 | 404 | 81.7 | 4.30 | 76.5 | 28.4 | 15.6 | 19.5 / 60.6 | 47.0 | 3.44 | 74.8 | 0.00 | 4.5 | 55.7 | – | ok |
| 450 | 1 | 470 | 469 | 126.8 | 7.36 | 112.9 | 28.0 | 14.9 | 19.4 / 59.1 | 50.0 | 3.58 | 91.2 | 0.13 | 4.4 | 56.1 | – | ok |

Per image at 450 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 13 | 402.9 | 57.4% | 0.43 |
| `postgres:alpine` | 35 | 28.3 | 10.9% | 0.02 |
| `ae3gis.local/suricata` | 13 | 59.9 | 8.5% | 0.43 |
| `ae3gis.local/openplc` | 12 | 51.4 | 6.8% | 0.02 |
| `ae3gis.local/open-vswitch` | 28 | 20.4 | 6.3% | 0.36 |
| `kathara/base` | 142 | 1.2 | 1.9% | 0.00 |
| `ae3gis.local/apache` | 15 | 8.6 | 1.4% | 0.06 |
| `ae3gis.local/vsftpd` | 34 | 3.4 | 1.3% | 0.05 |
| `ae3gis.local/samba` | 12 | 7.7 | 1.0% | 0.00 |
| `httpd:alpine` | 13 | 5.0 | 0.7% | 0.00 |
| `ae3gis.local/nginx` | 7 | 9.1 | 0.7% | 0.06 |
| `kathara/frr` | 39 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/isc-dhcp` | 32 | 1.2 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 9 | 3.6 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 12 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 11 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/snort2` | 11 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 14 | 2.0 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 9 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 9 | 2.7 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
