"""Curated data-source definitions and resolution."""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class DataSourceDefinition:
    """A curated source available by a stable catalog identifier."""

    id: str
    source: str
    description: str

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_/-]*", self.id):
            raise ValueError(f"invalid data source id: {self.id!r}")
        if not self.source.strip():
            raise ValueError("data source definition must have a source")
        if not self.description.strip():
            raise ValueError("data source definition must have a description")


def _normalize_catalog_source(source: str) -> str:
    return source.rstrip("/") if "://" in source else source


WIKIDATA_DESCRIPTION = """Wikidata is a collaboratively edited knowledge graph queried with SPARQL. Some English-facing labels, including Q42, use the multilingual `mul` language code: request `en,mul`, not only `en`, with `SERVICE wikibase:label`, and consider both values in direct label filters.

Critical query guidance:
- Use `SERVICE wikibase:mwapi` for bounded entity and property discovery instead of scanning labels across the graph.
- Keep geographic and transitive-path queries selective and bounded before increasing their scope.

Use `wdt:` for direct truthy claims. Use `p:`, `ps:`, `pq:`, and `wikibase:rank` when statements, qualifiers, or ranks matter. Wikidata dates may carry precision and calendar metadata beyond the normalized timestamp; query that statement metadata when it is material to the answer.

Official documentation:
- https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/Wikidata_Query_Help
- https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual
"""

WIKIDATA = DataSourceDefinition(
    id="wikidata",
    source="sparql+https://query.wikidata.org/sparql",
    description=WIKIDATA_DESCRIPTION,
)

DEFAULT_DATA_SOURCE_DEFINITIONS = (WIKIDATA,)


def resolve_data_source_definition(
    source: str,
    definitions: Sequence[DataSourceDefinition] = DEFAULT_DATA_SOURCE_DEFINITIONS,
) -> DataSourceDefinition | None:
    """Resolve a curated source by identifier or exact normalized locator."""
    normalized_source = _normalize_catalog_source(source)
    matches = [
        definition
        for definition in definitions
        if definition.id == source.lower() or _normalize_catalog_source(definition.source) == normalized_source
    ]
    if len(matches) > 1:
        raise ValueError(f"ambiguous data source definition: {source!r}")
    return matches[0] if matches else None


__all__ = [
    "DEFAULT_DATA_SOURCE_DEFINITIONS",
    "DataSourceDefinition",
    "resolve_data_source_definition",
]
