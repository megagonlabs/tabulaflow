# NYC Taxi Zones Sample Source

`nyc_taxi_zones.json` is a raw JSON export of the NYC Taxi Zones dataset from
NYC Open Data.

- Source: NYC Open Data, "NYC Taxi Zones"
- Dataset identifier: `8meu-9t5y`
- Export URL: `https://data.cityofnewyork.us/resource/8meu-9t5y.json?$limit=5000`
- Downloaded: 2026-06-30
- SHA-256: `2b51bd2e40f6a1f74d0986abd39b5286451874277b1ebad9e2ec38d8043bb450`

The bundled SQLite database stores these source fields in the `nyc_taxi_zones`
table:

- `the_geom`
- `shape_leng`
- `shape_area`
- `zone`
- `locationid`
- `borough`

This third-party data is bundled for sample/demo use and is not licensed under
TabulaFlow's BSD-3-Clause code license. It remains subject to NYC Open Data
terms and source-provider disclaimers.
