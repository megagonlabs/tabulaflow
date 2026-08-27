"""Canonical ordering and identifiers for ambiguous research tasks."""

import copy
import itertools

import numpy as np

from tabulaflow.research.types import AmbigNL2QTask, GoldAmbiguityPoint


def int_to_letter(idx: int) -> str:
    """Convert a zero-based index to an Excel-style uppercase identifier."""
    result = ""
    while True:
        result = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"[idx % 26] + result
        idx //= 26
        if idx == 0:
            return result
        idx -= 1


def sort_gold_queries(task: AmbigNL2QTask) -> AmbigNL2QTask:
    """Return a copy whose gold queries follow ambiguity-point product order."""
    task = copy.deepcopy(task)
    finite_points = [point for point in task.gold_ambiguity_points if point.type == "finite"]
    query_ids = [
        "GQRY" + "".join(f"-{point.id}.{idx}" for point, idx in zip(finite_points, indexes))
        for indexes in itertools.product(*[range(len(point.interpretations)) for point in finite_points])
    ]
    queries_by_id = {query.id: query for query in task.gold_queries}
    task.gold_queries = [queries_by_id[query_id] for query_id in query_ids]
    return AmbigNL2QTask.model_validate(task.model_dump())


def sort_ambiguity_points(task: AmbigNL2QTask) -> AmbigNL2QTask:
    """Return a copy with ambiguity points and dependent query ids in text order."""
    task = sort_gold_queries(copy.deepcopy(task))

    def location(point: GoldAmbiguityPoint) -> tuple[int, int, int]:
        return (task.question.index(point.phrase), len(point.phrase), 0 if point.type == "finite" else 1)

    def remap_query_id(query_id: str, id_mapping: dict[str, str]) -> str:
        parts = query_id.split("-")
        return "-".join(
            [parts[0], *sorted(part.translate(str.maketrans(id_mapping)) for part in parts[1:])]  # type: ignore[arg-type]
        )

    point_order = sorted(range(len(task.gold_ambiguity_points)), key=lambda i: location(task.gold_ambiguity_points[i]))
    new_points = [task.gold_ambiguity_points[i] for i in point_order]

    finite_points = [point for point in task.gold_ambiguity_points if point.type == "finite"]
    finite_order = sorted(range(len(finite_points)), key=lambda i: location(finite_points[i]))
    query_indexes = np.arange(len(task.gold_queries)).reshape([len(point.interpretations) for point in finite_points])
    task.gold_queries = [task.gold_queries[i] for i in np.permute_dims(query_indexes, finite_order).flatten()]

    task.gold_ambiguity_points = new_points
    id_mapping = {point.id: int_to_letter(i) for i, point in enumerate(new_points)}
    for point in task.gold_ambiguity_points:
        point.id = id_mapping[point.id]
    for query in task.gold_queries:
        query.id = remap_query_id(query.id, id_mapping)

    assert task.gold_intended_query_id is not None
    task.gold_intended_query_id = remap_query_id(task.gold_intended_query_id, id_mapping)
    return AmbigNL2QTask.model_validate(task.model_dump())
