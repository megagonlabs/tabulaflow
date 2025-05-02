import re
import logging
import litellm
import jinja2
from mintq.schema import ERDiagram, ERDiagramRelation
from mintq.schema_formatter import get_schema_formatter
from mintq.metadata_synthesizer.base import BaseMetadataSynthesizer

logger = logging.getLogger(__name__)


class RuleBasedERDiagramSynthesizer(BaseMetadataSynthesizer):
    def run(self, db_connector) -> ERDiagram:
        schema = db_connector.schema

        suffixes = "id|key|code|number|no|ref"

        erd = ERDiagram(db_schema=schema, relations=[])
        for from_table in schema.tables:
            for from_column in from_table.columns:
                patterns = [
                    rf"(.+?)_?(:?{suffixes})$",
                    r".*?_(.+?)$",
                ]
                target_hint = None
                for pattern in patterns:
                    m = re.match(pattern, from_column.name, re.I)
                    if m:
                        target_hint = m.group(1).lower()
                        break
                if not target_hint:
                    continue

                for to_table in schema.tables:
                    if from_table.name == to_table.name:
                        continue

                    if to_table.name.lower().startswith(target_hint):
                        candidates = [
                            col.name
                            for col in to_table.columns
                            if re.match(
                                rf"^({re.escape(target_hint)})?_?({suffixes})$",
                                col.name,
                                re.I,
                            )
                        ]
                        if len(candidates) > 1:
                            logger.warning(
                                "Multiple candidate columns found for %s in %s and %s: %s",
                                from_column.name,
                                from_table.name,
                                to_table.name,
                                ", ".join(candidates),
                            )
                        if candidates:
                            erd.relations.append(
                                ERDiagramRelation(
                                    from_table=from_table.name,
                                    from_column=from_column.name,
                                    to_table=to_table.name,
                                    to_column=candidates[0],
                                )
                            )
        return erd


CANDIDATE_FK_PROMPT = """
You are a helpful assistant that synthesizes ER diagrams from a given database schema.
Given a table, you need to determine what columns might be foreign keys.
- The output should be a JSON list of dictionaries with the following keys:
  - "column": the name of the column that might be a foreign key
  - "reference_table": the name of the table that the foreign key references

=== Example ===

Database: ECOMMERCE

Here are the tables in the database:
- orders
- customers
- products
- order_items

Here is the schema of the selected table:
Table: orders (10000 rows)
  - id: VARCHAR
  - customer_id: VARCHAR
  - product_id: VARCHAR
  - quantity: INTEGER
  - total_price: FLOAT

Output:
```json
[
    {"column": "customer_id", "reference_table": "customers"},
    {"column": "product_id", "reference_table": "products"},
]
```

=== Your task ===

Database: {{db_name}}

Here are the tables in the database:
{{all_tables}}

Here is the schema of the selected table:
{{table_schema}}

You need to determine what columns might be foreign keys.

Output:
"""


class LLMERDiagramSynthesizer(BaseMetadataSynthesizer):
    def run(self, db_connector) -> ERDiagram:
        schema = db_connector.schema
        formatter = get_schema_formatter("sql_default")

        all_schema_names = [table.schema_name for table in schema.tables]
        is_multi_schema = len(set(all_schema_names)) > 1

        all_tables = [
            f"{table.schema_name}.{table.name}" if table.schema_name and is_multi_schema else table.name
            for table in schema.tables
        ]
        all_tables = "\n".join([f"- {table}" for table in all_tables])

        prompts = [
            jinja2.Template(CANDIDATE_FK_PROMPT).render(
                db_name=schema.name,
                all_tables=all_tables,
                table_schema=formatter.format_table(table),
            )
            for table in schema.tables
        ]
        print(prompts[0])


if __name__ == "__main__":
    import json
    import time
    from mintq.schema_formatter import get_schema_formatter
    from mintq.db_connector.snowflake_conn import SnowflakeConnector
    from mintq.visualization import er_diagram_to_graphviz
    import os

    t0 = time.time()
    connector = SnowflakeConnector(
        "ADVENTUREWORKS",
        os.environ["SF_USER"],
        os.environ["SF_PASSWORD"],
        os.environ["SF_ACCOUNT"],
        "ADVENTUREWORKS",
    )
    synthesizer = LLMERDiagramSynthesizer()
    erd = synthesizer.run(connector)
    exit(9)
    print(json.dumps(erd.model_dump(), indent=2))
    print(f"Time taken: {time.time() - t0} seconds")

    g = er_diagram_to_graphviz(erd)
    g.render("erd", format="png")
