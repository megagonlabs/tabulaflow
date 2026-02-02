```sql
-- Database: formula_1

-- Table: circuits (72 rows)
CREATE TABLE circuits (
    circuitId INTEGER NULL PRIMARY KEY,
        -- <description>Circuit identifier — unique ID for each circuit record.</description>
        -- <example>23</example>
    circuitRef TEXT NOT NULL,
        -- <description>Circuit reference (short slug) — a compact, human-readable identifier used for each circuit (commonly a short name/slug). All 72 rows are populated and values are distinct, so this column effectively serves as a unique short label for circuits.</description>
        -- <example>'sepang'</example>
    name TEXT NOT NULL,
        -- <description>Full circuit name (official venue name of the racing circuit, e.g., 'Sepang International Circuit').</description>
        -- <example>'Sepang International Circuit'</example>
    location TEXT NULL,
        -- <description>Circuit location — the city or locality where the circuit is situated (typically a town/city name, e.g. Kuala Lumpur, Montmeló, Hockenheim).</description>
        -- <example>'Kuala Lumpur'</example>
    country TEXT NULL,
        -- <description>Circuit country — the country where the circuit is located.</description>
        -- <example>'Malaysia'</example>
    lat REAL NULL,
        -- <description>Circuit latitude (decimal degrees) — geographic latitude of the circuit’s location; positive values indicate north, negative indicate south. Current data range ≈ -34.9272 to 57.2653 with no missing values in this dataset.</description>
        -- <example>2.761</example>
    lng REAL NULL,
        -- <description>Circuit longitude — the geographic east/west coordinate for the circuit location, paired with lat (coordinates expressed as (lat, lng)).</description>
        -- <example>101.738</example>
    url TEXT NOT NULL
        -- <description>Wikipedia article URL for the circuit — link to the circuit's Wikipedia page (one URL provided for each circuit).</description>
        -- <example>'http://en.wikipedia.org/wiki/A1-Ring'</example>
);

-- Table: constructorResults (11082 rows)
CREATE TABLE constructorResults (
    constructorResultsId INTEGER NULL PRIMARY KEY,
        -- <description>Constructor result record identifier (primary key).</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race identifier — indicates which race this constructor result record refers to (identifies the race the constructor result belongs to).</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    constructorId INTEGER NOT NULL,
        -- <description>Constructor reference linking each constructorResults row to the corresponding constructors table record—identifies which constructor the result belongs to.</description>
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    points REAL NULL,
        -- <description>Constructor points awarded for the race — the number of championship points the constructor earned at that event (often 0; can include fractional values).</description>
        -- <example>14.000</example>
    status TEXT NULL,
        -- <description>Constructor race status code indicating the constructor's outcome in that race (mostly unused).</description>
        -- <values>{'D'}</values>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- Table: constructorStandings (11836 rows)
CREATE TABLE constructorStandings (
    constructorStandingsId INTEGER NULL PRIMARY KEY,
        -- <description>Constructor standings record identifier.</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race identifier for which these constructor-standings record applies. Always populated; appears in 11,836 records covering 906 distinct race IDs (range 1–982).</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    constructorId INTEGER NOT NULL,
        -- <description>Constructor identifier for the standing record — the constructor referenced by this row (links to constructors.constructorId).</description>
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    points REAL NOT NULL,
        -- <description>Constructor's points awarded for that race toward the season standings (cumulative scoring for the constructor).</description>
        -- <example>14.000</example>
    position INTEGER NULL,
        -- <description>Constructor's rank in the championship standings after the race.</description>
        -- <example>1</example>
    positionText TEXT NULL,
        -- <description>Constructor standings position as text — textual duplicate of position, mostly the same numeric values but occasionally uses non‑numeric flags (e.g. 'E'); largely redundant and not very useful.</description>
        -- <example>'1'</example>
    wins INTEGER NOT NULL,
        -- <description>Constructor season wins — count of race victories the constructor has earned in the season (accumulated up to this standing).</description>
        -- <example>1</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- Table: constructors (208 rows)
CREATE TABLE constructors (
    constructorId INTEGER NULL PRIMARY KEY,
        -- <description>Constructor identifier — unique identifier for each constructor in the dataset.</description>
        -- <example>147</example>
    constructorRef TEXT NOT NULL,
        -- <description>Constructor reference — short, stable identifier (slug) for a constructor used as a compact name for lookups, display, and URLs.</description>
        -- <example>'mclaren'</example>
    name TEXT NOT NULL,
        -- <description>Constructor full name — the official/team name used to identify each constructor.</description>
        -- <example>'AFM'</example>
    nationality TEXT NULL,
        -- <description>Constructor nationality — the country or national identity associated with each constructor (populated for all rows; no NULLs).</description>
        -- <example>'British'</example>
    url TEXT NOT NULL
        -- <description>Constructor page URL (typically a Wikipedia link to the constructor's article)</description>
        -- <example>'http://en.wikipedia.org/wiki/McLaren'</example>
);

-- Table: driverStandings (31578 rows)
CREATE TABLE driverStandings (
    driverStandingsId INTEGER NULL PRIMARY KEY,
        -- <description>Driver standings record identifier — unique identifier for each row in the driverStandings table.</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race identifier — foreign key referencing races.raceId that associates this driver-standings record with a specific race.</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <description>Driver identifier for the standing record — assigns each row to a specific driver.</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    points REAL NOT NULL,
        -- <description>Driver championship points — the points total recorded for the driver at this standings entry (typically the cumulative championship points awarded up to the referenced race).</description>
        -- <example>10.000</example>
    position INTEGER NULL,
        -- <description>Driver's championship rank after the referenced race (1 = top of the standings).</description>
        -- <example>1</example>
    positionText TEXT NULL,
        -- <description>Textual finishing position or short status code — typically a text duplicate of the numeric ‘position’ but occasionally contains non‑numeric codes (e.g. 'D'), so it is usually redundant and retained for compatibility.</description>
        -- <example>'1'</example>
    wins INTEGER NOT NULL,
        -- <description>Cumulative season wins for the driver — the number of races the driver has won in that season as recorded in this standings entry (i.e., up to the associated race).</description>
        -- <example>1</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

-- Table: drivers (840 rows)
CREATE TABLE drivers (
    driverId INTEGER NULL PRIMARY KEY,
        -- <description>Driver identifier — the table's primary key used to reference drivers from other tables (foreign-key target).</description>
        -- <example>452</example>
    driverRef TEXT NOT NULL,
        -- <description>driver reference name — a short, human-friendly identifier (slug) for a driver used as a stable reference (e.g., 'hamilton', 'kubica').</description>
        -- <example>'hamilton'</example>
    number INTEGER NULL,
        -- <description>racing number assigned to a driver (the car number displayed during events); only a small subset of rows have values — 36 distinct numbers found across 840 drivers (most rows are null).</description>
        -- <example>44</example>
    code TEXT NULL,
        -- <description>Driver three-letter abbreviation used as a short identifier (e.g., HAM, VET). Many drivers do not have a code — 83 non-null values across 840 rows (80 distinct codes). Null or empty means no assigned code.</description>
        -- <example>'HAM'</example>
    forename TEXT NOT NULL,
        -- <description>Driver's given (first) name — the personal forename used with the surname to identify each driver.</description>
        -- <example>'Lewis'</example>
    surname TEXT NOT NULL,
        -- <description>Driver's surname (family name) — the family name of the driver; populated for all 840 drivers (0 empty) with 784 distinct values (examples: Hamilton, Heidfeld, Rosberg).</description>
        -- <example>'Hamilton'</example>
    dob DATE NULL,
        -- <description>driver's date of birth — birth date for each driver; mostly populated (840 rows, 1 NULL) with values ranging from 1896-12-28 to 1998-10-29.</description>
        -- <example>'1985-01-07'</example>
    nationality TEXT NULL,
        -- <description>Driver nationality — the driver's country or national identity; populated for all 840 drivers with 41 distinct values.</description>
        -- <example>'British'</example>
    url TEXT NOT NULL
        -- <description>Driver profile URL — link to a web page (typically a Wikipedia biography) for the driver; nearly all rows are populated and values are unique.</description>
        -- <example>''</example>
);

-- Table: lapTimes (420369 rows)
CREATE TABLE lapTimes (
    raceId INTEGER NOT NULL,
        -- <description>Race identifier linking each lap-time record to the race it belongs to (covers 389 distinct races in this table).</description>
        -- <example>1</example>
        -- <fk> -> races.raceId</fk>
        -- <fk>composite</fk>
    driverId INTEGER NOT NULL,
        -- <description>Driver identifier linking each lap time to the drivers table (foreign key to drivers.driverId); part of the lapTimes composite primary key and contains no nulls.</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
        -- <fk>composite</fk>
    lap INTEGER NOT NULL,
        -- <description>Lap number within a race — the sequential lap index for each recorded lap (observed values range from 1 to 78); contains no nulls.</description>
        -- <example>1</example>
    position INTEGER NULL,
        -- <description>Driver's on-track position for the recorded lap — the driver's placement on track at that lap (a per‑lap snapshot, not the final race finishing position).</description>
        -- <example>13</example>
    time TEXT NULL,
        -- <description>Lap time — the driver's elapsed time for a single lap, recorded as a string in M:SS.mmm (minutes:seconds.milliseconds) format.</description>
        -- <example>'1:49.088'</example>
    milliseconds INTEGER NULL,
        -- <description>Lap time for a single lap, measured in milliseconds — precise per-lap timing used for performance comparisons and calculations. Complete column with no nulls; observed values range roughly from 67,411 to 7,507,550 ms.</description>
        -- <example>109088</example>
    PRIMARY KEY (raceId, driverId, lap),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (raceId, driverId) REFERENCES driverStandings(raceId, driverId)
);

-- Table: pitStops (6070 rows)
CREATE TABLE pitStops (
    raceId INTEGER NOT NULL,
        -- <description>Race identifier indicating which race this pit stop belongs to.</description>
        -- <example>841</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <description>Driver identifier for the pit stop — identifies which driver made the stop; populated for all 6,070 rows (54 distinct drivers).</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    stop INTEGER NOT NULL,
        -- <description>Pit stop sequence number for a driver in a race — increments (1, 2, ...) each time the driver stops; unique per race and driver. Observed values range from 1 to 6 with no missing values.</description>
        -- <example>1</example>
    lap INTEGER NOT NULL,
        -- <description>Pit stop lap number — the race lap on which the pit stop occurred (dataset values range 1–74; no missing values).</description>
        -- <example>16</example>
    time TEXT NOT NULL,
        -- <description>Pit stop clock time (HH:MM:SS) — the session wall‑clock time of day when the pit stop occurred.</description>
        -- <example>'17:28:24'</example>
    duration TEXT NULL,
        -- <description>Pit stop duration — elapsed time of the pit stop measured in seconds (decimal seconds, e.g. 23.227); used to compare and analyze pit stop performance. Contains values for all rows (no NULLs) with ~4,713 distinct durations across 6,070 records.</description>
        -- <example>'23.227'</example>
    milliseconds INTEGER NULL,
        -- <description>Pit stop duration (time taken to complete the pit stop), recorded in milliseconds.</description>
        -- <example>23227</example>
    PRIMARY KEY (raceId, driverId, stop),
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId)
);

-- Table: qualifying (7397 rows)
CREATE TABLE qualifying (
    qualifyId INTEGER NULL PRIMARY KEY,
        -- <description>Qualifying record identifier — unique primary key for each row in the qualifying table (identifies individual qualifying session entries).</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race identifier linking each qualifying record to the races table (FK -> races.raceId); non-null and fully referentially valid.</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
    driverId INTEGER NOT NULL,
        -- <description>Qualifying driver identifier (FK to drivers.driverId) indicating which driver recorded the qualifying times.</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
    constructorId INTEGER NOT NULL,
        -- <description>Constructor identifier for the qualifying entry — identifies which constructor took part in the qualifying session (references constructors table). All 7,397 rows are populated, referencing 41 distinct constructors.</description>
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    number INTEGER NOT NULL,
        -- <description>driver's race/car number for that qualifying entry (the number displayed on the driver's car during the event).</description>
        -- <example>22</example>
    position INTEGER NULL,
        -- <description>Qualifying finishing position — the driver's final rank in that qualifying session (used to determine starting grid order for the race).</description>
        -- <example>1</example>
    q1 TEXT NULL,
        -- <description>Q1 lap time from the first qualifying segment (Q1) — the driver’s best lap recorded in Q1, formatted as minutes:seconds.milliseconds (e.g. '1:22.677'). NULL when no time was set (117 of 7,397 rows).</description>
        -- <example>'1:26.572'</example>
    q2 TEXT NULL,
        -- <description>Qualifying 2 lap time — the driver's best lap time recorded in the second qualifying phase (Q2), expressed as a time string (e.g., "1:25.187"); typically populated only for drivers who advanced to Q2 and used to determine progression to Q3.</description>
        -- <example>'1:25.187'</example>
    q3 TEXT NULL,
        -- <description>Q3 qualifying lap time — the driver's best lap recorded in Q3 (formatted like m:ss.mmm). Populated only for drivers who advanced to Q3 (typically the top 10 in Q2); many rows are NULL (about 29% populated in this dataset).</description>
        -- <example>'1:26.714'</example>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId)
);

-- Table: races (976 rows)
CREATE TABLE races (
    raceId INTEGER NULL PRIMARY KEY,
        -- <description>Race identifier — unique identifier for each race in the races table.</description>
        -- <example>837</example>
    year INTEGER NOT NULL,
        -- <description>Race year — the calendar year in which the event (race) took place.</description>
        -- <example>2009</example>
        -- <fk> -> seasons.year</fk>
    round INTEGER NOT NULL,
        -- <description>Season round number — the race's sequential round within its Formula 1 season (values in this dataset range from 1 to 21; no nulls).</description>
        -- <example>1</example>
    circuitId INTEGER NOT NULL,
        -- <description>Circuit reference linking each race to its hosting circuit (foreign key to circuits.circuitId). All 976 races have a value; it maps to 72 distinct circuits, though 22 rows reference circuit IDs not present in the circuits table.</description>
        -- <example>1</example>
        -- <fk> -> circuits.circuitId</fk>
    name TEXT NOT NULL,
        -- <description>race name — official title of the Grand Prix event held on that date (e.g., “Australian Grand Prix”); identifies the named event for the race.</description>
        -- <example>'Australian Grand Prix'</example>
    date DATE NOT NULL,
        -- <description>Race date — the calendar date on which the race was held.</description>
        -- <example>'2009-03-29'</example>
    time TEXT NULL,
        -- <description>Race start time (local scheduled time of day); many rows are missing and a small set of common placeholder times appear in the populated records.</description>
        -- <example>'06:00:00'</example>
    url TEXT NULL,
        -- <description>Race webpage URL — link to an online page (typically the race's Wikipedia article) with background and details about the specific Grand Prix.</description>
        -- <example>'http://en.wikipedia.org/wiki/1950_Belgian_Grand_Prix'</example>
    FOREIGN KEY (year) REFERENCES seasons(year),
    FOREIGN KEY (circuitId) REFERENCES circuits(circuitId)
);

-- Table: results (23657 rows)
CREATE TABLE results (
    resultId INTEGER NULL PRIMARY KEY,
        -- <description>Result identifier for a race result record (primary key of the results table).</description>
        -- <example>1</example>
    raceId INTEGER NOT NULL,
        -- <description>Race reference — foreign key to races.raceId identifying which race this result record belongs to; non‑null and references existing races (no orphaned raceId values).</description>
        -- <example>18</example>
        -- <fk> -> races.raceId</fk>
        -- <fk>composite</fk>
    driverId INTEGER NOT NULL,
        -- <description>Driver identifier linking this result row to the corresponding driver (references drivers.driverId). Always populated in the dataset (no NULL values).</description>
        -- <example>1</example>
        -- <fk> -> drivers.driverId</fk>
        -- <fk>composite</fk>
    constructorId INTEGER NOT NULL,
        -- <description>Constructor identifier linking a race result to its constructor (references the constructors table).</description>
        -- <example>1</example>
        -- <fk> -> constructors.constructorId</fk>
    number INTEGER NULL,
        -- <description>Driver racing (car) number assigned for that result — the number displayed on the car for the driver in that event. May be null (6 rows) or 0 for some records; historical driver permanent numbers are often missing in drivers.number, so results.number does not always match drivers.number.</description>
        -- <example>22</example>
    grid INTEGER NOT NULL,
        -- <description>Driver starting grid position for the race (starting slot on the grid). Contains 0 for special cases (see note). No NULLs; observed values range 0–34.</description>
        -- <example>1</example>
    position INTEGER NULL,
        -- <description>Finishing position of the driver in the race — the official finishing place (1 = winner). Many rows are NULL (10,528 of 23,657), typically when no official finishing position was recorded (e.g., retired, disqualified or otherwise not classified). Observed values range from 1 to 33.</description>
        -- <example>1</example>
    positionText TEXT NOT NULL,
        -- <description>textual finishing position or outcome code — a text field that duplicates numeric 'position' for finishing drivers and stores short outcome codes (e.g. 'R' for retired, 'F' for failure) for non-finishers; largely redundant with the 'position' column.</description>
        -- <example>'1'</example>
    positionOrder INTEGER NOT NULL,
        -- <description>Sequential finishing rank for the race (1 = winner), used to order the final classification.</description>
        -- <example>1</example>
    points REAL NOT NULL,
        -- <description>Race result points — the championship points awarded to a driver for that race (used to compute season standings). Dataset contains 33 distinct point totals ranging from 0 to 50; 0 is the most common value (17,037 of 23,657 records).</description>
        -- <example>10.000</example>
    laps INTEGER NOT NULL,
        -- <description>Number of laps completed by the driver in the race (total laps the driver completed; 0 indicates no laps completed).</description>
        -- <example>58</example>
    time TEXT NULL,
        -- <description>Race finish time or finishing gap to the winner — stores either a driver's absolute finishing time (winner) or a time delta relative to the winner prefixed with '+'. Null when not recorded.</description>
        -- <example>'1:34:50.616'</example>
    milliseconds INTEGER NULL,
        -- <description>Finish time for the result, expressed in milliseconds — the driver's actual race time when available; null when a precise finishing time isn't recorded (e.g., retirements or only a gap is given). Present in ~25% of rows (5,960 non-null values, 5,923 distinct); values range ≈1,474,900 ms (≈24m35s) to ≈15,090,500 ms (≈4h11m), mean ≈6,308,770 ms (≈1h45m). Useful for exact time calculations and comparing/converting the textual time/gap fields.</description>
        -- <example>5690616</example>
    fastestLap INTEGER NULL,
        -- <description>Fastest lap number for the driver in that race — the lap index of the driver's quickest lap (used with raceId and driverId to reference lapTimes.(raceId, driverId, lap)). Null when no fastest-lap is recorded.</description>
        -- <example>39</example>
        -- <fk>composite</fk>
    rank INTEGER NULL,
        -- <description>Driver's fastest-lap rank (position ordered by fastest-lap speed). Recorded for a minority of results (~22.9% present); values observed range 0–24, otherwise null.</description>
        -- <example>2</example>
    fastestLapTime TEXT NULL,
        -- <description>Fastest lap time recorded by the driver in that race (lap time string in minutes:seconds.milliseconds); lower values indicate a faster lap.</description>
        -- <example>'1:27.452'</example>
    fastestLapSpeed TEXT NULL,
        -- <description>Fastest lap speed (km/h) — the speed recorded for the driver's fastest lap in this result, expressed in kilometres per hour; many rows are blank (5,268 of 23,657 rows populated), observed range ≈89.54–257.32 km/h (mean ≈200.69 km/h).</description>
        -- <example>'218.300'</example>
    statusId INTEGER NOT NULL,
        -- <description>Result status reference (foreign key to status table) indicating how the driver finished or why they retired — the finishing classification/reason (e.g., "Finished", "+1 Lap", "Engine"). Contains no nulls and maps to many distinct status codes.</description>
        -- <example>1</example>
        -- <fk> -> status.statusId</fk>
    FOREIGN KEY (raceId) REFERENCES races(raceId),
    FOREIGN KEY (driverId) REFERENCES drivers(driverId),
    FOREIGN KEY (constructorId) REFERENCES constructors(constructorId),
    FOREIGN KEY (statusId) REFERENCES status(statusId),
    FOREIGN KEY (raceId, driverId, fastestLap) REFERENCES lapTimes(raceId, driverId, lap)
);

-- Table: seasons (68 rows)
CREATE TABLE seasons (
    year INTEGER NOT NULL PRIMARY KEY,
        -- <description>Season year — the calendar year that identifies a Formula 1 championship season (one row per year).</description>
        -- <example>1950</example>
    url TEXT NOT NULL
        -- <description>Season Wikipedia page URL — link to the Wikipedia article for that year's Formula 1 season.</description>
        -- <example>'http://en.wikipedia.org/wiki/1950_Formula_One_season'</example>
);

-- Table: status (134 rows)
CREATE TABLE status (
    statusId INTEGER NULL PRIMARY KEY,
        -- <description>Status identifier — primary key for the status table that maps numeric IDs to human-readable race-status descriptions and is referenced by results.statusId.</description>
        -- <example>1</example>
    status TEXT NOT NULL
        -- <description>Race result status label — human-readable outcome or reason describing how a driver’s result was recorded (e.g. 'Finished', '+11 Laps', 'Power loss', 'Water leak').</description>
        -- <example>'Finished'</example>
);
```