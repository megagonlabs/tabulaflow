"""Read-only SPARQL Query connector over HTTP.

The connector supports ``SELECT`` and ``ASK`` through the standard SPARQL JSON
result format. Results are normalized into ordinary tabular values for display,
serialization, and workspace materialization; language and unfamiliar datatype
metadata use an N-Triples-compatible string representation, but the table is not
an RDF round-trip format.

Protocol references:
https://www.w3.org/TR/sparql11-results-json/ and
https://www.w3.org/TR/rdf11-concepts/#section-Graph-Literal.

Queries return failures as ``ExecResult.error`` while task cancellation propagates.
One overall deadline covers concurrency throttling, bounded HTTP 429 retries,
response streaming, and parsing. Independent row and response-byte limits bound
materialization. The minimal RDF schema is configured locally, so refreshing it is
deterministic and performs no network discovery.
"""

from __future__ import annotations

import asyncio
import json
import math
import re
import time
from collections.abc import Mapping
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from email.utils import parsedate_to_datetime
from typing import Any, ClassVar, Literal
from urllib.parse import urlparse

import httpx
import pandas as pd

from tabulaflow.core.results import ErrorInfo, ExecResult
from tabulaflow.core.schema import GraphQueryLanguage, RDFSchema
from tabulaflow.data.config import SPARQLConnectorConfig
from tabulaflow.data.protocols import ResultTooLargeError, validate_global_id
from tabulaflow.data.connect import _global_id_from_url

_UNSET = object()
_MAX_RETRIES = 2
_MAX_RETRY_AFTER_SECONDS = 60
_USER_AGENT = "tabulaflow (+https://github.com/megagonlabs/tabulaflow)"
_XSD = "http://www.w3.org/2001/XMLSchema#"
_INTEGER_PATTERN = re.compile(r"[+-]?[0-9]+")
_DECIMAL_PATTERN = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")
_FLOAT_PATTERN = re.compile(r"[+-]?(?:(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[Ee][+-]?[0-9]+)?)")
_DATE_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
_DATETIME_PATTERN = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T.+")
_INTEGER_BOUNDS: dict[str, tuple[int | None, int | None]] = {
    "byte": (-128, 127),
    "short": (-32768, 32767),
    "int": (-2147483648, 2147483647),
    "long": (-9223372036854775808, 9223372036854775807),
    "unsignedByte": (0, 255),
    "unsignedShort": (0, 65535),
    "unsignedInt": (0, 4294967295),
    "unsignedLong": (0, 18446744073709551615),
    "positiveInteger": (1, None),
    "nonNegativeInteger": (0, None),
    "negativeInteger": (None, -1),
    "nonPositiveInteger": (None, 0),
    "integer": (None, None),
}


class SPARQLResponseTooLargeError(RuntimeError):
    """A response exceeded the configured byte limit."""

    def __init__(self, max_bytes: int) -> None:
        super().__init__(f"SPARQL response exceeded the {max_bytes:,}-byte limit")


class InvalidSPARQLResultError(ValueError):
    """A response is not a valid supported SPARQL JSON result."""


def _escape_rdf_lexical(value: str) -> str:
    escaped: list[str] = []
    replacements = {
        "\b": "\\b",
        "\t": "\\t",
        "\n": "\\n",
        "\f": "\\f",
        "\r": "\\r",
        '"': '\\"',
        "\\": "\\\\",
    }
    for char in value:
        replacement = replacements.get(char)
        if replacement is not None:
            escaped.append(replacement)
        elif ord(char) < 0x20 or ord(char) == 0x7F:
            escaped.append(f"\\u{ord(char):04X}")
        else:
            escaped.append(char)
    return '"' + "".join(escaped) + '"'


def _lexical_literal(value: str, *, language: str | None = None, datatype: str | None = None) -> str:
    literal = _escape_rdf_lexical(value)
    if language is not None:
        return f"{literal}@{language}"
    assert datatype is not None
    return f"{literal}^^<{datatype}>"


def _native_typed_literal(value: str, datatype: str) -> object:
    if not datatype.startswith(_XSD):
        raise ValueError
    name = datatype[len(_XSD) :]
    if name == "string":
        return value
    if name == "boolean":
        values = {"true": True, "1": True, "false": False, "0": False}
        if value not in values:
            raise ValueError
        return values[value]
    if name in _INTEGER_BOUNDS:
        if _INTEGER_PATTERN.fullmatch(value) is None:
            raise ValueError
        parsed = int(value)
        lower, upper = _INTEGER_BOUNDS[name]
        if (lower is not None and parsed < lower) or (upper is not None and parsed > upper):
            raise ValueError
        return parsed
    if name == "decimal":
        if _DECIMAL_PATTERN.fullmatch(value) is None:
            raise ValueError
        try:
            return Decimal(value)
        except InvalidOperation as exc:
            raise ValueError from exc
    if name in {"float", "double"}:
        special = {"INF": math.inf, "-INF": -math.inf, "NaN": math.nan}
        if value in special:
            return special[value]
        if _FLOAT_PATTERN.fullmatch(value) is None:
            raise ValueError
        return float(value)
    if name == "date":
        if _DATE_PATTERN.fullmatch(value) is None:
            raise ValueError
        return date.fromisoformat(value)
    if name == "dateTime":
        if _DATETIME_PATTERN.fullmatch(value) is None:
            raise ValueError
        return datetime.fromisoformat(value[:-1] + "+00:00" if value.endswith("Z") else value)
    raise ValueError


def _binding_value(binding: object) -> object:
    """Normalize one SPARQL JSON binding into a portable table-cell value.

    IRIs and plain literals become strings, blank nodes use an ``_:`` prefix,
    and recognized valid XSD literals become native Python scalars. Language
    tags and datatypes without an exact native conversion use a
    metadata-preserving N-Triples-compatible string. This normalization is not
    an RDF round-trip representation.

    Args:
        binding: SPARQL JSON binding object containing string ``type`` and
            ``value`` fields, with optional ``xml:lang`` or ``datatype``.

    Returns:
        Portable value suitable for a normalized result DataFrame.

    Raises:
        InvalidSPARQLResultError: If the binding is malformed or has an
            unsupported term type.
    """
    if not isinstance(binding, dict):
        raise InvalidSPARQLResultError("SPARQL binding must be an object")
    term_type = binding.get("type")
    value = binding.get("value")
    if not isinstance(term_type, str) or not isinstance(value, str):
        raise InvalidSPARQLResultError("SPARQL binding must contain string type and value fields")
    language = binding.get("xml:lang")
    datatype = binding.get("datatype")
    if language is not None and not isinstance(language, str):
        raise InvalidSPARQLResultError("SPARQL binding language must be a string")
    if datatype is not None and not isinstance(datatype, str):
        raise InvalidSPARQLResultError("SPARQL binding datatype must be a string")

    if term_type == "uri":
        if language is not None or datatype is not None:
            raise InvalidSPARQLResultError("IRI bindings cannot have a language or datatype")
        return value
    if term_type == "bnode":
        if language is not None or datatype is not None:
            raise InvalidSPARQLResultError("blank-node bindings cannot have a language or datatype")
        return value if value.startswith("_:") else f"_:{value}"
    if term_type not in {"literal", "typed-literal"}:
        raise InvalidSPARQLResultError(f"unsupported SPARQL binding type: {term_type!r}")
    if term_type == "typed-literal" and datatype is None:
        raise InvalidSPARQLResultError("typed-literal binding must have a datatype")
    if language is not None:
        if datatype is not None:
            raise InvalidSPARQLResultError("literal binding cannot have both language and datatype")
        return _lexical_literal(value, language=language)
    if datatype is None:
        return value
    try:
        return _native_typed_literal(value, datatype)
    except (OverflowError, ValueError):
        return _lexical_literal(value, datatype=datatype)


def _parse_sparql_json(content: bytes, max_rows: int | None) -> pd.DataFrame:
    """Parse and validate a SPARQL ``SELECT`` or ``ASK`` JSON result.

    Args:
        content: Complete response body within the configured byte limit.
        max_rows: Maximum permitted ``SELECT`` bindings, or ``None``.

    Returns:
        Result variables and bindings as a portable DataFrame.

    Raises:
        InvalidSPARQLResultError: If the document is malformed or is not a
            supported result shape.
        ResultTooLargeError: If a ``SELECT`` result exceeds ``max_rows``.
    """
    try:
        document = json.loads(content)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise InvalidSPARQLResultError("endpoint did not return valid SPARQL JSON") from exc
    if not isinstance(document, dict):
        raise InvalidSPARQLResultError("SPARQL JSON result must be an object")

    has_boolean = "boolean" in document
    has_results = "results" in document
    if has_boolean == has_results:
        raise InvalidSPARQLResultError("SPARQL JSON result must contain exactly one of boolean or results")
    head = document.get("head")
    if not isinstance(head, dict):
        raise InvalidSPARQLResultError("SPARQL JSON result must contain a head object")

    if has_boolean:
        value = document["boolean"]
        if not isinstance(value, bool):
            raise InvalidSPARQLResultError("SPARQL ASK result must contain a boolean")
        return pd.DataFrame({"boolean": pd.Series([value], dtype=object)})

    results = document.get("results")
    if not isinstance(results, dict):
        raise InvalidSPARQLResultError("SPARQL SELECT results must be an object")
    variables = head.get("vars")
    bindings = results.get("bindings")
    if (
        not isinstance(variables, list)
        or not all(isinstance(variable, str) for variable in variables)
        or len(set(variables)) != len(variables)
    ):
        raise InvalidSPARQLResultError("SPARQL SELECT head.vars must contain unique strings")
    if not isinstance(bindings, list):
        raise InvalidSPARQLResultError("SPARQL SELECT results.bindings must be an array")
    if max_rows is not None and len(bindings) > max_rows:
        raise ResultTooLargeError(max_rows)

    rows: list[list[object]] = []
    variable_set = set(variables)
    for binding in bindings:
        if not isinstance(binding, dict) or not all(isinstance(name, str) for name in binding):
            raise InvalidSPARQLResultError("each SPARQL SELECT binding must be an object")
        unknown = set(binding) - variable_set
        if unknown:
            raise InvalidSPARQLResultError(f"binding contains variables absent from head.vars: {sorted(unknown)!r}")
        rows.append([_binding_value(binding[name]) if name in binding else None for name in variables])
    return pd.DataFrame(rows, columns=variables, dtype=object)


def _retry_after_seconds(value: str | None) -> float | None:
    if value is None:
        return 1.0
    try:
        seconds = max(0.0, float(value))
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            seconds = max(0.0, (retry_at - datetime.now(timezone.utc)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return 1.0
    return seconds if seconds <= _MAX_RETRY_AFTER_SECONDS else None


class SPARQLConnector:
    """Read-only connector for a standards-compatible SPARQL query endpoint."""

    backend: ClassVar[Literal["sparql"]] = "sparql"
    language: ClassVar[GraphQueryLanguage] = "sparql"

    def __init__(
        self,
        endpoint_url: str,
        global_id: str,
        schema: RDFSchema,
        client: httpx.AsyncClient,
        *,
        config: SPARQLConnectorConfig,
    ) -> None:
        self.endpoint_url = endpoint_url
        self.global_id = global_id
        self.schema = schema
        self.read_only = True
        self.config = config
        self._client = client
        self._query_semaphore = asyncio.Semaphore(config.max_query_concurrency)
        self._closed = False

    @classmethod
    async def from_url_async(
        cls,
        url: str,
        *,
        display_name: str,
        global_id: str | None = None,
        read_only: bool = True,
        auth: tuple[str, str] | None = None,
        config: SPARQLConnectorConfig | None = None,
        description: str | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> SPARQLConnector:
        """Create and verify a connector for an HTTP SPARQL query endpoint.

        Args:
            url: Absolute HTTP or HTTPS query-endpoint URL.
            display_name: Human-readable name stored in the RDF schema.
            global_id: Stable cache and source identifier derived from ``url``
                when omitted.
            read_only: Must remain true until SPARQL Update is supported.
            auth: Optional HTTP Basic username and password.
            config: Immutable execution and HTTP policy.
            description: Optional source description stored in the RDF schema.
            transport: Optional HTTPX transport, primarily for custom networking
                and deterministic tests.

        Returns:
            A verified SPARQL connector.

        Raises:
            ValueError: If the URL or requested access mode is unsupported.
            RuntimeError: If endpoint verification fails.
        """
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or parsed.hostname is None:
            raise ValueError("SPARQL endpoint URL must use http or https and include a host")
        if parsed.username is not None or parsed.password is not None:
            raise ValueError("SPARQL endpoint URL must not contain credentials; pass auth separately")
        if not read_only:
            raise ValueError("SPARQLConnector currently supports read-only query endpoints only")
        resolved_config = SPARQLConnectorConfig() if config is None else config
        connector = cls(
            endpoint_url=url,
            global_id=validate_global_id(global_id or _global_id_from_url(url)),
            schema=RDFSchema(display_name=display_name, description=description),
            client=httpx.AsyncClient(
                follow_redirects=True,
                timeout=None,
                transport=transport,
                auth=auth,
                headers={"User-Agent": _USER_AGENT},
            ),
            config=resolved_config,
        )
        try:
            result = await connector.run_query_async("ASK {}")
            if result.error is not None:
                raise RuntimeError(f"SPARQL endpoint verification failed: {result.error.message}")
            return connector
        except BaseException:
            await connector.close_async()
            raise

    def _check_open(self) -> None:
        if self._closed:
            raise RuntimeError("SPARQLConnector is closed")

    async def _read_response(self, query: str) -> bytes:
        for attempt in range(_MAX_RETRIES + 1):
            async with self._client.stream(
                "POST",
                self.endpoint_url,
                content=query.encode(),
                headers={
                    "Accept": "application/sparql-results+json",
                    "Content-Type": "application/sparql-query; charset=utf-8",
                },
            ) as response:
                if response.status_code == 429 and attempt < _MAX_RETRIES:
                    delay = _retry_after_seconds(response.headers.get("Retry-After"))
                    if delay is None:
                        response.raise_for_status()
                else:
                    response.raise_for_status()
                    content = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(content) + len(chunk) > self.config.max_response_bytes:
                            raise SPARQLResponseTooLargeError(self.config.max_response_bytes)
                        content.extend(chunk)
                    return bytes(content)
            assert delay is not None
            await asyncio.sleep(delay)
        raise AssertionError("unreachable")

    async def _execute(self, query: str, timeout: int | None) -> pd.DataFrame:
        async def execute() -> pd.DataFrame:
            async with self._query_semaphore:
                content = await self._read_response(query)
                return _parse_sparql_json(content, self.config.max_result_rows)

        if timeout is None:
            return await execute()
        async with asyncio.timeout(timeout):
            return await execute()

    async def run_query_async(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
        timeout: int | None | object = _UNSET,
    ) -> ExecResult:
        """Execute a SPARQL SELECT or ASK query and return a tabular result.

        Args:
            query: Complete SPARQL query text.
            parameters: Must be empty because SPARQL has no standard parameter
                binding protocol.
            timeout: Overall operation timeout. Omitting it uses the configured
                default; ``None`` disables it.

        Returns:
            Query rows or failure details as an execution result. Task
            cancellation propagates.
        """
        self._check_open()
        effective_timeout = self.config.query_timeout_seconds if timeout is _UNSET else timeout
        assert isinstance(effective_timeout, int) or effective_timeout is None
        started = time.perf_counter()
        try:
            if parameters:
                raise ValueError("SPARQL does not support standardized query parameters; include values in the query")
            if not query.strip():
                raise ValueError("SPARQL query must not be empty")
            df = await self._execute(query, effective_timeout)
            return ExecResult(df=df, latency_seconds=time.perf_counter() - started)
        except Exception as exc:
            return ExecResult(
                error=ErrorInfo(exc_type=type(exc).__name__, message=str(exc)),
                latency_seconds=time.perf_counter() - started,
            )

    async def refresh_schema_async(self) -> RDFSchema:
        """Return the configured minimal RDF schema without network discovery."""
        self._check_open()
        return self.schema

    async def close_async(self) -> None:
        """Close the endpoint HTTP client."""
        if self._closed:
            return
        await self._client.aclose()
        self._closed = True


__all__ = [
    "InvalidSPARQLResultError",
    "SPARQLConnector",
    "SPARQLResponseTooLargeError",
]
