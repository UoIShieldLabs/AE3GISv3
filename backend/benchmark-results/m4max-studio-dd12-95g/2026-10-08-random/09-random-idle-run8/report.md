# Benchmark: m4max-studio-dd12-95g · random-idle run 8

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `dc8470732834` · bench
- **Environment fingerprint:** `f945328ce7a0df5c46079251b416f16a2ecb32309cf26caec37f83015401d1fe`
- **Topology:** generated, random (seed 8), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1660 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 2101.4 of 101850.2 MB used (2.1%) · host CPU 8.0% · Docker processes 317.2 MB · Docker's disk 9.2% used
- **Outcome:** ceiling 2320 hosts · climb: ceiling between 2320 and 2330 hosts (2330 failed) · 2026-10-24T21:34:32 → 2026-10-25T01:48:23

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1660 | 1 | 1722 | 1721 | 606.3 | 87.14 | 591.7 | 28.4 | 16.3 | 16.1 / 52.2 | 47.5 | 4.55 | 50.2 | 0.00 | 3.7 | 9.5 | – | ok |
| 2075 | 1 | 2151 | 2150 | 1027.5 | 108.44 | 1027.0 | 27.4 | 16.1 | 16.0 / 52.0 | 51.3 | 4.68 | 65.6 | 0.00 | 3.7 | 9.6 | – | ok |
| 2590 | 1 | 2682 | 2681 | 3560.7 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2330 | 1 | 2414 | 2413 | 2770.8 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ReadTimeout: UnixHTTPConnectionPool(host='localhost', port=None): Read timed out. (read timeout=300.0) |
| 2200 | 1 | 2279 | 2278 | 1231.4 | 115.18 | 937.9 | 26.1 | 15.6 | 16.3 / 52.2 | 53.7 | 4.74 | 74.0 | 0.00 | 3.8 | 9.7 | – | ok |
| 2320 | 1 | 2404 | 2403 | 1277.4 | 124.98 | 656.1 | 25.3 | 15.9 | 16.0 / 52.1 | 54.0 | 4.62 | 77.8 | 0.00 | 3.8 | 9.7 | – | ok |

Per image at 2320 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 42 | 398.7 | 43.4% | 0.07 |
| `ae3gis.local/suricata` | 71 | 70.9 | 13.0% | 0.35 |
| `postgres:alpine` | 163 | 30.0 | 12.7% | 0.01 |
| `ae3gis.local/openplc` | 83 | 51.8 | 11.1% | 0.01 |
| `ae3gis.local/open-vswitch` | 124 | 20.4 | 6.5% | 0.60 |
| `kathara/base` | 720 | 1.2 | 2.3% | 0.00 |
| `ae3gis.local/vsftpd` | 197 | 3.4 | 1.7% | 0.06 |
| `ae3gis.local/samba` | 80 | 7.8 | 1.6% | 0.00 |
| `ae3gis.local/nginx` | 56 | 10.9 | 1.6% | 0.07 |
| `ae3gis.local/apache` | 70 | 8.7 | 1.6% | 0.07 |
| `httpd:alpine` | 59 | 5.0 | 0.8% | 0.00 |
| `kathara/frr` | 235 | 1.2 | 0.7% | 0.00 |
| `ae3gis.local/isc-dhcp` | 162 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 56 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 59 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 51 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/benign-client` | 49 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 48 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 39 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 40 | 2.0 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
