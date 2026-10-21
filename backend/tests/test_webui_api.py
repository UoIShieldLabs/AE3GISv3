"""The node web-UI relay: curl inside the node, relay the page, gate on deploy."""

from tests.conftest import TWO_SUBNETS


def _deploy(client, wait_jobs, topology, fake_engine):
    client.post(f"/api/v1/topologies/{topology['id']}/deploy")
    wait_jobs()


def _with_port(client):
    # hA (a workstation) gets a web UI on 8000, like process-sim.
    data = {**TWO_SUBNETS}
    import copy

    data = copy.deepcopy(TWO_SUBNETS)
    data["sites"][0]["subnets"][0]["containers"][2]["webUiPort"] = 8000
    r = client.post("/api/v1/topologies", json={"name": "web", "data": data})
    return r.json()


def test_relays_a_nodes_web_page(client, wait_jobs, fake_engine):
    rec = _with_port(client)
    _deploy(client, wait_jobs, rec, fake_engine)
    fake_engine.web_ui_pages["hA"] = "<html><head></head><body>city powered</body></html>"
    r = client.get(f"/api/v1/topologies/{rec['id']}/webui/hA/")
    assert r.status_code == 200
    assert "city powered" in r.text
    # the relay injects a <base> so relative assets resolve back through it
    assert f'<base href="/api/v1/topologies/{rec["id"]}/webui/hA/">' in r.text


def test_rewrites_root_absolute_asset_urls(client, wait_jobs, fake_engine):
    rec = _with_port(client)
    _deploy(client, wait_jobs, rec, fake_engine)
    fake_engine.web_ui_pages["hA"] = (
        '<html><head></head><body><img src="/static/x.png"></body></html>'
    )
    r = client.get(f"/api/v1/topologies/{rec['id']}/webui/hA/")
    assert f'src="/api/v1/topologies/{rec["id"]}/webui/hA/static/x.png"' in r.text


def test_root_without_slash_redirects(client, wait_jobs, fake_engine):
    rec = _with_port(client)
    _deploy(client, wait_jobs, rec, fake_engine)
    r = client.get(f"/api/v1/topologies/{rec['id']}/webui/hA", follow_redirects=False)
    assert r.status_code in (307, 308)
    assert r.headers["location"].endswith("/webui/hA/")


def test_refuses_when_not_deployed(client, topology, fake_engine):
    rec = _with_port(client)
    r = client.get(f"/api/v1/topologies/{rec['id']}/webui/hA/")
    assert r.status_code == 409 and r.json()["code"] == "bad_state"


def test_node_without_a_web_port_is_rejected(client, wait_jobs, topology, fake_engine):
    _deploy(client, wait_jobs, topology, fake_engine)
    # rA is a router with no webUiPort and none in the catalog.
    r = client.get(f"/api/v1/topologies/{topology['id']}/webui/rA/")
    assert r.status_code == 422 and r.json()["code"] == "no_web_ui"


def test_catalog_web_ui_port_is_used_when_unset(client, wait_jobs, fake_engine):
    # An hmi type carries webUiPort 8080 in the catalog; no per-node override needed.
    import copy

    data = copy.deepcopy(TWO_SUBNETS)
    data["sites"][0]["subnets"][0]["containers"][2]["type"] = "hmi"
    rec = client.post("/api/v1/topologies", json={"name": "hmi", "data": data}).json()
    client.post(f"/api/v1/topologies/{rec['id']}/deploy")
    wait_jobs()
    fake_engine.web_ui_pages["hA"] = "<html>hmi</html>"
    assert client.get(f"/api/v1/topologies/{rec['id']}/webui/hA/").status_code == 200
