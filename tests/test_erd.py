from tabulaflow.core import TableRef
from tabulaflow.research.preprocessing.erd import (
    ERDConceptualEntity,
    ERDRelationship,
    ERDRelationshipParticipant,
    ERDiagram,
    EntitySourceTable,
    MermaidERDiagramFormatter,
)


def _erd() -> ERDiagram:
    return ERDiagram(
        conceptual_entities=[
            ERDConceptualEntity(
                name="Customer",
                description="A customer.",
                source_tables=[
                    EntitySourceTable(
                        schema_name="public", table_name="customers", mapping_description="Customer records."
                    )
                ],
            ),
            ERDConceptualEntity(
                name="Order",
                description="An order.",
                source_tables=[
                    EntitySourceTable(schema_name="public", table_name="orders", mapping_description="Order records.")
                ],
            ),
        ],
        relationships=[
            ERDRelationship(
                name="Places",
                description="A customer places orders.",
                participants=[
                    ERDRelationshipParticipant(
                        entity="Customer", role="customer", max_cardinality="one", participation="mandatory"
                    ),
                    ERDRelationshipParticipant(
                        entity="Order", role="order", max_cardinality="many", participation="optional"
                    ),
                ],
                join_sql_snippet="FROM customers JOIN orders ON customers.id = orders.customer_id",
            )
        ],
    )


def test_trim_removes_entities_and_relationships_outside_selected_tables() -> None:
    trimmed = _erd().trim([TableRef(schema_name="public", table_name="customers")])

    assert [entity.name for entity in trimmed.conceptual_entities] == ["Customer"]
    assert trimmed.relationships == []


def test_mermaid_formatter_preserves_entities_relationships_and_join_path() -> None:
    rendered = MermaidERDiagramFormatter().format(_erd())

    assert "Customer ||--o{ Order" in rendered
    assert "%% SQL join path: `FROM customers JOIN orders ON customers.id = orders.customer_id`" in rendered
