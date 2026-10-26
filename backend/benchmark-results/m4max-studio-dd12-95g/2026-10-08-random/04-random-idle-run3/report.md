# Benchmark: m4max-studio-dd12-95g · random-idle run 3

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `dc8470732834` · bench
- **Environment fingerprint:** `f945328ce7a0df5c46079251b416f16a2ecb32309cf26caec37f83015401d1fe`
- **Topology:** generated, random (seed 3), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1620 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1985.6 of 101850.2 MB used (1.9%) · host CPU 0.2% · Docker processes 298.5 MB · Docker's disk 8.3% used
- **Outcome:** ceiling 1620 hosts · climb: 2020 hosts failed (destroy_failed) · stopped: destroy_failed (RuntimeError: Still running: h4_48) · 2026-10-24T13:51:32 → 2026-10-24T14:57:49

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1620 | 1 | 1680 | 1679 | 547.4 | 85.80 | 534.2 | 29.4 | 16.3 | 16.8 / 52.0 | 47.0 | 4.57 | 50.3 | 0.00 | 4.3 | 8.6 | – | ok |
| 2020 | 1 | 2094 | 2093 | 922.1 | 106.37 | 1472.2 | 27.5 | 15.9 | 16.5 / 51.8 | 50.3 | 4.67 | 64.3 | 0.00 | 4.2 | 8.7 | – | failed: RuntimeError: Still running: h4_48 |

Per image at 1620 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 30 | 417.6 | 44.3% | 0.11 |
| `postgres:alpine` | 134 | 30.4 | 14.4% | 0.01 |
| `ae3gis.local/suricata` | 44 | 71.6 | 11.1% | 0.34 |
| `ae3gis.local/openplc` | 56 | 52.3 | 10.4% | 0.01 |
| `ae3gis.local/open-vswitch` | 100 | 20.4 | 7.2% | 0.38 |
| `kathara/base` | 511 | 1.2 | 2.2% | 0.00 |
| `ae3gis.local/samba` | 55 | 8.6 | 1.7% | 0.00 |
| `ae3gis.local/nginx` | 37 | 11.1 | 1.4% | 0.05 |
| `ae3gis.local/vsftpd` | 106 | 3.5 | 1.3% | 0.05 |
| `ae3gis.local/apache` | 38 | 9.0 | 1.2% | 0.06 |
| `httpd:alpine` | 49 | 5.1 | 0.9% | 0.00 |
| `kathara/frr` | 146 | 1.2 | 0.6% | 0.00 |
| `ae3gis.local/snort2` | 48 | 2.9 | 0.5% | 0.00 |
| `ae3gis.local/isc-dhcp` | 113 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/nftables` | 41 | 3.1 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 35 | 3.4 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 39 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 35 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/wazuh-agent` | 39 | 2.3 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 24 | 3.1 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
