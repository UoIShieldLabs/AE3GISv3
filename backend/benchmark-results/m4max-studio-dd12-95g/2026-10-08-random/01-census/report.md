# Benchmark: m4max-studio-dd12-95g · census

- **Host:** m4max-studio-dd12-95g · Docker Desktop · aarch64 · 12 CPUs · 101853.4 MB
- **Kernel / Docker:** 6.10.14-linuxkit · Docker 28.4.0 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `1a66f9c9ecdb` · bench
- **Environment fingerprint:** `dda3a67f640694cd032f0c1b552394a2ec9fe5db7084416971b68484b88dfb62`
- **Topology:** generated: 1 server(s), ≤ 200 hosts per subnet, ≤ 48 per switch, hosts `workstation`
- **Steps:** census of 29 cases, 5 nodes each × 1 · pre 20.0s, settle 30.0s, hold 30.0s · monitor every 5.0s
- **Load:** idle (no traffic)
- **At rest (before the first step):** 1961.1 of 101853.4 MB used (1.9%) · host CPU 0.1% · Docker processes 467.2 MB · Docker's disk 6.3% used
- **Outcome:** 27 of 29 cases usable · 2026-10-08T18:23:09 → 2026-10-08T19:07:02

One step per case: 5 nodes of it as the client hosts of a small campus (a base router and switches, one base server). Host MB / node is estimated: the step's memory change less its base nodes, costed at the reference (workstation · kathara/base) per node. Cgroup MB is the nodes' own; CPU is over the hold (100 = one core). Usable: it passed, or only the host ran out of memory.

| Case | Outcome | Deploy s | Ready s | Host MB / node (est.) | Cgroup MB / node | CPU % / node | Disk MB / node | Usable |
|---|---|---:|---:|---:|---:|---:|---:|---|
| `workstation · kathara/base` | ok | 1.1 | 0.01 | 5.9 | 2.0 | 0.00 | 0.5 | yes |
| `router · kathara/frr` | ok | 1.0 | 0.00 | 25.3 | 1.2 | 0.00 | 0.5 | yes |
| `switch · kathara/base` | ok | 1.0 | 0.00 | 22.0 | 1.3 | 0.00 | 0.5 | yes |
| `switch · ae3gis.local/open-vswitch` | ok | 0.9 | 0.00 | 38.2 | 20.2 | 0.39 | 0.5 | yes |
| `firewall · kathara/frr` | ok | 1.1 | 0.00 | 26.9 | 1.2 | 0.00 | 0.5 | yes |
| `firewall · ae3gis.local/iptables` | ok | 0.9 | 0.00 | 24.7 | 4.7 | 0.00 | 0.4 | yes |
| `firewall · ae3gis.local/nftables` | ok | 1.0 | 0.00 | 35.9 | 4.9 | 0.00 | 0.4 | yes |
| `firewall · ae3gis.local/firehol` | ok | 1.1 | 0.00 | 32.5 | 5.4 | 0.00 | 0.4 | yes |
| `ids · ae3gis.local/suricata` | ok | 0.9 | 0.01 | 93.2 | 74.8 | 0.66 | 0.4 | yes |
| `ids · ae3gis.local/snort3` | ok | 1.0 | 0.01 | 24.6 | 4.6 | 0.00 | 0.4 | yes |
| `ids · ae3gis.local/snort2` | ok | 0.9 | 0.01 | 14.1 | 4.5 | 0.00 | 0.4 | yes |
| `ids · ae3gis.local/zeek` | skipped: Building Zeek failed: BuildError: E: Couldn't find any package by regex 'zeekctl-6.0' | – | – | – | – | – | – | no |
| `siem · ae3gis.local/wazuh-manager` | ok | 0.9 | 0.01 | 572.8 | 624.4 | 48.71 | 2933.4 | yes |
| `web-server · httpd:alpine` | ok | 1.0 | 0.01 | 21.4 | 4.7 | 0.00 | 0.4 | yes |
| `web-server · ae3gis.local/apache` | ok | 1.0 | 0.02 | 26.4 | 10.4 | 0.04 | 0.4 | yes |
| `web-server · ae3gis.local/nginx` | ok | 1.0 | 0.02 | 34.3 | 11.9 | 0.03 | 0.4 | yes |
| `file-server · kathara/base` | ok | 1.0 | 0.01 | 29.1 | 1.2 | 0.00 | 0.4 | yes |
| `file-server · ae3gis.local/samba` | ok | 1.0 | 0.01 | 27.5 | 14.2 | 0.00 | 3.3 | yes |
| `ftp-server · ae3gis.local/vsftpd` | ok | 0.9 | 0.01 | 24.6 | 4.3 | 0.03 | 0.4 | yes |
| `database-server · postgres:alpine` | ok | 1.0 | 0.01 | 32.4 | 27.2 | 0.13 | 41.0 | yes |
| `dns-server · kathara/base` | ok | 0.9 | 0.01 | 19.0 | 1.2 | 0.00 | 0.4 | yes |
| `dhcp-server · ae3gis.local/isc-dhcp` | ok | 0.9 | 0.01 | 18.4 | 1.5 | 0.00 | 0.4 | yes |
| `workstation · ae3gis.local/benign-client` | ok | 1.0 | 0.01 | 15.9 | 4.4 | 0.00 | 0.4 | yes |
| `workstation · ae3gis.local/wazuh-agent` | ok | 1.0 | 0.01 | 30.4 | 2.2 | 0.01 | 0.4 | yes |
| `workstation · ae3gis.local/firefox` | ok | 1.0 | 0.01 | 434.0 | 463.1 | 0.47 | 36.0 | yes |
| `attacker · ae3gis.local/malicious-client` | skipped: Builds only for linux/amd64; this host is linux/arm64 | – | – | – | – | – | – | no |
| `plc · kathara/base` | ok | 1.0 | 0.01 | 23.2 | 1.2 | 0.00 | 0.4 | yes |
| `plc · ae3gis.local/openplc` | ok | 1.0 | 0.01 | 76.3 | 55.9 | 0.02 | 0.6 | yes |
| `hmi · kathara/base` | ok | 0.9 | 0.01 | 27.1 | 1.2 | 0.00 | 0.4 | yes |
