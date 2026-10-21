# Benchmark: m4max-studio-dd12-95g · random-idle run 4

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, random (seed 4), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 790 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1671.5 of 101850.2 MB used (1.6%) · host CPU 0.1% · Docker processes 265.8 MB · Docker's disk 6.5% used
- **Outcome:** ceiling 2280 hosts · climb: 2290 hosts failed (deploy_failed) · stopped: deploy_failed (ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0)) · 2026-10-09T21:38:56 → 2026-10-10T05:21:20

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 790 | 1 | 819 | 818 | 182.2 | 28.79 | 198.9 | 31.1 | 16.0 | 19.5 / 70.7 | 41.7 | 4.38 | 26.9 | 0.00 | 4.5 | 6.7 | – | ok |
| 987 | 1 | 1023 | 1022 | 283.0 | 41.99 | 285.3 | 27.9 | 15.7 | 17.4 / 52.0 | 44.1 | 4.55 | 32.2 | 0.00 | 4.2 | 6.7 | – | ok |
| 1230 | 1 | 1276 | 1275 | 413.9 | 50.66 | 428.3 | 26.8 | 15.4 | 16.4 / 52.0 | 45.7 | 4.65 | 39.3 | 0.00 | 4.2 | 6.7 | – | ok |
| 1537 | 1 | 1593 | 1592 | 629.1 | 71.75 | 634.8 | 26.8 | 15.9 | 16.6 / 51.9 | 47.1 | 4.65 | 48.7 | 0.00 | 4.1 | 6.8 | – | ok |
| 1920 | 1 | 1990 | 1989 | 975.5 | 95.64 | 1012.9 | 27.6 | 15.7 | 16.5 / 51.9 | 49.7 | 4.65 | 62.3 | 0.00 | 4.0 | 6.9 | – | ok |
| 2400 | 1 | 2486 | 2485 | 3234.5 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2160 | 1 | 2238 | 2237 | 1288.2 | 111.21 | 1318.1 | 26.1 | 16.0 | 16.5 / 51.9 | 52.1 | 4.67 | 71.9 | 0.00 | 4.0 | 6.9 | – | ok |
| 2390 | 1 | 2475 | 2474 | 3359.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2280 | 1 | 2363 | 2362 | 1485.5 | 117.19 | 875.8 | 25.0 | 15.8 | 16.2 / 51.9 | 54.2 | 4.69 | 74.9 | 0.01 | 4.0 | 7.3 | – | ok |
| 2380 | 1 | 2465 | 2464 | 2743.7 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2330 | 1 | 2414 | 2413 | 944.5 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| 2300 | 1 | 2384 | 2383 | 2538.3 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2290 | 1 | 2373 | 2372 | 2546.5 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |

Per image at 2280 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 43 | 399.2 | 44.8% | 0.06 |
| `postgres:alpine` | 165 | 30.1 | 12.9% | 0.01 |
| `ae3gis.local/openplc` | 94 | 51.8 | 12.7% | 0.01 |
| `ae3gis.local/suricata` | 55 | 70.8 | 10.2% | 0.35 |
| `ae3gis.local/open-vswitch` | 121 | 20.2 | 6.4% | 0.64 |
| `kathara/base` | 737 | 1.2 | 2.4% | 0.00 |
| `ae3gis.local/samba` | 104 | 7.8 | 2.1% | 0.00 |
| `ae3gis.local/nginx` | 61 | 10.8 | 1.7% | 0.07 |
| `ae3gis.local/vsftpd` | 168 | 3.4 | 1.5% | 0.06 |
| `ae3gis.local/apache` | 42 | 8.7 | 1.0% | 0.08 |
| `httpd:alpine` | 67 | 5.0 | 0.9% | 0.00 |
| `kathara/frr` | 234 | 1.2 | 0.8% | 0.00 |
| `ae3gis.local/isc-dhcp` | 157 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 60 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 52 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 56 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 42 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 39 | 2.8 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 37 | 2.8 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 29 | 2.0 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
