# Benchmark: microsoft-surface-7 · random-idle run 1

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `2c8a6d1851b04fe9809915716131e3830beec9616c320afb9f3900302ff61b78`
- **Topology:** generated, random (seed 1), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (14 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), attacker (malicious-client), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 100 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 964.8 of 16605.5 MB used (5.8%) · host CPU 2.8% · Docker processes 345.5 MB · Docker's disk 13.3% used
- **Outcome:** ceiling 460 hosts · climb: 470 hosts failed (deploy_slow) · stopped: deploy_slow (deploy took 1944s) · 2026-10-08T18:16:02 → 2026-10-08T23:00:14

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 100 | 1 | 107 | 106 | 98.3 | 0.77 | 51.9 | 34.8 | 31.1 | 15.0 / 56.7 | 10.2 | 0.62 | 29.5 | 0.00 | 4.4 | 13.3 | – | ok |
| 200 | 1 | 209 | 208 | 288.5 | 6.37 | 148.3 | 34.3 | 26.7 | 18.4 / 52.2 | 27.9 | 1.71 | 56.5 | 0.00 | 5.1 | 13.4 | – | ok |
| 310 | 1 | 324 | 323 | 581.5 | 6.41 | 337.0 | 24.8 | 16.9 | 18.7 / 55.3 | 80.5 | 4.97 | 73.9 | 0.00 | 4.4 | 13.4 | – | ok |
| 380 | 1 | 395 | 394 | 1003.4 | 9.84 | 541.5 | 21.8 | 16.0 | 16.1 / 50.2 | – | – | – | – | 5.1 | – | – | ok |
| 410 | 1 | 428 | 427 | 1061.6 | 12.18 | 647.0 | 20.5 | 14.4 | 14.5 / 39.3 | 81.6 | 4.91 | 80.8 | 0.07 | 5.3 | 13.5 | – | ok |
| 440 | 1 | 458 | 457 | 1298.7 | 19.18 | 766.0 | 19.7 | 16.1 | 12.1 / 30.4 | – | – | – | – | 5.1 | – | – | ok |
| 480 | 1 | 500 | 499 | 1772.0 | 27.76 | 1182.5 | – | – | – / – | – | – | – | – | – | – | – | stopped: host memory 95.0% > 95.0% for 3 sweeps |
| 460 | 1 | 480 | 479 | 1761.2 | 56.68 | 1310.3 | 18.6 | 17.9 | 11.3 / 28.9 | – | – | – | – | 5.1 | – | – | ok |
| 470 | 1 | 490 | 489 | 1943.8 | 16.61 | 932.9 | – | – | – / – | – | – | – | – | – | – | – | stopped: deploy took 1944s |

Per image at 460 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 12 | 196.4 | 43.6% | – |
| `postgres:alpine` | 43 | 23.2 | 18.5% | – |
| `ae3gis.local/suricata` | 14 | 31.7 | 8.2% | – |
| `ae3gis.local/openplc` | 14 | 26.0 | 6.8% | – |
| `ae3gis.local/open-vswitch` | 24 | 10.9 | 4.9% | – |
| `ae3gis.local/samba` | 21 | 9.3 | 3.6% | – |
| `kathara/base` | 134 | 1.1 | 2.7% | – |
| `ae3gis.local/vsftpd` | 40 | 3.1 | 2.3% | – |
| `httpd:alpine` | 19 | 4.9 | 1.7% | – |
| `ae3gis.local/nginx` | 11 | 7.1 | 1.4% | – |
| `ae3gis.local/malicious-client` | 25 | 2.6 | 1.2% | – |
| `ae3gis.local/apache` | 5 | 9.7 | 0.9% | – |
| `kathara/frr` | 39 | 1.1 | 0.8% | – |
| `ae3gis.local/snort3` | 15 | 2.8 | 0.8% | – |
| `ae3gis.local/firehol` | 10 | 3.5 | 0.7% | – |
| `ae3gis.local/snort2` | 11 | 2.7 | 0.5% | – |
| `ae3gis.local/iptables` | 8 | 3.2 | 0.5% | – |
| `ae3gis.local/isc-dhcp` | 22 | 1.1 | 0.4% | – |
| `ae3gis.local/nftables` | 5 | 2.8 | 0.3% | – |
| `ae3gis.local/benign-client` | 4 | 2.3 | 0.2% | – |
| `ae3gis.local/wazuh-agent` | 4 | 1.4 | 0.1% | – |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
