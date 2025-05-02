import re
import logging
from mintq.schema import ERDiagram, ERDiagramRelation
from mintq.metadata_synthesizer.base import BaseMetadataSynthesizer

logger = logging.getLogger(__name__)


class ERDiagramSynthesizer(BaseMetadataSynthesizer):
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
    synthesizer = ERDiagramSynthesizer()
    erd = synthesizer.run(connector)
    print(json.dumps(erd.model_dump(), indent=2))
    print(f"Time taken: {time.time() - t0} seconds")

    g = er_diagram_to_graphviz(erd)
    g.render("erd", format="png")
