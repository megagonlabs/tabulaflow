```sql
-- Database: formula_1

/*
Table: circuits
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
        -- <description>Unique identifier for a circuit.</description>
        -- <example>23</example>
    circuitRef TEXT NOT NULL,
        -- <description>Short reference name for the circuit — a compact, human-friendly identifier used to refer to the circuit (e.g., 'sepang', 'bahrain').</description>
        -- <example>'sepang'</example>
    name TEXT NOT NULL,
        -- <description>Official full name of the circuit (e.g., 'Sepang International Circuit').</description>
        -- <example>'Sepang International Circuit'</example>
    location TEXT NOT NULL,
        -- <description>Circuit location — the city, town, or locality where the circuit is situated.</description>
        -- <example>'Kuala Lumpur'</example>
    country TEXT NOT NULL,
        -- <description>Country where the circuit is located.</description>
        -- <example>'Malaysia'</example>
    lat REAL NOT NULL,
        -- <description>Circuit latitude — decimal degrees (positive = north, negative = south); pairs with lng to define the circuit's geographic coordinates.</description>
        -- <example>2.761</example>
    lng REAL NOT NULL,
        -- <description>Circuit longitude — the geographic east–west coordinate of the circuit's location, used together with latitude to form the circuit's GPS coordinates.</description>
        -- <example>101.738</example>
    url TEXT NOT NULL
        -- <description>URL to the circuit's Wikipedia page (external reference with background and details about the circuit).</description>
        -- <example>'http://en.wikipedia.org/wiki/A1-Ring'</example>
);

/*
Table: constructorResults
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
        -- <description>Unique identifier for a constructor result record in the constructorResults table.</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race identifier linking a constructor result to a specific race (references races.raceId).</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    constructorId INTEGER NOT NULL,
        -- <description>Constructor identifier referencing the constructors table (foreign key linking this result to a constructor).</description>
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    points REAL NOT NULL,
        -- <description>Constructor points awarded for that race — the number of championship points earned by the constructor in the specific race.</description>
        -- <example>14.000</example>
    status TEXT NULL,
        -- <description>Constructor result status code indicating the constructor's outcome or condition in that race.</description>
        -- <values>{'D'}</values>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

/*
Table: constructorStandings
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
        -- <description>Constructor standings record identifier — unique id for each constructor's standings entry in the constructorStandings table.</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race identifier linking a constructor's standing record to a specific race in the races table (references races.raceId).</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    constructorId INTEGER NOT NULL,
        -- <description>Constructor identifier linking the standings row to the constructors table (foreign key).</description>
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    points REAL NOT NULL,
        -- <description>Constructor points awarded for the race.</description>
        -- <example>14.000</example>
    position INTEGER NOT NULL,
        -- <description>Constructor's rank in the season standings after the given race (1 = top position).</description>
        -- <example>1</example>
    wins INTEGER NOT NULL,
        -- <description>Constructor season wins — count of races the constructor has won for that season (the number of wins recorded in this standings entry).</description>
        -- <example>1</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

/*
Table: constructors
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
        -- <description>Unique constructor identifier for each constructor in the constructors table.</description>
        -- <example>147</example>
    constructorRef TEXT NOT NULL,
        -- <description>Constructor reference — short reference/slug identifying a constructor (e.g., 'mclaren', 'toro_rosso', 'fittipaldi').</description>
        -- <example>'mclaren'</example>
    name TEXT NOT NULL,
        -- <description>Constructor full name — the official or commonly used team name for the constructor, used for display and reporting.</description>
        -- <example>'AFM'</example>
    nationality TEXT NOT NULL,
        -- <description>Constructor nationality — the registered country or national identity of the constructor (team).</description>
        -- <example>'British'</example>
    url TEXT NOT NULL
        -- <description>URL of the constructor's information page (typically the constructor's Wikipedia article)</description>
        -- <example>'http://en.wikipedia.org/wiki/McLaren'</example>
);

/*
Table: driverStandings
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
        -- <description>Driver standings record identifier</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race identifier for the driver-standings record.</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <description>Driver identifier for the standings record (references the drivers table).</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    points REAL NOT NULL,
        -- <description>Driver championship points at this standings snapshot — the points total used to rank the driver after the referenced race.</description>
        -- <example>10.000</example>
    position INTEGER NOT NULL,
        -- <description>Driver championship position — the numeric rank of the driver in the season standings after the referenced race.</description>
        -- <example>1</example>
    wins INTEGER NOT NULL,
        -- <description>Driver season win count — cumulative number of race wins credited to the driver in that season as of the standings record.</description>
        -- <example>1</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

/*
Table: drivers
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
        -- <description>Unique driver identifier used to link a driver record to related tables (e.g., results, lapTimes, pitStops, qualifying, driverStandings).</description>
        -- <example>452</example>
    driverRef TEXT NOT NULL,
        -- <description>Driver reference — short, human-readable identifier for a driver used as a stable reference within the dataset (e.g., 'hamilton').</description>
        -- <example>'hamilton'</example>
    number INTEGER NULL,
        -- <description>Driver race number (the car number assigned to a driver for race entries), used to identify the driver’s car on timing and entry lists; may be null for drivers without an assigned number (historical or one-off entries).</description>
        -- <example>44</example>
    code TEXT NULL,
        -- <description>Driver abbreviation code — a short uppercase identifier (typically three letters) used to represent a driver (may be NULL when no code is assigned).</description>
        -- <example>'HAM'</example>
    forename TEXT NOT NULL,
        -- <description>Driver's given (first) name — the personal forename used with the surname to identify a driver.</description>
        -- <example>'Lewis'</example>
    surname TEXT NOT NULL,
        -- <description>Driver's family name (surname), i.e., the driver's last name used to identify the driver.</description>
        -- <example>'Hamilton'</example>
    dob DATE NULL,
        -- <description>Driver's date of birth — the driver's birth date, used to compute age and career timelines; may be NULL when unknown.</description>
        -- <example>'1985-01-07'</example>
    nationality TEXT NOT NULL,
        -- <description>Driver nationality — the country or national identity associated with a driver (e.g., British, German, Brazilian).</description>
        -- <example>'British'</example>
    url TEXT NOT NULL
        -- <description>Driver biography page URL (external link to the driver's profile, typically a Wikipedia page)</description>
        -- <example>''</example>
);

/*
Table: lapTimes
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
        -- <description>Race identifier linking each lap-time row to its race in the races table (foreign key to races.raceId).</description>
        -- <example>1</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <description>Driver identifier linking each recorded lap to a driver (references drivers.driverId); part of the lapTimes composite primary key (raceId, driverId, lap).</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    lap INTEGER NOT NULL,
        -- <description>Lap number within a race (sequential lap index starting at 1).</description>
        -- <example>1</example>
    position INTEGER NOT NULL,
        -- <description>Driver's race position at the end of the lap</description>
        -- <example>13</example>
    time TEXT NOT NULL,
        -- <description>Lap time — the time taken by a driver to complete a lap, formatted as minutes:seconds.milliseconds (e.g., '1:30.615').</description>
        -- <example>'1:49.088'</example>
    milliseconds INTEGER NOT NULL,
        -- <description>Lap duration in milliseconds for the given race/driver/lap — a precise numeric measure of the lap time.</description>
        -- <example>109088</example>
    PRIMARY KEY (raceId, driverId, lap),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

/*
Table: pitStops
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
        -- <description>Race identifier for the pit stop — references races.raceId and is part of the pitStops composite primary key (raceId, driverId, stop).</description>
        -- <example>841</example>
        -- <fk> -> races.raceId</fk>
        -- <fk>composite</fk>
    driverId INTEGER NOT NULL,
        -- <description>Driver identifier for the pit stop record, indicating which driver made the stop (references drivers.driverId).</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
        -- <fk>composite</fk>
    stop INTEGER NOT NULL,
        -- <description>Pit stop sequence number — the ordinal (1, 2, ...) of a driver's pit stop during a race.</description>
        -- <example>1</example>
    lap INTEGER NOT NULL,
        -- <description>Lap number on which the pit stop occurred during the race.</description>
        -- <example>16</example>
        -- <fk>composite</fk>
    time TEXT NOT NULL,
        -- <description>Pit stop clock time (wall‑clock time of day when the stop occurred), recorded as HH:MM:SS (e.g. 17:28:24).</description>
        -- <example>'17:28:24'</example>
    duration TEXT NOT NULL,
        -- <description>Pit stop duration in seconds (allowing fractional seconds)</description>
        -- <example>'23.227'</example>
    milliseconds INTEGER NOT NULL,
        -- <description>Pit stop duration measured in milliseconds.</description>
        -- <example>23227</example>
    PRIMARY KEY (raceId, driverId, stop),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (raceId, driverId, lap) REFERENCES lapTimes(raceId, driverId, lap)
);

/*
Table: qualifying
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
        -- <description>Qualifying entry identifier — unique identifier for each row in the qualifying table (one record per driver's qualifying result).</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race identifier for the qualifying session, linking this qualifying record to a specific race in the races table.</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <description>Driver identifier linking each qualifying record to a driver (foreign key → drivers.driverId).</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    constructorId INTEGER NOT NULL,
        -- <description>Constructor identifier for the qualifying entry — identifies the constructor the driver was representing in that qualifying session (references constructors.constructorId).</description>
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    number INTEGER NOT NULL,
        -- <description>Driver car number used for this qualifying entry (the number displayed on the driver's car).</description>
        -- <example>22</example>
    position INTEGER NOT NULL,
        -- <description>Qualifying position on the session’s results (starting grid order); 1 indicates pole position.</description>
        -- <example>1</example>
    q1 TEXT NULL,
        -- <description>Q1 lap time — the driver's best lap recorded during the first qualifying period (Q1), used to help determine which drivers advance to the next qualifying round.</description>
        -- <example>'1:26.572'</example>
    q2 TEXT NULL,
        -- <description>Qualifying 2 lap time — the driver's lap time posted in the second qualifying segment (Q2); null when the driver did not record a Q2 time (e.g., eliminated in Q1 or did not run).</description>
        -- <example>'1:25.187'</example>
    q3 TEXT NULL,
        -- <description>Qualifying 3 lap time — the driver’s best lap in Q3 (only recorded for drivers who reached Q3; typically the top 10 from Q2), given in minutes:seconds.milliseconds (e.g. '1:26.714').</description>
        -- <example>'1:26.714'</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

/*
Table: races
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
        -- <description>Race identifier — the unique id for a specific Grand Prix event, used to link race records across the dataset (referenced by results, lapTimes, pitStops, qualifying, and standings tables).</description>
        -- <example>837</example>
    year INTEGER NOT NULL,
        -- <description>Race year — the calendar year when the race took place; links to the seasons table (seasons.year).</description>
        -- <example>2009</example>
        -- <fk> -> seasons.year</fk>
    round INTEGER NOT NULL,
        -- <description>Round number within the championship season indicating this race’s order in that year’s calendar.</description>
        -- <example>1</example>
    circuitId INTEGER NOT NULL,
        -- <description>Circuit identifier linking the race to the circuit where it was held (references circuits.circuitId).</description>
        -- <example>1</example>
        -- <fk> -> circuits.circuitId</fk>
    name TEXT NOT NULL,
        -- <description>Race name — the official event title for the race (for example, 'Australian Grand Prix').</description>
        -- <example>'Australian Grand Prix'</example>
    date DATE NOT NULL,
        -- <description>Race date — the calendar date on which the race took place.</description>
        -- <example>'2009-03-29'</example>
    time TEXT NULL,
        -- <description>Scheduled start time of the race (local time at the circuit).</description>
        -- <example>'06:00:00'</example>
    url TEXT NOT NULL,
        -- <description>Race URL — link to a web page describing the race (typically the race’s Wikipedia page).</description>
        -- <example>'http://en.wikipedia.org/wiki/1950_Belgian_Grand_Prix'</example>
    FOREIGN KEY (year) REFERENCES seasons(year),
    FOREIGN KEY (circuitId) REFERENCES circuits(circuitId)
);

/*
Table: results
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
        -- <description>Unique identifier for a single driver's result record in the results table.</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race identifier linking this result to the corresponding row in the races table (indicates which race the result belongs to).</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
        -- <fk>composite</fk>
    driverId INTEGER NOT NULL,
        -- <description>Driver identifier linking each result row to a driver in the drivers table.</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
        -- <fk>composite</fk>
    constructorId INTEGER NOT NULL,
        -- <description>Constructor identifier — the constructor (team) associated with this race result.</description>
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    number INTEGER NULL,
        -- <description>Car number identifying the driver's racing number for the event (the car identifier used to identify the competitor), distinct from finishing position; may be NULL if not assigned.</description>
        -- <example>22</example>
    grid INTEGER NOT NULL,
        -- <description>Starting grid position for the race — the driver's assigned starting slot on the grid (determined by qualifying); used to set the race start order.</description>
        -- <example>1</example>
    position INTEGER NULL,
        -- <description>Finishing position for the driver in that race — the reported numeric result (may be null when no numeric finishing position is recorded, e.g., retirements or disqualifications). Prefer positionOrder for a guaranteed numeric finishing order; positionText holds the original textual value.</description>
        -- <example>1</example>
    positionOrder INTEGER NOT NULL,
        -- <description>Final ranking order — the numeric sequence used to determine and sort competitors' finishing positions within a race (the canonical sort key for result rows).</description>
        -- <example>1</example>
    points REAL NOT NULL,
        -- <description>Points awarded to the driver for that race — the value credited toward the driver's championship total.</description>
        -- <example>10.000</example>
    laps INTEGER NOT NULL,
        -- <description>Total number of race laps completed by the driver for that result.</description>
        -- <example>58</example>
    time TEXT NULL,
        -- <description>Driver finish time for the race — the winner's total race time (e.g., 1:36:03.785) or, for other classified finishers, the time gap to the winner (e.g., +45.605). Null indicates no recorded finish time (e.g., retirement or disqualification).</description>
        -- <example>'1:34:50.616'</example>
    milliseconds INTEGER NULL,
        -- <description>Finishing time in milliseconds — the numeric equivalent of the result’s recorded finish time (the 'time' column), expressed in milliseconds for easy arithmetic and ranking; null when a precise finish time is not available.</description>
        -- <example>5690616</example>
    fastestLap INTEGER NULL,
        -- <description>Fastest lap number — the lap on which this driver recorded their quickest lap in the race; corresponds to lapTimes(raceId, driverId, lap) and may be NULL if a fastest lap isn't recorded.</description>
        -- <example>39</example>
        -- <fk>composite</fk>
    rank INTEGER NULL,
        -- <description>Fastest-lap rank — the driver's rank in the race determined by their fastest-lap time (lower numbers indicate a faster/better rank).</description>
        -- <example>2</example>
    fastestLapTime TEXT NULL,
        -- <description>Fastest lap time for the driver in the race — the driver's quickest lap, recorded as a lap-time string (e.g., '1:27.452'); smaller values indicate a faster lap and are used when determining fastest‑lap ranking.</description>
        -- <example>'1:27.452'</example>
    fastestLapSpeed TEXT NULL,
        -- <description>Fastest lap speed for the driver's quickest lap in the race (kilometres per hour).</description>
        -- <example>'218.300'</example>
    statusId INTEGER NOT NULL,
        -- <description>Result status reference linking each result to its outcome description in the status table (e.g., Finished, Accident, Engine).</description>
        -- <example>1</example>
        -- <fk> -> status.statusId</fk>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId),
    FOREIGN KEY (statusId) REFERENCES status(statusId),
    FOREIGN KEY (raceId, driverId, fastestLap) REFERENCES lapTimes(raceId, driverId, lap)
);

/*
Table: seasons
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
        -- <description>Season year — the calendar year of the Formula 1 season (e.g., 1950).</description>
        -- <example>1950</example>
    url TEXT NOT NULL
        -- <description>URL for the season's Wikipedia page</description>
        -- <example>'http://en.wikipedia.org/wiki/1950_Formula_One_season'</example>
);

/*
Table: status
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
        -- <description>Status identifier linking a status code to its human-readable label in the status lookup table (referenced by other tables such as results).</description>
        -- <example>1</example>
    status TEXT NOT NULL
        -- <description>Race outcome description — a human-readable status explaining how a competitor's result was recorded (e.g., 'Finished', '+11 Laps', 'Engine', 'Collision').</description>
        -- <example>'Finished'</example>
);
```