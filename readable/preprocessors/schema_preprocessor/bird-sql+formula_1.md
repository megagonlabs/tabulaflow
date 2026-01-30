```sql
-- Database: formula_1

-- Table: circuits (72 rows)
CREATE TABLE circuits (
    circuitId INTEGER PRIMARY KEY,  -- e.g. 23
    circuitRef TEXT NOT NULL,  -- e.g. 'sepang'
    name TEXT NOT NULL,  -- e.g. 'Sepang International Circuit'
    location TEXT,  -- e.g. 'Kuala Lumpur'
    country TEXT,  -- e.g. 'Malaysia'
    lat REAL,  -- e.g. 2.761
    lng REAL,  -- e.g. 101.738
    url TEXT NOT NULL  -- e.g. 'http://en.wikipedia.org/wiki/A1-Ring'
);

-- Table: constructorResults (11082 rows)
CREATE TABLE constructorResults (
    constructorResultsId INTEGER PRIMARY KEY,  -- e.g. 1
    raceId INTEGER NOT NULL,  -- e.g. 18; FK -> races.raceId
    constructorId INTEGER NOT NULL,  -- e.g. 1; FK -> constructors.constructorId
    points REAL,  -- e.g. 14.000
    status TEXT,  -- values: {'D'}
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- Table: constructorStandings (11836 rows)
CREATE TABLE constructorStandings (
    constructorStandingsId INTEGER PRIMARY KEY,  -- e.g. 1
    raceId INTEGER NOT NULL,  -- e.g. 18; FK -> races.raceId
    constructorId INTEGER NOT NULL,  -- e.g. 1; FK -> constructors.constructorId
    points REAL NOT NULL,  -- e.g. 14.000
    position INTEGER,  -- e.g. 1
    positionText TEXT,  -- e.g. '1'
    wins INTEGER NOT NULL,  -- e.g. 1
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- Table: constructors (208 rows)
CREATE TABLE constructors (
    constructorId INTEGER PRIMARY KEY,  -- e.g. 147
    constructorRef TEXT NOT NULL,  -- e.g. 'mclaren'
    name TEXT NOT NULL,  -- e.g. 'AFM'
    nationality TEXT,  -- e.g. 'British'
    url TEXT NOT NULL  -- e.g. 'http://en.wikipedia.org/wiki/McLaren'
);

-- Table: driverStandings (31578 rows)
CREATE TABLE driverStandings (
    driverStandingsId INTEGER PRIMARY KEY,  -- e.g. 1
    raceId INTEGER NOT NULL,  -- e.g. 18; FK -> races.raceId
    driverId INTEGER NOT NULL,  -- e.g. 1; FK -> drivers.driverId
    points REAL NOT NULL,  -- e.g. 10.000
    position INTEGER,  -- e.g. 1
    positionText TEXT,  -- e.g. '1'
    wins INTEGER NOT NULL,  -- e.g. 1
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

-- Table: drivers (840 rows)
CREATE TABLE drivers (
    driverId INTEGER PRIMARY KEY,  -- e.g. 452
    driverRef TEXT NOT NULL,  -- e.g. 'hamilton'
    number INTEGER,  -- e.g. 44
    code TEXT,  -- e.g. 'HAM'
    forename TEXT NOT NULL,  -- e.g. 'Lewis'
    surname TEXT NOT NULL,  -- e.g. 'Hamilton'
    dob DATE,  -- e.g. '1985-01-07'
    nationality TEXT,  -- e.g. 'British'
    url TEXT NOT NULL  -- e.g. ''
);

-- Table: lapTimes (420369 rows)
CREATE TABLE lapTimes (
    raceId INTEGER NOT NULL,  -- e.g. 1; FK -> races.raceId; FK (composite)
    driverId INTEGER NOT NULL,  -- e.g. 1; FK -> drivers.driverId; FK (composite)
    lap INTEGER NOT NULL,  -- e.g. 1
    position INTEGER,  -- e.g. 13
    time TEXT,  -- e.g. '1:49.088'
    milliseconds INTEGER,  -- e.g. 109088
    PRIMARY KEY (raceId, driverId, lap),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (raceId, driverId) REFERENCES driverStandings(raceId, driverId)
);

-- Table: pitStops (6070 rows)
CREATE TABLE pitStops (
    raceId INTEGER NOT NULL,  -- e.g. 841; FK -> races.raceId
    driverId INTEGER NOT NULL,  -- e.g. 1; FK -> drivers.driverId
    stop INTEGER NOT NULL,  -- e.g. 1
    lap INTEGER NOT NULL,  -- e.g. 16
    time TEXT NOT NULL,  -- e.g. '17:28:24'
    duration TEXT,  -- e.g. '23.227'
    milliseconds INTEGER,  -- e.g. 23227
    PRIMARY KEY (raceId, driverId, stop),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

-- Table: qualifying (7397 rows)
CREATE TABLE qualifying (
    qualifyId INTEGER PRIMARY KEY,  -- e.g. 1
    raceId INTEGER NOT NULL,  -- e.g. 18; FK -> races.raceId
    driverId INTEGER NOT NULL,  -- e.g. 1; FK -> drivers.driverId
    constructorId INTEGER NOT NULL,  -- e.g. 1; FK -> constructors.constructorId
    number INTEGER NOT NULL,  -- e.g. 22
    position INTEGER,  -- e.g. 1
    q1 TEXT,  -- e.g. '1:26.572'
    q2 TEXT,  -- e.g. '1:25.187'
    q3 TEXT,  -- e.g. '1:26.714'
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- Table: races (976 rows)
CREATE TABLE races (
    raceId INTEGER PRIMARY KEY,  -- e.g. 837
    year INTEGER NOT NULL,  -- e.g. 2009; FK -> seasons.year
    round INTEGER NOT NULL,  -- e.g. 1
    circuitId INTEGER NOT NULL,  -- e.g. 1; FK -> circuits.circuitId
    name TEXT NOT NULL,  -- e.g. 'Australian Grand Prix'
    date DATE NOT NULL,  -- e.g. '2009-03-29'
    time TEXT,  -- e.g. '06:00:00'
    url TEXT,  -- e.g. 'http://en.wikipedia.org/wiki/1950_Belgian_Grand_Prix'
    FOREIGN KEY (year) REFERENCES seasons(year),
    FOREIGN KEY (circuitId) REFERENCES circuits(circuitId)
);

-- Table: results (23657 rows)
CREATE TABLE results (
    resultId INTEGER PRIMARY KEY,  -- e.g. 1
    raceId INTEGER NOT NULL,  -- e.g. 18; FK -> races.raceId; FK (composite)
    driverId INTEGER NOT NULL,  -- e.g. 1; FK -> drivers.driverId; FK (composite)
    constructorId INTEGER NOT NULL,  -- e.g. 1; FK -> constructors.constructorId
    number INTEGER,  -- e.g. 22
    grid INTEGER NOT NULL,  -- e.g. 1
    position INTEGER,  -- e.g. 1
    positionText TEXT NOT NULL,  -- e.g. '1'
    positionOrder INTEGER NOT NULL,  -- e.g. 1
    points REAL NOT NULL,  -- e.g. 10.000
    laps INTEGER NOT NULL,  -- e.g. 58
    time TEXT,  -- e.g. '1:34:50.616'
    milliseconds INTEGER,  -- e.g. 5690616
    fastestLap INTEGER,  -- e.g. 39; FK (composite)
    rank INTEGER,  -- e.g. 2
    fastestLapTime TEXT,  -- e.g. '1:27.452'
    fastestLapSpeed TEXT,  -- e.g. '218.300'
    statusId INTEGER NOT NULL,  -- e.g. 1; FK -> status.statusId
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId),
    FOREIGN KEY (statusId) REFERENCES status(statusId),
    FOREIGN KEY (raceId, driverId, fastestLap) REFERENCES lapTimes(raceId, driverId, lap)
);

-- Table: seasons (68 rows)
CREATE TABLE seasons (
    year INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1950
    url TEXT NOT NULL  -- e.g. 'http://en.wikipedia.org/wiki/1950_Formula_One_season'
);

-- Table: status (134 rows)
CREATE TABLE status (
    statusId INTEGER PRIMARY KEY,  -- e.g. 1
    status TEXT NOT NULL  -- e.g. 'Finished'
);
```