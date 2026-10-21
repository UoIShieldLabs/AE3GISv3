# Benchmark: m4max-studio-dd12-95g · random-idle run 5

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, random (seed 5), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1590 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1851.2 of 101850.2 MB used (1.8%) · host CPU 0.2% · Docker processes 287.6 MB · Docker's disk 6.8% used
- **Outcome:** ceiling 2350 hosts · climb: 2360 hosts failed (deploy_failed) · stopped: deploy_failed (ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0)) · 2026-10-10T05:22:49 → 2026-10-10T12:39:44

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1590 | 1 | 1647 | 1646 | 624.1 | 76.10 | 686.6 | 29.9 | 16.2 | 17.5 / 52.0 | 46.4 | 4.62 | 50.2 | 0.00 | 4.4 | 7.2 | – | ok |
| 1987 | 1 | 2058 | 2057 | 1056.8 | 102.68 | 1094.7 | 27.6 | 15.9 | 16.9 / 52.0 | 50.4 | 4.82 | 62.4 | 0.00 | 4.2 | 7.2 | – | ok |
| 2480 | 1 | 2570 | 2569 | 3502.5 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2230 | 1 | 2311 | 2310 | 1398.0 | 108.30 | 1448.3 | 26.6 | 15.1 | 16.2 / 51.9 | 52.8 | 4.77 | 74.1 | 0.00 | 4.1 | 7.3 | – | ok |
| 2470 | 1 | 2560 | 2559 | 3339.6 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2350 | 1 | 2435 | 2434 | 1433.6 | 126.53 | 876.9 | 25.1 | 14.9 | 16.2 / 52.0 | 52.9 | 4.63 | 76.2 | 0.03 | 4.1 | 7.6 | – | ok |
| 2460 | 1 | 2550 | 2549 | 938.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| 2400 | 1 | 2486 | 2485 | 2552.0 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2380 | 1 | 2465 | 2464 | 2532.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2360 | 1 | 2445 | 2444 | 2494.3 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |

Per image at 2350 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 43 | 399.9 | 43.6% | 0.06 |
| `postgres:alpine` | 180 | 30.0 | 13.7% | 0.01 |
| `ae3gis.local/openplc` | 100 | 51.9 | 13.1% | 0.01 |
| `ae3gis.local/suricata` | 61 | 71.0 | 11.0% | 0.35 |
| `ae3gis.local/open-vswitch` | 119 | 20.1 | 6.1% | 0.60 |
| `kathara/base` | 726 | 1.2 | 2.2% | 0.00 |
| `ae3gis.local/nginx` | 56 | 10.9 | 1.5% | 0.07 |
| `ae3gis.local/samba` | 75 | 7.9 | 1.5% | 0.00 |
| `ae3gis.local/vsftpd` | 167 | 3.4 | 1.4% | 0.06 |
| `ae3gis.local/apache` | 59 | 8.7 | 1.3% | 0.07 |
| `httpd:alpine` | 62 | 5.0 | 0.8% | 0.00 |
| `kathara/frr` | 230 | 1.2 | 0.7% | 0.00 |
| `ae3gis.local/isc-dhcp` | 198 | 1.2 | 0.6% | 0.00 |
| `ae3gis.local/nftables` | 62 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 59 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 49 | 3.1 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 51 | 2.8 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 50 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 41 | 2.8 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 47 | 2.1 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
