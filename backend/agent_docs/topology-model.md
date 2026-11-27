# The AE3GIS topology model

A topology is a drill-down hierarchy: **Topology → Sites → Subnets → Devices**.
Every entity has an id (e.g. `site-…`, `subnet-…`, `node-…`, links `c-…`); tools
take these ids, and `get_topology` prints them in `[brackets]`.

## Subnets
- `cidr` (e.g. `10.0.1.0/24`), unique across the topology.
- `gateway`: the IP of the subnet's gateway **router**; hosts get their default
  route through it. `add_subnet` creates the router (first address) and a switch
  (second address), linked, unless `infra: false`.
- `purdueLevel` (optional): 5, 4, 3.5 (DMZ), 3, 2, 1, 0 — used by the Purdue layout.

## Devices
- `type`: a catalog type (`get_catalog`). Its **role** decides how the device is
  configured: `router` (forwards between subnets), `switch` (bridges its subnet's
  segment), `host` (everything else: workstations, servers, PLCs, HMIs, IDS…).
- `ip`: inside the subnet's CIDR, unique there (network/broadcast are reserved).
- `image` (optional): defaults to the type's image; variants are in the catalog.
- `env` (optional): environment variables set at deploy (e.g. point a client at a
  peer's IP — there is no cross-node DNS).
- `interfaces` (optional, dual-homing): extra legs `{subnetId, ip}` into other
  subnets (`add_interface`). Never on a switch (it would bridge two subnets). A
  dual-homed host does **not** forward by default.
- `mirrorTo` (Open vSwitch switches only): mirror the bridge's traffic to that
  device's port (SPAN), for a passive IDS.
- `webUiPort` (optional): the HTTP port the device serves a web UI on.

## Links
- Inside a subnet: device ↔ device (normally every device to the subnet switch;
  `add_device` does that by default). Unlinked devices get a `device.unlinked` warning.
- Between subnets of one site (`subnetConnections`) and between sites
  (`siteConnections`): always **router ↔ router**. `connect` with two subnets or two
  sites picks (or creates) their gateway routers. Each router-to-router link gets a
  `/30` from `10.255.0.0/24`; static routes between all subnets are computed for you
  (shortest path), so a routed network needs no manual route commands.

## Validation
`validate_topology` / `get_topology` list diagnostics. **Errors block deploy**
(e.g. `ip.outside_subnet`, `ip.duplicate`, `cidr.invalid`, `gateway.not_router`,
`type.unknown`, `connection.endpoint_unknown`); **warnings** only inform (e.g.
`device.unlinked`, `subnet.no_router`, `subnet.empty`). Saving is never refused.

## Editing while deployed
Editing a deployed topology changes the saved design only; the running lab keeps
the old one until you `destroy` and `deploy` again.

## Positions
New entities need no position: the editor places them (and `arrange` re-lays a
level out: tree, circle, grid, purdue).
