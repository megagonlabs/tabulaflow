```sql
-- Database: airline

-- Table: "Air Carriers" (1656 rows)
CREATE TABLE "Air Carriers" (
    Code INTEGER PRIMARY KEY,  -- e.g. 19031
    Description TEXT  -- e.g. 'Mackey International Inc.: MAC'
);

-- Table: Airlines (701352 rows)
CREATE TABLE Airlines (
    FL_DATE TEXT,  -- e.g. '2018/8/1'
    OP_CARRIER_AIRLINE_ID INTEGER,  -- e.g. 19805; FK -> "Air Carriers".Code
    TAIL_NUM TEXT,  -- e.g. 'N956AN'
    OP_CARRIER_FL_NUM INTEGER,  -- e.g. 1587
    ORIGIN_AIRPORT_ID INTEGER,  -- e.g. 12478
    ORIGIN_AIRPORT_SEQ_ID INTEGER,  -- e.g. 1247805
    ORIGIN_CITY_MARKET_ID INTEGER,  -- e.g. 31703
    ORIGIN TEXT,  -- e.g. 'JFK'; FK -> Airports.Code
    DEST_AIRPORT_ID INTEGER,  -- e.g. 14107
    DEST_AIRPORT_SEQ_ID INTEGER,  -- e.g. 1410702
    DEST_CITY_MARKET_ID INTEGER,  -- e.g. 30466
    DEST TEXT,  -- e.g. 'PHX'; FK -> Airports.Code
    CRS_DEP_TIME INTEGER,  -- e.g. 1640
    DEP_TIME INTEGER,  -- e.g. 1649
    DEP_DELAY INTEGER,  -- e.g. 9
    DEP_DELAY_NEW INTEGER,  -- e.g. 9
    ARR_TIME INTEGER,  -- e.g. 2006
    ARR_DELAY INTEGER,  -- e.g. 44
    ARR_DELAY_NEW INTEGER,  -- e.g. 44
    CANCELLED INTEGER,  -- e.g. 0
    CANCELLATION_CODE TEXT,  -- values: {'A', 'B', 'C'}
    CRS_ELAPSED_TIME INTEGER,  -- e.g. 342
    ACTUAL_ELAPSED_TIME INTEGER,  -- e.g. 377
    CARRIER_DELAY INTEGER,  -- e.g. 9
    WEATHER_DELAY INTEGER,  -- e.g. 0
    NAS_DELAY INTEGER,  -- e.g. 35
    SECURITY_DELAY INTEGER,  -- e.g. 0
    LATE_AIRCRAFT_DELAY INTEGER,  -- e.g. 0
    FOREIGN KEY (ORIGIN) REFERENCES Airports(Code),
    FOREIGN KEY (DEST) REFERENCES Airports(Code),
    FOREIGN KEY (OP_CARRIER_AIRLINE_ID) REFERENCES "Air Carriers"(Code)
);

-- Table: Airports (6510 rows)
CREATE TABLE Airports (
    Code TEXT PRIMARY KEY,  -- e.g. '01A'
    Description TEXT  -- e.g. 'Afognak Lake, AK: Afognak Lake Airport'
);
```