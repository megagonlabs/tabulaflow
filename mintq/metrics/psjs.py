"""Provenance Subgraph Jaccard Similarity (PSJS) metric from CypherBench.

Computes Jaccard similarity between the sets of node element IDs in the
provenance subgraphs of the predicted and gold Cypher queries.

Reference: https://github.com/megagonlabs/cypherbench
"""

import logging
import re
from typing import ClassVar

from mintq.db_connector import NL2QDBConnector
from mintq.db_connector.neo4j_conn import Neo4jConnector
from mintq.metrics.base import metric_registry
from mintq.metrics.utils import get_final_gold_query, get_final_pred_query
from mintq.schema import NL2QTaskOutput, NumericOrNull

logger = logging.getLogger(__name__)


def _split_by_union(cypher: str) -> list[str]:
    """Split a Cypher query by UNION, handling CALL { ... } blocks."""
    pattern = r"\bUNION\b"

    if cypher.strip().startswith("CALL"):
        inner_query_match = re.search(r"CALL\s*\{(.*?)\}\s*(WITH|RETURN|WHERE|UNWIND)", cypher, re.DOTALL)
        if inner_query_match:
            inner_query = inner_query_match.group(1)
            return [q.strip() for q in re.split(pattern, inner_query)]
        else:
            return [cypher.strip()]
    else:
        return [q.strip() for q in re.split(pattern, cypher)]


_CLAUSE_PATTERN = re.compile(
    r"\b(MATCH|OPTIONAL MATCH|WHERE|RETURN|UNION|WITH|CREATE|SET|DELETE"
    r"|MERGE|UNWIND|ORDER BY|LIMIT|SKIP|FOREACH|CALL|YIELD)\b"
)


def _split_cypher_into_clauses(cypher_query: str) -> list[str]:
    """Split a Cypher query into its constituent clauses."""
    matches = list(_CLAUSE_PATTERN.finditer(cypher_query))
    clauses = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(cypher_query)
        clauses.append(cypher_query[start:end].strip())
    return clauses


def _extract_match_cypher(cypher: str) -> str | None:
    """Extract the MATCH/OPTIONAL MATCH/WHERE portion of a Cypher query."""
    if not cypher.startswith("MATCH"):
        return None

    clauses = _split_cypher_into_clauses(cypher)
    match_clauses = []
    for clause in clauses:
        if not any(clause.startswith(kw) for kw in ["MATCH", "OPTIONAL MATCH", "WITH", "WHERE"]):
            break
        if clause.startswith("WITH"):
            if " as " in clause.lower():
                break
            else:
                match_clauses.append("WITH *")
        else:
            match_clauses.append(clause)

    while match_clauses and match_clauses[-1].startswith("WITH"):
        match_clauses.pop()

    return " ".join(match_clauses)


def _add_variables(match_cypher: str) -> str:
    """Add temporary variable names to anonymous nodes and relationships."""
    node_counter = 0
    relationship_counter = 0

    def replace_node(match: re.Match[str]) -> str:
        nonlocal node_counter
        replacement = f"(ntmp{node_counter}:{match.group(2)}{match.group(3) or ''})"
        node_counter += 1
        return replacement

    def replace_relationship(match: re.Match[str]) -> str:
        nonlocal relationship_counter
        replacement = f"[rtmp{relationship_counter}{match.group(2)}]"
        relationship_counter += 1
        return replacement

    clauses = _split_cypher_into_clauses(match_cypher)
    for i, clause in enumerate(clauses):
        if clause.startswith("MATCH") or clause.startswith("OPTIONAL MATCH"):
            clause = re.sub(r"(\[)(:.*?)(\])", replace_relationship, clause)
            clauses[i] = re.sub(r"(\(:)([A-Za-z]+)(\s*\{.*?\})?\)", replace_node, clause)

    return " ".join(clauses)


def _extract_node_variables(match_cypher: str) -> list[str]:
    """Extract named node variables from MATCH clauses."""
    sanitized = re.sub(r"\{[^}]*\}", "{dummy}", match_cypher)
    pattern = r"\((\w+)(?::[^\)]*|\))"
    variables: list[str] = []
    clauses = _split_cypher_into_clauses(sanitized)
    for clause in clauses:
        if clause.startswith("MATCH") or clause.startswith("OPTIONAL MATCH"):
            variables += re.findall(pattern, clause)
    return sorted(set(variables))


def _get_ps_cypher(cypher: str, return_var: str = "elemId") -> str:
    """Build a Cypher query returning node element IDs of the provenance subgraph."""
    sub_cyphers = _split_by_union(cypher)
    ps_cyphers = []
    for sub_cypher in sub_cyphers:
        match_cypher = _extract_match_cypher(sub_cypher)
        if match_cypher:
            match_cypher = _add_variables(match_cypher)
            node_vars = _extract_node_variables(match_cypher)
            node_expr = " + ".join(f"collect(distinct elementId({var}))" for var in node_vars)
            node_expr = node_expr if node_expr else "[]"
            ps_cyphers.append(
                f"{match_cypher} WITH {node_expr} AS elemIds UNWIND elemIds AS elemId RETURN elemId AS {return_var}"
            )

    if len(ps_cyphers) == 0:
        logger.warning(f"No MATCH clause found in cypher: {cypher}")
        return f"UNWIND [] AS elemId RETURN elemId AS {return_var}"

    return " UNION ".join(ps_cyphers)


@metric_registry.register
class PSJS:
    """Provenance Subgraph Jaccard Similarity (PSJS) from CypherBench.

    For each query, extracts the MATCH pattern, runs it against Neo4j to
    collect node element IDs, then computes Jaccard similarity between the
    gold and predicted provenance node sets.
    """

    name: ClassVar[str] = "psjs"
    compatible_output_types: ClassVar[list[str]] = ["simple"]

    async def compute_async(self, task: NL2QTaskOutput, db_connector: NL2QDBConnector | None = None) -> NumericOrNull:
        pred_query = get_final_pred_query(task, check_exec_result=False, roundtrip_exec_result_csv=False)
        gold_query = get_final_gold_query(task, check_exec_result=False, roundtrip_exec_result_csv=False)

        if pred_query is None or gold_query.query is None:
            return 0.0

        pred_cypher = pred_query.query
        target_cypher = gold_query.query

        if pred_cypher == target_cypher:
            return 1.0

        if not isinstance(db_connector, Neo4jConnector):
            raise TypeError(f"PSJS requires a Neo4jConnector, got {type(db_connector)}")

        target_ps_cypher = _get_ps_cypher(target_cypher, return_var="elemId1")
        pred_ps_cypher = _get_ps_cypher(pred_cypher, return_var="elemId2")

        try:
            target_records = await db_connector._run_cypher(target_ps_cypher)
            target_ps = {record["elemId1"] for record in target_records}

            pred_records = await db_connector._run_cypher(pred_ps_cypher, timeout=120)
            pred_ps = {record["elemId2"] for record in pred_records}

            intersection = len(target_ps & pred_ps)
            union = len(target_ps | pred_ps)
            return intersection / union if union > 0 else 0.0
        except Exception as e:
            logger.warning(f"PSJS evaluation failed: {e}")
            return 0.0
