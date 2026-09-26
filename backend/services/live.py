"""In-process fan-out of live job data to WebSocket subscribers.

A capture or traffic run publishes small JSON messages (packet batches,
samples, status) to its job's channel; each WebSocket subscribes. Subscriber
queues are bounded: a slow browser loses the oldest messages (counted in
``dropped``), never slows the job. A replay ring lets a late joiner start from
recent history. Everything runs on the app loop; ``publish_threadsafe`` is for
producers on worker threads (e.g. a sidecar's output pump).
"""

from __future__ import annotations

import asyncio
from collections import deque
from collections.abc import Callable
from typing import Any

Message = dict[str, Any]


class Subscriber:
    def __init__(self, maxsize: int) -> None:
        self._queue: asyncio.Queue[Message | None] = asyncio.Queue(maxsize=maxsize)
        self.dropped = 0
        self.closed = False

    def put(self, msg: Message | None) -> None:
        if self.closed:
            return
        while True:
            try:
                self._queue.put_nowait(msg)
                return
            except asyncio.QueueFull:
                try:
                    self._queue.get_nowait()
                    self.dropped += 1
                except asyncio.QueueEmpty:  # pragma: no cover - raced to empty
                    pass

    async def get(self) -> Message | None:
        """The next message, or None once the channel closed."""
        msg = await self._queue.get()
        if msg is None:
            self.closed = True
        return msg


class Channel:
    def __init__(self, loop: asyncio.AbstractEventLoop, replay: int) -> None:
        self._loop = loop
        self._subs: set[Subscriber] = set()
        self._ring: deque[Message] = deque(maxlen=replay)
        self.closed = False
        self.final: Message | None = None

    @property
    def subscribers(self) -> int:
        return len(self._subs)

    def publish(self, msg: Message, *, replay: bool = True) -> None:
        if self.closed:
            return
        if replay:
            self._ring.append(msg)
        for sub in list(self._subs):
            sub.put(msg)

    def publish_threadsafe(self, msg: Message, *, replay: bool = True) -> None:
        self._loop.call_soon_threadsafe(lambda: self.publish(msg, replay=replay))

    def subscribe(self, maxsize: int = 256) -> tuple[Subscriber, list[Message]]:
        """A subscriber plus the recent history to show first."""
        sub = Subscriber(maxsize)
        history = list(self._ring)
        if self.closed:
            if self.final is not None:
                sub.put(self.final)
            sub.put(None)
        else:
            self._subs.add(sub)
        return sub, history

    def unsubscribe(self, sub: Subscriber) -> None:
        self._subs.discard(sub)

    def close(self, final: Message | None = None) -> None:
        if self.closed:
            return
        self.closed = True
        self.final = final
        for sub in list(self._subs):
            if final is not None:
                sub.put(final)
            sub.put(None)
        self._subs.clear()


class LiveHub:
    """Channels by key (a job id). A closed channel lingers so late subscribers
    get its final message; ``discard`` forgets it."""

    def __init__(self, replay: int = 200) -> None:
        self._channels: dict[str, Channel] = {}
        self._replay = replay

    def open(self, key: str, *, replay: int | None = None) -> Channel:
        ch = self._channels.get(key)
        if ch is None or ch.closed:
            ch = Channel(asyncio.get_running_loop(), replay or self._replay)
            self._channels[key] = ch
        return ch

    def get(self, key: str) -> Channel | None:
        return self._channels.get(key)

    def discard(self, key: str) -> None:
        self._channels.pop(key, None)

    def prune(self, keep: int = 50) -> None:
        """Forget the oldest closed channels beyond ``keep``."""
        closed = [k for k, ch in self._channels.items() if ch.closed]
        for key in closed[: max(0, len(closed) - keep)]:
            self._channels.pop(key, None)


async def wait_for_channel(
    hub: LiveHub, key: str, is_active: Callable[[], bool], poll: float = 0.25
) -> Channel | None:
    """The job's live channel once its handler has opened it, or None when the
    job is finished. A job still queued or preparing (e.g. building its image)
    has no channel yet: wait for it rather than calling the job done."""
    while True:
        channel = hub.get(key)
        if channel is not None and not channel.closed:
            return channel
        if not await asyncio.to_thread(is_active):
            return None
        await asyncio.sleep(poll)
