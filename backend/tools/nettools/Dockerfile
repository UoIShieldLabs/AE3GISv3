# AE3GIS network tools: the image capture and traffic sidecars run.
#
# A sidecar shares one node's network namespace (network_mode=container:<node>),
# so these tools see the node's interfaces and send from its IP and routes,
# whatever image the node itself runs. Built by AE3GIS like any other node
# image (see catalog "tools"); the build fails if iperf3 lacks --json-stream,
# which the traffic runner parses.
FROM alpine:3.22

RUN apk add --no-cache tcpdump iperf3 iproute2 procps \
    && iperf3 --help | grep -q -- --json-stream

CMD ["sleep", "infinity"]
