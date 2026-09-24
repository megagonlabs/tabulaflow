from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tabulaflow.core import RDFSchema
from tabulaflow.data.catalog import WIKIDATA_DESCRIPTION
from tabulaflow.data.connect import connect_data_source
from tabulaflow.data.sparql import SPARQLConnector


async def test_catalog_source_uses_generic_connector_and_adds_description(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    connector = SimpleNamespace(schema=RDFSchema(display_name="wikidata"))

    async def fake_connect_url(url: str, **kwargs: Any) -> Any:
        captured["url"] = url
        captured.update(kwargs)
        return connector

    monkeypatch.setattr("tabulaflow.data.connect.connect_url", fake_connect_url)

    result = await connect_data_source("wikidata", display_name="knowledge")

    assert result is connector
    assert captured == {
        "url": "sparql+https://query.wikidata.org/sparql",
        "display_name": "knowledge",
        "read_only": True,
    }
    assert connector.schema.description == WIKIDATA_DESCRIPTION


async def test_direct_sparql_url_gets_no_catalog_description(monkeypatch: pytest.MonkeyPatch) -> None:
    connector = SimpleNamespace(schema=RDFSchema(display_name="example"))

    async def fake_connect_url(url: str, **kwargs: Any) -> Any:
        return connector

    monkeypatch.setattr("tabulaflow.data.connect.connect_url", fake_connect_url)

    await connect_data_source("sparql+https://example.test/query", display_name="example")

    assert connector.schema.description is None


@pytest.mark.parametrize(
    "source", ["wikidata", "sparql+https://query.wikidata.org/sparql", "sparql+https://example.test/query"]
)
async def test_sparql_connect_does_not_contact_endpoint(source: str, monkeypatch: pytest.MonkeyPatch) -> None:
    async def reject_network(self: SPARQLConnector, query: str) -> bytes:
        raise AssertionError("endpoint contacted during connection")

    monkeypatch.setattr(SPARQLConnector, "_read_response", reject_network)

    connector = await connect_data_source(source, display_name="wikidata")
    try:
        assert connector.schema.display_name == "wikidata"
    finally:
        await connector.close_async()


async def test_database_path_is_normalized_before_connecting(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "source.duckdb"
    path.touch()
    captured: dict[str, Any] = {}
    connector = SimpleNamespace(schema=RDFSchema(display_name="example"))

    async def fake_connect_url(url: str, **kwargs: Any) -> Any:
        captured["url"] = url
        return connector

    monkeypatch.setattr("tabulaflow.data.connect.connect_url", fake_connect_url)

    await connect_data_source(str(path), display_name="example")

    assert captured["url"] == f"duckdb:///{path}"


async def test_local_data_files_are_loaded_into_one_connector(tmp_path: Path) -> None:
    customers = tmp_path / "customers.csv"
    orders = tmp_path / "orders.csv"
    customers.write_text("id,name\n1,Ada\n", encoding="utf-8")
    orders.write_text("id,total\n1,42\n", encoding="utf-8")

    connector = await connect_data_source(
        [str(customers), str(orders)],
        display_name="local_files",
        data_dir=tmp_path / "data",
    )
    try:
        result = await connector.run_query_async("SELECT name, total FROM customers JOIN orders USING (id)")
    finally:
        await connector.close_async()

    assert result.error is None and result.df is not None
    assert result.df.to_dict(orient="records") == [{"name": "Ada", "total": 42}]


async def test_multiple_sources_must_all_be_data_files(tmp_path: Path) -> None:
    data_file = tmp_path / "data.csv"
    database_file = tmp_path / "data.duckdb"
    data_file.touch()
    database_file.touch()

    with pytest.raises(ValueError, match="multiple sources are supported only for local data files"):
        await connect_data_source([str(data_file), str(database_file)], display_name="mixed")
