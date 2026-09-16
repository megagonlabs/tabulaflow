"""Shared mechanics for installing research benchmarks."""

from __future__ import annotations

import asyncio
import shutil
import uuid
import zipfile
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import httpx
from gdown.download import download as gdown_download
from tqdm import tqdm

from tabulaflow._paths import DEFAULT_HOME_DIR

ProgressCallback = Callable[[str], None]
FetchFunction = Callable[[Path, ProgressCallback], Awaitable[None]]
DEFAULT_BENCHMARK_DIR = DEFAULT_HOME_DIR / "benchmarks"


class BenchmarkInstallationError(RuntimeError):
    """Raised when benchmark data cannot be installed."""


@dataclass(frozen=True)
class BenchmarkInstallation:
    """Local installation requirements for one benchmark."""

    name: str
    required_paths: tuple[str, ...]
    fetch: FetchFunction | None = None

    @property
    def directory(self) -> Path:
        return DEFAULT_BENCHMARK_DIR / self.name

    @property
    def missing_paths(self) -> tuple[str, ...]:
        return tuple(path for path in self.required_paths if not (self.directory / path).exists())

    @property
    def is_installed(self) -> bool:
        return not self.missing_paths

    def require(self) -> None:
        """Raise an actionable error when the benchmark is not installed."""
        if not self.is_installed:
            raise BenchmarkInstallationError(
                f"{self.name} is not downloaded.\n\n"
                f"Run:\n  tabulaflow benchmark download {self.name}"
            )

    async def install(self, *, force: bool = False, progress: ProgressCallback | None = None) -> Path:
        """Download, verify, and atomically install the benchmark."""
        progress = progress or (lambda _: None)
        if self.is_installed and (not force or self.fetch is None):
            return self.directory
        if self.fetch is None:
            lines = [f"{self.name} requires manual setup."]
            lines.append(f"Missing from {self.directory}:")
            lines.extend(f"  {path}" for path in self.missing_paths)
            raise BenchmarkInstallationError("\n".join(lines))
        if self.directory.exists() and not force:
            raise BenchmarkInstallationError(
                f"{self.directory} exists but is not a valid {self.name} installation; use --force to replace it"
            )

        self.directory.parent.mkdir(parents=True, exist_ok=True)
        downloads_dir = self.directory.parent / ".downloads"
        downloads_dir.mkdir(exist_ok=True)
        staging = downloads_dir / self.name
        staging.mkdir(exist_ok=True)
        await self.fetch(staging, progress)
        missing = [path for path in self.required_paths if not (staging / path).exists()]
        if missing:
            raise BenchmarkInstallationError(f"downloaded {self.name} is missing: {', '.join(missing)}")
        _replace_directory(staging, self.directory)
        return self.directory


def _replace_directory(source: Path, destination: Path) -> None:
    backup = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.old")
    if destination.exists():
        destination.rename(backup)
    try:
        source.rename(destination)
    except BaseException:
        if backup.exists():
            backup.rename(destination)
        raise
    shutil.rmtree(backup, ignore_errors=True)


async def download_file(url: str, destination: Path, *, auth: httpx.BasicAuth | None = None) -> None:
    """Download a file, resuming a partial transfer when supported."""
    if destination.is_file():
        return
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f"{destination.name}.part")
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {"Range": f"bytes={offset}-"} if offset else None
    async with httpx.AsyncClient(follow_redirects=True, timeout=None, auth=auth) as client:
        async with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            append = offset > 0 and response.status_code == httpx.codes.PARTIAL_CONTENT
            total = _download_size(response, offset if append else 0)
            remaining = total - offset if total is not None and append else total
            if remaining is not None and remaining > shutil.disk_usage(destination.parent).free:
                raise BenchmarkInstallationError(f"not enough disk space to download {destination.name}")
            with (
                partial.open("ab" if append else "wb") as output,
                tqdm(
                    total=total,
                    initial=offset if append else 0,
                    desc=destination.name.lstrip("."),
                    unit="B",
                    unit_scale=True,
                    unit_divisor=1024,
                ) as progress,
            ):
                async for chunk in response.aiter_bytes():
                    output.write(chunk)
                    progress.update(len(chunk))
    partial.replace(destination)


def _download_size(response: httpx.Response, offset: int) -> int | None:
    content_range = response.headers.get("Content-Range")
    if content_range and "/" in content_range:
        total = content_range.rsplit("/", 1)[1]
        if total.isdigit():
            return int(total)
    content_length = response.headers.get("Content-Length")
    return offset + int(content_length) if content_length and content_length.isdigit() else None


async def download_zip(url: str, destination: Path, *, auth: httpx.BasicAuth | None = None) -> None:
    """Download a ZIP archive and reject invalid completed transfers."""
    if destination.exists() and not zipfile.is_zipfile(destination):
        destination.unlink()
    await download_file(url, destination, auth=auth)
    if not zipfile.is_zipfile(destination):
        destination.unlink(missing_ok=True)
        raise BenchmarkInstallationError(f"downloaded file is not a ZIP archive: {url}")


async def download_google_drive(url: str, destination: Path) -> None:
    """Download a public Google Drive file."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    result = await asyncio.to_thread(lambda: gdown_download(url=url, output=str(destination), quiet=False, resume=True))
    if result is None:
        raise BenchmarkInstallationError(f"failed to download {url}")


def extract_zip(archive: Path, destination: Path) -> None:
    """Safely extract a ZIP archive."""
    destination.mkdir(parents=True, exist_ok=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive) as zip_file:
        if sum(member.file_size for member in zip_file.infolist()) > shutil.disk_usage(destination).free:
            raise BenchmarkInstallationError(f"not enough disk space to extract {archive.name}")
        for member in zip_file.infolist():
            if not (root / member.filename).resolve().is_relative_to(root):
                raise BenchmarkInstallationError(f"unsafe path in {archive}: {member.filename}")
        zip_file.extractall(destination)


def copy_directory_contents(source: Path, destination: Path) -> None:
    """Copy a directory's contents into another directory."""
    destination.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        target = destination / path.name
        if path.is_dir():
            shutil.copytree(path, target, dirs_exist_ok=True)
        else:
            shutil.copy2(path, target)


async def download_github_directory(
    repository: str,
    revision: str,
    source_directory: str,
    destination: Path,
) -> None:
    """Download one directory from a pinned GitHub repository revision."""
    repository_name = repository.rsplit("/", 1)[-1]
    archive = destination / f".{repository_name}-{revision}.zip"
    extracted = destination / f".{repository_name}-{revision}"
    await download_zip(f"https://github.com/{repository}/archive/{revision}.zip", archive)
    if extracted.exists():
        shutil.rmtree(extracted)
    await asyncio.to_thread(extract_zip, archive, extracted)
    roots = [path for path in extracted.iterdir() if path.is_dir()]
    if len(roots) != 1:
        raise BenchmarkInstallationError(f"repository root not found in {repository}@{revision}")
    source = roots[0] / source_directory if source_directory else roots[0]
    if not source.is_dir():
        raise BenchmarkInstallationError(f"{source_directory} not found in {repository}@{revision}")
    await asyncio.to_thread(copy_directory_contents, source, destination)
    archive.unlink()
    shutil.rmtree(extracted)


__all__ = [
    "BenchmarkInstallation",
    "BenchmarkInstallationError",
    "DEFAULT_BENCHMARK_DIR",
    "ProgressCallback",
    "copy_directory_contents",
    "download_file",
    "download_github_directory",
    "download_google_drive",
    "download_zip",
    "extract_zip",
]
