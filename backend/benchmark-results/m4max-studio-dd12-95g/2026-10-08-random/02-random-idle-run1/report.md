# Benchmark: m4max-studio-dd12-95g · random-idle run 1

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `dc8470732834` · bench
- **Environment fingerprint:** `f945328ce7a0df5c46079251b416f16a2ecb32309cf26caec37f83015401d1fe`
- **Topology:** generated, random (seed 1), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 100 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1606.4 of 101850.2 MB used (1.6%) · host CPU 0.1% · Docker processes 255.8 MB · Docker's disk 7.0% used
- **Outcome:** ceiling 2240 hosts · 2026-10-24T00:06:38 → 2026-10-24T05:53:34

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 107 | 106 | 8.4 | 6.12 | 4.7 | 29.0 | 16.3 | 21.1 / 68.3 | 1.9 | 0.13 | 4.7 | 0.00 | 4.4 | 7.0 | – | ok |
| 120 | 1 | 127 | 126 | 10.2 | 4.19 | 5.8 | 24.4 | 15.7 | 15.7 / 51.6 | 2.6 | 0.18 | 5.6 | 0.00 | 5.0 | 7.0 | – | ok |
| 150 | 1 | 158 | 157 | 13.6 | 4.25 | 7.6 | 28.2 | 15.8 | 17.2 / 54.6 | 2.9 | 0.19 | 6.8 | 0.00 | 5.1 | 7.0 | – | ok |
| 187 | 1 | 195 | 194 | 17.9 | 0.40 | 10.3 | 29.0 | 15.8 | 19.7 / 70.7 | 3.5 | 0.23 | 8.6 | 0.00 | 5.2 | 7.0 | – | ok |
| 230 | 1 | 241 | 240 | 22.7 | 0.84 | 14.1 | 31.1 | 15.8 | 19.6 / 70.7 | 17.9 | 1.88 | 10.3 | 0.00 | 5.0 | 7.0 | – | ok |
| 287 | 1 | 300 | 299 | 29.8 | 1.06 | 20.5 | 31.0 | 15.5 | 19.0 / 70.7 | 36.5 | 4.02 | 11.8 | 0.00 | 4.4 | 7.1 | – | ok |
| 358 | 1 | 373 | 372 | 40.7 | 1.34 | 30.4 | 30.1 | 15.7 | 19.7 / 70.7 | 37.4 | 4.08 | 14.3 | 0.00 | 5.3 | 7.1 | – | ok |
| 447 | 1 | 465 | 464 | 58.4 | 1.74 | 45.6 | 31.2 | 15.7 | 20.5 / 70.8 | 38.4 | 4.13 | 17.7 | 0.00 | 5.3 | 7.1 | – | ok |
| 558 | 1 | 580 | 579 | 80.8 | 2.18 | 68.7 | 28.0 | 15.7 | 17.9 / 51.9 | 40.4 | 4.31 | 19.8 | 0.00 | 5.0 | 7.1 | – | ok |
| 697 | 1 | 725 | 724 | 119.7 | 24.82 | 107.2 | 29.2 | 15.5 | 18.9 / 52.1 | 41.3 | 4.38 | 24.9 | 0.00 | 5.0 | 7.2 | – | ok |
| 870 | 1 | 904 | 903 | 182.9 | 38.33 | 160.9 | 29.2 | 15.7 | 19.0 / 52.2 | 43.0 | 4.46 | 31.1 | 0.00 | 4.6 | 7.2 | – | ok |
| 1087 | 1 | 1128 | 1127 | 273.1 | 42.24 | 252.1 | 27.9 | 15.7 | 17.9 / 52.0 | 45.4 | 4.61 | 37.0 | 0.00 | 4.5 | 7.2 | – | ok |
| 1358 | 1 | 1408 | 1407 | 429.3 | 55.85 | 399.8 | 28.9 | 15.7 | 18.6 / 64.3 | 46.4 | 4.60 | 47.0 | 0.00 | 4.5 | 7.3 | – | ok |
| 1697 | 1 | 1760 | 1759 | 686.3 | 78.37 | 648.6 | 30.5 | 15.7 | 19.6 / 70.8 | 48.5 | 4.60 | 61.2 | 0.00 | 4.7 | 7.4 | – | ok |
| 2120 | 1 | 2197 | 2196 | 1091.9 | 104.93 | 1069.8 | 29.9 | 16.0 | 19.2 / 56.0 | 51.6 | 4.59 | 75.6 | 0.00 | 4.7 | 7.5 | – | ok |
| 2460 | 1 | 2550 | 2549 | 3180.0 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2290 | 1 | 2373 | 2372 | 2260.3 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2200 | 1 | 2279 | 2278 | 1145.0 | 112.57 | 584.0 | 27.1 | 15.7 | 19.5 / 70.8 | 53.8 | 4.63 | 79.1 | 0.00 | 4.8 | 7.8 | – | ok |
| 2280 | 1 | 2363 | 2362 | 2000.5 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2240 | 1 | 2321 | 2320 | 1314.8 | 122.20 | 630.7 | 21.9 | 10.9 | 19.3 / 70.8 | 54.4 | 4.60 | 80.2 | 0.01 | 4.7 | 7.8 | – | ok |

Per image at 2240 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 58 | 396.8 | 51.4% | 0.06 |
| `postgres:alpine` | 192 | 29.9 | 12.8% | 0.01 |
| `ae3gis.local/openplc` | 86 | 51.8 | 9.9% | 0.01 |
| `ae3gis.local/suricata` | 58 | 71.2 | 9.2% | 0.35 |
| `ae3gis.local/open-vswitch` | 127 | 21.3 | 6.0% | 0.72 |
| `kathara/base` | 660 | 1.2 | 1.8% | 0.00 |
| `ae3gis.local/samba` | 89 | 8.1 | 1.6% | 0.00 |
| `ae3gis.local/nginx` | 64 | 10.9 | 1.6% | 0.06 |
| `ae3gis.local/vsftpd` | 164 | 3.4 | 1.2% | 0.06 |
| `ae3gis.local/apache` | 46 | 8.7 | 0.9% | 0.07 |
| `kathara/frr` | 253 | 1.2 | 0.7% | 0.00 |
| `httpd:alpine` | 53 | 5.0 | 0.6% | 0.00 |
| `ae3gis.local/isc-dhcp` | 161 | 1.2 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 66 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 57 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 44 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 43 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/firehol` | 37 | 3.0 | 0.2% | 0.00 |
| `ae3gis.local/nftables` | 30 | 2.7 | 0.2% | 0.00 |
| `ae3gis.local/wazuh-agent` | 33 | 2.0 | 0.1% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
