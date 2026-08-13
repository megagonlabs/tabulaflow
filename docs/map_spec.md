# Agent-Facing Map Spec

Declarative map interface for agents. The goal is to let an agent attach a map
view to a source without exposing Leaflet internals or requiring browser
rendering knowledge.

The map spec is intentionally much smaller than Vega-Lite. Vega-Lite is a full
visual grammar; maps need a stable semantic contract over spatial sources:
points from latitude/longitude columns, GeoJSON geometry, semantic encodings,
tooltips, and viewport behavior. Concrete presentation such as exact colors,
opacity, stroke width, and point radius ranges belongs to the output pane
renderer, not the agent-facing spec.

## 1. Tool Contract

```python
render_map(
    map_spec: dict,
) -> str
```

- The map is a standalone artifact, not attached to a source. Each
  column/geojson layer names the source it reads from via its own
  `source_id`; inline `points` layers omit it. Layers with different `source_id`
  values overlay data from multiple sources on one map.
- `map_spec` references each source's query-result columns by their original names.
- The tool returns a `MAP<n>` id; cite that id (e.g. `MAP1`) to
  show the map. It renders as its own map-only card (no data/query tabs) — the
  source tables are cited separately when the user wants them.
- The app validates the spec, rewrites each layer's column names to its source's
  pane field ids, bundles the per-source datasets, and the output pane renders it.

The tool should accept a declarative TabulaFlow map spec, not raw Leaflet
options. Leaflet is the current renderer, but the agent-facing contract should
remain semantic enough to survive a future renderer change.

## 2. Top-Level Spec

```json
{
  "title": "Store locations by revenue",
  "view": {
    "fit": true,
    "center": [37.7749, -122.4194],
    "zoom": 10
  },
  "layers": []
}
```

Fields:

| Field | Required | Description |
|---|---:|---|
| `title` | no | Human-readable map label. |
| `view` | no | Initial viewport behavior. Defaults to fit all valid layers. |
| `layers` | yes | Non-empty list of map layers. |

Coordinate convention:

- `view.center` uses `[lat, lng]`, matching Leaflet's user-facing API.
- GeoJSON coordinates use standard GeoJSON order: `[lng, lat]`.

## 3. Basemap

V1 uses the bundled OpenStreetMap tile configuration. `basemap`, `tileUrl`,
`attribution`, and basemap-level `maxZoom` are not part of the public map spec.

Custom basemaps are deferred because they create attribution, licensing,
privacy, API-key, and availability concerns. Add them only when there is a
specific user-facing need.

## 4. View

```json
{
  "view": {
    "fit": true,
    "center": [37.7749, -122.4194],
    "zoom": 10,
    "maxZoom": 14
  }
}
```

Supported fields:

| Field | Required | Description |
|---|---:|---|
| `fit` | no | If true, fit the viewport to all valid rendered features. Default true. |
| `center` | no | Initial center as `[lat, lng]`. Used when `fit` is false or no bounds exist. |
| `zoom` | no | Initial zoom. |
| `maxZoom` | no | Maximum zoom used by fit behavior. |

If `fit` is true and valid geometry exists, `center` and `zoom` are fallback
values only.

## 5. Layer Types

### 5.1 Points Layer

Use for point markers. A points layer has either column mode or inline mode.
Column mode uses ordinary SQL results with separate latitude and longitude
columns:

```json
{
  "type": "points",
  "lat": "latitude",
  "lng": "longitude",
  "label": "city",
  "tooltip": ["city", "state", "revenue"],
  "marker": {
    "type": "pin"
  }
}
```

Fields:

| Field | Required | Description |
|---|---:|---|
| `type` | yes | Must be `"points"`. |
| `source_id` | yes in column mode | Source id (e.g. `"S3"`). Omit for inline mode. |
| `lat` | yes in column mode | Latitude column. Values must be numeric and in `[-90, 90]`. |
| `lng` | yes in column mode | Longitude column. Values must be numeric and in `[-180, 180]`. |
| `points` | yes in inline mode | Non-empty list of inline point objects with numeric `lat` and `lng`. |
| `label` | no | Short identity field/property used for marker titles and default feature names. |
| `tooltip` | no | Detail content shown on hover and click in V1. Field/property, list of fields/properties, or `true` for all safe scalar fields. |
| `marker` | no | Point mark type. Defaults to `{"type": "pin"}`. |
| `color` | no | Semantic categorical color encoding. |
| `size` | no | Semantic numeric size encoding. |

Inline mode is useful for adding a small number of agent-specified markers,
such as a destination pin on top of a route geometry:

```json
{
  "type": "points",
  "points": [
    {
      "lat": 37.7749,
      "lng": -122.4194,
      "label": "Destination",
      "address": "San Francisco"
    }
  ],
  "label": "label",
  "tooltip": ["label", "address"]
}
```

Inline point objects must contain `lat` and `lng`. Other inline point
properties must be strings, numbers, booleans, or null. In inline mode,
`label`, `tooltip`, `color.field`, and `size.field` reference inline point
property names, not query-result columns.

`lat`/`lng` column mode and `points` inline mode are mutually exclusive.

Marker types:

```json
{"marker": {"type": "pin"}}
```

```json
{"marker": {"type": "circle"}}
```

`pin` is the default for small and moderate point sets. `circle` is better when
the map uses color or size encodings.

### 5.2 GeoJSON Layer

Use for browser-ready geometry: points, lines, polygons, multipolygons, and
feature collections.

```json
{
  "type": "geojson",
  "geojson": "boundary_geojson",
  "label": "region_name",
  "tooltip": ["region_name", "population"],
  "color": {"field": "region_type"}
}
```

Fields:

| Field | Required | Description |
|---|---:|---|
| `type` | yes | Must be `"geojson"`. |
| `source_id` | yes for a column source | Source id (e.g. `"S3"`). Required when `geojson` is a column; also required for an inline object that uses `label`/`tooltip`/`color`. |
| `geojson` | yes | Column name containing GeoJSON, or an inline GeoJSON object. |
| `label` | no | Short identity column/property used for feature names. |
| `tooltip` | no | Detail content shown on hover and click in V1. Column/property, list of columns/properties, or `true`. |
| `color` | no | Semantic categorical color encoding. |

The `geojson` value can be:

- a column containing GeoJSON strings
- a column containing JSON-like objects
- an inline GeoJSON `Geometry`
- an inline GeoJSON `Feature`
- an inline GeoJSON `FeatureCollection`

When row-level GeoJSON is supplied, the renderer should merge normal row fields
into each feature's `properties` so tooltip, label, and color encodings can
reference ordinary query-result columns.

### 5.3 Future Geometry Layer

Database-native geometry formats are intentionally not first-class in V1.
Instead, agents should convert geometry to GeoJSON in SQL and use a `geojson`
layer.

Examples:

```sql
-- PostGIS
SELECT ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geom_geojson
FROM regions;
```

```sql
-- Snowflake
SELECT ST_ASGEOJSON(geom) AS geom_geojson
FROM regions;
```

```sql
-- BigQuery
SELECT ST_ASGEOJSON(geog) AS geom_geojson
FROM regions;
```

```sql
-- DuckDB spatial
SELECT ST_AsGeoJSON(geom) AS geom_geojson
FROM regions;
```

A later `geometry` layer may support:

```json
{
  "type": "geometry",
  "geometry": "geom",
  "format": "wkt"
}
```

Do not implement this until WKT/WKB parsing is needed in practice.

## 6. Semantic Encodings

The public spec exposes data semantics, not concrete styling. The agent can say
which field should control color or size; the output pane chooses the actual
palette, opacity, stroke width, and radius range.

### Categorical Color

```json
"color": {
  "field": "status"
}
```

The renderer chooses a stable palette.
When a categorical color field has a compact set of values, the output pane
automatically shows a top-right legend. Agents do not need to request or
configure legends.

### Ordered Categorical Color

```json
"color": {
  "field": "risk",
  "domain": ["low", "medium", "high"]
}
```

`domain` is useful when category order matters or when stable color assignment
across related maps is important. The renderer still chooses the palette.

### Numeric Point Size

```json
"size": {
  "field": "revenue"
}
```

`size` is only supported on `points` layers. The renderer chooses the radius
range.

Supported encoding fields:

| Encoding | Field | Description |
|---|---|---|
| `color` | `field` | Column/property used for categorical color. |
| `color` | `domain` | Optional category order. |
| `size` | `field` | Numeric column used for point size. |

Unsupported presentation fields include fixed hex colors, explicit color
palettes/ranges, fixed numeric sizes, vector `style`, fill opacity, stroke
opacity, stroke width, fill/stroke colors, and custom legends.

## 7. Label and Tooltip Semantics

`label` is a short identity field. It should usually be one column/property and
should answer "what is this feature?".

Use `label` for:

- marker titles
- accessibility names
- default feature names
- future always-visible text labels, if added later

`tooltip` is the feature detail content. In V1, the same `tooltip` content is
used for both hover and click interactions. Do not add a separate `popup` field
until the UI needs different hover content and click-detail content.

Tooltip forms:

```json
"tooltip": "name"
```

```json
"tooltip": ["name", "status", "value"]
```

```json
"tooltip": true
```

Rules:

- A string displays one field.
- A list displays a compact key-value table in the listed order.
- `true` displays all safe scalar fields, capped to a small count.
- If `tooltip` is absent, `label` is used as the fallback detail text when
  present.

Label and tooltip text must be HTML-escaped by the renderer.

## 8. Coordinate and CRS Requirements

GeoJSON layers must be WGS84 longitude/latitude GeoJSON.

- GeoJSON coordinates are `[lng, lat]`.
- Latitude must be in `[-90, 90]`.
- Longitude must be in `[-180, 180]`.
- If source geometry uses another CRS, the query should transform it before
  calling `render_map`.

The output pane should not reproject geometry in JavaScript. Reprojection
belongs in SQL or in an explicit preprocessing layer, because the database
usually knows the source CRS and has mature spatial functions.

## 9. Validation Rules

The tool should fail fast when:

- no source exists
- `layers` is missing or empty
- a layer has an unsupported `type`
- a referenced column does not exist
- point coordinates are not numeric
- all point rows are invalid or outside valid ranges
- GeoJSON is invalid JSON
- GeoJSON has an unsupported geometry type
- GeoJSON coordinates are obviously not WGS84 lon/lat

The tool may skip individual invalid rows when at least one valid feature
remains. The payload should include skipped-row metadata so the pane can show a
small non-blocking warning later.

Suggested metadata:

```json
{
  "skippedRows": 3,
  "skipReasons": {
    "invalid_coordinate": 2,
    "invalid_geojson": 1
  }
}
```

## 10. V1 Implementation Scope

Implement the smallest useful contract first:

```json
{
  "layers": [
    {
      "type": "points",
      "source_id": "S1",
      "lat": "lat",
      "lng": "lng",
      "label": "name",
      "tooltip": ["name", "status"]
    }
  ]
}
```

```json
{
  "layers": [
    {
      "type": "geojson",
      "source_id": "S1",
      "geojson": "geom_geojson",
      "tooltip": ["name", "value"]
    }
  ]
}
```

V1 should support:

- one or more layers
- points from `lat`/`lng` columns or inline point objects
- GeoJSON from a column or inline object
- pin and circle point marks
- renderer-owned styling for markers and GeoJSON
- semantic color and point-size encodings
- labels and key-value tooltips
- fit-to-data viewport
- fixed OpenStreetMap basemap

Defer:

- clustering
- heatmaps
- time sliders
- table-map linked selection
- WKT/WKB parsing
- custom CRS/reprojection
- manual or complex legends
- map exports beyond the existing pane/export path

## 11. Examples

### Store Locations

```json
{
  "title": "Store locations",
  "layers": [
    {
      "type": "points",
      "source_id": "S1",
      "lat": "latitude",
      "lng": "longitude",
      "label": "store_name",
      "tooltip": ["store_name", "city", "revenue"]
    }
  ]
}
```

### Regions From GeoJSON

```json
{
  "title": "Revenue by region",
  "layers": [
    {
      "type": "geojson",
      "source_id": "S1",
      "geojson": "region_geojson",
      "label": "region",
      "tooltip": ["region", "revenue"],
      "color": {
        "field": "tier",
        "domain": ["low", "medium", "high"]
      }
    }
  ]
}
```

### Boundaries Plus Points (multiple sources)

Overlay boundaries from one query (`S1`) and facility points from another (`S2`)
— the layers come from different results and are joined only on the map.

```json
{
  "title": "Facilities by service area",
  "layers": [
    {
      "type": "geojson",
      "source_id": "S1",
      "geojson": "service_area_geojson",
      "label": "service_area"
    },
    {
      "type": "points",
      "source_id": "S2",
      "lat": "facility_lat",
      "lng": "facility_lng",
      "label": "facility_name",
      "tooltip": ["facility_name", "status"]
    }
  ]
}
```

## 12. Agent Guidance

Agents should:

- Use `points` when the result has latitude and longitude columns.
- Use inline `points` for a small number of explicit markers, such as an origin
  or destination pin over a route.
- Use `geojson` when the result already contains map geometry.
- Convert database geometry to WGS84 GeoJSON in SQL before calling
  `render_map`.
- Prefer simple map specs with labels and tooltips; add color or size encodings
  only when they clarify the spatial result.
- Use `render_chart` for ordinary statistical charts; use `render_map` only when
  spatial position or geometry is essential to the answer.
