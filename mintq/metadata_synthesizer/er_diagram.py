import re
import logging
import litellm
import jinja2
import collections
from mintq.db_connector import BaseSQLDBConnector
from mintq.schema import ERDiagram, ERDiagramRelation
from mintq.schema_formatter import SQLDefaultSchemaFormatter
from mintq.utils import extract_code

logger = logging.getLogger(__name__)


class RuleBasedERDiagramSynthesizer:
    name = "rule_based_er_diagram"

    def run(self, db_connector: BaseSQLDBConnector) -> ERDiagram:
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
- Given a table, you need to determine what columns might be foreign keys.
- If a column looks like a foreign key but its reference table is not in the database, ignore it.
- The output should be a JSON list of dictionaries with the following keys:
  - "source_column": the name of the column that might be a foreign key
  - "target_table": the name of the table that the foreign key references.
    - The table name should include the schema name if it exists.
    - The table and schema names should be quoted if they contain spaces.

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
    {"source_column": "customer_id", "target_table": "customers"},
    {"source_column": "product_id", "target_table": "products"}
]
```

=== Your task ===

Database: {{db_name}}

Here are the tables in the database:
{{all_table_names}}

Here is the schema of the selected table:
{{table_schema}}

Output:
"""


REFERENCE_COLUMN_PROMPT = """
You are a helpful assistant that synthesizes ER diagrams from a given database schema.
- Given a candidate foreign key column in a source table, you need to select from the target table the column that it references.
- The output should be a list of JSON dictionaries with the following keys:
  - "source_table": the name of the source table
    - The table name should include the schema name if it exists.
    - The table and schema names should be quoted if they contain spaces.
  - "source_column": the name of the source column that is a candidate foreign key
  - "target_column": the name of the column in the target table that the foreign key references. If no reference column is found, set this to null.

=== Example ===

Database: ECOMMERCE

Candidate Foreign Keys:
- (Table: orders) customer_id 
- (Table: orders) product_id 

Here is the schema of the target table:
Table: customers (10000 rows)
  - id: VARCHAR
  - name: VARCHAR
  - email: VARCHAR

Output:
```json
[
    {"source_table": "orders", "source_column": "customer_id", "target_column": "id"},
    {"source_table": "orders", "source_column": "product_id", "target_column": null}
]
```

=== Your task ===

Database: {{db_name}}

Candidate Foreign Keys:
{{candidate_foreign_keys}}

Here is the schema of the target table:
{{target_table}}

Output:
"""


class LLMERDiagramSynthesizer:
    name = "llm_er_diagram"

    def __init__(self, llm: str = "openai/gpt-4o"):
        self.llm = llm

    def run(self, db_connector: BaseSQLDBConnector) -> ERDiagram:
        schema = db_connector.schema
        formatter = SQLDefaultSchemaFormatter()

        prompts = [
            jinja2.Template(CANDIDATE_FK_PROMPT).render(
                db_name=schema.name,
                all_table_names="\n".join([f"- {formatter.format_table_name(table)}" for table in schema.tables]),
                table_schema=formatter.format_table(table),
            )
            for table in schema.tables
        ]
        responses = litellm.batch_completion(
            model=self.llm,
            messages=[[{"role": "user", "content": prompt}] for prompt in prompts],
            temperature=0.0,
        )

        reference_table_to_fks = collections.defaultdict(list)
        for table, r in zip(schema.tables, responses):
            for dic in json.loads(extract_code(r["choices"][0]["message"]["content"])):
                reference_table_to_fks[dic["target_table"]].append(
                    (formatter.format_table_name(table), dic["source_column"])
                )

        prompts = []
        for table in schema.tables:
            candidate_fks = "\n".join(
                [f"- (Table: {t}) {c}" for t, c in reference_table_to_fks[formatter.format_table_name(table)]]
            )
            prompts.append(
                jinja2.Template(REFERENCE_COLUMN_PROMPT).render(
                    db_name=schema.name,
                    candidate_foreign_keys=candidate_fks,
                    target_table=formatter.format_table(table),
                )
            )
        responses = litellm.batch_completion(
            model=self.llm,
            messages=[[{"role": "user", "content": prompt}] for prompt in prompts],
            temperature=0.0,
        )

        all_tables = {formatter.format_table_name(table): table for table in schema.tables}

        erd = ERDiagram(db_schema=schema, relations=[])
        for table, r in zip(schema.tables, responses):
            for dic in extract_code(r["choices"][0]["message"]["content"]):
                if dic["target_column"] is not None:
                    src_table = all_tables[dic["source_table"]]
                    erd.relations.append(
                        ERDiagramRelation(
                            from_schema=src_table.schema_name,
                            from_table=src_table.name,
                            from_column=dic["source_column"],
                            to_schema=table.schema_name,
                            to_table=table.name,
                            to_column=dic["target_column"],
                        )
                    )
        return erd


if __name__ == "__main__":
    import json
    import time
    from mintq.db_connector.snowflake_conn import SnowflakeConnector
    from mintq.visualization import er_diagram_to_graphviz
    import os

    t0 = time.time()
    connector = SnowflakeConnector(
        "AIRLINES",
        os.environ["SF_USER"],
        os.environ["SF_PASSWORD"],
        os.environ["SF_ACCOUNT"],
        "AIRLINES",
    )
    synthesizer = LLMERDiagramSynthesizer()
    erd = synthesizer.run(connector)
    print(json.dumps(erd.model_dump(), indent=2))
    print(f"Time taken: {time.time() - t0} seconds")

    g = er_diagram_to_graphviz(erd)
    g.render("erd", format="png")
