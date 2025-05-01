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
        g.attr("node", shape="none", fontname="Courier")  # Remove outer box
        g.attr("graph", rankdir="LR", nodesep="0.25", ranksep="0.5")

        for table in self.db_schema.tables:
            # Create a table node with columns as rows
            columns_html = (
                '<TR><TD COLSPAN="2" BGCOLOR="#444444" ALIGN="LEFT"><FONT COLOR="white"><B>'
                + table.name
                + "</B></FONT></TD></TR>"
            )
            for col in table.columns:
                columns_html += f'<TR><TD PORT="{col.name}-name" ALIGN="LEFT" BGCOLOR="#eeeeee"><FONT COLOR="#2b2b2b">{col.name}</FONT></TD>"\
                "<TD PORT="{col.name}-type" ALIGN="RIGHT" BGCOLOR="#eeeeee"><FONT COLOR="#666666">{col.type}</FONT></TD></TR>'

            # Create HTML table for the node
            table_html = f"""<
            <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2">
                {columns_html}
            </TABLE>>"""

            g.node(table.name, table_html)

        for relation in self.relations:
            g.edge(
                f"{relation.from_table}:{relation.from_column}-type:e",
                f"{relation.to_table}:{relation.to_column}-name:w",
                label="",
                color="#cccccc",
                dir="none",
                arrowhead="dot",
                arrowtail="dot",
                arrowsize="0.5",
            )
        return g


class ERDiagramSynthesizer(BaseMetadataSynthesizer):
    def run(self, db_connector):
        # schema = db_connector.schema

        if not os.path.exists("cache/airlines_schema.json"):
            with open("cache/airlines_schema.json", "w") as f:
                f.write(schema.model_dump_json())
        else:
            with open("cache/airlines_schema.json", "r") as f:
                schema = SQLSchema.model_validate_json(f.read())

        suffixes = "id|key|code|number|no|ref"

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
    # connector = SnowflakeConnector(
    #     "AIRLINES",
    #     os.environ["SF_USER"],
    #     os.environ["SF_PASSWORD"],
    #     os.environ["SF_ACCOUNT"],
    #     "AIRLINES",
    # )
    synthesizer = ERDiagramSynthesizer()
    erd = synthesizer.run(None)
    print(json.dumps(erd.model_dump(), indent=2))
    print(f"Time taken: {time.time() - t0} seconds")

    g = erd.to_graphviz()
    g.render("erd", format="png")
