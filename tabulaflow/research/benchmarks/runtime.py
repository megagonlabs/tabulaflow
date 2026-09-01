"""Shared mechanics for managed benchmark database runtimes."""

from __future__ import annotations

import asyncio
import shutil
import time
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from pathlib import Path

from tabulaflow.research.benchmarks.installation import ProgressCallback

RuntimeAction = Callable[[str | None, ProgressCallback], Awaitable[None]]
ReadinessCheck = Callable[[], Awaitable[bool]]


class BenchmarkRuntimeError(RuntimeError):
    """Raised when a managed benchmark runtime operation fails."""


@dataclass(frozen=True)
class BenchmarkRuntime:
    """Start and stop operations for a managed benchmark database runtime."""

    start_action: RuntimeAction
    stop_action: RuntimeAction
    splits: tuple[str, ...] = ()
    default_split: str | None = None

    def resolve_split(self, split: str | None) -> str | None:
        """Validate and resolve an optional runtime split."""
        resolved = split or self.default_split
        if resolved is not None and resolved not in self.splits:
            choices = ", ".join(self.splits)
            raise BenchmarkRuntimeError(f"unsupported split {resolved!r}; available: {choices}")
        if resolved is None and split is not None:
            raise BenchmarkRuntimeError("this benchmark runtime does not use splits")
        return resolved

    async def start(self, split: str | None, progress: ProgressCallback) -> None:
        await self.start_action(self.resolve_split(split), progress)

    async def stop(self, split: str | None, progress: ProgressCallback) -> None:
        await self.stop_action(self.resolve_split(split), progress)


async def run_command(*command: str, cwd: Path | None = None) -> str:
    """Run a command and return stdout, raising a concise runtime error."""
    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        raise BenchmarkRuntimeError(f"{command[0]} is not installed") from None
    stdout, stderr = await process.communicate()
    if process.returncode != 0:
        message = stderr.decode().strip() or stdout.decode().strip() or f"exit code {process.returncode}"
        raise BenchmarkRuntimeError(f"{' '.join(command)} failed: {message}")
    return stdout.decode().strip()


async def ensure_docker() -> None:
    """Verify that Docker and its daemon are available."""
    if shutil.which("docker") is None:
        raise BenchmarkRuntimeError("Docker is not installed")
    await run_command("docker", "info")
    await run_command("docker", "compose", "version")


async def wait_until_ready(
    check: ReadinessCheck,
    description: str,
    *,
    timeout: float = 300,
    interval: float = 2,
) -> None:
    """Wait until an asynchronous readiness check succeeds."""
    deadline = time.monotonic() + timeout
    while True:
        if await check():
            return
        if time.monotonic() >= deadline:
            raise BenchmarkRuntimeError(f"timed out waiting for {description}")
        await asyncio.sleep(interval)


async def container_exists(name: str) -> bool:
    """Return whether a Docker container exists."""
    output = await run_command("docker", "ps", "-a", "--format", "{{.Names}}")
    return name in output.splitlines()


async def start_containers(names: Sequence[str]) -> None:
    """Start existing Docker containers."""
    await run_command("docker", "start", *names)


async def stop_containers(names: Sequence[str]) -> None:
    """Stop existing Docker containers that are currently running."""
    existing = [name for name in names if await container_exists(name)]
    if existing:
        await run_command("docker", "stop", *existing)


__all__ = [
    "BenchmarkRuntime",
    "BenchmarkRuntimeError",
    "container_exists",
    "ensure_docker",
    "run_command",
    "start_containers",
    "stop_containers",
    "wait_until_ready",
]
