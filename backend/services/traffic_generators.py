"""Traffic generators a run can use, by name.

A generator turns a flow spec into sidecar command lines for its server and
client ends, and parses their output into samples. iperf3 is the first; an
HTTP (Locust) or Modbus/TCP generator plugs in here with its own tool image
role in the catalog.
"""

from __future__ import annotations

from typing import Any, Protocol

from domain.traffic import iperf3


class TrafficGenerator(Protocol):
    name: str
    tool_role: str  # catalog "tools" key naming the sidecar image

    def server_argv(self, flow: dict[str, Any], port: int, interval: float) -> list[str]: ...

    def client_argv(
        self, flow: dict[str, Any], server_ip: str, port: int, interval: float
    ) -> list[str]: ...

    def parser(self, flow_id: str, role: str, offset: float) -> iperf3.Iperf3StreamParser: ...

    def listening(self, ss_output: str, port: int) -> bool: ...


class Iperf3Generator:
    name = "iperf3"
    tool_role = "iperf3"

    def server_argv(self, flow: dict[str, Any], port: int, interval: float) -> list[str]:
        return iperf3.server_argv(port, interval)

    def client_argv(
        self, flow: dict[str, Any], server_ip: str, port: int, interval: float
    ) -> list[str]:
        return iperf3.client_argv(flow, server_ip, port, interval)

    def parser(self, flow_id: str, role: str, offset: float) -> iperf3.Iperf3StreamParser:
        return iperf3.Iperf3StreamParser(flow_id, role, offset)

    def listening(self, ss_output: str, port: int) -> bool:
        return f":{port} " in ss_output or ss_output.rstrip().endswith(f":{port}")


GENERATORS: dict[str, TrafficGenerator] = {"iperf3": Iperf3Generator()}
