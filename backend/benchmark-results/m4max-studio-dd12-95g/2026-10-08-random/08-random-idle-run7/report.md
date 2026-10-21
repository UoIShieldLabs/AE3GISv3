# Benchmark: m4max-studio-dd12-95g · random-idle run 7

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, random (seed 7), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1140 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1904.6 of 101850.2 MB used (1.9%) · host CPU 0.1% · Docker processes 301.4 MB · Docker's disk 7.5% used
- **Outcome:** ceiling 2380 hosts · climb: 2390 hosts failed (deploy_failed) · stopped: deploy_failed (ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0)) · 2026-10-10T14:00:33 → 2026-10-10T23:41:36

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1140 | 1 | 1182 | 1181 | 337.1 | 49.97 | 355.8 | 24.8 | 16.1 | 12.7 / 51.7 | 45.9 | 4.78 | 30.9 | 0.00 | 3.1 | 7.6 | – | ok |
| 1420 | 1 | 1473 | 1472 | 528.7 | 70.14 | 541.1 | 25.2 | 15.6 | 14.0 / 51.8 | 46.0 | 4.60 | 41.6 | 0.00 | 3.3 | 7.7 | – | ok |
| 1775 | 1 | 1839 | 1838 | 825.9 | 86.18 | 842.0 | 24.9 | 15.6 | 14.3 / 51.9 | 48.0 | 4.63 | 52.7 | 0.00 | 3.5 | 7.8 | – | ok |
| 2218 | 1 | 2299 | 2298 | 1311.5 | 117.58 | 1373.8 | 25.6 | 16.0 | 14.8 / 51.9 | 51.6 | 4.71 | 67.5 | 0.00 | 3.8 | 7.9 | – | ok |
| 2770 | 1 | 2869 | 2868 | 4226.3 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2490 | 1 | 2580 | 2579 | 2900.0 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2350 | 1 | 2435 | 2434 | 1506.7 | 135.23 | 885.3 | 23.1 | 15.2 | 14.7 / 51.8 | 53.9 | 4.67 | 74.6 | 0.01 | 3.8 | 8.2 | – | ok |
| 2480 | 1 | 2570 | 2569 | 2761.0 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2420 | 1 | 2508 | 2507 | 2623.7 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2380 | 1 | 2465 | 2464 | 1565.5 | 132.26 | 924.2 | 21.7 | 15.3 | 14.6 / 51.8 | 54.2 | 4.51 | 73.3 | 0.01 | 3.8 | 8.2 | – | ok |
| 2410 | 1 | 2498 | 2497 | 2632.4 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2400 | 1 | 2486 | 2485 | 2617.1 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2390 | 1 | 2475 | 2474 | 2610.1 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |

Per image at 2380 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 35 | 397.5 | 38.7% | 0.07 |
| `postgres:alpine` | 170 | 29.9 | 14.2% | 0.01 |
| `ae3gis.local/openplc` | 89 | 51.8 | 12.8% | 0.01 |
| `ae3gis.local/suricata` | 64 | 71.0 | 12.6% | 0.35 |
| `ae3gis.local/open-vswitch` | 119 | 20.2 | 6.7% | 0.71 |
| `kathara/base` | 723 | 1.2 | 2.5% | 0.00 |
| `ae3gis.local/samba` | 96 | 7.9 | 2.1% | 0.00 |
| `ae3gis.local/nginx` | 65 | 10.9 | 2.0% | 0.07 |
| `ae3gis.local/vsftpd` | 198 | 3.4 | 1.9% | 0.06 |
| `ae3gis.local/apache` | 64 | 8.7 | 1.5% | 0.08 |
| `httpd:alpine` | 81 | 5.0 | 1.1% | 0.00 |
| `kathara/frr` | 227 | 1.2 | 0.8% | 0.00 |
| `ae3gis.local/isc-dhcp` | 195 | 1.2 | 0.6% | 0.00 |
| `ae3gis.local/snort3` | 64 | 2.8 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 54 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 54 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/benign-client` | 45 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 43 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/firehol` | 38 | 3.0 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 41 | 2.1 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
