# Benchmark: m4-macbook-air · random-idle run 2

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated, random (seed 2), ≤ 200 hosts per subnet, ≤ 48 per switch: each node draws a type of its pool with equal odds, then one of its images. Hosts (13 types): router (frr), switch (base / open-vswitch), firewall (frr / iptables / nftables / firehol), ids (suricata / snort3 / snort2), web-server (httpd:alpine / apache / nginx), file-server (base / samba), ftp-server (vsftpd), database-server (postgres:alpine), dns-server (base), dhcp-server (isc-dhcp), workstation (base / benign-client / wazuh-agent / firefox), plc (base / openplc), hmi (base). Switches: switch (base / open-vswitch). Routers: router (frr), firewall (frr / iptables)
- **Steps:** adaptive from 340 hosts toward 93% memory, done at ≥ 90% (closing 0.6 of the projected gap per step, ≥ 10 hosts, ≤ ×2), failures on a host limit retried lower (descend 0.7), ceiling rerun ×0 · pre 20.0s, settle 60.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 921.0 of 16746.1 MB used (5.5%) · host CPU 0.4% · Docker processes 256.0 MB · Docker's disk 52.8% used
- **Outcome:** ceiling 560 hosts · climb: memory peaked at 90.1% at 560 hosts · 2026-10-06T05:16:31 → 2026-10-06T06:00:13

| Hosts | # | Nodes | Links | Deploy s | Ready s | Destroy s | Marginal MB/node | Docker MB/node | Node cgroup MB (mean / p95) | Host CPU % | Docker cores | Host mem % max | Mem stall % max | Disk MB/node | Disk % max | Delivered | Outcome |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 340 | 1 | 354 | 353 | 67.8 | 3.41 | 55.0 | 27.3 | 15.7 | 17.3 / 60.6 | 46.3 | 3.46 | 65.1 | 0.00 | 3.7 | 54.9 | – | ok |
| 440 | 1 | 458 | 457 | 111.5 | 5.45 | 92.3 | 24.0 | 15.3 | 14.6 / 51.9 | 48.5 | 3.55 | 77.4 | 0.05 | 4.1 | 55.8 | – | ok |
| 500 | 1 | 521 | 520 | 151.4 | 8.85 | 123.3 | 23.0 | 15.0 | 14.6 / 51.7 | 49.9 | 3.61 | 86.3 | 0.11 | 4.1 | 56.2 | – | ok |
| 530 | 1 | 551 | 550 | 176.3 | 7.34 | 139.0 | 21.7 | 14.3 | 14.0 / 51.9 | 50.0 | 3.62 | 88.2 | 0.32 | 4.0 | 56.3 | – | ok |
| 550 | 1 | 572 | 571 | 198.0 | 9.31 | 158.5 | 21.1 | 13.9 | 14.0 / 50.0 | 51.3 | 3.66 | 90.0 | 0.03 | 4.2 | 56.6 | – | ok |
| 560 | 1 | 582 | 581 | 208.6 | 10.65 | 156.7 | 20.4 | 13.6 | 13.8 / 47.9 | 50.5 | 3.61 | 90.1 | 0.05 | 4.1 | 56.6 | – | ok |

Per image at 560 hosts (largest passing scale, mean of 1 run(s)): the container's cgroup memory over settle, its CPU over hold (100 = one core).

| Image | Nodes | Cgroup MB / node | Share of node memory | CPU % / node |
|---|---:|---:|---:|---:|
| `ae3gis.local/firefox` | 9 | 381.1 | 42.7% | 0.44 |
| `postgres:alpine` | 46 | 27.9 | 16.0% | 0.03 |
| `ae3gis.local/suricata` | 15 | 57.1 | 10.7% | 0.47 |
| `ae3gis.local/openplc` | 16 | 46.0 | 9.2% | 0.01 |
| `ae3gis.local/open-vswitch` | 27 | 19.3 | 6.5% | 0.38 |
| `kathara/base` | 175 | 1.2 | 2.6% | 0.00 |
| `ae3gis.local/vsftpd` | 46 | 3.3 | 1.9% | 0.05 |
| `ae3gis.local/apache` | 18 | 8.4 | 1.9% | 0.06 |
| `ae3gis.local/samba` | 17 | 8.7 | 1.8% | 0.00 |
| `ae3gis.local/nginx` | 14 | 8.7 | 1.5% | 0.06 |
| `httpd:alpine` | 16 | 4.8 | 1.0% | 0.00 |
| `kathara/frr` | 55 | 1.2 | 0.8% | 0.00 |
| `ae3gis.local/isc-dhcp` | 40 | 1.1 | 0.6% | 0.00 |
| `ae3gis.local/iptables` | 16 | 2.7 | 0.5% | 0.00 |
| `ae3gis.local/snort3` | 16 | 2.6 | 0.5% | 0.00 |
| `ae3gis.local/firehol` | 14 | 2.9 | 0.5% | 0.00 |
| `ae3gis.local/snort2` | 12 | 2.6 | 0.4% | 0.00 |
| `ae3gis.local/nftables` | 11 | 2.7 | 0.4% | 0.00 |
| `ae3gis.local/benign-client` | 9 | 2.7 | 0.3% | 0.00 |
| `ae3gis.local/wazuh-agent` | 10 | 2.0 | 0.3% | 0.00 |

Marginal memory = (host memory used after deploy − before) ÷ nodes; it includes what a node costs outside its container (containerd shim, VDE switches, kernel). Node cgroup memory is the container's own figure. Ready = every host reached its gateway and a far address. Host CPU, Docker cores (dockerd + containerd + shims + VDE switches) and memory are over the hold window.
