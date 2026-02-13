```sql
-- Database: craftbeer

/*
Schema: NULLTable: beers
Rows: 2410
Sample rows:
| id   | brewery_id   | abv   | ibu   | name                     | style                          | ounces   |
|------|--------------|-------|-------|--------------------------|--------------------------------|----------|
| 1    | 166          | 0.065 | 65.0  | Dale's Pale Ale          | American Pale Ale (APA)        | 12.0     |
| 4    | 166          | 0.087 | 85.0  | Gordon Ale (2009)        | American Double / Imperial IPA | 12.0     |
| 5    | 166          | 0.08  | 35.0  | Old Chub                 | Scottish Ale                   | 12.0     |
| 6    | 166          | 0.099 | 100.0 | GUBNA Imperial IPA       | American Double / Imperial IPA | 12.0     |
| 7    | 166          | 0.053 | 35.0  | Mama's Little Yella Pils | Czech Pilsener                 | 12.0     |
| ...  | ...          | ...   | ...   | ...                      | ...                            | ...      |
*/
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

/*
Schema: NULLTable: breweries
Rows: 558
Sample rows:
| id   | name                      | city          | state   |
|------|---------------------------|---------------|---------|
| 0    | NorthGate Brewing         | Minneapolis   | MN      |
| 1    | Against the Grain Brewery | Louisville    | KY      |
| 2    | Jack's Abby Craft Lagers  | Framingham    | MA      |
| 3    | Mike Hess Brewing Company | San Diego     | CA      |
| 4    | Fort Point Beer Company   | San Francisco | CA      |
| ...  | ...                       | ...           | ...     |
*/
CREATE TABLE breweries (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    name TEXT NOT NULL,
        -- <example>'NorthGate Brewing '</example>
    city TEXT NOT NULL,
        -- <example>'Minneapolis'</example>
    state TEXT NOT NULL
        -- <example>'MN'</example>
);
```