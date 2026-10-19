# Benchmark: microsoft-surface-7 · random-idle run 7

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `704de102e05249dc78e3ef4356455b5c320a16e8822c258dbe8d26d816384402`
- **Topology:** generated, random (seed 7), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 270 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1055.0 of 16605.5 MB used (6.3%) · host CPU 2.1% · Docker processes 401.3 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 460 hosts · climb: memory peaked at 91.2% at 460 hosts · 2026-10-09T06:20:08 → 2026-10-09T08:56:40

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 270 | 1 | 283 | 282 | 495.3 | 4.83 | 279.6 | 28.0 | 29.6 | 9.0 / 50.5 | 15.4 | 0.90 | 56.8 | 0.00 | 3.2 | 13.4 | – | ok |
| 400 | 1 | 416 | 415 | 915.2 | 10.09 | 657.2 | 19.1 | 20.7 | 9.0 / 51.7 | 53.6 | 3.29 | 67.4 | 0.00 | 3.0 | 13.4 | – | ok |
| 480 | 1 | 500 | 499 | 1370.3 | 12.53 | 926.0 | – | – | – / – | – | – | – | – | – | – | – | stopped: host memory 95.1% > 95.0% for 3 sweeps |
| 440 | 1 | 458 | 457 | 1179.7 | 14.39 | 770.7 | 26.3 | 28.5 | 8.4 / 39.6 | 34.1 | 1.99 | 76.1 | 0.14 | 2.8 | 13.4 | – | ok |
| 460 | 1 | 480 | 479 | 1233.6 | 10.46 | 821.9 | 25.1 | 27.4 | 8.2 / 41.7 | 63.9 | 3.71 | 91.2 | 0.00 | 2.8 | 13.4 | – | ok |

Per image at 460 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `postgres:alpine` | 28 | 31.0 | 22.0% | 0.03 |
| `ae3gis.local/suricata` | 12 | 55.6 | 16.9% | 0.99 |
| `ae3gis.local/openplc` | 11 | 53.1 | 14.8% | 0.04 |
| `ae3gis.local/firefox` | 1 | 432.9 | 10.9% | 0.83 |
| `ae3gis.local/open-vswitch` | 26 | 11.5 | 7.5% | 0.78 |
| `kathara/base` | 140 | 1.1 | 3.8% | 0.00 |
| `ae3gis.local/vsftpd` | 40 | 3.5 | 3.6% | 0.10 |
| `ae3gis.local/samba` | 13 | 10.1 | 3.3% | 0.01 |
| `ae3gis.local/nginx` | 11 | 9.7 | 2.7% | 0.08 |
| `ae3gis.local/malicious-client` | 34 | 2.9 | 2.5% | 0.00 |
| `httpd:alpine` | 16 | 5.4 | 2.2% | 0.01 |
| `ae3gis.local/apache` | 7 | 10.9 | 1.9% | 0.08 |
| `ae3gis.local/snort2` | 17 | 3.2 | 1.4% | 0.00 |
| `ae3gis.local/benign-client` | 16 | 2.8 | 1.1% | 0.00 |
| `kathara/frr` | 35 | 1.2 | 1.1% | 0.00 |
| `ae3gis.local/snort3` | 11 | 3.2 | 0.9% | 0.00 |
| `ae3gis.local/iptables` | 10 | 3.4 | 0.9% | 0.00 |
| `ae3gis.local/isc-dhcp` | 30 | 1.1 | 0.8% | 0.00 |
| `ae3gis.local/nftables` | 11 | 2.9 | 0.8% | 0.00 |
| `ae3gis.local/firehol` | 5 | 3.7 | 0.5% | 0.00 |
| `ae3gis.local/wazuh-agent` | 6 | 2.3 | 0.3% | 0.01 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
