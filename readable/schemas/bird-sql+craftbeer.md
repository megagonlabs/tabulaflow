```sql
-- Database: craftbeer

-- Table: beers (2410 rows)
CREATE TABLE beers (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>2687</example>
    brewery_id INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> breweries.id</fk>
    abv REAL NULL,
        -- <example>0.065</example>
    ibu REAL NULL,
        -- <example>65.000</example>
    name TEXT NOT NULL,
        -- <example>'Dale's Pale Ale'</example>
    style TEXT NULL,
        -- <example>'American Pale Ale (APA)'</example>
    ounces REAL NOT NULL,
        -- <example>12.000</example>
    FOREIGN KEY (brewery_id) REFERENCES breweries(id)
);

-- Table: breweries (558 rows)
CREATE TABLE breweries (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    name TEXT NULL,
        -- <example>'NorthGate Brewing '</example>
    city TEXT NULL,
        -- <example>'Minneapolis'</example>
    state TEXT NULL
        -- <example>'MN'</example>
);
```