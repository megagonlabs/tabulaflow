"""RDF schema formatting for SPARQL query generation."""

from typing import ClassVar

from tabulaflow.core.schema import RDFSchema
from tabulaflow.output.formatting.schema import schema_formatter_registry


@schema_formatter_registry.register
class SPARQLSchemaFormatter:
    """Format a minimal RDF source description for SPARQL queries."""

    name: ClassVar[str] = "sparql"

    def format(self, schema: RDFSchema) -> str:
        header = f"Data source: {schema.display_name} (Query language: sparql)"
        if schema.description:
            header += f"\nDescription: {schema.description}"
        return f"{header}\n\nDeclare any required prefixes in the SPARQL query."
