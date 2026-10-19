"""The Docker Hub client (services/dockerhub.py) against an in-memory Hub."""

import asyncio

import pytest

from services.dockerhub import NamespaceNotFound, RateLimited, parse_hub_url
from tests.hubfake import FakeHub, standard_labels


@pytest.mark.parametrize(
    ("text", "namespace"),
    [
        ("https://hub.docker.com/u/uiaegisv3", "uiaegisv3"),
        ("https://hub.docker.com/u/uiaegisv3/", "uiaegisv3"),
        ("hub.docker.com/orgs/ShieldLabs/members", "shieldlabs"),
        ("https://hub.docker.com/r/uiaegisv3/router", "uiaegisv3"),
        ("https://hub.docker.com/repositories/uiaegisv3", "uiaegisv3"),
        ("docker.io/uiaegisv3", "uiaegisv3"),
        ("https://index.docker.io/uiaegisv3/router", "uiaegisv3"),
        ("  uiaegisv3 ", "uiaegisv3"),
    ],
)
def test_namespace_from_a_url(text, namespace):
    assert parse_hub_url(text) == namespace


@pytest.mark.parametrize(
    "text",
    ["", "https://hub.docker.com/", "https://hub.docker.com/_/nginx", "ghcr.io/org", "a b", "x"],
)
def test_not_a_namespace(text):
    with pytest.raises(ValueError):
        parse_hub_url(text)


def run(coro):
    return asyncio.run(coro)


def test_repositories_follow_pages():
    hub = FakeHub(page_size=2)
    for name in "abcde":
        hub.add("lab", name)

    async def go():
        async with hub.client() as c:
            return await c.repositories("lab")

    assert [r.name for r in run(go())] == list("abcde")


def test_an_unknown_namespace():
    async def go():
        async with FakeHub().client() as c:
            await c.repositories("nobody")

    with pytest.raises(NamespaceNotFound):
        run(go())


def test_latest_wins_else_the_newest_tag():
    hub = FakeHub()
    hub.add("lab", "a", tags=("1.1", "latest", "1.0"), platforms=("linux/amd64", "linux/arm64/v8"))
    hub.add("lab", "b", tags=("2.0", "1.0"))
    hub.add("lab", "c", tags=())

    async def go():
        async with hub.client() as c:
            return [await c.pick_tag("lab", r) for r in "abc"]

    a, b, c = run(go())
    assert a.name == "latest" and a.platforms == ["linux/amd64", "linux/arm64/v8"]
    assert a.digest == hub.namespaces["lab"]["a"].top_digest
    assert b.name == "2.0"
    assert c is None


def test_labels_through_an_index_cost_pulls_and_report_the_budget():
    hub = FakeHub(remaining=50)
    repo = hub.add(
        "lab",
        "plc",
        labels={**standard_labels("plc"), "maintainer": "x"},
        platforms=("linux/amd64", "linux/arm64"),
    )

    async def go():
        async with hub.client() as c:
            before = await c.remaining("lab", "plc", repo.top_digest)
            got = await c.labels("lab", "plc", repo.top_digest, ["linux/arm64"])
            return before, got

    before, got = run(go())
    assert before == 50 and hub.heads == 1
    assert got.labels == standard_labels("plc")  # non-standard keys dropped
    assert hub.manifest_gets == 2 and got.remaining == 48


def test_labels_of_a_single_manifest_and_the_rate_limit():
    hub = FakeHub(remaining=1)
    repo = hub.add("lab", "plc", labels=standard_labels("plc"), index=False)

    async def go():
        async with hub.client() as c:
            first = await c.labels("lab", "plc", repo.top_digest, [])
            await c.labels("lab", "plc", repo.top_digest, [])
            return first

    with pytest.raises(RateLimited):
        run(go())
    assert hub.manifest_gets == 1
