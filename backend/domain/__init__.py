"""Engine-agnostic domain logic over the opaque topology JSON.

- ``topology``: typed read-only views/helpers over the dict.
- ``validation``: diagnostics (errors block deploy, warnings inform).
- ``plan``: topology -> LabPlan (interfaces, IPs, routes, startup commands).
- ``export``: LabPlan -> lab spec JSON / Kathara lab / ContainerLab topology.
"""
