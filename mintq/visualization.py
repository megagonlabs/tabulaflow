import graphviz
from mintq.schema_formatter import get_schema_formatter
from mintq.schema import ERDiagram


def er_diagram_to_graphviz(erd: ERDiagram) -> graphviz.Digraph:
    g = graphviz.Digraph()
    g.attr("node", shape="none", fontname="Courier")  # Remove outer box
    g.attr("graph", rankdir="LR", nodesep="0.25", ranksep="0.5", splines="true")

    formatter = get_schema_formatter("sql_default")

    for table in erd.db_schema.tables:
        # Create a table node with columns as rows
        columns_html = (
            '<TR><TD COLSPAN="2" BGCOLOR="#4f5475" ALIGN="LEFT"><FONT COLOR="white"><B>'
            + formatter.format_table_name(table)
            + "</B></FONT></TD></TR>"
        )
        for col in table.columns:
            columns_html += f'<TR><TD PORT="{col.name}-name" ALIGN="LEFT" BGCOLOR="#eeeeee"><FONT COLOR="#2b2b2b">{col.name}</FONT></TD>"\
            "<TD PORT="{col.name}-type" ALIGN="RIGHT" BGCOLOR="#eeeeee"><FONT POINT-SIZE="10" COLOR="#888888">{col.type}</FONT></TD></TR>'

        # Create HTML table for the node
        table_html = f"""<
        <TABLE BORDER="0" CELLBORDER="0" CELLSPACING="2" CELLPADDING="4">
            {columns_html}
        </TABLE>>"""

        g.node(f"{table.schema_name}.{table.name}", table_html)

    for relation in erd.relations:
        g.edge(
            f"{relation.from_schema}.{relation.from_table}:{relation.from_column}-type:e",
            f"{relation.to_schema}.{relation.to_table}:{relation.to_column}-name:w",
            label="",
            color="#cccccc",
            dir="none",
        )
    return g
