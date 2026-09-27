"""Traffic generators a run can use, by name.

A generator turns a flow spec into the command lines of its server and client
ends (run by the netns driver inside the nodes' network namespaces, so the
tools come from the driver's image) and parses their output into samples.
iperf3 is the first; an HTTP (Locust) or Modbus/TCP generator plugs in here.
"""

from __future__ import annotations

from typing import Any, Protocol

from domain.traffic import iperf3


class TrafficGenerator(Protocol):
    name: str

    def server_argv(self, flow: dict[str, Any], port: int, interval: float) -> list[str]: ...

    def client_argv(
        self, flow: dict[str, Any], server_ip: str, port: int, interval: float
    ) -> list[str]: ...

    def parser(self, flow_id: str, role: str, offset: float) -> iperf3.Iperf3StreamParser: ...


class Iperf3Generator:
    name = "iperf3"

    def server_argv(self, flow: dict[str, Any], port: int, interval: float) -> list[str]:
        # Bind to the node's own address (not one the user typed: a NAT or
        # virtual address need not exist on the node).
        bind = flow.get("server_address") if flow.get("bind_server") else None
        return iperf3.server_argv(port, interval, bind)

    def client_argv(
        self, flow: dict[str, Any], server_ip: str, port: int, interval: float
    ) -> list[str]:
        return iperf3.client_argv(flow, server_ip, port, interval)

    def parser(self, flow_id: str, role: str, offset: float) -> iperf3.Iperf3StreamParser:
        return iperf3.Iperf3StreamParser(flow_id, role, offset)


GENERATORS: dict[str, TrafficGenerator] = {"iperf3": Iperf3Generator()}
