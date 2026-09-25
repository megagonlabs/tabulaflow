from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
import time

import httpx
import pytest

import tabulaflow.app.model_catalog as model_catalog_module
from tabulaflow.app.model_catalog import (
    ModelCatalog,
    _BundledCatalog,
    _CatalogEntry,
    _available_models,
    _parse_catalog,
    _release_cutoff,
    llm_model_catalog,
    load_local_model_catalog,
    load_model_catalog,
)


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
    release_date: str = "2026-06-01",
    tool_call: bool = True,
    status: str | None = None,
    output: tuple[str, ...] | None = ("text",),
) -> dict[str, object]:
    return {
        "id": model_id,
        "release_date": release_date,
        "tool_call": tool_call,
        "status": status,
        "limit": {"context": context},
        "modalities": {} if output is None else {"output": list(output)},
    }


def _write_bundled_catalog(
    path: Path,
    *models: _CatalogEntry,
    snapshot_date: date = date(2026, 9, 24),
    release_cutoff: date = date(2026, 3, 24),
) -> None:
    path.write_text(
        _BundledCatalog(
            snapshot_date=snapshot_date,
            release_cutoff=release_cutoff,
            models=models,
        ).model_dump_json()
    )


def test_release_cutoff_is_six_calendar_months_before_the_snapshot() -> None:
    assert _release_cutoff(date(2026, 9, 24)) == date(2026, 3, 24)
    assert _release_cutoff(date(2024, 8, 31)) == date(2024, 2, 29)


def test_catalog_filter_is_shared_and_capability_based() -> None:
    payload = _catalog(
        _model("kept"),
        _model("short", context=127_999),
        _model("old", release_date="2026-03-23"),
        _model("no-tools", tool_call=False),
        _model("deprecated", status="deprecated"),
        _model("missing-output", output=None),
        _model("image-output", output=("image",)),
        _model("audio-output", output=("text", "audio")),
        _model("multimodal-output", output=("text", "image")),
    )

    parsed = _parse_catalog(
        payload,
        release_cutoff=date(2026, 3, 24),
        provider_prefixes=frozenset({"fireworks"}),
    )

    assert parsed == (_CatalogEntry(id="fireworks:kept", release_date=date(2026, 6, 1)),)
    assert _available_models(
        parsed,
        release_cutoff=date(2026, 3, 24),
        provider_prefixes=frozenset({"fireworks"}),
    ) == (
        "fireworks:kept",
    )


def test_model_catalog_orders_explicit_models_without_an_implicit_fallback() -> None:
    catalog = llm_model_catalog(
        current="anthropic:claude-sonnet-5",
        recommended=("openai:gpt-5.6-sol",),
        available=(
            "xai:grok-4.6",
            "anthropic:claude-haiku-4-5",
            "openai:gpt-5.6-sol",
            "anthropic:claude-sonnet-5",
        ),
    )

    assert catalog == (
        "openai:gpt-5.6-sol",
        "anthropic:claude-sonnet-5",
        "anthropic:claude-haiku-4-5",
        "xai:grok-4.6",
    )
    assert llm_model_catalog(current="gateway/openai:custom", recommended=()) == (
        "gateway/openai:custom",
    )


@pytest.mark.asyncio
async def test_catalog_cache_revalidates_with_etag(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    bundled_path = tmp_path / "bundled.json"
    _write_bundled_catalog(bundled_path)
    first_now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(200, json=_catalog(_model("kept")), headers={"ETag": '"v1"'})
        return httpx.Response(304)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        assert await load_model_catalog(path=path, bundled_path=bundled_path, now=first_now, client=client) == (
            "fireworks:kept",
        )
        assert await load_model_catalog(
            path=path, bundled_path=bundled_path, now=first_now + timedelta(hours=1), client=client
        ) == (
            "fireworks:kept",
        )
        assert await load_model_catalog(
            path=path, bundled_path=bundled_path, now=first_now + timedelta(days=2), client=client
        ) == (
            "fireworks:kept",
        )

    assert len(requests) == 2
    assert requests[1].headers["if-none-match"] == '"v1"'


@pytest.mark.asyncio
async def test_catalog_revalidation_keeps_the_version_cutoff(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    bundled_path = tmp_path / "bundled.json"
    _write_bundled_catalog(bundled_path)
    first_now = datetime(2026, 9, 24, tzinfo=timezone.utc)
    responses = iter(
        (
            httpx.Response(200, json=_catalog(_model("aging", release_date="2026-03-24")), headers={"ETag": '"v1"'}),
            httpx.Response(304),
        )
    )

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: next(responses))) as client:
        assert await load_model_catalog(path=path, bundled_path=bundled_path, now=first_now, client=client) == (
            "fireworks:aging",
        )
        assert await load_model_catalog(
            path=path,
            bundled_path=bundled_path,
            now=first_now + timedelta(days=2),
            client=client,
        ) == (
            "fireworks:aging",
        )


@pytest.mark.asyncio
async def test_catalog_refresh_keeps_stale_cache_on_failure(tmp_path: Path) -> None:
    path = tmp_path / "models.json"
    bundled_path = tmp_path / "bundled.json"
    _write_bundled_catalog(bundled_path)
    now = datetime(2026, 9, 24, tzinfo=timezone.utc)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                json=_catalog(_model("kept", release_date="2026-03-24")),
            )
        )
    ) as client:
        assert await load_model_catalog(path=path, bundled_path=bundled_path, now=now, client=client) == (
            "fireworks:kept",
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(503))) as client:
        assert await load_model_catalog(
            path=path,
            bundled_path=bundled_path,
            now=now + timedelta(days=2),
            client=client,
        ) == (
            "fireworks:kept",
        )


@pytest.mark.asyncio
async def test_local_catalog_falls_back_to_the_bundled_snapshot(tmp_path: Path) -> None:
    bundled_path = tmp_path / "bundled.json"
    _write_bundled_catalog(
        bundled_path,
        _CatalogEntry(id="fireworks:bundled", release_date=date(2026, 6, 1)),
    )

    expected = ("fireworks:bundled",)
    assert await load_local_model_catalog(
        path=tmp_path / "missing-cache.json",
        bundled_path=bundled_path,
    ) == expected

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: httpx.Response(503))) as client:
        assert await load_model_catalog(
            path=tmp_path / "missing-cache.json",
            bundled_path=bundled_path,
            now=datetime(2026, 9, 24, tzinfo=timezone.utc),
            client=client,
        ) == expected


@pytest.mark.asyncio
async def test_distribution_bundles_a_filtered_catalog(tmp_path: Path) -> None:
    models = await load_local_model_catalog(path=tmp_path / "missing-cache.json")

    assert any(model.startswith("fireworks:") for model in models)
    assert any(model.startswith("together:") for model in models)


@pytest.mark.asyncio
async def test_local_catalog_filtering_does_not_block_the_event_loop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundled_path = tmp_path / "bundled.json"
    _write_bundled_catalog(
        bundled_path,
        _CatalogEntry(id="fireworks:bundled", release_date=date(2026, 6, 1)),
    )
    completion_order: list[str] = []

    def slow_filter(
        models: tuple[_CatalogEntry, ...],
        *,
        release_cutoff: date,
    ) -> tuple[str, ...]:
        time.sleep(0.1)
        completion_order.append("catalog")
        assert release_cutoff == date(2026, 3, 24)
        return (models[0].id,)

    async def event_loop_task() -> None:
        await asyncio.sleep(0.01)
        completion_order.append("event-loop")

    monkeypatch.setattr(model_catalog_module, "_available_models", slow_filter)
    await asyncio.gather(
        load_local_model_catalog(
            path=tmp_path / "missing-cache.json",
            bundled_path=bundled_path,
        ),
        event_loop_task(),
    )

    assert completion_order == ["event-loop", "catalog"]


@pytest.mark.asyncio
async def test_process_catalog_returns_local_models_while_warming(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bundled_path = tmp_path / "bundled.json"
    _write_bundled_catalog(
        bundled_path,
        _CatalogEntry(id="fireworks:bundled", release_date=date(2026, 6, 1)),
    )
    refresh_started = asyncio.Event()
    finish_refresh = asyncio.Event()

    async def refresh(**_kwargs: object) -> tuple[str, ...]:
        refresh_started.set()
        await finish_refresh.wait()
        return ("fireworks:refreshed",)

    monkeypatch.setattr(model_catalog_module, "load_model_catalog", refresh)
    catalog = ModelCatalog(
        path=tmp_path / "missing-cache.json",
        bundled_path=bundled_path,
    )
    warming = asyncio.create_task(catalog.warm())
    await refresh_started.wait()

    assert await catalog.get() == ("fireworks:bundled",)

    finish_refresh.set()
    assert await warming == ("fireworks:refreshed",)
    assert await catalog.get() == ("fireworks:refreshed",)
