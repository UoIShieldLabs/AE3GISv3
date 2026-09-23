import os
import time

from services.joblogs import JobLogStore


def test_append_and_read_by_offset(tmp_path):
    store = JobLogStore(tmp_path)
    for i in range(5):
        store.append("j1", f"line {i}")
    chunk = store.read("j1", 0)
    assert chunk.text.splitlines() == [f"line {i}" for i in range(5)]
    assert chunk.next_offset == chunk.size
    store.append("j1", "line 5")
    more = store.read("j1", chunk.next_offset)
    assert more.text == "line 5\n"
    assert store.read("j1", more.next_offset).text == ""
    assert store.read("missing", 0).text == ""


def test_reads_end_on_a_line_boundary(tmp_path):
    store = JobLogStore(tmp_path)
    for i in range(400):
        store.append("j1", f"{i:04d} " + "x" * 20)
    chunk = store.read("j1", 0, limit=1024)
    assert chunk.text.endswith("\n") and len(chunk.text) <= 1024
    tail = store.read("j1", None, limit=1024)
    assert tail.text.splitlines()[0].startswith(tuple("0123456789"))
    assert tail.text.splitlines()[-1].startswith("0399") and tail.next_offset == tail.size


def test_capped_log_keeps_the_end(tmp_path):
    store = JobLogStore(tmp_path, max_bytes=2000)
    for i in range(1000):
        store.append("j1", f"line {i}")
    store.close("j1")
    text = store.path("j1").read_text()
    assert "line 0\n" in text
    assert "log truncated" in text
    assert text.rstrip().endswith("line 999")
    assert "line 500\n" not in text  # the middle is dropped


def test_gc_removes_old_logs(tmp_path):
    store = JobLogStore(tmp_path)
    store.append("old", "x")
    store.close("old")
    store.append("new", "y")
    store.close("new")
    past = time.time() - 30 * 86400
    os.utime(store.path("old"), (past, past))
    assert store.gc(14) == 1
    assert not store.path("old").exists() and store.path("new").exists()
