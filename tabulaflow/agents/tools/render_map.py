"""Model-facing tool for creating map output artifacts."""

import json
from typing import ClassVar

import pandas as pd
from pydantic_ai import Tool

from tabulaflow.output.maps import (
    MapSpecError,
    normalize_map_spec,
    parse_map_spec,
    referenced_source_ids,
)
from tabulaflow.output.store import OutputStore, SourceNotApplicable, SourceResolutionError


class RenderMapTool:
    """Create a declarative map artifact from one or more sources."""

    name: ClassVar = "render_map"

    def __init__(self, output_store: OutputStore | None = None) -> None:
        self._output_store = output_store or OutputStore()

    async def __call__(self, *, map_spec: str) -> str:
        """Create a map from one or more sources.

        The spec is a JSON string containing an object with a non-empty
        ``layers`` list. Each column/geojson layer names the source it
        reads from via ``source_id``; layers with different ``source_id`` values
        overlay data from multiple sources on one map (e.g. GeoJSON
        boundaries from one source and point markers from another).

        Full public grammar:
        - Top level:
          ``title``: optional string.
          ``view``: optional object with ``fit`` bool, ``center`` as
          ``[lat, lng]``, ``zoom`` number, and ``maxZoom`` number.
          ``layers``: required non-empty list.
        - Common layer fields:
          ``source_id``: output-store source id the layer reads from (e.g.
          ``"S3"``). Required for column and geojson layers; omit for inline
          ``points``.
          ``label``: optional field name for the short feature identity.
          ``tooltip``: optional field name, list of field names, or ``true``;
          shown as popup body fields on hover and click. Popup titles use
          ``label`` when present. String values that are full ``http(s)`` URLs
          render as links.
          ``color``: optional ``{"field":"status"}`` or
          ``{"field":"status","domain":[...]}``; the output pane chooses the
          palette.
        - ``points`` layer:
          Column mode: ``{"type":"points","source_id":"S3","lat":"lat","lng":"lng"}``.
          Inline mode:
          ``{"type":"points","points":[{"lat":37.7,"lng":-122.4,"label":"Destination"}]}``.
          Add optional ``label``, ``tooltip``, ``color``, ``marker``, and
          ``size``. Inline ``label``, ``tooltip``, ``color``, and ``size``
          reference inline point property names.
          ``marker`` is ``{"type":"pin"}`` or ``{"type":"circle"}``.
          ``size`` is ``{"field":"value"}``; the output pane chooses the
          radius range.
        - ``geojson`` layer:
          ``{"type":"geojson","source_id":"S3","geojson":"geom_geojson"}`` plus
          optional ``label``, ``tooltip``, and ``color``. ``geojson`` is a
          column name or inline WGS84 GeoJSON object. If the database has
          native geometry, convert it in SQL first (e.g.
          ``ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geom_geojson``) and
          reference that column.

        Minimal examples:
        ``{"layers":[{"type":"points","source_id":"S3","lat":"lat","lng":"lng","label":"name","tooltip":["status"]}]}``
        ``{"layers":[{"type":"points","points":[{"lat":37.7,"lng":-122.4,"label":"Destination"}],"label":"label"}]}``
        ``{"layers":[{"type":"geojson","source_id":"S3","geojson":"geom_geojson","label":"name","tooltip":["status"]}]}``

        Multi-source overlay:
        ``{"layers":[{"type":"geojson","source_id":"S1","geojson":"area_geojson","label":"area"},{"type":"points","source_id":"S2","lat":"lat","lng":"lng","label":"name"}]}``

        Prefer defaults unless the user asks for styling or a fixed viewport.

        If the database has native geometry, convert it to WGS84 GeoJSON in SQL
        before calling this tool, using the database's spatial functions. For
        example, PostGIS:
        ``ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geom_geojson``; DuckDB
        spatial: ``ST_AsGeoJSON(ST_Transform(geom, 'EPSG:4326')) AS geom_geojson``.

        Returns the new map id (``MAP1``, ``MAP2``, …) to cite in the answer.

        Args:
            map_spec: Declarative map specification as a JSON string. GeoJSON
                coordinates must be WGS84 longitude/latitude.
        """
        try:
            spec = json.loads(map_spec)
        except (json.JSONDecodeError, TypeError) as e:
            return f"(error: invalid JSON — {e})"

        if not isinstance(spec, dict):
            return "(error: map_spec must be a JSON object)"

        try:
            parsed = parse_map_spec(spec)
        except MapSpecError as e:
            return f"(error: {e})"

        source_ids = referenced_source_ids(parsed)
        sources: dict[str, pd.DataFrame] = {}
        row_counts: dict[str, int] = {}
        for rid in source_ids:
            try:
                payload = await self._output_store.resolve_source(rid)
            except KeyError:
                return f"(error: unknown source_id {rid!r})"
            except (SourceNotApplicable, SourceResolutionError) as e:
                return f"(error: {e})"
            df = payload.df
            if df is None:
                return f"(error: query {rid} returned no data)"
            if df.empty:
                return f"(error: query {rid} result is empty)"
            sources[rid] = df
            row_counts[rid] = len(df)

        try:
            normalize_map_spec(parsed, sources)
        except MapSpecError as e:
            return f"(error: {e})"

        map_artifact = self._output_store.add_map_artifact(
            source_ids,
            parsed.model_dump(exclude_none=True, by_alias=True),
        )
        map_id = map_artifact.id
        label = "Map"
        if source_ids:
            rows_desc = " + ".join(f"{row_counts[rid]:,}" for rid in source_ids)
            return f"{label} {map_id} created from {', '.join(source_ids)} — {rows_desc} rows"
        return f"{label} {map_id} created"

    def as_pydantic_ai_tool(self) -> Tool:
        return Tool(self.__call__, name=self.name)
