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

## Non-Portable Concepts

OSM Bright's POI and icon layers rely on OpenMapTiles fields such as `class`,
`subclass`, and `rank`. The official Shortbread TileJSON does not document those
fields for `pois`, so direct icon mapping would be brittle. Add icons only after
inspecting real Shortbread POI feature properties and committing a small,
licensed local sprite set.

OSM Bright also has detailed bridge, tunnel, ramp, and per-road-class layers.
Shortbread has fewer fields, so the output pane style uses a smaller hierarchy:
rail, minor, secondary/tertiary, primary/trunk, and motorway.

## Licensing

The style in this repository is not vendored from OSM Bright. It is a
schema-native Shortbread style that references OSM Bright's visual hierarchy.
Because the design is intentionally OSM Bright-inspired, the map attribution
links to OSM Bright in addition to the required OpenStreetMap attribution.
