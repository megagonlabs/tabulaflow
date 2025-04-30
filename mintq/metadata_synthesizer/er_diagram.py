from pydantic import BaseModel
from typing import List
import re
import logging
import graphviz
from mintq.schema import SQLSchema
from mintq.metadata_synthesizer.base import BaseMetadataSynthesizer

logger = logging.getLogger(__name__)


class Relation(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class ERDiagram(BaseModel):
    db_schema: SQLSchema
    relations: List[Relation]

    def to_graphviz(self):
        g = graphviz.Digraph()
        for table in self.db_schema.tables:
            g.node(table.name, table.name)
        for relation in self.relations:
            g.edge(
                relation.from_table,
                relation.to_table,
                label=f"{relation.from_column}:{relation.to_column}",
            )
        return g


class ERDiagramSynthesizer(BaseMetadataSynthesizer):
    def run(self, db_connector):
        schema = db_connector.schema

        suffixes = "id|key|code|number|no"

        erd = ERDiagram(db_schema=schema, relations=[])
        for from_table in schema.tables:
            for from_column in from_table.columns:
                m = re.match(rf"(.+?)_?(:?{suffixes})$", from_column.name, re.I)
                if not m:
                    continue
                target_hint = m.group(1).lower()
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
                                Relation(
                                    from_table=from_table.name,
                                    from_column=from_column.name,
                                    to_table=to_table.name,
                                    to_column=candidates[0],
                                )
                            )
        return erd


if __name__ == "__main__":
    import json
    import time
    from mintq.schema_formatter import get_schema_formatter
    from mintq.db_connector.snowflake_conn import SnowflakeConnector
    import os

    t0 = time.time()
    connector = SnowflakeConnector(
        "AIRLINES",
        os.environ["SF_USER"],
        os.environ["SF_PASSWORD"],
        os.environ["SF_ACCOUNT"],
        "AIRLINES",
    )
    synthesizer = ERDiagramSynthesizer()
    erd = synthesizer.run(connector)
    print(json.dumps(erd.model_dump(), indent=2))
    print(f"Time taken: {time.time() - t0} seconds")

    g = erd.to_graphviz()
    g.render("erd", format="png")
