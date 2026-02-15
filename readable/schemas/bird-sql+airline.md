```sql
-- Database: airline

/*
Schema: NULL
Table: "Air Carriers"
Rows: 1656
Sample rows:
| Code   | Description                     |
|--------|---------------------------------|
| 19031  | Mackey International Inc.: MAC  |
| 19032  | Munz Northern Airlines Inc.: XY |
| 19033  | Cochise Airlines Inc.: COC      |
| 19034  | Golden Gate Airlines Inc.: GSA  |
| 19035  | Aeromech Inc.: RZZ              |
| ...    | ...                             |
*/
CREATE TABLE "Air Carriers" (
    "Code" INTEGER NOT NULL PRIMARY KEY,
        -- <example>19031</example>
    "Description" TEXT NOT NULL
        -- <example>'Mackey International Inc.: MAC'</example>
);

/*
Schema: NULL
Table: Airlines
Rows: 701352
Sample rows:
| FL_DATE   | OP_CARRIER_AIRLINE_ID   | TAIL_NUM   | OP_CARRIER_FL_NUM   | ORIGIN_AIRPORT_ID   | ORIGIN_AIRPORT_SEQ_ID   | ORIGIN_CITY_MARKET_ID   | ORIGIN   | DEST_AIRPORT_ID   | DEST_AIRPORT_SEQ_ID   | DEST_CITY_MARKET_ID   | DEST   | CRS_DEP_TIME   | DEP_TIME   | DEP_DELAY   | DEP_DELAY_NEW   | ARR_TIME   | ARR_DELAY   | ARR_DELAY_NEW   | CANCELLED   | CANCELLATION_CODE   | CRS_ELAPSED_TIME   | ACTUAL_ELAPSED_TIME   | CARRIER_DELAY   | WEATHER_DELAY   | NAS_DELAY   | SECURITY_DELAY   | LATE_AIRCRAFT_DELAY   |
|-----------|-------------------------|------------|---------------------|---------------------|-------------------------|-------------------------|----------|-------------------|-----------------------|-----------------------|--------|----------------|------------|-------------|-----------------|------------|-------------|-----------------|-------------|---------------------|--------------------|-----------------------|-----------------|-----------------|-------------|------------------|-----------------------|
| 2018/8/1  | 19805                   | N956AN     | 1587                | 12478               | 1247805                 | 31703                   | JFK      | 14107             | 1410702               | 30466                 | PHX    | 1640           | 1649       | 9           | 9               | 2006       | 44          | 44              | 0           | [NULL]              | 342                | 377                   | 9.0             | 0.0             | 35.0        | 0.0              | 0.0                   |
| 2018/8/1  | 19805                   | N973AN     | 1588                | 14107               | 1410702                 | 30466                   | PHX      | 11618             | 1161802               | 31703                 | EWR    | 1512           | 1541       | 29          | 29              | 2350       | 53          | 53              | 0           | [NULL]              | 285                | 309                   | 0.0             | 0.0             | 53.0        | 0.0              | 0.0                   |
| 2018/8/1  | 19805                   | N9006      | 1590                | 11042               | 1104205                 | 30647                   | CLE      | 11298             | 1129806               | 30194                 | DFW    | 744            | 741        | -3          | 0               | 938        | -2          | 0               | 0           | [NULL]              | 176                | 177                   | [NULL]          | [NULL]          | [NULL]      | [NULL]           | [NULL]                |
| 2018/8/1  | 19805                   | N870NN     | 1591                | 14843               | 1484306                 | 34819                   | SJU      | 11298             | 1129806               | 30194                 | DFW    | 900            | 944        | 44          | 44              | 1347       | 43          | 43              | 0           | [NULL]              | 304                | 303                   | 43.0            | 0.0             | 0.0         | 0.0              | 0.0                   |
| 2018/8/1  | 19805                   | N9023N     | 1593                | 10423               | 1042302                 | 30423                   | AUS      | 13303             | 1330303               | 32467                 | MIA    | 600            | 556        | -4          | 0               | 951        | -2          | 0               | 0           | [NULL]              | 173                | 175                   | [NULL]          | [NULL]          | [NULL]      | [NULL]           | [NULL]                |
| ...       | ...                     | ...        | ...                 | ...                 | ...                     | ...                     | ...      | ...               | ...                   | ...                   | ...    | ...            | ...        | ...         | ...             | ...        | ...         | ...             | ...         | ...                 | ...                | ...                   | ...             | ...             | ...         | ...              | ...                   |
*/
CREATE TABLE Airlines (
    "FL_DATE" TEXT NOT NULL,
        -- <example>'2018/8/1'</example>
    "OP_CARRIER_AIRLINE_ID" INTEGER NOT NULL,
        -- <example>19805</example>
        -- <fk> -> "Air Carriers"."Code"</fk>
    "TAIL_NUM" TEXT NULL,
        -- <example>'N956AN'</example>
    "OP_CARRIER_FL_NUM" INTEGER NOT NULL,
        -- <example>1587</example>
    "ORIGIN_AIRPORT_ID" INTEGER NOT NULL,
        -- <example>12478</example>
    "ORIGIN_AIRPORT_SEQ_ID" INTEGER NOT NULL,
        -- <example>1247805</example>
    "ORIGIN_CITY_MARKET_ID" INTEGER NOT NULL,
        -- <example>31703</example>
    "ORIGIN" TEXT NOT NULL,
        -- <example>'JFK'</example>
        -- <fk> -> Airports."Code"</fk>
    "DEST_AIRPORT_ID" INTEGER NOT NULL,
        -- <example>14107</example>
    "DEST_AIRPORT_SEQ_ID" INTEGER NOT NULL,
        -- <example>1410702</example>
    "DEST_CITY_MARKET_ID" INTEGER NOT NULL,
        -- <example>30466</example>
    "DEST" TEXT NOT NULL,
        -- <example>'PHX'</example>
        -- <fk> -> Airports."Code"</fk>
    "CRS_DEP_TIME" INTEGER NOT NULL,
        -- <example>1640</example>
    "DEP_TIME" INTEGER NULL,
        -- <example>1649</example>
    "DEP_DELAY" INTEGER NULL,
        -- <example>9</example>
    "DEP_DELAY_NEW" INTEGER NULL,
        -- <example>9</example>
    "ARR_TIME" INTEGER NULL,
        -- <example>2006</example>
    "ARR_DELAY" INTEGER NULL,
        -- <example>44</example>
    "ARR_DELAY_NEW" INTEGER NULL,
        -- <example>44</example>
    "CANCELLED" INTEGER NOT NULL,
        -- <example>0</example>
    "CANCELLATION_CODE" TEXT NULL,
        -- <values>{'A', 'B', 'C'}</values>
    "CRS_ELAPSED_TIME" INTEGER NOT NULL,
        -- <example>342</example>
    "ACTUAL_ELAPSED_TIME" INTEGER NULL,
        -- <example>377</example>
    "CARRIER_DELAY" INTEGER NULL,
        -- <example>9</example>
    "WEATHER_DELAY" INTEGER NULL,
        -- <example>0</example>
    "NAS_DELAY" INTEGER NULL,
        -- <example>35</example>
    "SECURITY_DELAY" INTEGER NULL,
        -- <example>0</example>
    "LATE_AIRCRAFT_DELAY" INTEGER NULL,
        -- <example>0</example>
    FOREIGN KEY ("ORIGIN") REFERENCES Airports("Code"),
    FOREIGN KEY ("DEST") REFERENCES Airports("Code"),
    FOREIGN KEY ("OP_CARRIER_AIRLINE_ID") REFERENCES "Air Carriers"("Code")
);

/*
Schema: NULL
Table: Airports
Rows: 6510
Sample rows:
| Code   | Description                                   |
|--------|-----------------------------------------------|
| 01A    | Afognak Lake, AK: Afognak Lake Airport        |
| 03A    | Granite Mountain, AK: Bear Creek Mining Strip |
| 04A    | Lik, AK: Lik Mining Camp                      |
| 05A    | Little Squaw, AK: Little Squaw Airport        |
| 06A    | Kizhuyak, AK: Kizhuyak Bay                    |
| ...    | ...                                           |
*/
CREATE TABLE Airports (
    "Code" TEXT NOT NULL PRIMARY KEY,
        -- <example>'01A'</example>
    "Description" TEXT NOT NULL
        -- <example>'Afognak Lake, AK: Afognak Lake Airport'</example>
);
```