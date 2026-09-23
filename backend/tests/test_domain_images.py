from domain.images import ContextFile, StatusInput, fingerprint, image_status

FILES = [ContextFile("dockerfile", False, b"FROM ubuntu\n"), ContextFile("run.sh", True, b"echo")]


def test_fingerprint_is_stable_and_order_independent():
    a = fingerprint(FILES, "dockerfile", {})
    assert a == fingerprint(list(reversed(FILES)), "dockerfile", {})
    assert len(a) == 64


def test_fingerprint_changes_with_any_build_input():
    base = fingerprint(FILES, "dockerfile", {})
    edited = [ContextFile("dockerfile", False, b"FROM debian\n"), FILES[1]]
    not_exec = [FILES[0], ContextFile("run.sh", False, b"echo")]
    renamed = [FILES[0], ContextFile("start.sh", True, b"echo")]
    variants = {
        fingerprint(edited, "dockerfile", {}),
        fingerprint(not_exec, "dockerfile", {}),
        fingerprint(renamed, "dockerfile", {}),
        fingerprint(FILES, "Dockerfile", {}),
        fingerprint(FILES, "dockerfile", {"V": "1"}),
        fingerprint(FILES + [ContextFile("extra", False, b"")], "dockerfile", {}),
    }
    assert base not in variants and len(variants) == 6


def _status(**kw):
    base = dict(buildable=True, present=True, built_fingerprint="a", expected_fingerprint="a")
    return image_status(StatusInput(**{**base, **kw}))[0]


def test_status_matrix():
    assert _status() == "ready"
    assert _status(expected_fingerprint="b") == "stale"
    assert _status(expected_fingerprint=None) == "ready"  # source not readable: can't tell
    assert _status(built_fingerprint=None) == "unmanaged"
    assert _status(present=False) == "missing"
    assert _status(present=False, unavailable_reason="no buildx") == "unavailable"
    assert _status(present=False, last_build_error="boom") == "failed"
    assert _status(present=True, last_build_error="boom") == "ready"  # an older image is still fine
    assert _status(building=True) == "building"
    assert _status(buildable=False, present=True, built_fingerprint=None) == "ready"
    assert _status(buildable=False, present=False) == "missing"
