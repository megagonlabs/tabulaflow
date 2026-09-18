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


WIKIDATA_DESCRIPTION = """Wikidata is a collaborative knowledge graph queried with SPARQL.

Query notes:
- Labels: Use the user's requested language, then `mul`, with English as a fallback unless the user asks for one language only. For example, use `fr,mul,en` with `SERVICE wikibase:label`; when no preference is known, use `en,mul`.
- Direct label filters: Match each language tag explicitly, such as `LANG(?label) IN ("fr", "mul", "en")`; `"fr,mul,en"` is a label-service preference list, not a language tag.
- Discovery: Resolve names to QIDs and PIDs with `SERVICE wikibase:mwapi` in the user's requested language, then query by those IDs; avoid graph-wide label scans.
- Statements: `wdt:` returns truthy claims. Use `p:`, `ps:`, `pq:`, and `wikibase:rank` for qualifiers or ranks.
- Dates: Query statement precision and calendar metadata when normalized timestamps are insufficient.

Docs: [Query help](https://www.wikidata.org/wiki/Wikidata:SPARQL_query_service/Wikidata_Query_Help) · [User manual](https://www.mediawiki.org/wiki/Wikidata_Query_Service/User_Manual)
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
