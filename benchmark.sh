#!/bin/bash
# Scale benchmark: deploys topologies of increasing size, captures metrics, destroys.
# Usage: ./benchmark.sh [base_url] [token] [--stress]
# Example: ./benchmark.sh http://localhost:8000 test --stress

BASE_URL="${1:-http://localhost:8000}"
TOKEN="${2:-test}"
STRESS=false
for arg in "$@"; do [[ "$arg" == "--stress" ]] && STRESS=true; done
STEPS=(3000)
OUTPUT="benchmark_results.csv"

echo "base_url=$BASE_URL  token=$TOKEN"
echo "Results will be written to $OUTPUT"
echo

echo "nodes,deploy_time_s,host_ram_total_mib,host_ram_delta_mib,host_cpu_pct,veths,netns,iptables_rules" > "$OUTPUT"

# Build a topology JSON with N workstation containers in one subnet
make_topology() {
    local n=$1
    local containers=""
    local connections=""
    local subnet_id="subnet-bench"
    local site_id="site-bench"

    # Router as first node (required by ADD_SUBNET convention)
    containers=$(cat <<EOF
{"id":"router-0","name":"router","type":"router","ip":"10.0.0.1"}
EOF
)
    connections=""

    for i in $(seq 1 "$n"); do
        local cid="ws-$i"
        local ip="10.0.$((( i - 1) / 254 + 1)).$(( (i - 1) % 254 + 1))"
        containers="${containers},{\"id\":\"${cid}\",\"name\":\"ws${i}\",\"type\":\"workstation\",\"ip\":\"${ip}\"}"
        connections="${connections},{\"from\":\"router-0\",\"to\":\"${cid}\"}"
    done

    # Strip leading comma from connections
    connections="${connections#,}"

    cat <<EOF
{
  "name": "bench-${n}",
  "sites": [{
    "id": "${site_id}",
    "name": "BenchSite",
    "location": "bench",
    "position": {"x":0,"y":0},
    "subnets": [{
      "id": "${subnet_id}",
      "name": "BenchSubnet",
      "cidr": "10.0.0.0/8",
      "containers": [${containers}],
      "connections": [${connections}]
    }],
    "subnetConnections": []
  }],
  "siteConnections": []
}
EOF
}

for N in "${STEPS[@]}"; do
    echo "=== $N nodes ==="

    # Create topology
    TOPO_JSON=$(make_topology "$N")
    printf '{"name":"bench-%s","data":%s}' "$N" "$TOPO_JSON" > /tmp/bench_topo.json
    CREATE_RESP=$(curl -sf -X POST "$BASE_URL/api/topologies" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d @/tmp/bench_topo.json)

    if [ $? -ne 0 ]; then
        echo "  ERROR: failed to create topology for N=$N"
        continue
    fi

    TOPO_ID=$(echo "$CREATE_RESP" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
    echo "  topology_id=$TOPO_ID"

    # Snapshot host RAM and CPU before deploy
    HOST_RAM_BEFORE=$(free -m | awk '/Mem/{print $3}')
    HOST_CPU_BEFORE=$(top -bn2 | grep "Cpu(s)" | tail -1 | awk '{print $2+$4}')

    # Deploy and time it — show a live spinner with elapsed time
    echo "  deploying..."
    START=$(date +%s)
    curl -sf -X POST "$BASE_URL/api/topologies/$TOPO_ID/deploy" \
        -H "Authorization: Bearer $TOKEN" \
        --max-time 600 -o /tmp/bench_deploy_resp.json &
    CURL_PID=$!
    SPIN='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    SI=0
    while kill -0 $CURL_PID 2>/dev/null; do
        ELAPSED=$(( $(date +%s) - START ))
        RUNNING=$(docker ps --filter "name=clab-" -q 2>/dev/null | wc -l)
        CHAR="${SPIN:$((SI % 10)):1}"
        printf "\r  %s  elapsed: %ds  containers up: %d / %d " "$CHAR" "$ELAPSED" "$RUNNING" "$N"
        SI=$((SI + 1))
        sleep 1
    done
    wait $CURL_PID
    DEPLOY_RC=$?
    printf "\r  %-60s\r" ""  # clear spinner line
    END=$(date +%s)
    DEPLOY_TIME=$((END - START))
    DEPLOY_RESP=$(cat /tmp/bench_deploy_resp.json 2>/dev/null)

    if [ $DEPLOY_RC -ne 0 ]; then
        echo "  ERROR: deploy failed or timed out (exit $DEPLOY_RC) after ${DEPLOY_TIME}s"
        # Still capture kernel state to see how far it got
    fi

    echo "  deploy_time=${DEPLOY_TIME}s"

    # Wait a moment for containers to settle
    sleep 2

    # Stress: run a CPU + memory workload in every container
    if [ "$STRESS" = true ]; then
        echo "  stressing containers..."
        for c in $(docker ps --filter "name=clab-" --format "{{.Names}}" 2>/dev/null); do
            docker exec -d "$c" sh -c '
                while true; do
                    ping -c1 -W1 127.0.0.1 > /dev/null 2>&1
                    dd if=/dev/urandom bs=4k count=8 2>/dev/null | md5sum > /dev/null
                    sleep 2
                done
            ' 2>/dev/null
        done
        sleep 5  # let workload ramp up before sampling
    fi

    # Host-level RAM and CPU after deploy + stress
    HOST_RAM_AFTER=$(free -m | awk '/Mem/{print $3}')
    HOST_RAM_DELTA=$((HOST_RAM_AFTER - HOST_RAM_BEFORE))
    HOST_CPU=$(top -bn2 | grep "Cpu(s)" | tail -1 | awk '{print $2+$4}')
    HOST_RAM_TOTAL=$HOST_RAM_AFTER

    # Kernel networking metrics
    VETHS=$(ip link show type veth 2>/dev/null | grep -c '^[0-9]' || echo 0)
    NETNS=$(sudo ip netns list 2>/dev/null | wc -l || echo 0)
    IPTABLES=$(sudo iptables -L 2>/dev/null | wc -l || echo 0)

    echo "  host_ram_total=${HOST_RAM_TOTAL}MiB  host_ram_delta=${HOST_RAM_DELTA}MiB  host_cpu=${HOST_CPU}%  veths=${VETHS}  netns=${NETNS}  iptables=${IPTABLES}"
    echo "$N,$DEPLOY_TIME,$HOST_RAM_TOTAL,$HOST_RAM_DELTA,$HOST_CPU,$VETHS,$NETNS,$IPTABLES" >> "$OUTPUT"

    # Destroy
    echo "  destroying..."
    curl -sf -X POST "$BASE_URL/api/topologies/$TOPO_ID/destroy" \
        -H "Authorization: Bearer $TOKEN" --max-time 120 > /dev/null
    curl -sf -X DELETE "$BASE_URL/api/topologies/$TOPO_ID" \
        -H "Authorization: Bearer $TOKEN" > /dev/null

    echo "  done"
    echo
    sleep 3
done

echo "=== Complete. Results in $OUTPUT ==="
cat "$OUTPUT"
