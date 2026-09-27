# AE3GIS network tools: the image capture sidecars and the helper containers run.
#
# A sidecar shares one node's network namespace (network_mode=container:<node>),
# so these tools see the node's interfaces and send from its IP and routes,
# whatever image the node itself runs. Helpers are not inside any node:
# - ae3gis-collect (monitor): reads host and container counters from /proc and
#   the host cgroup tree (host PID + cgroup namespaces, cgroupfs read-only)
# - ae3gis-netns (traffic driver): runs iperf3/ping inside node network
#   namespaces with setns (host PID namespace + CAP_SYS_ADMIN + CAP_SYS_PTRACE)
# Built by AE3GIS like any other node image (see catalog "tools"); the build
# fails if iperf3 lacks --json-stream, which the traffic runner parses.
FROM alpine:3.22

RUN apk add --no-cache tcpdump iperf3 iproute2 procps python3 \
    && iperf3 --help | grep -q -- --json-stream \
    && python3 -c "import os; os.setns"

COPY ae3gis_collect.py /usr/local/bin/ae3gis-collect
COPY ae3gis_netns.py /usr/local/bin/ae3gis-netns
RUN chmod +x /usr/local/bin/ae3gis-collect /usr/local/bin/ae3gis-netns

CMD ["sleep", "infinity"]
