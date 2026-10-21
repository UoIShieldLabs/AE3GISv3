# Benchmark: microsoft-surface-7 · census

- **Host:** microsoft-surface-7 · Docker Desktop · x86_64 · 8 CPUs · 16605.5 MB
- **Kernel / Docker:** 6.6.87.2-microsoft-standard-WSL2 · Docker 28.3.3 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `d3ccc923637a` · bench
- **Environment fingerprint:** `9476f028774056264e0bb3c49269b67e9730142e0fd03421b00df0a179d93165`
- **Topology:** generated: 1 server(s), ≤ 200 hosts per subnet, ≤ 48 per switch, hosts `workstation`
- **Steps:** census of 29 cases, 5 nodes each × 1 · pre 20.0s, settle 30.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1574.9 of 16605.5 MB used (9.5%) · host CPU 1.6% · Docker processes 907.7 MB · Docker's disk 13.3% used
- **Outcome:** 28 of 29 cases usable · 2026-10-08T17:22:36 → 2026-10-08T18:13:26

One step per case: 5 nodes of it as the client hosts of a small campus (a base router and switches, one base server). Host MB / node is estimated: the step's memory change less its base nodes, costed at the reference (workstation · kathara/base) per node. Cgroup MB is the nodes' own; CPU is over the hold (100 = one core). Usable: it passed, or only the host ran out of memory.

| Case | Outcome | Deploy s | Ready s | Host MB / node (est.) | Cgroup MB / node | CPU % / node | Disk MB / node | Usable |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `workstation · kathara/base` | ok | 5.3 | 0.04 | -19.9 | 2.6 | 0.00 | 0.5 | yes |
| `router · kathara/frr` | ok | 5.2 | 0.01 | 40.4 | 1.0 | 0.00 | 0.5 | yes |
| `switch · kathara/base` | ok | 5.3 | 0.01 | 34.1 | 1.0 | 0.00 | 0.5 | yes |
| `switch · ae3gis.local/open-vswitch` | ok | 5.1 | 0.01 | 76.3 | 12.5 | 0.40 | 0.5 | yes |
| `firewall · kathara/frr` | ok | 5.3 | 0.01 | 55.1 | 1.0 | 0.00 | 0.5 | yes |
| `firewall · ae3gis.local/iptables` | ok | 4.8 | 0.01 | 42.3 | 3.7 | 0.00 | 0.5 | yes |
| `firewall · ae3gis.local/nftables` | ok | 5.0 | 0.01 | 36.0 | 3.7 | 0.00 | 0.4 | yes |
| `firewall · ae3gis.local/firehol` | ok | 4.7 | 0.00 | 60.9 | 4.6 | 0.00 | 0.4 | yes |
| `ids · ae3gis.local/suricata` | ok | 4.9 | 0.03 | 116.7 | 60.7 | 0.69 | 0.4 | yes |
| `ids · ae3gis.local/snort3` | ok | 4.7 | 0.03 | 44.6 | 3.5 | 0.00 | 0.4 | yes |
| `ids · ae3gis.local/snort2` | ok | 4.9 | 0.03 | 33.9 | 3.5 | 0.00 | 0.4 | yes |
| `ids · ae3gis.local/zeek` | skipped: Building Zeek failed: BuildError: E: Couldn't find any package by regex 'zeekctl-6.0' | – | – | – | – | – | – | no |
| `siem · ae3gis.local/wazuh-manager` | ok | 5.1 | 0.05 | 291.7 | 308.9 | 96.49 | 911.1 | yes |
| `web-server · httpd:alpine` | ok | 7.3 | 0.03 | 49.3 | 5.0 | 0.01 | 0.4 | yes |
| `web-server · ae3gis.local/apache` | ok | 5.1 | 0.02 | 62.1 | 9.9 | 0.07 | 0.4 | yes |
| `web-server · ae3gis.local/nginx` | ok | 5.1 | 0.03 | 32.0 | 9.5 | 0.06 | 0.4 | yes |
| `file-server · kathara/base` | ok | 5.0 | 0.03 | 64.3 | 1.0 | 0.00 | 0.4 | yes |
| `file-server · ae3gis.local/samba` | ok | 4.9 | 0.02 | 63.3 | 13.2 | 0.00 | 3.3 | yes |
| `ftp-server · ae3gis.local/vsftpd` | ok | 4.5 | 0.02 | 55.2 | 4.1 | 0.05 | 0.4 | yes |
| `database-server · postgres:alpine` | ok | 5.1 | 0.04 | 60.2 | 40.9 | 0.20 | 41.0 | yes |
| `dns-server · kathara/base` | ok | 4.7 | 0.03 | 46.9 | 1.0 | 0.00 | 0.4 | yes |
| `dhcp-server · ae3gis.local/isc-dhcp` | ok | 4.7 | 0.04 | 55.6 | 1.2 | 0.00 | 0.4 | yes |
| `workstation · ae3gis.local/benign-client` | ok | 4.6 | 0.03 | 50.5 | 3.4 | 0.00 | 0.4 | yes |
| `workstation · ae3gis.local/wazuh-agent` | ok | 4.7 | 0.03 | 36.0 | 2.3 | 0.01 | 0.4 | yes |
| `workstation · ae3gis.local/firefox` | ok | 5.1 | 0.06 | 438.9 | 420.1 | 0.61 | 26.4 | yes |
| `attacker · ae3gis.local/malicious-client` | ok | 4.9 | 0.03 | 56.0 | 3.5 | 0.00 | 0.4 | yes |
| `plc · kathara/base` | ok | 4.7 | 0.02 | 39.6 | 1.0 | 0.00 | 0.4 | yes |
| `plc · ae3gis.local/openplc` | ok | 5.1 | 0.04 | 84.7 | 56.8 | 0.04 | 0.6 | yes |
| `hmi · kathara/base` | ok | 5.1 | 0.03 | 50.7 | 1.0 | 0.00 | 0.4 | yes |
