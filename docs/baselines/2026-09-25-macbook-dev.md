# Traffic baseline — 2026-09-25 01:07 UTC

- **Host:** macbook-dev · Docker Desktop · aarch64 · 8 CPUs · 8.2 GB
- **Kernel / Docker:** 6.10.14-linuxkit · Docker 28.3.2 · cgroup v2
- **Kathará:** 3.8.3 · network plugin `kathara/katharanp_vde`
- **AE3GIS:** `606b5d8a67ad` (modified) · dev
- **Tools:** iperf 3.19.1 (cJSON 1.7.15)
- **Environment fingerprint:** `8b1b774640bf3668996ea14224c16359382f17ac575817adcc6172e38e15e45d`
- **Flow:** `host-a` → `host-b`, 20s per test, 1 s samples

| Test | Direction | Mean Mb/s | p50 | Min | Max | Retrans. | RTT ms | Jitter ms | Loss % | Run |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| TCP, 1 stream | client → server | 72.4 | 75.6 | 38.7 | 85.6 | 78 | 126.83 | – | – | `9e90c0d2` |
| TCP, 4 streams | client → server | 67.1 | 68.2 | 37.7 | 78.6 | 211 | 262.58 | – | – | `510c3f9a` |
| UDP, 100 Mb/s, 1200 B | client → server | 82.0 | 84.4 | 49.2 | 98.2 | – | – | 0.177 | 17.581 | `b9c12b7f` |
| TCP, reverse | server → client | 47.7 | 49.9 | 32.5 | 56.8 | 66 | 87.86 | – | – | `89d446d5` |
| TCP, both ways | client → server | 25.5 | 27.2 | 11.5 | 33.6 | 13 | 178.19 | – | – | `06635de6` |
| TCP, both ways | server → client | 26.1 | 27.8 | 12.5 | 32.5 | 4 | 187.98 | – | – | `06635de6` |
| TCP, 1 stream, while capturing | client → server | 56.6 | 57.7 | 30.4 | 67.9 | 159 | 172.42 | – | – | `a0cbcb33` |
| ↳ capture on host-a eth0 (headers only) | | 148,455 packets | | | | | | | 0 dropped | `7e4597c4` |
