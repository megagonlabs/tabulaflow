import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal

import httpx
import pytest

from tabulaflow.data import SPARQLConnector, SPARQLConnectorConfig
from tabulaflow.data.protocols import DataConnector

_URL = "https://example.test/sparql"
_ASK = {"head": {}, "boolean": True}
_XSD = "http://www.w3.org/2001/XMLSchema#"


def _response(document: object, *, status_code: int = 200, headers: dict[str, str] | None = None) -> httpx.Response:
    return httpx.Response(status_code, json=document, headers=headers)


def _transport_for(document: object) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.content == b"ASK {}":
            return _response(_ASK)
        return _response(document)

    return httpx.MockTransport(handler)


async def _connector(
    document: object,
    *,
    config: SPARQLConnectorConfig | None = None,
) -> SPARQLConnector:
    return await SPARQLConnector.from_url_async(
        _URL,
        display_name="example",
        global_id="sparql-test",
        config=config,
        description="Example RDF source",
        transport=_transport_for(document),
    )


def _select(variables: list[str], bindings: list[dict[str, object]]) -> dict[str, object]:
    return {"head": {"vars": variables}, "results": {"bindings": bindings}}


async def test_select_normalizes_rdf_terms_and_request_metadata() -> None:
    requests: list[httpx.Request] = []
    document = _select(
        ["iri", "blank", "missing", "text"],
        [
            {
                "iri": {"type": "uri", "value": "https://example.test/item/1"},
                "blank": {"type": "bnode", "value": "node1"},
                "text": {"type": "literal", "value": "hello"},
            }
        ],
    )

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return _response(_ASK if request.content == b"ASK {}" else document)

    config = SPARQLConnectorConfig(query_timeout_seconds=None)
    connector = await SPARQLConnector.from_url_async(
        _URL,
        display_name="example",
        global_id="sparql-test",
        config=config,
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await connector.run_query_async("SELECT * WHERE { ?s ?p ?o }")
    finally:
        await connector.close_async()

    assert result.error is None
    assert result.df is not None
    assert result.df.to_dict("records") == [
        {"iri": "https://example.test/item/1", "blank": "_:node1", "missing": None, "text": "hello"}
    ]
    assert requests[-1].headers["user-agent"].startswith("tabulaflow")
    assert requests[-1].headers["accept"] == "application/sparql-results+json"
    assert requests[-1].headers["content-type"] == "application/sparql-query; charset=utf-8"


async def test_typed_literals_use_native_values_when_conversion_is_exact() -> None:
    document = _select(
        ["boolean", "integer", "decimal", "double", "date", "datetime", "string"],
        [
            {
                "boolean": {"type": "literal", "value": "true", "datatype": _XSD + "boolean"},
                "integer": {"type": "literal", "value": "42", "datatype": _XSD + "integer"},
                "decimal": {"type": "literal", "value": "12.50", "datatype": _XSD + "decimal"},
                "double": {"type": "literal", "value": "1.5E2", "datatype": _XSD + "double"},
                "date": {"type": "literal", "value": "2026-09-06", "datatype": _XSD + "date"},
                "datetime": {
                    "type": "literal",
                    "value": "2026-09-06T12:30:00Z",
                    "datatype": _XSD + "dateTime",
                },
                "string": {"type": "literal", "value": "value", "datatype": _XSD + "string"},
            }
        ],
    )
    connector = await _connector(document)
    try:
        result = await connector.run_query_async("SELECT * WHERE {}")
    finally:
        await connector.close_async()

    assert result.df is not None
    row = result.df.iloc[0]
    assert row["boolean"] is True
    assert row["integer"] == 42
    assert row["decimal"] == Decimal("12.50")
    assert row["double"] == 150.0
    assert row["date"] == date(2026, 9, 6)
    assert row["datetime"] == datetime(2026, 9, 6, 12, 30, tzinfo=timezone.utc)
    assert row["string"] == "value"


async def test_language_unknown_and_invalid_typed_literals_remain_lossless() -> None:
    document = _select(
        ["language", "custom", "invalid"],
        [
            {
                "language": {"type": "literal", "value": 'line\n"two"', "xml:lang": "en-GB"},
                "custom": {
                    "type": "typed-literal",
                    "value": "abc",
                    "datatype": "https://example.test/type",
                },
                "invalid": {"type": "literal", "value": "truthy", "datatype": _XSD + "boolean"},
            }
        ],
    )
    connector = await _connector(document)
    try:
        result = await connector.run_query_async("SELECT * WHERE {}")
    finally:
        await connector.close_async()

    assert result.df is not None
    assert result.df.to_dict("records") == [
        {
            "language": '"line\\n\\"two\\""@en-GB',
            "custom": '"abc"^^<https://example.test/type>',
            "invalid": f'"truthy"^^<{_XSD}boolean>',
        }
    ]


async def test_ask_returns_one_boolean_cell() -> None:
    connector = await _connector({"head": {}, "boolean": False})
    try:
        result = await connector.run_query_async("ASK { ?s ?p ?o }")
    finally:
        await connector.close_async()

    assert result.df is not None
    assert result.df.to_dict("records") == [{"boolean": False}]


@pytest.mark.parametrize(
    "document, error_text",
    [
        ({"head": {}, "results": {}}, "head.vars"),
        ({"head": {}, "boolean": "true"}, "must contain a boolean"),
        ({"head": {}, "triples": []}, "only SPARQL SELECT and ASK"),
    ],
)
async def test_malformed_or_unsupported_results_are_errors(document: object, error_text: str) -> None:
    connector = await _connector(document)
    try:
        result = await connector.run_query_async("SELECT * WHERE {}")
    finally:
        await connector.close_async()

    assert result.error is not None
    assert result.error.exc_type == "InvalidSPARQLResultError"
    assert error_text in result.error.message


async def test_invalid_json_is_reported_as_a_result_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.content == b"ASK {}":
            return _response(_ASK)
        return httpx.Response(200, content=b"not json")

    connector = await SPARQLConnector.from_url_async(
        _URL,
        display_name="example",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await connector.run_query_async("SELECT * WHERE {}")
    finally:
        await connector.close_async()

    assert result.error is not None
    assert result.error.exc_type == "InvalidSPARQLResultError"
    assert "valid SPARQL JSON" in result.error.message


async def test_nonempty_parameters_are_rejected_without_http_request() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return _response(_ASK)

    connector = await SPARQLConnector.from_url_async(
        _URL,
        display_name="example",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await connector.run_query_async("SELECT * WHERE {}", {"value": 1})
    finally:
        await connector.close_async()

    assert result.error is not None
    assert result.error.exc_type == "ValueError"
    assert calls == 1


async def test_row_and_response_size_limits_are_enforced() -> None:
    rows: list[dict[str, object]] = [
        {"x": {"type": "literal", "value": str(value)}} for value in range(2)
    ]
    row_limited = await _connector(
        _select(["x"], rows), config=SPARQLConnectorConfig(max_result_rows=1, query_timeout_seconds=None)
    )
    try:
        row_result = await row_limited.run_query_async("SELECT ?x WHERE {}")
    finally:
        await row_limited.close_async()

    assert row_result.error is not None
    assert row_result.error.exc_type == "ResultTooLargeError"

    byte_limited = await _connector(
        _select(["x"], [{"x": {"type": "literal", "value": "x" * 200}}]),
        config=SPARQLConnectorConfig(max_response_bytes=100, query_timeout_seconds=None),
    )
    try:
        byte_result = await byte_limited.run_query_async("SELECT ?x WHERE {}")
    finally:
        await byte_limited.close_async()

    assert byte_result.error is not None
    assert byte_result.error.exc_type == "SPARQLResponseTooLargeError"


async def test_429_retries_after_server_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    query_attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal query_attempts
        if request.content == b"ASK {}":
            return _response(_ASK)
        query_attempts += 1
        if query_attempts == 1:
            return _response({}, status_code=429, headers={"Retry-After": "3"})
        return _response(_select(["x"], []))

    async def sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("tabulaflow.data.sparql.asyncio.sleep", sleep)
    connector = await SPARQLConnector.from_url_async(
        _URL,
        display_name="example",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await connector.run_query_async("SELECT ?x WHERE {}")
    finally:
        await connector.close_async()

    assert result.error is None
    assert query_attempts == 2
    assert delays == [3.0]


async def test_429_retry_count_is_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    query_attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal query_attempts
        if request.content == b"ASK {}":
            return _response(_ASK)
        query_attempts += 1
        return _response({}, status_code=429, headers={"Retry-After": "0"})

    async def sleep(_delay: float) -> None:
        pass

    monkeypatch.setattr("tabulaflow.data.sparql.asyncio.sleep", sleep)
    connector = await SPARQLConnector.from_url_async(
        _URL,
        display_name="example",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await connector.run_query_async("SELECT ?x WHERE {}")
    finally:
        await connector.close_async()

    assert result.error is not None
    assert result.error.exc_type == "HTTPStatusError"
    assert query_attempts == 3


async def test_429_is_not_retried_before_a_long_retry_after_delay(monkeypatch: pytest.MonkeyPatch) -> None:
    query_attempts = 0
    delays: list[float] = []

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal query_attempts
        if request.content == b"ASK {}":
            return _response(_ASK)
        query_attempts += 1
        return _response({}, status_code=429, headers={"Retry-After": "3600"})

    async def sleep(delay: float) -> None:
        delays.append(delay)

    monkeypatch.setattr("tabulaflow.data.sparql.asyncio.sleep", sleep)
    connector = await SPARQLConnector.from_url_async(
        _URL,
        display_name="example",
        transport=httpx.MockTransport(handler),
    )
    try:
        result = await connector.run_query_async("SELECT ?x WHERE {}")
    finally:
        await connector.close_async()

    assert result.error is not None
    assert result.error.exc_type == "HTTPStatusError"
    assert query_attempts == 1
    assert delays == []


async def test_timeout_and_cancellation_propagate_correctly() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        if request.content == b"ASK {}":
            return _response(_ASK)
        started.set()
        await release.wait()
        return _response(_select(["x"], []))

    connector = await SPARQLConnector.from_url_async(
        _URL,
        display_name="example",
        transport=httpx.MockTransport(handler),
    )
    try:
        timed_out = await connector.run_query_async("SELECT ?x WHERE {}", timeout=1)
        assert timed_out.error is not None
        assert timed_out.error.exc_type == "TimeoutError"

        started.clear()
        task = asyncio.create_task(connector.run_query_async("SELECT ?x WHERE {}", timeout=None))
        await started.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        release.set()
        await connector.close_async()


async def test_query_concurrency_is_bounded() -> None:
    active = 0
    maximum_active = 0
    release = asyncio.Event()
    all_started = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal active, maximum_active
        if request.content == b"ASK {}":
            return _response(_ASK)
        active += 1
        maximum_active = max(maximum_active, active)
        if active == 2:
            all_started.set()
        await release.wait()
        active -= 1
        return _response(_select(["x"], []))

    connector = await SPARQLConnector.from_url_async(
        _URL,
        display_name="example",
        config=SPARQLConnectorConfig(max_query_concurrency=2, query_timeout_seconds=None),
        transport=httpx.MockTransport(handler),
    )
    try:
        tasks = [asyncio.create_task(connector.run_query_async("SELECT ?x WHERE {}")) for _ in range(4)]
        await asyncio.wait_for(all_started.wait(), timeout=1)
        await asyncio.sleep(0)
        assert maximum_active == 2
        release.set()
        results = await asyncio.gather(*tasks)
    finally:
        await connector.close_async()

    assert all(result.error is None for result in results)


async def test_refresh_is_deterministic_and_close_is_idempotent() -> None:
    connector = await _connector(_select(["x"], []))
    previous = connector.schema
    refreshed = await connector.refresh_schema_async()

    assert refreshed == previous
    assert refreshed is previous
    assert connector.backend == "sparql"
    assert connector.language == "sparql"
    assert connector.read_only is True
    typed_connector: DataConnector = connector
    assert typed_connector.global_id == "sparql-test"

    await connector.close_async()
    await connector.close_async()
    with pytest.raises(RuntimeError, match="closed"):
        await connector.run_query_async("ASK {}")


class _FailingTransport(httpx.AsyncBaseTransport):
    def __init__(self) -> None:
        self.closed = False

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, request=request)

    async def aclose(self) -> None:
        self.closed = True


async def test_constructor_failure_closes_http_transport() -> None:
    transport = _FailingTransport()

    with pytest.raises(RuntimeError, match="verification failed"):
        await SPARQLConnector.from_url_async(_URL, display_name="example", transport=transport)

    assert transport.closed is True


@pytest.mark.parametrize("url", ["ftp://example.test/query", "https:///missing-host", "not-a-url"])
async def test_endpoint_url_must_be_http(url: str) -> None:
    with pytest.raises(ValueError, match="must use http or https"):
        await SPARQLConnector.from_url_async(url, display_name="example")


async def test_writable_connector_is_not_supported() -> None:
    with pytest.raises(ValueError, match="read-only"):
        await SPARQLConnector.from_url_async(_URL, display_name="example", read_only=False)
