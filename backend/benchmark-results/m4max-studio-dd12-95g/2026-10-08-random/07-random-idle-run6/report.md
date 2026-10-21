# Benchmark: m4max-studio-dd12-95g · random-idle run 6

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, random (seed 6), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1640 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1852.9 of 101850.2 MB used (1.8%) · host CPU 0.1% · Docker processes 296.8 MB · Docker's disk 7.2% used
- **Outcome:** ceiling 1640 hosts · climb: 2050 hosts failed (destroy_failed) · stopped: destroy_failed (RuntimeError: Still running: h3_72) · 2026-10-10T12:43:14 → 2026-10-10T13:59:17

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1640 | 1 | 1700 | 1699 | 665.8 | 86.80 | 709.5 | 29.6 | 16.3 | 17.3 / 52.0 | 46.7 | 4.58 | 51.2 | 0.00 | 4.2 | 7.5 | – | ok |
| 2050 | 1 | 2126 | 2125 | 1100.3 | 105.58 | 1582.9 | 28.7 | 15.9 | 18.0 / 51.9 | 50.3 | 4.67 | 66.7 | 0.00 | 4.4 | 7.6 | – | failed: RuntimeError: Still running: h3_72 |

Per image at 1640 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 33 | 417.3 | 46.8% | 0.10 |
| `postgres:alpine` | 130 | 30.5 | 13.5% | 0.01 |
| `ae3gis.local/openplc` | 63 | 52.3 | 11.2% | 0.01 |
| `ae3gis.local/suricata` | 40 | 72.4 | 9.8% | 0.34 |
| `ae3gis.local/open-vswitch` | 89 | 20.8 | 6.3% | 0.38 |
| `kathara/base` | 497 | 1.2 | 2.1% | 0.00 |
| `ae3gis.local/samba` | 60 | 8.6 | 1.7% | 0.00 |
| `ae3gis.local/vsftpd` | 138 | 3.5 | 1.6% | 0.05 |
| `ae3gis.local/nginx` | 35 | 11.3 | 1.3% | 0.06 |
| `ae3gis.local/apache` | 45 | 8.7 | 1.3% | 0.05 |
| `kathara/frr` | 163 | 1.3 | 0.7% | 0.00 |
| `httpd:alpine` | 40 | 5.1 | 0.7% | 0.00 |
| `ae3gis.local/isc-dhcp` | 117 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 45 | 2.9 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 37 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/benign-client` | 36 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 31 | 3.4 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 35 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 31 | 3.2 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 35 | 2.3 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
