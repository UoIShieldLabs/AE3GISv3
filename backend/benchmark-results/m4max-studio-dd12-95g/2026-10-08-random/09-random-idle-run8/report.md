# Benchmark: m4max-studio-dd12-95g · random-idle run 8

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101850.2 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `ce3d1d4d6876` · bench
- **Environment fingerprint:** `0e8f6a947b5a7ff1a1d9e23754bbb6e07cb99957fc025824705c857fce7e0e9f`
- **Topology:** generated, random (seed 8), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 1660 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×1.25), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1992.6 of 101850.2 MB used (1.9%) · host CPU 0.1% · Docker processes 321.6 MB · Docker's disk 7.8% used
- **Outcome:** ceiling 2070 hosts · climb: ceiling between 2070 and 2075 hosts (2075 failed) · 2026-10-10T23:45:08 → 2026-10-11T01:46:38

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1660 | 1 | 1722 | 1721 | 680.7 | 82.33 | 748.9 | 28.2 | 16.3 | 16.2 / 52.1 | 47.2 | 4.58 | 49.8 | 0.00 | 3.7 | 8.1 | – | ok |
| 2075 | 1 | 2151 | 2150 | 793.9 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| 1870 | 1 | 1939 | 1938 | 934.9 | 97.64 | 979.8 | 26.3 | 15.1 | 15.6 / 52.0 | 48.7 | 4.47 | 58.0 | 0.00 | 3.6 | 8.1 | – | ok |
| 2070 | 1 | 2146 | 2145 | 1187.1 | 111.04 | 1180.5 | 26.1 | 15.9 | 16.0 / 52.0 | 50.7 | 4.56 | 65.2 | 0.00 | 3.7 | 8.2 | – | ok |

Per image at 2070 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 37 | 399.1 | 42.9% | 0.08 |
| `ae3gis.local/suricata` | 64 | 70.8 | 13.2% | 0.35 |
| `postgres:alpine` | 140 | 30.0 | 12.2% | 0.01 |
| `ae3gis.local/openplc` | 77 | 51.8 | 11.6% | 0.01 |
| `ae3gis.local/open-vswitch` | 118 | 20.2 | 6.9% | 0.48 |
| `kathara/base` | 638 | 1.2 | 2.3% | 0.00 |
| `ae3gis.local/vsftpd` | 178 | 3.5 | 1.8% | 0.05 |
| `ae3gis.local/apache` | 64 | 8.6 | 1.6% | 0.06 |
| `ae3gis.local/samba` | 70 | 7.8 | 1.6% | 0.00 |
| `ae3gis.local/nginx` | 49 | 10.9 | 1.5% | 0.06 |
| `kathara/frr` | 208 | 1.2 | 0.7% | 0.00 |
| `httpd:alpine` | 51 | 5.0 | 0.7% | 0.00 |
| `ae3gis.local/isc-dhcp` | 149 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 47 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/snort2` | 50 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 47 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/benign-client` | 46 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/iptables` | 41 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/nftables` | 36 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 36 | 2.0 | 0.2% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
