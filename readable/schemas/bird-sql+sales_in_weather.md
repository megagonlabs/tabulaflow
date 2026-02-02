```sql
-- Database: sales_in_weather

-- Table: relation (45 rows)
CREATE TABLE relation (
    store_nbr INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> sales_in_weather.store_nbr</fk>
    station_nbr INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> weather.station_nbr</fk>
    FOREIGN KEY (store_nbr) REFERENCES sales_in_weather(store_nbr),
    FOREIGN KEY (station_nbr) REFERENCES weather(station_nbr)
);

-- Table: sales_in_weather (4617600 rows)
CREATE TABLE sales_in_weather (
    date DATE NULL,
        -- <example>'2012-01-01'</example>
    store_nbr INTEGER NULL,
        -- <example>1</example>
    item_nbr INTEGER NULL,
        -- <example>1</example>
    units INTEGER NULL,
        -- <example>0</example>
    PRIMARY KEY (date, store_nbr, item_nbr)
);

-- Table: weather (20517 rows)
CREATE TABLE weather (
    station_nbr INTEGER NULL,
        -- <example>1</example>
    date DATE NULL,
        -- <example>'2012-01-01'</example>
    tmax INTEGER NULL,
        -- <example>52</example>
    tmin INTEGER NULL,
        -- <example>31</example>
    tavg INTEGER NULL,
        -- <example>42</example>
    depart INTEGER NULL,
        -- <example>16</example>
    dewpoint INTEGER NULL,
        -- <example>36</example>
    wetbulb INTEGER NULL,
        -- <example>40</example>
    heat INTEGER NULL,
        -- <example>23</example>
    cool INTEGER NULL,
        -- <example>0</example>
    sunrise TEXT NULL,
        -- <example>'07:16:00'</example>
    sunset TEXT NULL,
        -- <example>'16:26:00'</example>
    codesum TEXT NULL,
        -- <example>'RA FZFG BR'</example>
    snowfall REAL NULL,
        -- <example>0.000</example>
    preciptotal REAL NULL,
        -- <example>0.050</example>
    stnpressure REAL NULL,
        -- <example>29.780</example>
    sealevel REAL NULL,
        -- <example>29.920</example>
    resultspeed REAL NULL,
        -- <example>3.600</example>
    resultdir INTEGER NULL,
        -- <example>20</example>
    avgspeed REAL NULL,
        -- <example>4.600</example>
    PRIMARY KEY (station_nbr, date)
);
```