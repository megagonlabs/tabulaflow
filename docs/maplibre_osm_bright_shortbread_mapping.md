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
| Country/state boundaries and country labels | `boundaries`, `boundary_labels`, bundled Natural Earth boundary lines | Keep country/state borders legible; use bundled low-zoom fallback geometry where Shortbread has no matching boundary features. |

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
| `landcover-glacier`, `landcover-ice-shelf`, `landcover-wood`, `landcover-grass`, `landcover-grass-park`, `landcover-sand` | `landcover.class`, `landcover.subclass`, `park.class` | `land.kind`, `sites.kind` | approximate | Implemented as separate OSM Bright-named layers, but Shortbread combines these into fewer land/site kinds. |
| `landuse-residential`, `landuse-commercial`, `landuse-industrial`, `landuse-cemetery`, `landuse-hospital`, `landuse-school`, `landuse-railway` | `landuse.class` | `sites.kind`, `land.kind` | approximate | Implemented as separate OSM Bright-named layers, but Shortbread landuse classes are coarser. |
| `water`, `water-offset`, `water-intermittent`, `water-pattern` | `water.class`, `intermittent`, `brunnel`, sprite `wave` | `water_polygons.kind`, OSM Bright sprite endpoint | approximate | `water`, `water-offset`, and `water-pattern` are active; `water-intermittent` is present but dormant because Shortbread does not expose `intermittent`. |
| `waterway_tunnel`, `waterway-other`, `waterway-other-intermittent`, `waterway-stream-canal`, `waterway-stream-canal-intermittent`, `waterway-river`, `waterway-river-intermittent` | `waterway.class`, `intermittent`, `brunnel` | `water_lines.kind`, `tunnel` | approximate | Active layers split river, stream/canal/drain/ditch, other, and tunnel waterways; intermittent layers are present but dormant because Shortbread does not expose an `intermittent` field. |
| `building`, `building-top` | `building` | `buildings` | approximate | Building fill and translated high-zoom tops are ported against Shortbread's single building layer. |
| `tunnel-*` road layers | `transportation.class`, `brunnel`, `ramp`, `subclass` | `streets.kind`, `tunnel`, `link`, `rail` | approximate | Tunnel roads are split by minor, secondary/tertiary, trunk/primary, motorway, link, and rail, but Shortbread has fewer subtype fields. |
| `ferry` | `transportation.class=ferry` | `ferries.kind` | approximate | Ferry geometry and labels are available. |
| `aeroway-*` | `aeroway.class` | `streets.kind`, `street_polygons.kind` | approximate | Runway/taxiway casing, fill, and white interior are ported from Shortbread street geometry. |
| `airport-label-major` | `aerodrome_label.iata`, sprite `airport_11` | bundled Natural Earth IATA-coded airport points | approximate | Natural Earth airport points replace Shortbread's missing aerodrome label layer and use OSM Bright's IATA-code visibility policy and airport sprite. |
| `road_area_pier`, `road_pier` | `transportation.class=pier` | `pier_lines`, `pier_polygons` | approximate | Shortbread pier geometry is styled as land-colored fill/lines. |
| `highway-*` road fill/casing layers | `transportation.class`, `ramp`, `brunnel`, `subclass` | `streets.kind`, `link`, `bridge`, `tunnel` | approximate | Roads are split into tunnel, normal, bridge, and link drawing order with minor, secondary/tertiary, trunk/primary, and motorway tiers. |
| `railway-*`, `railway-*-hatching` | `transportation.class=rail`, `service`, `brunnel` | `streets.rail`, `streets.service`, `streets.kind` | approximate | Normal, service, transit-like, tunnel, and bridge rail layers are split with Shortbread fields. |
| `bridge-*` road layers | `transportation.brunnel=bridge`, `class`, `ramp`, `subclass` | `streets.bridge`, `bridges.kind` | approximate | Bridge polygons and bridge road casings/fills are styled by coarse Shortbread road kind and link fields. |
| `cablecar`, `cablecar-dash` | `transportation.subclass=cable_car` | `aerialways.kind` | approximate | Shortbread aerialways are drawn as muted dashed lines without subtype-specific styling. |
| `boundary-land-level-4`, `boundary-land-level-2`, `boundary-land-disputed`, `boundary-water` | `boundary.admin_level`, `maritime`, `disputed` | `boundaries.admin_level`, `maritime`, `disputed`, bundled Natural Earth boundary lines | approximate | Boundary line widths, colors, joins, and dash patterns follow OSM Bright. Bundled Natural Earth country lines cover zooms below Shortbread `boundaries`; bundled Natural Earth admin-1 lines cover mid-zoom state/province visibility until Shortbread's detailed admin boundaries take over. |
| `waterway-name`, `water-name-lakeline`, `water-name-ocean`, `water-name-other` | `waterway`, `water_name.class` | `water_lines_labels`, `water_polygons_labels`, bundled `ocean-labels.geojson` | approximate | Waterways, large water polygons, other water polygons, and stable local ocean labels are split into OSM Bright-style layers. |
| `road_oneway`, `road_oneway_opposite` | sprite `oneway`, `transportation.oneway` | `streets.oneway`, `oneway_reverse` | approximate | Rendered as text arrows because OSM Bright sprites are not vendored. |
| `poi-level-1`, `poi-level-2`, `poi-level-3`, `poi-railway` | `poi.class`, `subclass`, `rank`, `level`, sprite icons | `pois`, `public_transport` | approximate | Layer names and zoom tiers are ported; class/rank/icon behavior is unavailable because Shortbread TileJSON does not document POI fields. |
| `highway-name-path`, `highway-name-minor`, `highway-name-major` | `transportation_name.class`, `network`, `ref` | `street_labels.kind`, `ref`, `name` | approximate | Street labels are split into major, local, and path layers using Shortbread `kind`. |
| `highway-shield`, `highway-shield-us-interstate`, `highway-shield-us-other` | shield sprites, `network`, `ref`, `ref_length` | `street_labels.kind`, `street_labels.ref` | approximate | Rendered as text-only shields split by road kind; Shortbread does not expose network/ref_length fields. |
| `place-other`, `place-village`, `place-town`, `place-city`, `place-city-capital` | `place.class`, `capital`, `rank`, sprite `star_11` | `place_labels.kind`, `population`, OSM Bright sprite endpoint | approximate | City labels are split by Shortbread population tiers so large and medium cities are bold; town/village labels are capped lower to reduce competition. `place-city-capital` is present and sprite-backed but dormant because Shortbread does not expose `capital`. |
| `place-state` | `place.class=state` | `boundary_labels.admin_level=4`, `way_area` | approximate | State/province labels are area-gated because Shortbread has no place rank. |
| `place-country-other`, `place-country-1`, `place-country-2`, `place-country-3` | `place.class=country`, `rank`, `iso_a2` | `boundary_labels.admin_level`, `way_area` | approximate | Country rank is approximated by `way_area`; `place-country-other` is present but dormant because Shortbread does not expose `iso_a2`. |
| `place-continent` | `place.class=continent` | bundled `continent-labels.geojson` | approximate | Shortbread has no continent layer, so stable local label points provide the OSM Bright low-zoom continent layer. |

## Non-Portable Concepts

OSM Bright's POI and icon layers rely on OpenMapTiles fields such as `class`,
`subclass`, and `rank`. The official Shortbread TileJSON does not document those
fields for `pois`, so direct icon mapping would be brittle. Add icons only after
inspecting real Shortbread POI feature properties and committing a small,
licensed local sprite set.

Shortbread has no documented `aerodrome_label` layer with IATA codes. The
style therefore uses public-domain Natural Earth 1:10m airport points with an
IATA code as a cartographic fallback for `airport-label-major`.

Shortbread's `boundaries` layer starts at source zoom `2`, and sampled
Shortbread tiles generally do not expose `admin_level=4` state/province lines
until around zoom `7`. The style therefore includes public-domain Natural
Earth fallback layers:

- `boundary-land-level-2-fallback`: Natural Earth 1:110m country boundary
  lines below zoom `2`.
- `boundary-land-level-4-fallback`: Natural Earth 1:50m admin-1/state
  boundary lines from zoom `2` until zoom `7`.

These fallbacks are intentionally low/mid-zoom only. Shortbread vector tiles
remain the detailed boundary source at higher zooms.

OSM Bright also has detailed bridge, tunnel, ramp, and per-road-class layers.
Shortbread has fewer fields, but the output pane style now keeps the OSM
Bright layer IDs where `kind`, `link`, `bridge`, `tunnel`, `rail`, or
`service` can support them.

The low-zoom country label port approximates OSM Bright's `place-country-*`
rank tiers with type-tolerant `admin_level` checks and mutually exclusive
`boundary_labels.way_area` buckets:

- `place-country-1`: zoom `0-8`, `way_area >= 8e12`
- `place-country-2`: zoom `2-8`, `1e12 <= way_area < 8e12`
- `place-country-3`: zoom `3-8`, `way_area < 1e12`

This intentionally restores visible labels at the broadest zooms, but it is not
an exact country-rank match because Shortbread has no country rank field.
`place-country-other` is included as a dormant, field-gated layer because
Shortbread boundary labels do not expose OSM Bright's `iso_a2`/missing-ISO
split.

All OSM Bright layer IDs are represented. Layers that depend on unavailable
Shortbread fields are intentionally dormant rather than approximated with
incorrect duplicate labels or false intermittent styling.

Common OSM Bright layer IDs are ordered to match upstream OSM Bright draw order.
Shortbread-only helper layers are anchored next to the closest equivalent
concept: `ocean` after the background, dam geometry before waterways, bridge
polygons before bridge road strokes, and local motorway/ferry labels before
place labels.

## Licensing

The style in this repository is not vendored from OSM Bright. It is a
schema-native Shortbread style that references OSM Bright's visual hierarchy
and its public sprite endpoint for the `wave` pattern and `star_11` icon.
Because the design is intentionally OSM Bright-inspired and uses its sprites,
the map attribution links to OSM Bright in addition to the required
OpenStreetMap attribution.
