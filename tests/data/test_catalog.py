import pytest

from tabulaflow.data.catalog import (
    DEFAULT_DATA_SOURCE_DEFINITIONS,
    DataSourceDefinition,
    resolve_data_source_definition,
)


def test_catalog_resolves_id_and_exact_normalized_locator() -> None:
    by_id = resolve_data_source_definition("WIKIDATA")
    by_url = resolve_data_source_definition("sparql+https://query.wikidata.org/sparql/")

    assert by_id is not None
    assert by_url is by_id
    assert by_id.id == "wikidata"


def test_wikidata_guidance_covers_multilingual_labels() -> None:
    definition = resolve_data_source_definition("wikidata")

    assert definition is not None
    assert "user's requested language" in definition.description
    assert "`mul` language-neutral labels" in definition.description
    assert "Keep queries selective and efficient" in definition.description


def test_resolver_rejects_ambiguous_definitions() -> None:
    definition = DataSourceDefinition(id="example", source="sparql+https://example.test/query", description="Example")

    with pytest.raises(ValueError, match="ambiguous data source definition"):
        resolve_data_source_definition(
            "example",
            [
                definition,
                DataSourceDefinition(id="example", source="sparql+https://other.test/query", description="Other"),
            ],
        )
    with pytest.raises(ValueError, match="ambiguous data source definition"):
        resolve_data_source_definition(
            "sparql+https://example.test/query",
            [
                definition,
                DataSourceDefinition(id="other", source="sparql+https://example.test/query/", description="Other"),
            ],
        )


def test_definitions_are_extended_with_tuple_composition() -> None:
    definition = DataSourceDefinition(id="example", source="sparql+https://example.test/query", description="Example")

    extended = (*DEFAULT_DATA_SOURCE_DEFINITIONS, definition)

    assert resolve_data_source_definition("example") is None
    assert resolve_data_source_definition("example", extended) is definition
