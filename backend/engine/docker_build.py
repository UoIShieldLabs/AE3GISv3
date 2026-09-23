"""Build images with BuildKit through the Docker CLI.

docker-py only speaks the legacy builder, which Docker has deprecated and which
lacks BuildKit's caching and output. The CLI (with the buildx plugin) is in the
backend image next to docker-ce-cli, and talks to the same daemon socket.
"""

from __future__ import annotations

import asyncio
import os
import re
import shutil
import signal
from collections import deque
from contextlib import suppress

from engine.base import BuildError, BuildSpec, Progress

# BuildKit lines can be long (a RUN command echoed in full); never choke on one.
_LINE_LIMIT = 1024 * 1024
_CANCEL_GRACE_S = 10.0
_TAIL_LINES = 200

# "#5 5.727 E: Package 'x' has no installation candidate" -> the tool's own message.
_STEP_PREFIX = re.compile(r"^#\d+ [\d.]+ ")
_CAUSES = (
    re.compile(r"^(E: |fatal: |ERROR: (?!failed to (build|solve)))"),  # apt, git, the tool itself
    re.compile(r"(^|: )error: ", re.IGNORECASE),  # compilers, most CLIs
    re.compile(r"^make(\[\d+\])?: \*\*\*"),
)


def explain_failure(lines: list[str]) -> str:
    """The most useful line of a failed build's output.

    BuildKit ends with "ERROR: failed to solve: process … did not complete",
    which only repeats the command; the step's own output (apt's "E: …", a
    compiler's "error: …") usually says why.
    """
    bodies = [_STEP_PREFIX.sub("", ln.strip()) for ln in lines]
    for cause in _CAUSES:
        for body in reversed(bodies):
            if cause.search(body):
                return body
    for line in reversed(lines):
        if "ERROR" in line:
            return line.strip()
    return next((ln.strip() for ln in reversed(lines) if ln.strip()), "")


def build_command(spec: BuildSpec) -> list[str]:
    # --load: whatever builder is selected (a docker-container builder keeps
    # results in its own cache otherwise), the image lands in the daemon's
    # image store, where Kathara looks for it.
    cmd = ["docker", "buildx", "build", "--load", "--progress=plain"]
    cmd += ["-f", str(spec.context / spec.dockerfile)]
    cmd += ["-t", spec.ref]
    for key, value in sorted(spec.labels.items()):
        cmd += ["--label", f"{key}={value}"]
    for key, value in sorted(spec.args.items()):
        cmd += ["--build-arg", f"{key}={value}"]
    if spec.pull:
        cmd.append("--pull")
    if spec.no_cache:
        cmd.append("--no-cache")
    cmd.append(str(spec.context))
    return cmd


async def _run(cmd: list[str], timeout: float = 20.0) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(), timeout)
    except TimeoutError:
        proc.kill()
        await proc.wait()
        return 124, "timed out"
    return proc.returncode or 0, out.decode("utf-8", errors="replace").strip()


async def buildx_available() -> tuple[bool, str]:
    if shutil.which("docker") is None:
        return False, "The docker CLI is not installed on the backend host"
    code, out = await _run(["docker", "buildx", "version"])
    if code != 0:
        return False, f"The docker buildx plugin is not available ({out or code})"
    return True, out


async def docker_build(spec: BuildSpec, on_line: Progress) -> None:
    env = {**os.environ, "DOCKER_CLI_HINTS": "false", "BUILDKIT_PROGRESS": "plain"}
    proc = await asyncio.create_subprocess_exec(
        *build_command(spec),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        env=env,
        limit=_LINE_LIMIT,
        # Our own signal handling decides when the build stops (see below).
        start_new_session=True,
    )
    assert proc.stdout is not None
    tail: deque[str] = deque(maxlen=_TAIL_LINES)
    try:
        while True:
            try:
                raw = await proc.stdout.readline()
            except ValueError:  # a single line over the limit; skip it
                on_line("[… output line too long, skipped …]")
                continue
            if not raw:
                break
            line = raw.decode("utf-8", errors="replace").rstrip()
            on_line(line)
            tail.append(line)
        code = await proc.wait()
    except asyncio.CancelledError:
        # SIGINT makes the CLI cancel the BuildKit solve cleanly (the cache is
        # kept); kill it if it does not stop in time.
        with suppress(ProcessLookupError):
            proc.send_signal(signal.SIGINT)
        try:
            await asyncio.wait_for(proc.wait(), _CANCEL_GRACE_S)
        except TimeoutError:
            with suppress(ProcessLookupError):
                proc.kill()
            await proc.wait()
        raise
    if code != 0:
        raise BuildError(explain_failure(list(tail)) or f"docker build exited with status {code}")
