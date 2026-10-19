# Benchmark: m4-macbook-air · random-idle run 4

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 4), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 310 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 910.5 of 16746.1 MB used (5.4%) · host CPU 0.3% · Docker processes 250.4 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 460 hosts · climb: memory peaked at 90.4% at 460 hosts · 2026-10-06T06:15:14 → 2026-10-06T06:41:34

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 310 | 1 | 324 | 323 | 70.0 | 4.12 | 53.6 | 30.7 | 15.7 | 21.1 / 60.6 | 49.5 | 3.61 | 65.7 | 0.00 | 4.5 | 55.1 | – | ok |
| 400 | 1 | 416 | 415 | 127.4 | 6.87 | 88.5 | 28.7 | 15.1 | 19.7 / 60.6 | 50.7 | 3.61 | 82.4 | 0.10 | 4.8 | 56.0 | – | ok |
| 440 | 1 | 458 | 457 | 153.0 | 7.19 | 108.6 | 27.1 | 15.0 | 18.8 / 60.6 | 50.9 | 3.62 | 87.3 | 0.14 | 4.8 | 56.3 | – | ok |
| 460 | 1 | 480 | 479 | 182.8 | 9.19 | 125.3 | 26.2 | 14.3 | 18.4 / 52.8 | 52.1 | 3.66 | 90.4 | 0.05 | 4.7 | 56.4 | – | ok |

Per image at 460 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 10 | 404.1 | 45.9% | 0.37 |
| `postgres:alpine` | 42 | 28.7 | 13.7% | 0.04 |
| `ae3gis.local/openplc` | 22 | 51.8 | 12.9% | 0.02 |
| `ae3gis.local/suricata` | 14 | 60.6 | 9.6% | 0.47 |
| `ae3gis.local/open-vswitch` | 32 | 20.3 | 7.4% | 0.43 |
| `ae3gis.local/samba` | 23 | 7.7 | 2.0% | 0.00 |
| `kathara/base` | 130 | 1.2 | 1.8% | 0.00 |
| `ae3gis.local/vsftpd` | 38 | 3.4 | 1.5% | 0.06 |
| `ae3gis.local/nginx` | 9 | 8.7 | 0.9% | 0.07 |
| `ae3gis.local/apache` | 9 | 8.7 | 0.9% | 0.08 |
| `kathara/frr` | 47 | 1.2 | 0.6% | 0.00 |
| `httpd:alpine` | 9 | 5.0 | 0.5% | 0.00 |
| `ae3gis.local/isc-dhcp` | 34 | 1.2 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 12 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 11 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/firehol` | 9 | 3.0 | 0.3% | 0.00 |
| `ae3gis.local/snort2` | 10 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 7 | 2.7 | 0.2% | 0.00 |
| `ae3gis.local/wazuh-agent` | 7 | 2.0 | 0.2% | 0.00 |
| `ae3gis.local/nftables` | 5 | 2.7 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
