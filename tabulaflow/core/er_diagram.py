"""Conceptual ER-diagram data structures.

The deterministic data model lives in ``core`` (consumed by ``core.formatters``);
the LLM synthesizer that *produces* an ``ERDiagram`` lives in ``modulehub``.
"""

from typing import Literal

from pydantic import BaseModel, Field

from tabulaflow.core.types import TableRef


class EntitySourceTable(BaseModel):
    schema_name: str | None
    table_name: str
    mapping_description: str = Field(
        description="A concise sentence description of what information is stored in the table."
    )


class ERDConceptualEntity(BaseModel):
    name: str = Field(description="The name of the conceptual entity, in PascalCase.")
    description: str = Field(description="A 1-2 sentence description of the conceptual entity.")
    source_tables: list[EntitySourceTable]


class ERDRelationshipParticipant(BaseModel):
    """A participant entity in a relationship with its cardinality."""

    entity: str
    role: str
    max_cardinality: Literal["one", "many"]
    participation: Literal["mandatory", "optional"]


class ERDRelationship(BaseModel):
    name: str = Field(description="The name of the relationship, in PascalCase.")
    description: str = Field(description="A 1-2 sentence description of the relationship.")
    participants: list[ERDRelationshipParticipant] = Field(description="The participants in the n-ary relationship.")
    join_sql_snippet: str = Field(
        description="The SQL snippet to join the participants. Should include all participating tables. Example: `FROM table1 JOIN table2 ON table1.id = table2.id`"
    )


class ERDiagram(BaseModel):
    conceptual_entities: list[ERDConceptualEntity]
    relationships: list[ERDRelationship]

    def trim(self, table_refs: list[TableRef], case_insensitive: bool = True) -> "ERDiagram":
        """Trim the ER diagram to only include entities and relationships relevant to the given tables."""

        def normalize(s: str | None) -> str | None:
            return s.lower() if s is not None and case_insensitive else s

        # Convert table_refs to a set of (schema_name, table_name) tuples for fast lookup
        table_ref_set = {(normalize(ref.schema_name), normalize(ref.table_name)) for ref in table_refs}

        # Keep entities that have at least one source table in the given table_refs
        kept_entities: list[ERDConceptualEntity] = []
        kept_entity_names: set[str] = set()
        for entity in self.conceptual_entities:
            for source_table in entity.source_tables:
                if (normalize(source_table.schema_name), normalize(source_table.table_name)) in table_ref_set:
                    kept_entities.append(entity)
                    kept_entity_names.add(entity.name)
                    break

        # Keep relationships where all participants are in the kept entities
        kept_relationships: list[ERDRelationship] = []
        for relationship in self.relationships:
            if all(p.entity in kept_entity_names for p in relationship.participants):
                kept_relationships.append(relationship)

        return ERDiagram(conceptual_entities=kept_entities, relationships=kept_relationships)
