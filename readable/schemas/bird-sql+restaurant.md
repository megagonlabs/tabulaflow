```sql
-- Database: restaurant

/*
Schema: NULL
Table: generalinfo
Rows: 9590
Sample rows:
| id_restaurant   | label                | food_type     | city          | review   |
|-----------------|----------------------|---------------|---------------|----------|
| 1               | sparky's diner       | 24 hour diner | san francisco | 2.3      |
| 2               | kabul afghan cuisine | afghani       | san carlos    | 3.8      |
| 3               | helmand restaurant   | afghani       | san francisco | 4.0      |
| 4               | afghani house        | afghani       | sunnyvale     | 3.6      |
| 5               | kabul afghan cusine  | afghani       | sunnyvale     | 3.7      |
| ...             | ...                  | ...           | ...           | ...      |
*/
CREATE TABLE generalinfo (
    "id_restaurant" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "label" TEXT NOT NULL,
        -- <example>'sparky's diner'</example>
    "food_type" TEXT NOT NULL,
        -- <example>'24 hour diner'</example>
    "city" TEXT NOT NULL,
        -- <example>'san francisco'</example>
        -- <fk> -> geographic."city"</fk>
    "review" REAL NOT NULL,
        -- <example>2.300</example>
    FOREIGN KEY ("city") REFERENCES geographic("city")
);

/*
Schema: NULL
Table: geographic
Rows: 168
Sample rows:
| city            | county              | region   |
|-----------------|---------------------|----------|
| alameda         | alameda county      | bay area |
| alamo           | contra costa county | bay area |
| albany          | alameda county      | bay area |
| alviso          | santa clara county  | bay area |
| american canyon | unknown             | bay area |
| ...             | ...                 | ...      |
*/
CREATE TABLE geographic (
    "city" TEXT NOT NULL PRIMARY KEY,
        -- <example>'alameda'</example>
    "county" TEXT NOT NULL,
        -- <example>'alameda county'</example>
    "region" TEXT NOT NULL
        -- <values>{'bay area', 'lake tahoe', 'los angeles area', 'monterey', 'napa valley', 'northern california', 'sacramento area', 'unknown', 'yosemite and mono lake area'}</values>
);

/*
Schema: NULL
Table: location
Rows: 9539
Sample rows:
| id_restaurant   | street_num   | street_name       | city          |
|-----------------|--------------|-------------------|---------------|
| 1               | 242.0        | church st         | san francisco |
| 2               | 135.0        | el camino real    | san carlos    |
| 3               | 430.0        | broadway          | san francisco |
| 4               | 1103.0       | e. el camino real | sunnyvale     |
| 5               | 833.0        | w. el camino real | sunnyvale     |
| ...             | ...          | ...               | ...           |
*/
CREATE TABLE location (
    "id_restaurant" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> generalinfo."id_restaurant"</fk>
    "street_num" INTEGER NULL,
        -- <example>242</example>
    "street_name" TEXT NULL,
        -- <example>'church st'</example>
    "city" TEXT NULL,
        -- <example>'san francisco'</example>
        -- <fk> -> geographic."city"</fk>
    FOREIGN KEY ("city") REFERENCES geographic("city"),
    FOREIGN KEY ("id_restaurant") REFERENCES generalinfo("id_restaurant")
);
```