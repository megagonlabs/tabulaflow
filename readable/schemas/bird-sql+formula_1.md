```sql
-- Database: formula_1

-- Table: circuits (72 rows)
CREATE TABLE circuits (
    circuitId INTEGER NULL PRIMARY KEY,
        -- <example>23</example>
    circuitRef TEXT NOT NULL,
        -- <example>'sepang'</example>
    name TEXT NOT NULL,
        -- <example>'Sepang International Circuit'</example>
    location TEXT NULL,
        -- <example>'Kuala Lumpur'</example>
    country TEXT NULL,
        -- <example>'Malaysia'</example>
    lat REAL NULL,
        -- <example>2.761</example>
    lng REAL NULL,
        -- <example>101.738</example>
    alt INTEGER NULL,
    url TEXT NOT NULL
        -- <example>'http://en.wikipedia.org/wiki/A1-Ring'</example>
);

-- Table: constructorResults (11082 rows)
CREATE TABLE constructorResults (
    constructorResultsId INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    constructorId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    points REAL NULL,
        -- <example>14.000</example>
    status TEXT NULL,
        -- <values>{'D'}</values>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- Table: constructorStandings (11836 rows)
CREATE TABLE constructorStandings (
    constructorStandingsId INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    constructorId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    points REAL NOT NULL,
        -- <example>14.000</example>
    position INTEGER NULL,
        -- <example>1</example>
    positionText TEXT NULL,
        -- <example>'1'</example>
    wins INTEGER NOT NULL,
        -- <example>1</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- Table: constructors (208 rows)
CREATE TABLE constructors (
    constructorId INTEGER NULL PRIMARY KEY,
        -- <example>147</example>
    constructorRef TEXT NOT NULL,
        -- <example>'mclaren'</example>
    name TEXT NOT NULL,
        -- <example>'AFM'</example>
    nationality TEXT NULL,
        -- <example>'British'</example>
    url TEXT NOT NULL
        -- <example>'http://en.wikipedia.org/wiki/McLaren'</example>
);

-- Table: driverStandings (31578 rows)
CREATE TABLE driverStandings (
    driverStandingsId INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    points REAL NOT NULL,
        -- <example>10.000</example>
    position INTEGER NULL,
        -- <example>1</example>
    positionText TEXT NULL,
        -- <example>'1'</example>
    wins INTEGER NOT NULL,
        -- <example>1</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

-- Table: drivers (840 rows)
CREATE TABLE drivers (
    driverId INTEGER NULL PRIMARY KEY,
        -- <example>452</example>
    driverRef TEXT NOT NULL,
        -- <example>'hamilton'</example>
    number INTEGER NULL,
        -- <example>44</example>
    code TEXT NULL,
        -- <example>'HAM'</example>
    forename TEXT NOT NULL,
        -- <example>'Lewis'</example>
    surname TEXT NOT NULL,
        -- <example>'Hamilton'</example>
    dob DATE NULL,
        -- <example>'1985-01-07'</example>
    nationality TEXT NULL,
        -- <example>'British'</example>
    url TEXT NOT NULL
        -- <example>''</example>
);

-- Table: lapTimes (420369 rows)
CREATE TABLE lapTimes (
    raceId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    lap INTEGER NOT NULL,
        -- <example>1</example>
    position INTEGER NULL,
        -- <example>13</example>
    time TEXT NULL,
        -- <example>'1:49.088'</example>
    milliseconds INTEGER NULL,
        -- <example>109088</example>
    PRIMARY KEY (raceId, driverId, lap),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

-- Table: pitStops (6070 rows)
CREATE TABLE pitStops (
    raceId INTEGER NOT NULL,
        -- <example>841</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    stop INTEGER NOT NULL,
        -- <example>1</example>
    lap INTEGER NOT NULL,
        -- <example>16</example>
    time TEXT NOT NULL,
        -- <example>'17:28:24'</example>
    duration TEXT NULL,
        -- <example>'23.227'</example>
    milliseconds INTEGER NULL,
        -- <example>23227</example>
    PRIMARY KEY (raceId, driverId, stop),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

-- Table: qualifying (7397 rows)
CREATE TABLE qualifying (
    qualifyId INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    constructorId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    number INTEGER NOT NULL,
        -- <example>22</example>
    position INTEGER NULL,
        -- <example>1</example>
    q1 TEXT NULL,
        -- <example>'1:26.572'</example>
    q2 TEXT NULL,
        -- <example>'1:25.187'</example>
    q3 TEXT NULL,
        -- <example>'1:26.714'</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- Table: races (976 rows)
CREATE TABLE races (
    raceId INTEGER NULL PRIMARY KEY,
        -- <example>837</example>
    year INTEGER NOT NULL,
        -- <example>2009</example>
        -- <fk> -> seasons.year</fk>
    round INTEGER NOT NULL,
        -- <example>1</example>
    circuitId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> circuits.circuitId</fk>
    name TEXT NOT NULL,
        -- <example>'Australian Grand Prix'</example>
    date DATE NOT NULL,
        -- <example>'2009-03-29'</example>
    time TEXT NULL,
        -- <example>'06:00:00'</example>
    url TEXT NULL,
        -- <example>'http://en.wikipedia.org/wiki/1950_Belgian_Grand_Prix'</example>
    FOREIGN KEY (year) REFERENCES seasons(year),
    FOREIGN KEY (circuitId) REFERENCES circuits(circuitId)
);

-- Table: results (23657 rows)
CREATE TABLE results (
    resultId INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    constructorId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    number INTEGER NULL,
        -- <example>22</example>
    grid INTEGER NOT NULL,
        -- <example>1</example>
    position INTEGER NULL,
        -- <example>1</example>
    positionText TEXT NOT NULL,
        -- <example>'1'</example>
    positionOrder INTEGER NOT NULL,
        -- <example>1</example>
    points REAL NOT NULL,
        -- <example>10.000</example>
    laps INTEGER NOT NULL,
        -- <example>58</example>
    time TEXT NULL,
        -- <example>'1:34:50.616'</example>
    milliseconds INTEGER NULL,
        -- <example>5690616</example>
    fastestLap INTEGER NULL,
        -- <example>39</example>
    rank INTEGER NULL,
        -- <example>2</example>
    fastestLapTime TEXT NULL,
        -- <example>'1:27.452'</example>
    fastestLapSpeed TEXT NULL,
        -- <example>'218.300'</example>
    statusId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> status.statusId</fk>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId),
    FOREIGN KEY (statusId) REFERENCES status(statusId)
);

-- Table: seasons (68 rows)
CREATE TABLE seasons (
    year INTEGER NOT NULL PRIMARY KEY,
        -- <example>1950</example>
    url TEXT NOT NULL
        -- <example>'http://en.wikipedia.org/wiki/1950_Formula_One_season'</example>
);

-- Table: status (134 rows)
CREATE TABLE status (
    statusId INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    status TEXT NOT NULL
        -- <example>'Finished'</example>
);
```