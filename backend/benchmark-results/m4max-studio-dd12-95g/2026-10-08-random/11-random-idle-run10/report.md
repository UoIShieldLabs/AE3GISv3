# Benchmark: m4max-studio-dd12-95g · random-idle run 10

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, random (seed 10), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1640 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1937.4 of 101850.2 MB used (1.9%) · host CPU 0.1% · Docker processes 329.0 MB · Docker's disk 8.1% used
- **Outcome:** ceiling 2290 hosts · climb: ceiling between 2290 and 2300 hosts (2300 failed) · 2026-10-11T09:38:38 → 2026-10-11T14:08:44

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1640 | 1 | 1700 | 1699 | 665.4 | 81.63 | 730.0 | 28.4 | 16.2 | 16.1 / 51.8 | 47.2 | 4.63 | 49.4 | 0.00 | 4.5 | 8.5 | – | ok |
| 2050 | 1 | 2126 | 2125 | 1129.2 | 103.16 | 1161.1 | – | – | – / – | – | – | – | – | – | – | – | ok |
| 2560 | 1 | 2652 | 2651 | 3583.1 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2300 | 1 | 2384 | 2383 | 3059.1 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2180 | 1 | 2258 | 2257 | 1343.4 | 107.90 | 1255.9 | 26.3 | 15.8 | 17.0 / 52.0 | 52.4 | 4.62 | 74.1 | 0.00 | 4.5 | 9.0 | – | ok |
| 2290 | 1 | 2373 | 2372 | 1338.5 | 120.45 | 843.4 | 25.7 | 15.5 | 17.0 / 51.9 | 53.6 | 4.58 | 76.9 | 0.01 | 4.5 | 9.0 | – | ok |

Per image at 2290 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 46 | 398.0 | 45.4% | 0.07 |
| `postgres:alpine` | 193 | 30.0 | 14.4% | 0.01 |
| `ae3gis.local/openplc` | 89 | 51.8 | 11.4% | 0.01 |
| `ae3gis.local/suricata` | 56 | 71.0 | 9.9% | 0.35 |
| `ae3gis.local/open-vswitch` | 133 | 19.9 | 6.6% | 0.61 |
| `kathara/base` | 682 | 1.2 | 2.1% | 0.00 |
| `ae3gis.local/samba` | 94 | 7.8 | 1.8% | 0.00 |
| `ae3gis.local/nginx` | 65 | 10.8 | 1.7% | 0.06 |
| `ae3gis.local/vsftpd` | 168 | 3.4 | 1.4% | 0.06 |
| `ae3gis.local/apache` | 53 | 8.7 | 1.1% | 0.07 |
| `httpd:alpine` | 60 | 5.0 | 0.7% | 0.00 |
| `kathara/frr` | 206 | 1.2 | 0.6% | 0.00 |
| `ae3gis.local/isc-dhcp` | 187 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 55 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 53 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 46 | 2.8 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 47 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 46 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/firehol` | 41 | 3.0 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 53 | 2.0 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
