# Benchmark: m4max-studio-dd12-95g · random-idle run 3

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `3af8219fb50f` · bench
- **Environment fingerprint:** `394927134a4d6058abfa96644e727c105e6bb8c8d0637e05b0cfcb8a55b7d2fc`
- **Topology:** generated, random (seed 3), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1620 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 2078.3 of 101850.2 MB used (2.0%) · host CPU 8.2% · Docker processes 333.0 MB · Docker's disk 9.3% used
- **Outcome:** ceiling 2340 hosts · climb: 2350 hosts failed (deploy_failed) · stopped: deploy_failed (ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0)) · 2026-10-26T17:56:16 → 2026-10-27T01:32:27

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1620 | 1 | 1680 | 1679 | 554.3 | 78.89 | 862.5 | 29.3 | 16.3 | 16.9 / 52.0 | 47.3 | 4.65 | 50.5 | 0.00 | 4.3 | 9.7 | – | ok |
| 2020 | 1 | 2094 | 2093 | 890.7 | 96.91 | 925.5 | 27.6 | 15.8 | 16.4 / 51.9 | 51.3 | 4.72 | 64.3 | 0.00 | 4.1 | 10.0 | – | ok |
| 2520 | 1 | 2611 | 2610 | 3072.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2270 | 1 | 2353 | 2352 | 1202.3 | 124.15 | 1168.5 | 26.4 | 15.9 | 17.0 / 52.0 | 53.3 | 4.68 | 75.3 | 0.00 | 4.2 | 10.0 | – | ok |
| 2510 | 1 | 2601 | 2600 | 2727.4 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2390 | 1 | 2475 | 2474 | 2095.5 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2330 | 1 | 2414 | 2413 | 1414.6 | 131.32 | 679.2 | 19.2 | 10.3 | 17.3 / 52.1 | 53.2 | 4.55 | 78.4 | 0.01 | 4.2 | 10.1 | – | ok |
| 2380 | 1 | 2465 | 2464 | 2228.9 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2360 | 1 | 2445 | 2444 | 2209.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2340 | 1 | 2424 | 2423 | 1334.1 | 125.56 | 685.8 | 20.1 | 10.2 | 17.2 / 52.0 | 55.3 | 4.60 | 79.2 | 0.01 | 4.2 | 10.1 | – | ok |
| 2350 | 1 | 2435 | 2434 | 2163.3 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |

Per image at 2340 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 50 | 394.1 | 47.3% | 0.07 |
| `postgres:alpine` | 179 | 29.8 | 12.8% | 0.01 |
| `ae3gis.local/openplc` | 89 | 51.8 | 11.1% | 0.01 |
| `ae3gis.local/suricata` | 59 | 70.8 | 10.0% | 0.34 |
| `ae3gis.local/open-vswitch` | 136 | 20.9 | 6.8% | 0.73 |
| `kathara/base` | 720 | 1.2 | 2.1% | 0.00 |
| `ae3gis.local/samba` | 83 | 8.1 | 1.6% | 0.00 |
| `ae3gis.local/vsftpd` | 170 | 3.4 | 1.4% | 0.07 |
| `ae3gis.local/nginx` | 52 | 11.0 | 1.4% | 0.06 |
| `ae3gis.local/apache` | 55 | 8.7 | 1.1% | 0.07 |
| `httpd:alpine` | 72 | 5.0 | 0.9% | 0.00 |
| `kathara/frr` | 212 | 1.2 | 0.6% | 0.00 |
| `ae3gis.local/snort2` | 71 | 2.7 | 0.5% | 0.00 |
| `ae3gis.local/isc-dhcp` | 156 | 1.2 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 67 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 54 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 58 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 47 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 57 | 2.0 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 37 | 2.7 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
