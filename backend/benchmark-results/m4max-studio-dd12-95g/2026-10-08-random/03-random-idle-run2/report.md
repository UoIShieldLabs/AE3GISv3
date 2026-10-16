# Benchmark: m4max-studio-dd12-95g · random-idle run 2

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101853.4 MB
- **Kernel / Docker:** 6.10.14-linuxkit · Docker 28.4.0 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `1a66f9c9ecdb` · bench
- **Environment fingerprint:** `dda3a67f640694cd032f0c1b552394a2ec9fe5db7084416971b68484b88dfb62`
- **Topology:** generated, random (seed 2), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 790 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1736.6 of 101853.4 MB used (1.7%) · host CPU 0.1% · Docker processes 318.2 MB · Docker's disk 6.3% used
- **Outcome:** ceiling 1200 hosts · climb: ceiling between 1200 and 1210 hosts (1210 failed) · 2026-10-09T01:05:15 → 2026-10-09T05:17:20

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 790 | 1 | 819 | 818 | 643.0 | 28.43 | 441.0 | 59.3 | 37.9 | 16.6 / 52.0 | 27.4 | 2.94 | 42.6 | 0.00 | 3.9 | 6.5 | – | ok |
| 1220 | 1 | 1266 | 1265 | 2958.3 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 1000 | 1 | 1037 | 1036 | 1160.0 | 36.91 | 803.7 | 36.8 | 32.6 | 15.5 / 51.8 | 31.6 | 3.34 | 53.2 | 0.00 | 3.8 | 6.5 | – | ok |
| 1210 | 1 | 1256 | 1255 | 2949.9 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 1100 | 1 | 1142 | 1141 | 1463.3 | 44.54 | 988.0 | 37.5 | 29.3 | 15.9 / 51.9 | 31.4 | 3.28 | 54.4 | 0.00 | 3.9 | 6.5 | – | ok |
| 1200 | 1 | 1244 | 1243 | 1726.9 | 58.95 | 1161.3 | 30.3 | 21.5 | 15.6 / 51.9 | 33.0 | 3.45 | 59.5 | 0.00 | 3.9 | 6.5 | – | ok |

Per image at 1200 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 23 | 387.3 | 45.8% | 0.06 |
| `postgres:alpine` | 85 | 30.1 | 13.1% | 0.01 |
| `ae3gis.local/suricata` | 32 | 70.9 | 11.7% | 0.34 |
| `ae3gis.local/openplc` | 38 | 51.8 | 10.1% | 0.01 |
| `ae3gis.local/open-vswitch` | 56 | 19.7 | 5.7% | 0.38 |
| `kathara/base` | 391 | 1.2 | 2.5% | 0.00 |
| `ae3gis.local/samba` | 46 | 7.7 | 1.8% | 0.00 |
| `ae3gis.local/vsftpd` | 98 | 3.5 | 1.8% | 0.03 |
| `ae3gis.local/nginx` | 27 | 10.8 | 1.5% | 0.04 |
| `ae3gis.local/apache` | 31 | 8.7 | 1.4% | 0.04 |
| `httpd:alpine` | 33 | 5.0 | 0.8% | 0.00 |
| `kathara/frr` | 113 | 1.2 | 0.7% | 0.00 |
| `ae3gis.local/isc-dhcp` | 86 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/iptables` | 37 | 2.7 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 35 | 2.7 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 29 | 3.0 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 27 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 21 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 18 | 2.7 | 0.2% | 0.00 |
| `ae3gis.local/wazuh-agent` | 18 | 2.0 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
