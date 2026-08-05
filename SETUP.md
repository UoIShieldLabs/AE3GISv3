# Getting a fresh clone running

Assumes Docker Desktop (with WSL2 integration) and ContainerLab are already
installed on this machine. This is everything else needed to go from a clean
`git clone` to a running AEGIS UI with the multi-homing test topology loaded.

## 1. Clone and check out this branch

```bash
git clone https://github.com/zachyyh/working.git
cd working
git checkout multihoming-patch
```

## 2. One-time sudoers setup (no manual `visudo` needed)

The backend needs to run `containerlab deploy`/`destroy` without a password
prompt. Run the setup script once per machine:

```bash
chmod +x scripts/setup-sudoers.sh
./scripts/setup-sudoers.sh
```

It writes `/etc/sudoers.d/ae3gis-containerlab` for your current user and
verifies it at the end — you should see the containerlab version print with
no password prompt. Safe to re-run any time (e.g. if `containerlab`'s install
path ever changes).

## 3. Bring the stack up

```bash
docker compose up --build
```

First run on a fresh machine will take a while (pulling/building images).
Once it settles, open the AEGIS UI at whatever port your `docker-compose.yml`
maps the frontend to (check `docker-compose.yml` if unsure — commonly
`http://localhost:5173` for the Vite dev server, or `http://localhost` if
it's served through a reverse proxy).

## 4. Load the multi-homing test topology

The topology JSON lives in the repo at
`automation/examples/multihoming_test/test_topology.json` — no need to
rebuild it, just import it directly:

```bash
curl -X POST http://localhost:8000/api/topologies/import-json \
  -H "Authorization: Bearer test" \
  -F "file=@automation/examples/multihoming_test/test_topology.json;type=application/json"
```

(`test` is the default `AE3GIS_INSTRUCTOR_TOKEN` from `backend/config.py` —
use whatever token you log into the UI with if it's been overridden.)

Refresh the UI, find **"ae3gis-multihoming-test"** in the topology list, open
it, and click Deploy.

## 5. Verify it deployed correctly

```bash
docker ps | grep clab
```

Find the `int-fw` container (name ends in `913f527e-1898-4b13-b5d8-9ead44c1e32d`)
and check its interfaces:

```bash
docker exec -it <int-fw-container-name> ip addr
```

You should see real addresses on 4 separate interfaces: `10.255.255.6/30`,
`10.1.20.1/24`, `10.1.30.1/24`, `10.1.99.1/24`. (Note: `int-fw` currently
shares an image with `perim-fw` — `uiaegisv3/fwallperim` — which ships its
own baked-in VyOS `config.boot` for the *perimeter* role. That config will
stack additional stale addresses on top of the correct ones via the kernel
even though ContainerLab's exec commands set the real ones correctly. This
is a known gap — the internal firewall doesn't have its own image/config
yet — not a problem with the multi-homing patch itself.)

## 6. Tear down when done

```bash
sudo containerlab destroy --topo backend/clab-workdir/<topology-id>.clab.yml
```

Find `<topology-id>` from the `import-json` response, or:
```bash
find backend/clab-workdir -maxdepth 1 -iname "*.clab.yml"
```

If `containerlab destroy` errors on its own management bridge (seen once on
the original dev machine, cause unclear — possibly related to
`docker compose down` disturbing Docker's networking state), fall back to:
```bash
docker rm -f $(docker ps -a --filter "name=clab-ae3gis-multihoming-test" -q)
```
