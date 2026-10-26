# Benchmark: m4max-studio-dd12-95g · random-idle run 6

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `dc8470732834` · bench
- **Environment fingerprint:** `f945328ce7a0df5c46079251b416f16a2ecb32309cf26caec37f83015401d1fe`
- **Topology:** generated, random (seed 6), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1640 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 2101.1 of 101850.2 MB used (2.1%) · host CPU 0.1% · Docker processes 304.3 MB · Docker's disk 8.6% used
- **Outcome:** ceiling 2360 hosts · climb: 2370 hosts failed (deploy_failed) · stopped: deploy_failed (ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0)) · 2026-10-24T14:59:07 → 2026-10-24T21:33:11

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1640 | 1 | 1700 | 1699 | 555.2 | 87.06 | 557.9 | 29.9 | 16.3 | 17.3 / 51.9 | 46.1 | 4.55 | 52.0 | 0.00 | 4.2 | 8.9 | – | ok |
| 2050 | 1 | 2126 | 2125 | 948.4 | 108.38 | 949.6 | 29.0 | 15.9 | 17.9 / 52.0 | 50.3 | 4.65 | 68.5 | 0.00 | 4.4 | 9.0 | – | ok |
| 2550 | 1 | 2642 | 2641 | 3247.6 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2300 | 1 | 2384 | 2383 | 1293.3 | 113.66 | 1233.1 | 26.7 | 15.9 | 17.4 / 51.9 | 53.4 | 4.70 | 77.2 | 0.00 | 4.3 | 9.1 | – | ok |
| 2540 | 1 | 2631 | 2630 | 2710.4 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2420 | 1 | 2508 | 2507 | 323.6 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: RuntimeError: MachineAlreadyExistsError: Device with name `r0` already exists. — h5_99 exited (137): /usr/local/bin/docker-entrypoint.sh: line 109:  1847 Killed                  sleep 5 |
| 2360 | 1 | 2445 | 2444 | 1285.4 | 128.62 | 675.1 | 25.4 | 15.0 | 17.4 / 52.0 | 53.9 | 4.59 | 77.0 | 0.00 | 4.3 | 9.4 | – | ok |
| 2410 | 1 | 2498 | 2497 | 2234.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2380 | 1 | 2465 | 2464 | 2229.9 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2370 | 1 | 2455 | 2454 | 2993.5 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |

Per image at 2360 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 52 | 397.6 | 48.7% | 0.07 |
| `postgres:alpine` | 182 | 30.0 | 12.8% | 0.01 |
| `ae3gis.local/openplc` | 84 | 51.8 | 10.2% | 0.01 |
| `ae3gis.local/suricata` | 60 | 71.2 | 10.1% | 0.35 |
| `ae3gis.local/open-vswitch` | 131 | 20.3 | 6.3% | 0.62 |
| `kathara/base` | 717 | 1.2 | 2.1% | 0.00 |
| `ae3gis.local/vsftpd` | 200 | 3.4 | 1.6% | 0.06 |
| `ae3gis.local/samba` | 83 | 8.0 | 1.6% | 0.00 |
| `ae3gis.local/nginx` | 54 | 10.9 | 1.4% | 0.07 |
| `ae3gis.local/apache` | 59 | 8.8 | 1.2% | 0.07 |
| `kathara/frr` | 250 | 1.2 | 0.7% | 0.00 |
| `httpd:alpine` | 54 | 5.0 | 0.6% | 0.00 |
| `ae3gis.local/isc-dhcp` | 165 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 55 | 3.1 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 59 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 54 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 49 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 47 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 43 | 2.8 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 47 | 2.0 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
