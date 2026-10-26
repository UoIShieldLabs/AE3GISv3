# Benchmark: m4max-studio-dd12-95g · random-idle run 2

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `dc8470732834` · bench
- **Environment fingerprint:** `f945328ce7a0df5c46079251b416f16a2ecb32309cf26caec37f83015401d1fe`
- **Topology:** generated, random (seed 2), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1560 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1878.6 of 101850.2 MB used (1.9%) · host CPU 0.1% · Docker processes 271.5 MB · Docker's disk 7.3% used
- **Outcome:** ceiling 2320 hosts · climb: 2330 hosts failed (deploy_failed) · stopped: deploy_failed (ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0)) · 2026-10-24T05:57:04 → 2026-10-24T13:48:11

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1560 | 1 | 1617 | 1616 | 522.9 | 73.30 | 519.1 | 29.7 | 16.2 | 17.2 / 52.1 | 46.5 | 4.63 | 49.1 | 0.00 | 3.9 | 7.6 | – | ok |
| 1950 | 1 | 2021 | 2020 | 882.4 | 101.70 | 863.2 | 27.5 | 15.9 | 16.5 / 52.1 | 49.4 | 4.62 | 62.2 | 0.00 | 3.9 | 7.6 | – | ok |
| 2437 | 1 | 2525 | 2524 | 3014.0 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2190 | 1 | 2268 | 2267 | 1202.8 | 115.89 | 1179.4 | 26.0 | 15.4 | 16.2 / 51.9 | 51.8 | 4.58 | 72.7 | 0.00 | 3.9 | 7.7 | – | ok |
| 2430 | 1 | 2518 | 2517 | 3268.9 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2310 | 1 | 2394 | 2393 | 1213.4 | 129.97 | 643.9 | 25.3 | 15.2 | 16.2 / 51.9 | 53.9 | 4.65 | 76.7 | 0.01 | 4.0 | 8.1 | – | ok |
| 2420 | 1 | 2508 | 2507 | 2216.2 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2360 | 1 | 2445 | 2444 | 3038.7 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2340 | 1 | 2424 | 2423 | 2913.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2320 | 1 | 2404 | 2403 | 1285.2 | 124.80 | 668.0 | 24.5 | 15.0 | 16.1 / 52.0 | 54.7 | 4.61 | 79.9 | 0.00 | 4.0 | 8.7 | – | ok |
| 2330 | 1 | 2414 | 2413 | 2140.7 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |

Per image at 2320 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 44 | 395.5 | 45.0% | 0.06 |
| `postgres:alpine` | 168 | 29.9 | 13.0% | 0.01 |
| `ae3gis.local/suricata` | 62 | 70.8 | 11.4% | 0.35 |
| `ae3gis.local/openplc` | 83 | 51.8 | 11.1% | 0.01 |
| `ae3gis.local/open-vswitch` | 128 | 19.5 | 6.5% | 0.69 |
| `kathara/base` | 716 | 1.2 | 2.3% | 0.00 |
| `ae3gis.local/samba` | 89 | 8.0 | 1.8% | 0.00 |
| `ae3gis.local/vsftpd` | 191 | 3.4 | 1.7% | 0.06 |
| `ae3gis.local/nginx` | 54 | 10.9 | 1.5% | 0.06 |
| `ae3gis.local/apache` | 55 | 8.8 | 1.2% | 0.07 |
| `kathara/frr` | 237 | 1.2 | 0.8% | 0.00 |
| `httpd:alpine` | 58 | 5.0 | 0.7% | 0.01 |
| `ae3gis.local/snort3` | 69 | 2.7 | 0.5% | 0.00 |
| `ae3gis.local/isc-dhcp` | 159 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 63 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 53 | 3.1 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 59 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 42 | 2.8 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 34 | 2.7 | 0.2% | 0.00 |
| `ae3gis.local/wazuh-agent` | 40 | 2.1 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
