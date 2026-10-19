# Benchmark: m4-macbook-air · census

- **Host:** m4-macbook-air · Docker Desktop · aarch64 · 8 CPUs · 16746.1 MB
- **Kernel / Docker:** 7.0.14-linuxkit · Docker 29.8.1 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `0c8ac80e40b3` · bench
- **Environment fingerprint:** `4fbe53e4ef6b8ff2d0eb491f2fc2a3fbedfb3fffdbb60f1f9709b01c9927bff6`
- **Topology:** generated: 1 server(s), ≤ 200 hosts per subnet, ≤ 48 per switch, hosts `workstation`
- **Steps:** census of 29 cases, 5 nodes each × 1 · pre 20.0s, settle 30.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1174.6 of 16746.1 MB used (7.0%) · host CPU 0.4% · Docker processes 270.1 MB · Docker's disk 52.8% used
- **Outcome:** 27 of 29 cases usable · 2026-10-06T03:38:19 → 2026-10-06T04:21:58

One step per case: 5 nodes of it as the client hosts of a small campus (a base router and switches, one base server). Host MB / node is estimated: the step's memory change less its base nodes, costed at the reference (workstation · kathara/base) per node. Cgroup MB is the nodes' own; CPU is over the hold (100 = one core). Usable: it passed, or only the host ran out of memory.

| Case | Outcome | Deploy s | Ready s | Host MB / node (est.) | Cgroup MB / node | CPU % / node | Disk MB / node | Usable |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `workstation · kathara/base` | ok | 1.8 | 0.02 | 10.3 | 1.6 | 0.00 | 0.5 | yes |
| `router · kathara/frr` | ok | 1.7 | 0.00 | -10.1 | 1.2 | 0.00 | 0.5 | yes |
| `switch · kathara/base` | ok | 1.5 | 0.00 | 16.9 | 1.2 | 0.00 | 0.5 | yes |
| `switch · ae3gis.local/open-vswitch` | ok | 1.5 | 0.00 | 4.8 | 20.8 | 0.43 | 0.5 | yes |
| `firewall · kathara/frr` | ok | 1.5 | 0.00 | -3.0 | 1.2 | 0.00 | 0.5 | yes |
| `firewall · ae3gis.local/iptables` | ok | 1.4 | 0.00 | 14.8 | 5.0 | 0.00 | 0.4 | yes |
| `firewall · ae3gis.local/nftables` | ok | 1.6 | 0.00 | 11.6 | 4.4 | 0.00 | 0.4 | yes |
| `firewall · ae3gis.local/firehol` | ok | 1.7 | 0.00 | 17.2 | 4.7 | 0.00 | 0.4 | yes |
| `ids · ae3gis.local/suricata` | ok | 1.5 | 0.03 | 70.1 | 67.9 | 0.82 | 0.4 | yes |
| `ids · ae3gis.local/snort3` | ok | 1.4 | 0.02 | -0.9 | 5.2 | 0.00 | 0.4 | yes |
| `ids · ae3gis.local/snort2` | ok | 1.6 | 0.02 | 10.1 | 4.9 | 0.00 | 0.4 | yes |
| `ids · ae3gis.local/zeek` | skipped: Building Zeek failed: BuildError: E: Couldn't find any package by regex 'zeekctl-6.0' | – | – | – | – | – | – | no |
| `siem · ae3gis.local/wazuh-manager` | stopped: Docker's disk 100.0% > 90% for 3 sweeps | – | – | – | – | – | – | yes |
| `web-server · httpd:alpine` | ok | 1.7 | 0.03 | 32.1 | 6.1 | 0.01 | 0.4 | yes |
| `web-server · ae3gis.local/apache` | ok | 1.6 | 0.02 | 16.2 | 10.2 | 0.07 | 0.4 | yes |
| `web-server · ae3gis.local/nginx` | ok | 1.5 | 0.02 | 23.0 | 10.0 | 0.06 | 0.4 | yes |
| `file-server · kathara/base` | ok | 1.6 | 0.02 | 13.0 | 1.2 | 0.00 | 0.4 | yes |
| `file-server · ae3gis.local/samba` | ok | 1.9 | 0.02 | 13.1 | 17.3 | 0.00 | 3.3 | yes |
| `ftp-server · ae3gis.local/vsftpd` | ok | 1.5 | 0.03 | 6.0 | 4.6 | 0.06 | 0.4 | yes |
| `database-server · postgres:alpine` | ok | 2.1 | 0.02 | 37.8 | 38.7 | 0.21 | 41.0 | yes |
| `dns-server · kathara/base` | ok | 1.6 | 0.02 | 5.6 | 1.2 | 0.00 | 0.4 | yes |
| `dhcp-server · ae3gis.local/isc-dhcp` | ok | 1.8 | 0.02 | 8.5 | 1.5 | 0.00 | 0.4 | yes |
| `workstation · ae3gis.local/benign-client` | ok | 1.6 | 0.02 | 2.1 | 4.8 | 0.00 | 0.4 | yes |
| `workstation · ae3gis.local/wazuh-agent` | ok | 1.7 | 0.03 | 12.8 | 2.4 | 0.01 | 0.4 | yes |
| `workstation · ae3gis.local/firefox` | ok | 2.2 | 0.05 | 421.6 | 515.0 | 0.75 | 35.9 | yes |
| `attacker · ae3gis.local/malicious-client` | skipped: Builds only for linux/amd64; this host is linux/arm64 | – | – | – | – | – | – | no |
| `plc · kathara/base` | ok | 1.6 | 0.03 | -4.9 | 1.2 | 0.00 | 0.4 | yes |
| `plc · ae3gis.local/openplc` | ok | 2.0 | 0.05 | 47.5 | 57.5 | 0.05 | 0.6 | yes |
| `hmi · kathara/base` | ok | 1.7 | 0.02 | -1.3 | 1.2 | 0.00 | 0.4 | yes |
