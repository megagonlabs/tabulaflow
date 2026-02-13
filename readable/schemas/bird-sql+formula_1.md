```sql
-- Database: formula_1

/*
Schema: NULLTable: circuits
Rows: 72
Sample rows:
| circuitId   | circuitRef   | name                           | location     | country   | lat     | lng     | alt    | url                                                         |
|-------------|--------------|--------------------------------|--------------|-----------|---------|---------|--------|-------------------------------------------------------------|
| 2           | sepang       | Sepang International Circuit   | Kuala Lumpur | Malaysia  | 2.76083 | 101.738 | [NULL] | http://en.wikipedia.org/wiki/Sepang_International_Circuit   |
| 3           | bahrain      | Bahrain International Circuit  | Sakhir       | Bahrain   | 26.0325 | 50.5106 | [NULL] | http://en.wikipedia.org/wiki/Bahrain_International_Circuit  |
| 4           | catalunya    | Circuit de Barcelona-Catalunya | Montmeló     | Spain     | 41.57   | 2.26111 | [NULL] | http://en.wikipedia.org/wiki/Circuit_de_Barcelona-Catalunya |
| 5           | istanbul     | Istanbul Park                  | Istanbul     | Turkey    | 40.9517 | 29.405  | [NULL] | http://en.wikipedia.org/wiki/Istanbul_Park                  |
| 6           | monaco       | Circuit de Monaco              | Monte-Carlo  | Monaco    | 43.7347 | 7.42056 | [NULL] | http://en.wikipedia.org/wiki/Circuit_de_Monaco              |
| ...         | ...          | ...                            | ...          | ...       | ...     | ...     | ...    | ...                                                         |
*/
CREATE TABLE circuits (
    circuitId INTEGER NOT NULL PRIMARY KEY,
        -- <example>23</example>
    circuitRef TEXT NOT NULL,
        -- <example>'sepang'</example>
    name TEXT NOT NULL,
        -- <example>'Sepang International Circuit'</example>
    location TEXT NOT NULL,
        -- <example>'Kuala Lumpur'</example>
    country TEXT NOT NULL,
        -- <example>'Malaysia'</example>
    lat REAL NOT NULL,
        -- <example>2.761</example>
    lng REAL NOT NULL,
        -- <example>101.738</example>
    alt INTEGER NULL,
    url TEXT NOT NULL
        -- <example>'http://en.wikipedia.org/wiki/A1-Ring'</example>
);

/*
Schema: NULLTable: constructorResults
Rows: 11082
Sample rows:
| constructorResultsId   | raceId   | constructorId   | points   | status   |
|------------------------|----------|-----------------|----------|----------|
| 1                      | 18       | 1               | 14.0     | [NULL]   |
| 2                      | 18       | 2               | 8.0      | [NULL]   |
| 3                      | 18       | 3               | 9.0      | [NULL]   |
| 4                      | 18       | 4               | 5.0      | [NULL]   |
| 5                      | 18       | 5               | 2.0      | [NULL]   |
| ...                    | ...      | ...             | ...      | ...      |
*/
CREATE TABLE constructorResults (
    constructorResultsId INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    constructorId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    points REAL NOT NULL,
        -- <example>14.000</example>
    status TEXT NULL,
        -- <values>{'D'}</values>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

/*
Schema: NULLTable: constructorStandings
Rows: 11836
Sample rows:
| constructorStandingsId   | raceId   | constructorId   | points   | position   | positionText   | wins   |
|--------------------------|----------|-----------------|----------|------------|----------------|--------|
| 1                        | 18       | 1               | 14.0     | 1          | 1              | 1      |
| 2                        | 18       | 2               | 8.0      | 3          | 3              | 0      |
| 3                        | 18       | 3               | 9.0      | 2          | 2              | 0      |
| 4                        | 18       | 4               | 5.0      | 4          | 4              | 0      |
| 5                        | 18       | 5               | 2.0      | 5          | 5              | 0      |
| ...                      | ...      | ...             | ...      | ...        | ...            | ...    |
*/
CREATE TABLE constructorStandings (
    constructorStandingsId INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    constructorId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    points REAL NOT NULL,
        -- <example>14.000</example>
    position INTEGER NOT NULL,
        -- <example>1</example>
    positionText TEXT NOT NULL,
        -- <example>'1'</example>
    wins INTEGER NOT NULL,
        -- <example>1</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

/*
Schema: NULLTable: constructors
Rows: 208
Sample rows:
| constructorId   | constructorRef   | name       | nationality   | url                                                          |
|-----------------|------------------|------------|---------------|--------------------------------------------------------------|
| 1               | mclaren          | McLaren    | British       | http://en.wikipedia.org/wiki/McLaren                         |
| 2               | bmw_sauber       | BMW Sauber | German        | http://en.wikipedia.org/wiki/BMW_Sauber                      |
| 3               | williams         | Williams   | British       | http://en.wikipedia.org/wiki/Williams_Grand_Prix_Engineering |
| 4               | renault          | Renault    | French        | http://en.wikipedia.org/wiki/Renault_F1                      |
| 5               | toro_rosso       | Toro Rosso | Italian       | http://en.wikipedia.org/wiki/Scuderia_Toro_Rosso             |
| ...             | ...              | ...        | ...           | ...                                                          |
*/
CREATE TABLE constructors (
    constructorId INTEGER NOT NULL PRIMARY KEY,
        -- <example>147</example>
    constructorRef TEXT NOT NULL,
        -- <example>'mclaren'</example>
    name TEXT NOT NULL,
        -- <example>'AFM'</example>
    nationality TEXT NOT NULL,
        -- <example>'British'</example>
    url TEXT NOT NULL
        -- <example>'http://en.wikipedia.org/wiki/McLaren'</example>
);

/*
Schema: NULLTable: driverStandings
Rows: 31578
Sample rows:
| driverStandingsId   | raceId   | driverId   | points   | position   | positionText   | wins   |
|---------------------|----------|------------|----------|------------|----------------|--------|
| 1                   | 18       | 1          | 10.0     | 1          | 1              | 1      |
| 2                   | 18       | 2          | 8.0      | 2          | 2              | 0      |
| 3                   | 18       | 3          | 6.0      | 3          | 3              | 0      |
| 4                   | 18       | 4          | 5.0      | 4          | 4              | 0      |
| 5                   | 18       | 5          | 4.0      | 5          | 5              | 0      |
| ...                 | ...      | ...        | ...      | ...        | ...            | ...    |
*/
CREATE TABLE driverStandings (
    driverStandingsId INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    points REAL NOT NULL,
        -- <example>10.000</example>
    position INTEGER NOT NULL,
        -- <example>1</example>
    positionText TEXT NOT NULL,
        -- <example>'1'</example>
    wins INTEGER NOT NULL,
        -- <example>1</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

/*
Schema: NULLTable: drivers
Rows: 840
Sample rows:
| driverId   | driverRef   | number   | code   | forename   | surname    | dob        | nationality   | url                                            |
|------------|-------------|----------|--------|------------|------------|------------|---------------|------------------------------------------------|
| 1          | hamilton    | 44.0     | HAM    | Lewis      | Hamilton   | 1985-01-07 | British       | http://en.wikipedia.org/wiki/Lewis_Hamilton    |
| 2          | heidfeld    | [NULL]   | HEI    | Nick       | Heidfeld   | 1977-05-10 | German        | http://en.wikipedia.org/wiki/Nick_Heidfeld     |
| 3          | rosberg     | 6.0      | ROS    | Nico       | Rosberg    | 1985-06-27 | German        | http://en.wikipedia.org/wiki/Nico_Rosberg      |
| 4          | alonso      | 14.0     | ALO    | Fernando   | Alonso     | 1981-07-29 | Spanish       | http://en.wikipedia.org/wiki/Fernando_Alonso   |
| 5          | kovalainen  | [NULL]   | KOV    | Heikki     | Kovalainen | 1981-10-19 | Finnish       | http://en.wikipedia.org/wiki/Heikki_Kovalainen |
| ...        | ...         | ...      | ...    | ...        | ...        | ...        | ...           | ...                                            |
*/
CREATE TABLE drivers (
    driverId INTEGER NOT NULL PRIMARY KEY,
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
    nationality TEXT NOT NULL,
        -- <example>'British'</example>
    url TEXT NOT NULL
        -- <example>''</example>
);

/*
Schema: NULLTable: lapTimes
Rows: 420369
Sample rows:
| raceId   | driverId   | lap   | position   | time     | milliseconds   |
|----------|------------|-------|------------|----------|----------------|
| 1        | 1          | 1     | 13         | 1:49.088 | 109088         |
| 1        | 1          | 2     | 12         | 1:33.740 | 93740          |
| 1        | 1          | 3     | 11         | 1:31.600 | 91600          |
| 1        | 1          | 4     | 10         | 1:31.067 | 91067          |
| 1        | 1          | 5     | 10         | 1:32.129 | 92129          |
| ...      | ...        | ...   | ...        | ...      | ...            |
*/
CREATE TABLE lapTimes (
    raceId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    lap INTEGER NOT NULL,
        -- <example>1</example>
    position INTEGER NOT NULL,
        -- <example>13</example>
    time TEXT NOT NULL,
        -- <example>'1:49.088'</example>
    milliseconds INTEGER NOT NULL,
        -- <example>109088</example>
    PRIMARY KEY (raceId, driverId, lap),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

/*
Schema: NULLTable: pitStops
Rows: 6070
Sample rows:
| raceId   | driverId   | stop   | lap   | time     | duration   | milliseconds   |
|----------|------------|--------|-------|----------|------------|----------------|
| 841      | 1          | 1      | 16    | 17:28:24 | 23.227     | 23227          |
| 841      | 1          | 2      | 36    | 17:59:29 | 23.199     | 23199          |
| 841      | 2          | 1      | 15    | 17:27:41 | 22.994     | 22994          |
| 841      | 2          | 2      | 30    | 17:51:32 | 25.098     | 25098          |
| 841      | 3          | 1      | 16    | 17:29:00 | 23.716     | 23716          |
| ...      | ...        | ...    | ...   | ...      | ...        | ...            |
*/
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
    duration TEXT NOT NULL,
        -- <example>'23.227'</example>
    milliseconds INTEGER NOT NULL,
        -- <example>23227</example>
    PRIMARY KEY (raceId, driverId, stop),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

/*
Schema: NULLTable: qualifying
Rows: 7397
Sample rows:
| qualifyId   | raceId   | driverId   | constructorId   | number   | position   | q1       | q2       | q3       |
|-------------|----------|------------|-----------------|----------|------------|----------|----------|----------|
| 1           | 18       | 1          | 1               | 22       | 1          | 1:26.572 | 1:25.187 | 1:26.714 |
| 2           | 18       | 9          | 2               | 4        | 2          | 1:26.103 | 1:25.315 | 1:26.869 |
| 3           | 18       | 5          | 1               | 23       | 3          | 1:25.664 | 1:25.452 | 1:27.079 |
| 4           | 18       | 13         | 6               | 2        | 4          | 1:25.994 | 1:25.691 | 1:27.178 |
| 5           | 18       | 2          | 2               | 3        | 5          | 1:25.960 | 1:25.518 | 1:27.236 |
| ...         | ...      | ...        | ...             | ...      | ...        | ...      | ...      | ...      |
*/
CREATE TABLE qualifying (
    qualifyId INTEGER NOT NULL PRIMARY KEY,
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
    position INTEGER NOT NULL,
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

/*
Schema: NULLTable: races
Rows: 976
Sample rows:
| raceId   | year   | round   | circuitId   | name                  | date       | time     | url                                                     |
|----------|--------|---------|-------------|-----------------------|------------|----------|---------------------------------------------------------|
| 1        | 2009   | 1       | 1           | Australian Grand Prix | 2009-03-29 | 06:00:00 | http://en.wikipedia.org/wiki/2009_Australian_Grand_Prix |
| 2        | 2009   | 2       | 2           | Malaysian Grand Prix  | 2009-04-05 | 09:00:00 | http://en.wikipedia.org/wiki/2009_Malaysian_Grand_Prix  |
| 3        | 2009   | 3       | 17          | Chinese Grand Prix    | 2009-04-19 | 07:00:00 | http://en.wikipedia.org/wiki/2009_Chinese_Grand_Prix    |
| 4        | 2009   | 4       | 3           | Bahrain Grand Prix    | 2009-04-26 | 12:00:00 | http://en.wikipedia.org/wiki/2009_Bahrain_Grand_Prix    |
| 5        | 2009   | 5       | 4           | Spanish Grand Prix    | 2009-05-10 | 12:00:00 | http://en.wikipedia.org/wiki/2009_Spanish_Grand_Prix    |
| ...      | ...    | ...     | ...         | ...                   | ...        | ...      | ...                                                     |
*/
CREATE TABLE races (
    raceId INTEGER NOT NULL PRIMARY KEY,
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
    url TEXT NOT NULL,
        -- <example>'http://en.wikipedia.org/wiki/1950_Belgian_Grand_Prix'</example>
    FOREIGN KEY (year) REFERENCES seasons(year),
    FOREIGN KEY (circuitId) REFERENCES circuits(circuitId)
);

/*
Schema: NULLTable: results
Rows: 23657
Sample rows:
| resultId   | raceId   | driverId   | constructorId   | number   | grid   | position   | positionText   | positionOrder   | points   | laps   | time        | milliseconds   | fastestLap   | rank   | fastestLapTime   | fastestLapSpeed   | statusId   |
|------------|----------|------------|-----------------|----------|--------|------------|----------------|-----------------|----------|--------|-------------|----------------|--------------|--------|------------------|-------------------|------------|
| 1          | 18       | 1          | 1               | 22       | 1      | 1.0        | 1              | 1               | 10.0     | 58     | 1:34:50.616 | 5690616.0      | 39           | 2      | 1:27.452         | 218.300           | 1          |
| 2          | 18       | 2          | 2               | 3        | 5      | 2.0        | 2              | 2               | 8.0      | 58     | +5.478      | 5696094.0      | 41           | 3      | 1:27.739         | 217.586           | 1          |
| 3          | 18       | 3          | 3               | 7        | 7      | 3.0        | 3              | 3               | 6.0      | 58     | +8.163      | 5698779.0      | 41           | 5      | 1:28.090         | 216.719           | 1          |
| 4          | 18       | 4          | 4               | 5        | 11     | 4.0        | 4              | 4               | 5.0      | 58     | +17.181     | 5707797.0      | 58           | 7      | 1:28.603         | 215.464           | 1          |
| 5          | 18       | 5          | 1               | 23       | 3      | 5.0        | 5              | 5               | 4.0      | 58     | +18.014     | 5708630.0      | 43           | 1      | 1:27.418         | 218.385           | 1          |
| ...        | ...      | ...        | ...             | ...      | ...    | ...        | ...            | ...             | ...      | ...    | ...         | ...            | ...          | ...    | ...              | ...               | ...        |
*/
CREATE TABLE results (
    resultId INTEGER NOT NULL PRIMARY KEY,
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

/*
Schema: NULLTable: seasons
Rows: 68
Sample rows:
| year   | url                                                  |
|--------|------------------------------------------------------|
| 1950   | http://en.wikipedia.org/wiki/1950_Formula_One_season |
| 1951   | http://en.wikipedia.org/wiki/1951_Formula_One_season |
| 1952   | http://en.wikipedia.org/wiki/1952_Formula_One_season |
| 1953   | http://en.wikipedia.org/wiki/1953_Formula_One_season |
| 1954   | http://en.wikipedia.org/wiki/1954_Formula_One_season |
| ...    | ...                                                  |
*/
CREATE TABLE seasons (
    year INTEGER NOT NULL PRIMARY KEY,
        -- <example>1950</example>
    url TEXT NOT NULL
        -- <example>'http://en.wikipedia.org/wiki/1950_Formula_One_season'</example>
);

/*
Schema: NULLTable: status
Rows: 134
Sample rows:
| statusId   | status       |
|------------|--------------|
| 1          | Finished     |
| 2          | Disqualified |
| 3          | Accident     |
| 4          | Collision    |
| 5          | Engine       |
| ...        | ...          |
*/
CREATE TABLE status (
    statusId INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    status TEXT NOT NULL
        -- <example>'Finished'</example>
);
```