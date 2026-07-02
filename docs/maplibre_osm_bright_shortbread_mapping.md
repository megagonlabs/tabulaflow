# OSM Bright to Shortbread Style Mapping

The output pane uses MapLibre with the official no-key OSM Shortbread vector
tiles at `https://vector.openstreetmap.org/shortbread_v1/tilejson.json`.
OSM Bright GL targets the OpenMapTiles schema, so it cannot be applied directly
to this tile source. The map style should port OSM Bright's visual priorities
onto Shortbread's available layers instead of copying OpenMapTiles layer rules.

## Portable Concepts

| OSM Bright concept | Shortbread layer | Implementation note |
| --- | --- | --- |
| Soft warm land background | `background`, `land`, `sites` | Use close but not identical fill colors so user overlays stay dominant. |
| Blue water with italic labels | `ocean`, `water_polygons`, `water_lines`, `water_*_labels` | Keep water labels sparse and area-gated. |
| Major-road casing and warm fill | `streets` | Split motorway/trunk/primary from secondary/tertiary, with subdued casing. |
| White local street grid | `streets`, `street_polygons` | Keep local roads visible at city zooms but below overlays. |
| City/town/neighborhood label hierarchy | `place_labels` | Use `kind` and `population`; large cities are bold. |
| Sparse high-zoom transit labels | `public_transport`, `ferries` | Shortbread exposes `kind` and names for these layers. |
| Sparse high-zoom POI text | `pois` | TileJSON does not document POI fields, so avoid icon/category rules for now. |
| Country/state boundaries and country labels | `boundaries`, `boundary_labels` | Keep low-contrast so they do not fight local analysis maps. |

## Port Status Matrix

Status meanings:

- `exact`: Shortbread exposes a compatible layer and fields.
- `approximate`: Shortbread exposes enough geometry/properties to mimic the
  visual policy, but not the exact OpenMapTiles filters.
- `unsupported`: Shortbread does not expose the required layer, fields, or
  sprite inputs.

| OSM Bright layers | OpenMapTiles dependency | Shortbread target | Status | Notes |
| --- | --- | --- | --- | --- |
| `background` | none | `background` | exact | Color can be copied directly. |
| `landcover-glacier`, `landcover-ice-shelf`, `landcover-wood`, `landcover-grass`, `landcover-grass-park`, `landcover-sand` | `landcover.class`, `landcover.subclass`, `park.class` | `land.kind`, `sites.kind` | approximate | Shortbread combines these into fewer land/site kinds. |
| `landuse-residential`, `landuse-commercial`, `landuse-industrial`, `landuse-cemetery`, `landuse-hospital`, `landuse-school`, `landuse-railway` | `landuse.class` | `sites.kind`, `land.kind` | approximate | Residential/commercial/industrial classes are not exposed separately. |
| `water`, `water-offset`, `water-intermittent`, `water-pattern` | `water.class`, `intermittent`, `brunnel` | `water_polygons.kind` | approximate | Intermittent/pattern styling is unsupported. |
| `waterway_tunnel`, `waterway-other`, `waterway-other-intermittent`, `waterway-stream-canal`, `waterway-stream-canal-intermittent`, `waterway-river`, `waterway-river-intermittent` | `waterway.class`, `intermittent`, `brunnel` | `water_lines.kind`, `bridge`, `tunnel` | approximate | Shortbread has water-line kind/bridge/tunnel but not the same class split. |
| `building`, `building-top` | `building` | `buildings` | approximate | Building fill and translated high-zoom tops are ported against Shortbread's single building layer. |
| `tunnel-*` road layers | `transportation.class`, `brunnel`, `ramp`, `subclass` | `streets.kind`, `tunnel`, `link`, `rail` | approximate | Tunnel roads are split by minor, secondary/tertiary, trunk/primary, motorway, link, and rail, but Shortbread has fewer subtype fields. |
| `ferry` | `transportation.class=ferry` | `ferries.kind` | approximate | Ferry geometry and labels are available. |
| `aeroway-*` | `aeroway.class` | `streets.kind`, `street_polygons.kind` | approximate | Runway/taxiway casing, fill, and white interior are ported from Shortbread street geometry. |
| `airport-label-major` | `aerodrome_label.iata`, sprite `airport_11` | bundled `airport-labels.geojson` | approximate | A small local major-airport label layer is used because Shortbread has no documented aerodrome label layer or IATA field. |
| `road_area_pier`, `road_pier` | `transportation.class=pier` | `pier_lines`, `pier_polygons` | approximate | Shortbread pier geometry is styled as land-colored fill/lines. |
| `highway-*` road fill/casing layers | `transportation.class`, `ramp`, `brunnel`, `subclass` | `streets.kind`, `link`, `bridge`, `tunnel` | approximate | Roads are split into tunnel, normal, bridge, and link drawing order with minor, secondary/tertiary, trunk/primary, and motorway tiers. |
| `railway-*`, `railway-*-hatching` | `transportation.class=rail`, `service`, `brunnel` | `streets.rail`, `bridges`, `street_labels` | approximate | Rail and hatching are drawn for normal and bridge rail; Shortbread does not expose OpenMapTiles service/transit classes. |
| `bridge-*` road layers | `transportation.brunnel=bridge`, `class`, `ramp`, `subclass` | `streets.bridge`, `bridges.kind` | approximate | Bridge polygons and bridge road casings/fills are styled by coarse Shortbread road kind and link fields. |
| `cablecar`, `cablecar-dash` | `transportation.subclass=cable_car` | `aerialways.kind` | approximate | Shortbread aerialways are drawn as muted dashed lines without subtype-specific styling. |
| `boundary-land-level-4`, `boundary-land-level-2`, `boundary-land-disputed`, `boundary-water` | `boundary.admin_level`, `maritime`, `disputed` | `boundaries.admin_level`, `maritime`, `disputed` | exact | Fields are compatible enough for a close port. |
| `waterway-name`, `water-name-lakeline`, `water-name-ocean`, `water-name-other` | `waterway`, `water_name.class` | `water_lines_labels`, `water_polygons_labels`, bundled `ocean-labels.geojson` | approximate | Waterways, large water polygons, other water polygons, and stable local ocean labels are split into OSM Bright-style layers. |
| `road_oneway`, `road_oneway_opposite` | sprite `oneway`, `transportation.oneway` | `streets.oneway`, `oneway_reverse` | approximate | Rendered as text arrows because OSM Bright sprites are not vendored. |
| `poi-level-1`, `poi-level-2`, `poi-level-3`, `poi-railway` | `poi.class`, `subclass`, `rank`, `level`, sprite icons | `pois`, `public_transport` | approximate | Layer names and zoom tiers are ported; class/rank/icon behavior is unavailable because Shortbread TileJSON does not document POI fields. |
| `highway-name-path`, `highway-name-minor`, `highway-name-major` | `transportation_name.class`, `network`, `ref` | `street_labels.kind`, `ref`, `name` | approximate | Street labels are split into major, local, and path layers using Shortbread `kind`. |
| `highway-shield`, `highway-shield-us-interstate`, `highway-shield-us-other` | shield sprites, `network`, `ref`, `ref_length` | `street_labels.kind`, `street_labels.ref` | approximate | Rendered as text-only shields split by road kind; Shortbread does not expose network/ref_length fields. |
| `place-other`, `place-village`, `place-town`, `place-city`, `place-city-capital` | `place.class`, `capital`, `rank` | `place_labels.kind`, `population` | approximate | City/town/village/other layers use OSM Bright names and Shortbread `kind`; capital/rank-specific styling is unavailable. |
| `place-state` | `place.class=state` | `boundary_labels.admin_level=4`, `way_area` | approximate | State/province labels are area-gated because Shortbread has no place rank. |
| `place-country-other`, `place-country-1`, `place-country-2`, `place-country-3` | `place.class=country`, `rank`, `iso_a2` | `boundary_labels.admin_level`, `way_area` | approximate | Country rank is approximated by `way_area`. |
| `place-continent` | `place.class=continent` | bundled `continent-labels.geojson` | approximate | Shortbread has no continent layer, so stable local label points provide the OSM Bright low-zoom continent layer. |

## Non-Portable Concepts

OSM Bright's POI and icon layers rely on OpenMapTiles fields such as `class`,
`subclass`, and `rank`. The official Shortbread TileJSON does not document those
fields for `pois`, so direct icon mapping would be brittle. Add icons only after
inspecting real Shortbread POI feature properties and committing a small,
licensed local sprite set.

OSM Bright also has detailed bridge, tunnel, ramp, and per-road-class layers.
Shortbread has fewer fields, so the output pane style uses a smaller hierarchy:
rail, minor, secondary/tertiary, primary/trunk, and motorway.

The low-zoom country label port approximates OSM Bright's `place-country-*`
rank tiers with mutually exclusive `boundary_labels.way_area` buckets:

- `country-labels-global`: zoom `0-8`, `way_area >= 8e12`
- `country-labels-regional`: zoom `2-8`, `1e12 <= way_area < 8e12`
- `country-labels-local`: zoom `3-8`, `way_area < 1e12`

This intentionally restores visible labels at the broadest zooms, but it is not
an exact country-rank match because Shortbread has no country rank field.

## Licensing

The style in this repository is not vendored from OSM Bright. It is a
schema-native Shortbread style that references OSM Bright's visual hierarchy.
Because the design is intentionally OSM Bright-inspired, the map attribution
links to OSM Bright in addition to the required OpenStreetMap attribution.
