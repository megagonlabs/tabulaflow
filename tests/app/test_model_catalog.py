from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from tabulaflow.app.model_catalog import _available_models, _parse_catalog, load_model_catalog


def _catalog(*models: dict[str, object]) -> dict[str, object]:
    return {
        "fireworks-ai": {
            "models": {str(model["id"]): model for model in models},
        }
    }


def _model(
    model_id: str,
    *,
    context: int = 128_000,
    release_date: str = "2025-01-01",
    tool_call: bool = True,
    status: str | None = None,
    output: list[str] | None = None,
) -> dict[str, object]:
    return {
        "id": model_id,
        "release_date": release_date,
        "tool_call": tool_call,
        "status": status,
        "limit": {"context": context},
        "modalities": {} if output is None else {"output": output},
    }


def test_catalog_filter_is_shared_and_capability_based() -> None:
    payload = _catalog(
        _model("kept"),
        _model("short", context=127_999),
        _model("old", release_date="2024-09-23"),
        _model("no-tools", tool_call=False),
        _model("deprecated", status="deprecated"),
        _model("image-output", output=["image"]),
    )

    parsed = _parse_catalog(payload, provider_prefixes=frozenset({"fireworks"}))

    assert _available_models(parsed, today=date(2026, 9, 24), provider_prefixes=frozenset({"fireworks"})) == (
        "fireworks:kept",
    )


@pytest.mark.asyncio
async def test_catalog_cache_revalidates_with_etag(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    first_now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, json=_catalog(_model("kept")), headers={"ETag": '"v1"'})
        return httpx.Response(304)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await load_model_catalog(path=path, now=first_now, client=client) == ("fireworks:kept",)
        assert await load_model_catalog(path=path, now=first_now + timedelta(hours=1), client=client) == (
            "fireworks:kept",
        )
        assert await load_model_catalog(path=path, now=first_now + timedelta(days=2), client=client) == (
            "fireworks:kept",
        )

    assert len(requests) == 2
    assert requests[1].headers["if-none-match"] == '"v1"'


@pytest.mark.asyncio
async def test_catalog_cache_reapplies_rolling_release_cutoff(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    first_now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    responses = iter(
        (
            httpx.Response(200, json=_catalog(_model("aging", release_date="2024-09-24")), headers={"ETag": '"v1"'}),
            httpx.Response(304),
        )
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: next(responses))) as client:
        assert await load_model_catalog(path=path, now=first_now, client=client) == ("fireworks:aging",)
        assert await load_model_catalog(path=path, now=first_now + timedelta(days=2), client=client) == ()


@pytest.mark.asyncio
async def test_catalog_refresh_keeps_stale_cache_on_failure(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, json=_catalog(_model("kept"))))
    ) as client:
        assert await load_model_catalog(path=path, now=now, client=client) == ("fireworks:kept",)

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(503))) as client:
        assert await load_model_catalog(path=path, now=now + timedelta(days=2), client=client) == (
            "fireworks:kept",
        )
