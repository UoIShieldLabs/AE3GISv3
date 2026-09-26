"""The live hub: bounded subscriber queues, replay, close."""

import asyncio

from services.live import LiveHub


def test_slow_subscribers_drop_the_oldest_and_late_ones_replay():
    async def run():
        hub = LiveHub(replay=3)
        ch = hub.open("job1")
        slow, history = ch.subscribe(maxsize=2)
        assert history == []
        for i in range(5):
            ch.publish({"i": i})
        got = [await slow.get(), await slow.get()]
        late, history = ch.subscribe()
        ch.close({"type": "end"})
        tail = [await late.get(), await late.get()]
        after, after_history = ch.subscribe()
        return got, slow.dropped, history, tail, await after.get(), await after.get(), after_history

    got, dropped, history, tail, final, eof, after_history = asyncio.run(run())
    assert got == [{"i": 3}, {"i": 4}] and dropped == 3
    assert history == [{"i": 2}, {"i": 3}, {"i": 4}]
    assert tail == [{"type": "end"}, None]
    assert (final, eof) == ({"type": "end"}, None) and len(after_history) == 3


def test_publish_threadsafe_and_prune():
    async def run():
        hub = LiveHub()
        ch = hub.open("a")
        sub, _ = ch.subscribe()
        await asyncio.to_thread(ch.publish_threadsafe, {"x": 1})
        msg = await asyncio.wait_for(sub.get(), 1)
        for key in ("a", "b", "c"):
            hub.open(key).close()
        hub.prune(keep=1)
        return msg, [k for k in ("a", "b", "c") if hub.get(k)]

    msg, kept = asyncio.run(run())
    assert msg == {"x": 1} and kept == ["c"]
