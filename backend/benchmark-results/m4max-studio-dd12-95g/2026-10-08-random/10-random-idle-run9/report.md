# Benchmark: m4max-studio-dd12-95g · random-idle run 9

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, random (seed 9), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1440 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1911.1 of 101850.2 MB used (1.9%) · host CPU 0.1% · Docker processes 316.9 MB · Docker's disk 7.8% used
- **Outcome:** ceiling 2350 hosts · climb: ceiling between 2350 and 2360 hosts (2360 failed) · 2026-10-11T01:48:00 → 2026-10-11T09:37:01

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1440 | 1 | 1493 | 1492 | 505.2 | 67.48 | 546.7 | 30.9 | 16.1 | 18.9 / 52.2 | 46.3 | 4.57 | 47.0 | 0.00 | 4.9 | 8.1 | – | ok |
| 1800 | 1 | 1865 | 1864 | 848.6 | 89.43 | 864.7 | 28.0 | 15.9 | 17.4 / 52.1 | 49.0 | 4.61 | 57.3 | 0.00 | 4.7 | 8.2 | – | ok |
| 2250 | 1 | 2333 | 2332 | 1386.3 | 118.43 | 1447.4 | 28.8 | 15.7 | 17.6 / 52.1 | 52.9 | 4.62 | 75.2 | 0.00 | 4.8 | 8.3 | – | ok |
| 2620 | 1 | 2715 | 2714 | 4003.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2440 | 1 | 2528 | 2527 | 3271.1 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2340 | 1 | 2424 | 2423 | 1444.3 | 122.58 | 880.2 | 26.2 | 15.3 | 17.6 / 52.0 | 54.7 | 4.59 | 77.6 | 0.01 | 4.7 | 8.7 | – | ok |
| 2430 | 1 | 2518 | 2517 | 2672.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2380 | 1 | 2465 | 2464 | 2590.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2360 | 1 | 2445 | 2444 | 2559.9 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2350 | 1 | 2435 | 2434 | 1479.0 | 127.01 | 922.6 | 23.2 | 14.1 | 17.4 / 52.0 | 56.5 | 4.55 | 80.1 | 0.00 | 4.7 | 8.7 | – | ok |

Per image at 2350 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 49 | 391.9 | 45.4% | 0.07 |
| `postgres:alpine` | 210 | 29.5 | 14.6% | 0.01 |
| `ae3gis.local/suricata` | 65 | 70.8 | 10.9% | 0.34 |
| `ae3gis.local/openplc` | 85 | 51.8 | 10.4% | 0.01 |
| `ae3gis.local/open-vswitch` | 148 | 20.1 | 7.0% | 0.74 |
| `kathara/base` | 707 | 1.2 | 2.0% | 0.00 |
| `ae3gis.local/samba` | 90 | 7.9 | 1.7% | 0.00 |
| `ae3gis.local/vsftpd` | 173 | 3.4 | 1.4% | 0.06 |
| `ae3gis.local/apache` | 66 | 8.8 | 1.4% | 0.07 |
| `ae3gis.local/nginx` | 53 | 10.9 | 1.4% | 0.07 |
| `httpd:alpine` | 63 | 5.0 | 0.7% | 0.00 |
| `kathara/frr` | 238 | 1.2 | 0.7% | 0.00 |
| `ae3gis.local/isc-dhcp` | 181 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 64 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 51 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 47 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 43 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/firehol` | 37 | 3.0 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 38 | 2.0 | 0.2% | 0.00 |
| `ae3gis.local/benign-client` | 27 | 2.7 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
