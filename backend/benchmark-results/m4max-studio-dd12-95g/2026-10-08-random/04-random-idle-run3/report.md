# Benchmark: m4max-studio-dd12-95g · random-idle run 3

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101853.4 MB
- **Kernel / Docker:** 6.10.14-linuxkit · Docker 28.4.0 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `1a66f9c9ecdb` · bench
- **Environment fingerprint:** `dda3a67f640694cd032f0c1b552394a2ec9fe5db7084416971b68484b88dfb62`
- **Topology:** generated, random (seed 3), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 840 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 2035.0 of 101853.4 MB used (2.0%) · host CPU 0.2% · Docker processes 438.2 MB · Docker's disk 6.3% used
- **Outcome:** ceiling 1140 hosts · climb: ceiling between 1140 and 1150 hosts (1150 failed) · 2026-10-09T05:18:55 → 2026-10-09T09:38:41

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 840 | 1 | 872 | 871 | 718.9 | 29.72 | 455.7 | 64.2 | 39.1 | 17.0 / 51.9 | 29.4 | 3.14 | 58.0 | 0.00 | 4.1 | 6.5 | – | ok |
| 1170 | 1 | 1213 | 1212 | 677.1 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| 1000 | 1 | 1037 | 1036 | 990.9 | 39.56 | 648.8 | 35.1 | 28.7 | 15.9 / 51.9 | 30.8 | 3.25 | 46.3 | 0.00 | 4.2 | 6.5 | – | ok |
| 1160 | 1 | 1203 | 1202 | 1861.9 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| 1080 | 1 | 1121 | 1120 | 1243.6 | 47.27 | 857.8 | 26.1 | 22.1 | 16.2 / 51.8 | 32.8 | 3.43 | 49.5 | 0.00 | 4.3 | 6.5 | – | ok |
| 1150 | 1 | 1193 | 1192 | 2491.3 | – | – | – | – | – / – | – | – | – | – | – | – | – | failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')) |
| 1120 | 1 | 1162 | 1161 | 1353.1 | 49.81 | 858.8 | 34.3 | 27.4 | 16.0 / 51.8 | 34.1 | 3.52 | 55.0 | 0.00 | 4.3 | 6.5 | – | ok |
| 1140 | 1 | 1182 | 1181 | 1418.4 | 52.25 | 956.2 | 29.3 | 22.4 | 15.9 / 51.8 | 34.9 | 3.58 | 55.4 | 0.00 | 4.2 | 6.5 | – | ok |

Per image at 1140 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 22 | 387.1 | 45.5% | 0.07 |
| `postgres:alpine` | 92 | 30.1 | 14.8% | 0.01 |
| `ae3gis.local/suricata` | 27 | 70.8 | 10.2% | 0.35 |
| `ae3gis.local/openplc` | 33 | 51.8 | 9.1% | 0.01 |
| `ae3gis.local/open-vswitch` | 73 | 19.8 | 7.7% | 0.38 |
| `kathara/base` | 363 | 1.2 | 2.4% | 0.00 |
| `ae3gis.local/nginx` | 26 | 10.8 | 1.5% | 0.04 |
| `ae3gis.local/vsftpd` | 81 | 3.4 | 1.5% | 0.03 |
| `ae3gis.local/samba` | 36 | 7.7 | 1.5% | 0.00 |
| `ae3gis.local/apache` | 29 | 8.6 | 1.3% | 0.04 |
| `httpd:alpine` | 27 | 5.0 | 0.7% | 0.00 |
| `kathara/frr` | 104 | 1.2 | 0.7% | 0.00 |
| `ae3gis.local/isc-dhcp` | 85 | 1.2 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 31 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 30 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/snort3` | 30 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/firehol` | 22 | 3.0 | 0.4% | 0.00 |
| `ae3gis.local/wazuh-agent` | 31 | 2.0 | 0.3% | 0.00 |
| `ae3gis.local/iptables` | 21 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/benign-client` | 19 | 2.7 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
