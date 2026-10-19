# Benchmark: m4-macbook-air · random-idle run 5

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 5), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 320 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 888.0 of 16746.1 MB used (5.3%) · host CPU 0.3% · Docker processes 253.2 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 500 hosts · climb: memory peaked at 90.1% at 500 hosts · 2026-10-06T06:43:08 → 2026-10-06T07:14:51

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 320 | 1 | 334 | 333 | 80.8 | 3.79 | 55.2 | 30.7 | 15.7 | 21.2 / 56.5 | 48.4 | 3.58 | 66.5 | 0.00 | 4.4 | 55.1 | – | ok |
| 400 | 1 | 416 | 415 | 117.0 | 6.50 | 82.0 | 27.1 | 15.3 | 18.1 / 51.9 | 49.6 | 3.61 | 78.8 | 0.11 | 4.4 | 55.7 | – | ok |
| 450 | 1 | 470 | 469 | 133.5 | 6.94 | 95.0 | 25.3 | 14.9 | 17.2 / 51.8 | 48.0 | 3.54 | 85.3 | 0.09 | 4.2 | 56.0 | – | ok |
| 480 | 1 | 500 | 499 | 143.0 | 7.47 | 108.6 | 24.1 | 14.4 | 16.5 / 51.8 | 49.7 | 3.64 | 88.1 | 0.02 | 4.1 | 56.1 | – | ok |
| 500 | 1 | 521 | 520 | 161.3 | 7.29 | 116.9 | 23.6 | 14.1 | 16.5 / 51.7 | 49.7 | 3.64 | 90.1 | 0.22 | 4.0 | 56.1 | – | ok |

Per image at 500 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 10 | 398.1 | 46.4% | 0.20 |
| `ae3gis.local/openplc` | 25 | 50.3 | 14.6% | 0.01 |
| `postgres:alpine` | 38 | 28.1 | 12.4% | 0.02 |
| `ae3gis.local/suricata` | 13 | 59.1 | 8.9% | 0.35 |
| `ae3gis.local/open-vswitch` | 25 | 20.2 | 5.9% | 0.33 |
| `kathara/base` | 149 | 1.2 | 2.1% | 0.00 |
| `ae3gis.local/vsftpd` | 40 | 3.3 | 1.6% | 0.05 |
| `ae3gis.local/apache` | 14 | 8.5 | 1.4% | 0.06 |
| `ae3gis.local/samba` | 15 | 7.7 | 1.3% | 0.00 |
| `httpd:alpine` | 16 | 5.0 | 0.9% | 0.00 |
| `kathara/frr` | 52 | 1.2 | 0.7% | 0.00 |
| `ae3gis.local/nginx` | 7 | 8.9 | 0.7% | 0.06 |
| `ae3gis.local/isc-dhcp` | 39 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 15 | 2.7 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 12 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 11 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 11 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 11 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 8 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 10 | 2.0 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
