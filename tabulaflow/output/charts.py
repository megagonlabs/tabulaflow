"""Vega-Lite chart specification validation."""

from __future__ import annotations

import re
from collections.abc import Mapping
import pandas as pd

from tabulaflow.output.specs import ArtifactSpecError

_CHART_MAX_ROWS = 20_000
_MULTIVIEW_KEYS = ("layer", "concat", "hconcat", "vconcat", "facet", "repeat", "spec")
_MARK_LABELS = {
    "bar": "Bar chart",
    "line": "Line chart",
    "point": "Scatter plot",
    "circle": "Scatter plot",
    "square": "Scatter plot",
    "tick": "Strip plot",
    "area": "Area chart",
    "arc": "Pie chart",
    "rect": "Heatmap",
    "boxplot": "Box plot",
    "rule": "Rule chart",
    "text": "Text chart",
    "trail": "Line chart",
    "geoshape": "Map",
}

__all__ = [
    "ChartSpecError",
    "chart_type_label",
    "validate_chart_spec",
]


class ChartSpecError(ArtifactSpecError):
    """Raised when a chart specification cannot be applied to its sources."""


def _resolve_chart_column(df: pd.DataFrame, name: str) -> str | None:
    """Resolve a column name case-insensitively."""
    for column in df.columns:
        if str(column).casefold() == name.casefold():
            return str(column)
    return None


def _chart_mark_type(spec: Mapping[str, object]) -> str:
    """Return the root Vega-Lite mark type, or an empty string for multi-view specs."""
    mark = spec.get("mark", "")
    return str(mark.get("type", "")) if isinstance(mark, Mapping) else str(mark)


def _is_multiview_spec(spec: Mapping[str, object]) -> bool:
    """Return whether a Vega-Lite specification contains multiple views."""
    return any(key in spec for key in _MULTIVIEW_KEYS)


def chart_type_label(spec: Mapping[str, object]) -> str:
    """Return a human-readable chart type label."""
    if any(key in spec for key in ("layer", "hconcat", "vconcat", "concat")):
        return "Composite chart"
    if "facet" in spec or "repeat" in spec:
        return "Faceted chart"
    return _MARK_LABELS.get(_chart_mark_type(spec), "Chart")


def validate_chart_spec(
    spec: Mapping[str, object],
    sources: Mapping[str, pd.DataFrame],
) -> None:
    """Validate a Vega-Lite spec against one or more source variants."""
    if "mark" not in spec and not _is_multiview_spec(spec):
        raise ChartSpecError("spec must have a 'mark' or be a multi-view spec (layer/facet/concat)")

    field_refs, has_transform = _spec_field_refs(spec)
    errors: list[str] = []
    for label, df in sources.items():
        if len(df) > _CHART_MAX_ROWS:
            errors.append(f"{label} — {len(df):,} rows is too large to chart; max {_CHART_MAX_ROWS:,} rows")
        if not has_transform:
            missing = sorted(field for field in field_refs if not _field_resolves(df, field))
            if missing:
                errors.append(f"{label} — field(s) not found: {missing}. Available columns: {list(df.columns)}")
    if errors:
        raise ChartSpecError(f"chart source validation failed for {len(errors)} issue(s):\n  " + "\n  ".join(errors))


def _spec_field_refs(spec: object) -> tuple[set[str], bool]:
    fields: set[str] = set()
    has_transform = False

    def walk(node: object) -> None:
        nonlocal has_transform
        if isinstance(node, Mapping):
            if "transform" in node:
                has_transform = True
            field = node.get("field")
            if isinstance(field, str):
                fields.add(field)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(spec)
    return fields, has_transform


def _field_resolves(df: pd.DataFrame, field: str) -> bool:
    if _resolve_chart_column(df, field) is not None:
        return True
    root = re.split(r"[.\[]", field, maxsplit=1)[0]
    return root != field and _resolve_chart_column(df, root) is not None
