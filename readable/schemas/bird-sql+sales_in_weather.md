```sql
-- Database: sales_in_weather

/*
Schema: NULL
Table: relation
Rows: 45
Sample rows:
| store_nbr   | station_nbr   |
|-------------|---------------|
| 1           | 1             |
| 2           | 14            |
| 3           | 7             |
| 4           | 9             |
| 5           | 12            |
| ...         | ...           |
*/
CREATE TABLE relation (
    "store_nbr" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> sales_in_weather."store_nbr"</fk>
    "station_nbr" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> weather."station_nbr"</fk>
    FOREIGN KEY ("store_nbr") REFERENCES sales_in_weather("store_nbr"),
    FOREIGN KEY ("station_nbr") REFERENCES weather("station_nbr")
);

/*
Schema: NULL
Table: sales_in_weather
Rows: 4617600
Sample rows:
| date       | store_nbr   | item_nbr   | units   |
|------------|-------------|------------|---------|
| 2012-01-01 | 1           | 1          | 0       |
| 2012-01-01 | 1           | 2          | 0       |
| 2012-01-01 | 1           | 3          | 0       |
| 2012-01-01 | 1           | 4          | 0       |
| 2012-01-01 | 1           | 5          | 0       |
| ...        | ...         | ...        | ...     |
*/
CREATE TABLE sales_in_weather (
    "date" DATE NOT NULL,
        -- <example>'2012-01-01'</example>
    "store_nbr" INTEGER NOT NULL,
        -- <example>1</example>
    "item_nbr" INTEGER NOT NULL,
        -- <example>1</example>
    "units" INTEGER NOT NULL,
        -- <example>0</example>
    PRIMARY KEY ("date", "store_nbr", "item_nbr")
);

/*
Schema: NULL
Table: weather
Rows: 20517
Sample rows:
| station_nbr   | date       | tmax   | tmin   | tavg   | depart   | dewpoint   | wetbulb   | heat   | cool   | sunrise   | sunset   | codesum    | snowfall   | preciptotal   | stnpressure   | sealevel   | resultspeed   | resultdir   | avgspeed   |
|---------------|------------|--------|--------|--------|----------|------------|-----------|--------|--------|-----------|----------|------------|------------|---------------|---------------|------------|---------------|-------------|------------|
| 1             | 2012-01-01 | 52     | 31     | 42     | [NULL]   | 36         | 40        | 23     | 0      | [NULL]    | [NULL]   | RA FZFG BR | [NULL]     | 0.05          | 29.78         | 29.92      | 3.6           | 20          | 4.6        |
| 1             | 2012-01-02 | 50     | 31     | 41     | [NULL]   | 26         | 35        | 24     | 0      | [NULL]    | [NULL]   |            | [NULL]     | 0.01          | 29.44         | 29.62      | 9.8           | 24          | 10.3       |
| 1             | 2012-01-03 | 32     | 11     | 22     | [NULL]   | 4          | 18        | 43     | 0      | [NULL]    | [NULL]   |            | [NULL]     | 0.0           | 29.67         | 29.87      | 10.8          | 31          | 11.6       |
| 1             | 2012-01-04 | 28     | 9      | 19     | [NULL]   | -1         | 14        | 46     | 0      | [NULL]    | [NULL]   |            | [NULL]     | 0.0           | 29.86         | 30.03      | 6.3           | 27          | 8.3        |
| 1             | 2012-01-05 | 38     | 25     | 32     | [NULL]   | 13         | 25        | 33     | 0      | [NULL]    | [NULL]   |            | [NULL]     | 0.0           | 29.67         | 29.84      | 6.9           | 25          | 7.8        |
| ...           | ...        | ...    | ...    | ...    | ...      | ...        | ...       | ...    | ...    | ...       | ...      | ...        | ...        | ...           | ...           | ...        | ...           | ...         | ...        |
*/
CREATE TABLE weather (
    "station_nbr" INTEGER NOT NULL,
        -- <example>1</example>
    "date" DATE NOT NULL,
        -- <example>'2012-01-01'</example>
    "tmax" INTEGER NULL,
        -- <example>52</example>
    "tmin" INTEGER NULL,
        -- <example>31</example>
    "tavg" INTEGER NULL,
        -- <example>42</example>
    "depart" INTEGER NULL,
        -- <example>16</example>
    "dewpoint" INTEGER NULL,
        -- <example>36</example>
    "wetbulb" INTEGER NULL,
        -- <example>40</example>
    "heat" INTEGER NULL,
        -- <example>23</example>
    "cool" INTEGER NULL,
        -- <example>0</example>
    "sunrise" TEXT NULL,
        -- <example>'07:16:00'</example>
    "sunset" TEXT NULL,
        -- <example>'16:26:00'</example>
    "codesum" TEXT NOT NULL,
        -- <example>'RA FZFG BR'</example>
    "snowfall" REAL NULL,
        -- <example>0.000</example>
    "preciptotal" REAL NULL,
        -- <example>0.050</example>
    "stnpressure" REAL NULL,
        -- <example>29.780</example>
    "sealevel" REAL NULL,
        -- <example>29.920</example>
    "resultspeed" REAL NULL,
        -- <example>3.600</example>
    "resultdir" INTEGER NULL,
        -- <example>20</example>
    "avgspeed" REAL NULL,
        -- <example>4.600</example>
    PRIMARY KEY ("station_nbr", "date")
);
```