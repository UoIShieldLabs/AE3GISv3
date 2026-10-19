# Benchmark: microsoft-surface-7 · random-idle run 8

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `704de102e05249dc78e3ef4356455b5c320a16e8822c258dbe8d26d816384402`
- **Topology:** generated, random (seed 8), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 320 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1041.2 of 16605.5 MB used (6.3%) · host CPU 2.3% · Docker processes 381.1 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 350 hosts · climb: memory peaked at 90.0% at 350 hosts · 2026-10-09T08:59:44 → 2026-10-09T09:47:56

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 320 | 1 | 334 | 333 | 733.3 | 9.14 | 435.8 | 36.7 | 29.5 | 17.9 / 54.4 | 21.5 | 1.20 | 82.3 | 0.00 | 3.4 | 13.4 | – | ok |
| 350 | 1 | 365 | 364 | 864.5 | 13.50 | 528.9 | 28.9 | 23.6 | 15.9 / 53.7 | 24.6 | 1.38 | 90.0 | 2.42 | 3.1 | 13.4 | – | ok |

Per image at 350 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 6 | 404.3 | 41.9% | 0.33 |
| `ae3gis.local/openplc` | 19 | 52.0 | 17.0% | 0.03 |
| `postgres:alpine` | 19 | 34.7 | 11.4% | 0.03 |
| `ae3gis.local/suricata` | 12 | 54.5 | 11.3% | 0.69 |
| `ae3gis.local/open-vswitch` | 26 | 12.3 | 5.5% | 0.51 |
| `kathara/base` | 97 | 1.1 | 1.8% | 0.00 |
| `ae3gis.local/vsftpd` | 26 | 3.8 | 1.7% | 0.07 |
| `ae3gis.local/samba` | 8 | 10.6 | 1.5% | 0.00 |
| `ae3gis.local/apache` | 8 | 10.3 | 1.4% | 0.08 |
| `ae3gis.local/malicious-client` | 21 | 3.0 | 1.1% | 0.00 |
| `ae3gis.local/nginx` | 6 | 10.3 | 1.1% | 0.09 |
| `kathara/frr` | 40 | 1.2 | 0.8% | 0.00 |
| `httpd:alpine` | 8 | 5.7 | 0.8% | 0.00 |
| `ae3gis.local/firehol` | 10 | 3.6 | 0.6% | 0.00 |
| `ae3gis.local/isc-dhcp` | 28 | 1.1 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 9 | 3.0 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 6 | 3.3 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 8 | 2.0 | 0.3% | 0.01 |
| `ae3gis.local/iptables` | 3 | 4.0 | 0.2% | 0.00 |
| `ae3gis.local/nftables` | 3 | 3.4 | 0.2% | 0.00 |
| `ae3gis.local/benign-client` | 2 | 3.1 | 0.1% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
