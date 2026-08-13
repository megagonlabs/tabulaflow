# Repro notes for I-5 + Superfund sites render_map bug

This document captures the last `render_map` call made in the session, plus the underlying data sources used to build the rendered result.

## Last `render_map` call

```json
{
  "source_id": "Q5",
  "map_spec": "{\"title\":\"California Superfund sites near I-5\",\"view\":{\"fit\":false,\"center\":[36.3,-119.7],\"zoom\":5.3,\"maxZoom\":12},\"layers\":[{\"type\":\"geojson\",\"geojson\":\"route_geojson\"},{\"type\":\"points\",\"lat\":\"lat\",\"lng\":\"lng\",\"label\":\"primary_name\",\"tooltip\":[\"primary_name\",\"city_name\",\"county_name\",\"active_status\",\"distance_to_i5_mi\"],\"color\":{\"field\":\"active_status\",\"domain\":[\"CURRENTLY ON THE FINAL NPL\",\"PROPOSED FOR NPL\",\"SITE IS PART OF NPL SITE\",\"NOT ON THE NPL\",\"REMOVED FROM PROPOSED NPL\",\"DELETED FROM THE FINAL NPL\"]},\"marker\":{\"type\":\"circle\"}}]}"
}
```

## Query used to create `Q5`

```sql
WITH sites AS (
  SELECT
    primary_name,
    location_address,
    city_name,
    county_name,
    state_code,
    postal_code,
    lat,
    lng,
    active_status,
    interest_type,
    distance_to_i5_mi,
    fac_url,
    route_geojson,
    row_number() OVER (ORDER BY distance_to_i5_mi, primary_name, city_name) AS rn
  FROM read_json_auto('/Users/yanlinf/.tabulaflow/sessions/20260701T054951Z-98306-fe26ab/scratch/ca_superfund_sites_near_i5.json')
)
SELECT
  primary_name,
  location_address,
  city_name,
  county_name,
  state_code,
  postal_code,
  lat,
  lng,
  active_status,
  interest_type,
  distance_to_i5_mi,
  fac_url,
  CASE WHEN rn = 1 THEN route_geojson ELSE NULL END AS route_geojson
FROM sites
ORDER BY distance_to_i5_mi, primary_name, city_name;
```

Notes:
- `Q5` contains 488 rows.
- Only the first row has a non-null `route_geojson` value.
- All rows have point coordinates in `lat` / `lng`.

## Original data sources

### 1) EPA Superfund site points
Public ArcGIS REST layer used to fetch the California Superfund site records:

- Service: `https://gispub.epa.gov/arcgis/rest/services/OEI/FRS_INTERESTS/MapServer/21`
- Query endpoint: `https://gispub.epa.gov/arcgis/rest/services/OEI/FRS_INTERESTS/MapServer/21/query`
- Layer name observed from metadata: `SEMS`
- Geometry type: point

Fields used from that source:
- `PRIMARY_NAME`
- `LOCATION_ADDRESS`
- `CITY_NAME`
- `COUNTY_NAME`
- `STATE_CODE`
- `POSTAL_CODE`
- `LATITUDE83`
- `LONGITUDE83`
- `ACTIVE_STATUS`
- `FAC_URL`
- `PGM_SYS_ID`
- `INTEREST_TYPE`
- `EPA_REGION_CODE`

California subset scratch file produced from the EPA layer:

- `/Users/yanlinf/.tabulaflow/sessions/20260701T054951Z-98306-fe26ab/scratch/ca_superfund_sites.csv`

### 2) I-5 route geometry
Approximate California I-5 corridor was generated via OSRM using ordered waypoints through California cities.

Routing service used:
- `https://router.project-osrm.org/route/v1/driving/...`

Waypoints used:
- Redding area: `(-122.5544, 41.9115)`
- Red Bluff area: `(-122.3917, 40.5865)`
- Sacramento: `(-121.4944, 38.5816)`
- Central Valley waypoint: `(-121.1311, 36.2063)`
- Fresno area: `(-119.6941, 36.3302)`
- Grapevine area: `(-118.7831, 34.9860)`
- Los Angeles: `(-118.2437, 34.0522)`
- San Diego: `(-117.1611, 32.7157)`

The returned route geometry was then downsampled and embedded as GeoJSON in the derived dataset.

### 3) Derived dataset used by `Q5`
The points near the I-5 corridor were computed in Python from the two sources above and saved to:

- `/Users/yanlinf/.tabulaflow/sessions/20260701T054951Z-98306-fe26ab/scratch/ca_superfund_sites_near_i5.json`

Logic used:
- Start with California rows from the EPA source.
- Compute approximate distance from each site point to the routed I-5 polyline.
- Keep rows within 10 miles of the route.
- Add `distance_to_i5_mi`.
- Store the same `route_geojson` payload on every row; `Q5` keeps it only on row 1.

## Symptom being investigated

Earlier, a `render_map` call using both the route layer and the points layer with auto-fit did not visibly show expected content. A later render using only points and a fixed California viewport appeared correctly. The final call above reintroduced both layers while keeping the fixed viewport.
