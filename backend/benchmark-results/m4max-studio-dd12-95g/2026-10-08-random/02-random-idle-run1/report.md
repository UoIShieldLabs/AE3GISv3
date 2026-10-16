# Benchmark: m4max-studio-dd12-95g · random-idle run 1

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101853.4 MB
- **Kernel / Docker:** 6.10.14-linuxkit · Docker 28.4.0 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `1a66f9c9ecdb` · bench
- **Environment fingerprint:** `dda3a67f640694cd032f0c1b552394a2ec9fe5db7084416971b68484b88dfb62`
- **Topology:** generated, random (seed 1), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 100 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1994.2 of 101853.4 MB used (2.0%) · host CPU 0.2% · Docker processes 245.2 MB · Docker's disk 6.3% used
- **Outcome:** ceiling 1140 hosts · climb: 1150 hosts failed (memory) · stopped: memory (host memory 96.4% > 95.0% for 3 sweeps) · 2026-10-08T19:08:27 → 2026-10-09T01:03:40

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 107 | 106 | 13.2 | 2.19 | 7.3 | 38.5 | 36.5 | 18.4 / 65.0 | 2.4 | 0.15 | 6.2 | 0.00 | 4.5 | 6.3 | – | ok |
| 200 | 1 | 209 | 208 | 38.8 | 0.36 | 24.0 | 51.9 | 40.3 | 19.2 / 63.2 | 19.0 | 2.17 | 16.7 | 0.00 | 5.3 | 6.4 | – | ok |
| 400 | 1 | 416 | 415 | 150.3 | 1.41 | 97.6 | 47.0 | 30.5 | 20.6 / 70.8 | 22.8 | 2.48 | 30.1 | 0.00 | 5.7 | 6.4 | – | ok |
| 800 | 1 | 830 | 829 | 656.4 | 34.23 | 446.2 | 43.7 | 27.1 | 18.3 / 52.1 | 27.6 | 2.92 | 51.6 | 0.00 | 4.7 | 6.5 | – | ok |
| 1340 | 1 | 1389 | 1388 | 615.0 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| 1070 | 1 | 1111 | 1110 | 1284.5 | 39.37 | 856.3 | 44.0 | 32.3 | 17.6 / 52.2 | 30.7 | 3.19 | 51.9 | 0.00 | 4.5 | 6.5 | – | ok |
| 1330 | 1 | 1379 | 1378 | 3489.2 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 1200 | 1 | 1244 | 1243 | 2723.6 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 1140 | 1 | 1182 | 1181 | 1478.1 | 44.14 | 1020.5 | 36.9 | 27.5 | 17.5 / 52.1 | 31.4 | 3.24 | 49.5 | 0.00 | 4.5 | 6.6 | – | ok |
| 1190 | 1 | 1233 | 1232 | 2684.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 1160 | 1 | 1203 | 1202 | 2544.9 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 1150 | 1 | 1193 | 1192 | 1443.5 | 49.98 | 485.4 | – | – | – / – | – | – | – | – | – | – | – | stopped: host memory 96.4% > 95.0% for 3 sweeps |

Per image at 1140 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 24 | 387.5 | 45.0% | 0.07 |
| `postgres:alpine` | 95 | 30.1 | 13.8% | 0.01 |
| `ae3gis.local/suricata` | 33 | 70.8 | 11.3% | 0.34 |
| `ae3gis.local/openplc` | 45 | 51.8 | 11.3% | 0.01 |
| `ae3gis.local/open-vswitch` | 66 | 21.2 | 6.8% | 0.38 |
| `kathara/base` | 326 | 1.2 | 1.9% | 0.00 |
| `ae3gis.local/nginx` | 33 | 10.8 | 1.7% | 0.04 |
| `ae3gis.local/vsftpd` | 94 | 3.5 | 1.6% | 0.03 |
| `ae3gis.local/samba` | 42 | 7.7 | 1.6% | 0.00 |
| `ae3gis.local/apache` | 23 | 8.6 | 1.0% | 0.04 |
| `kathara/frr` | 138 | 1.2 | 0.8% | 0.00 |
| `httpd:alpine` | 27 | 5.0 | 0.7% | 0.00 |
| `ae3gis.local/isc-dhcp` | 79 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 34 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 26 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/firehol` | 21 | 3.0 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 21 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 20 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 21 | 2.0 | 0.2% | 0.00 |
| `ae3gis.local/nftables` | 14 | 2.7 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
