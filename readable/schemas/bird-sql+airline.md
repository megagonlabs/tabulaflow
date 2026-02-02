```sql
-- Database: airline

-- Table: "Air Carriers" (1656 rows)
CREATE TABLE "Air Carriers" (
    Code INTEGER NULL PRIMARY KEY,
        -- <example>19031</example>
    Description TEXT NULL
        -- <example>'Mackey International Inc.: MAC'</example>
);

-- Table: Airlines (701352 rows)
CREATE TABLE Airlines (
    FL_DATE TEXT NULL,
        -- <example>'2018/8/1'</example>
    OP_CARRIER_AIRLINE_ID INTEGER NULL,
        -- <example>19805</example>
        -- <fk> -> "Air Carriers".Code</fk>
    TAIL_NUM TEXT NULL,
        -- <example>'N956AN'</example>
    OP_CARRIER_FL_NUM INTEGER NULL,
        -- <example>1587</example>
    ORIGIN_AIRPORT_ID INTEGER NULL,
        -- <example>12478</example>
    ORIGIN_AIRPORT_SEQ_ID INTEGER NULL,
        -- <example>1247805</example>
    ORIGIN_CITY_MARKET_ID INTEGER NULL,
        -- <example>31703</example>
    ORIGIN TEXT NULL,
        -- <example>'JFK'</example>
        -- <fk> -> Airports.Code</fk>
    DEST_AIRPORT_ID INTEGER NULL,
        -- <example>14107</example>
    DEST_AIRPORT_SEQ_ID INTEGER NULL,
        -- <example>1410702</example>
    DEST_CITY_MARKET_ID INTEGER NULL,
        -- <example>30466</example>
    DEST TEXT NULL,
        -- <example>'PHX'</example>
        -- <fk> -> Airports.Code</fk>
    CRS_DEP_TIME INTEGER NULL,
        -- <example>1640</example>
    DEP_TIME INTEGER NULL,
        -- <example>1649</example>
    DEP_DELAY INTEGER NULL,
        -- <example>9</example>
    DEP_DELAY_NEW INTEGER NULL,
        -- <example>9</example>
    ARR_TIME INTEGER NULL,
        -- <example>2006</example>
    ARR_DELAY INTEGER NULL,
        -- <example>44</example>
    ARR_DELAY_NEW INTEGER NULL,
        -- <example>44</example>
    CANCELLED INTEGER NULL,
        -- <example>0</example>
    CANCELLATION_CODE TEXT NULL,
        -- <values>{'A', 'B', 'C'}</values>
    CRS_ELAPSED_TIME INTEGER NULL,
        -- <example>342</example>
    ACTUAL_ELAPSED_TIME INTEGER NULL,
        -- <example>377</example>
    CARRIER_DELAY INTEGER NULL,
        -- <example>9</example>
    WEATHER_DELAY INTEGER NULL,
        -- <example>0</example>
    NAS_DELAY INTEGER NULL,
        -- <example>35</example>
    SECURITY_DELAY INTEGER NULL,
        -- <example>0</example>
    LATE_AIRCRAFT_DELAY INTEGER NULL,
        -- <example>0</example>
    FOREIGN KEY (ORIGIN) REFERENCES Airports(Code),
    FOREIGN KEY (DEST) REFERENCES Airports(Code),
    FOREIGN KEY (OP_CARRIER_AIRLINE_ID) REFERENCES "Air Carriers"(Code)
);

-- Table: Airports (6510 rows)
CREATE TABLE Airports (
    Code TEXT NULL PRIMARY KEY,
        -- <example>'01A'</example>
    Description TEXT NULL
        -- <example>'Afognak Lake, AK: Afognak Lake Airport'</example>
);
```