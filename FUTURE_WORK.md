# Future work

The v3 foundation ships the core (editor + Kathara deploy/destroy/status +
terminal). Re-home these deferred features onto the `DeploymentEngine`
abstraction, roughly in order of independence:

1. **Classroom mode** — sessions + student slots + join-code auth. Mostly
   engine-independent; quickest to restore. Reintroduces student read-only UI.
2. **Attack scenarios & scripts** — per-phase script execution and the
   instructor→student pushed-terminal flow, as an engine method.
3. **Firewall editor** — per-node rules via the engine's exec path (nftables).
4. **Wireshark capture** — a sidecar sharing a machine's network namespace,
   resolved through the engine.
5. **Container web-UI proxy** — reverse-proxy to a node's service port.
6. **AI assistant** — decoupled from the orchestrator; catalog-aware.

Cross-cutting:
- Build multi-arch node images and register them in `catalog/node_types.json`.
- Make the catalog env-overridable so image sets ship without editing the repo.
- CI: run backend pytest + frontend build/test/lint before deploy.
