```mermaid
erDiagram
    Race {
        table races "Core race metadata and foreign keys to season (year) and circuit."
    }
    Driver {
        table drivers "Core driver attributes (reference, name, number/code, DOB, nationality, URL)."
    }
    Constructor {
        table constructors "Core constructor/team attributes (reference, name, nationality, URL)."
    }
    Season {
        table seasons "One row per championship year with reference URL."
    }
    Circuit {
        table circuits "Track identity, location, geo-coordinates, altitude, and URL."
    }
    Status {
        table status "Status ID and textual description of result outcome."
    }
    RaceResult {
        table results "Fact table keyed by resultId with FKs to race, driver, constructor, and status; includes timing, position, and points."
    }
    QualifyingAttempt {
        table qualifying "One row per driver–constructor entry in qualifying for a race; includes Q1–Q3 times and final position/number."
    }
    LapTime {
        table lapTimes "Composite PK (raceId, driverId, lap); lap order, positions, and timing in text/milliseconds."
    }
    PitStop {
        table pitStops "Composite PK (raceId, driverId, stop); lap, timestamp, and duration in text/milliseconds."
    }
    DriverStanding {
        table driverStandings "Fact table by (raceId, driverId) with points, position, wins; FK to races and drivers."
    }
    ConstructorStanding {
        table constructorStandings "Fact table by (raceId, constructorId) with points, position, wins; FK to races and constructors."
    }
    ConstructorResult {
        table constructorResults "Fact table by (raceId, constructorId) with points and textual status; FKs to races and constructors."
    }
    Season }o--|| Race : "SeasonHasRaces" %% FROM seasons s JOIN races r ON r.year = s.year
    Circuit }o--|| Race : "CircuitHostsRaces" %% FROM circuits c JOIN races r ON r.circuitId = c.circuitId
    Race }o--|| RaceResult : "RaceHasResults" %% FROM races r JOIN results res ON res.raceId = r.raceId
    Driver }o--|| RaceResult : "ResultInvolvesDriver" %% FROM drivers d JOIN results res ON res.driverId = d.driverId
    Constructor }o--|| RaceResult : "ResultInvolvesConstructor" %% FROM constructors c JOIN results res ON res.constructorId = c.constructorId
    RaceResult ||--o{ Status : "ResultHasStatus" %% FROM results res JOIN status st ON st.statusId = res.statusId
    Race }o--|| QualifyingAttempt : "RaceHasQualifyingAttempts" %% FROM races r JOIN qualifying q ON q.raceId = r.raceId
    Driver }o--|| QualifyingAttempt : "QualifyingInvolvesDriver" %% FROM drivers d JOIN qualifying q ON q.driverId = d.driverId
    Constructor }o--|| QualifyingAttempt : "QualifyingInvolvesConstructor" %% FROM constructors c JOIN qualifying q ON q.constructorId = c.constructorId
    Race }o--|| LapTime : "RaceHasLapTimes" %% FROM races r JOIN lapTimes lt ON lt.raceId = r.raceId
    Driver }o--|| LapTime : "LapTimeForDriver" %% FROM drivers d JOIN lapTimes lt ON lt.driverId = d.driverId
    Race }o--|| PitStop : "RaceHasPitStops" %% FROM races r JOIN pitStops ps ON ps.raceId = r.raceId
    Driver }o--|| PitStop : "PitStopForDriver" %% FROM drivers d JOIN pitStops ps ON ps.driverId = d.driverId
    Race }o--|| DriverStanding : "RaceHasDriverStandings" %% FROM races r JOIN driverStandings ds ON ds.raceId = r.raceId
    Driver }o--|| DriverStanding : "DriverHasStandings" %% FROM drivers d JOIN driverStandings ds ON ds.driverId = d.driverId
    Race }o--|| ConstructorStanding : "RaceHasConstructorStandings" %% FROM races r JOIN constructorStandings cs ON cs.raceId = r.raceId
    Constructor }o--|| ConstructorStanding : "ConstructorHasStandings" %% FROM constructors c JOIN constructorStandings cs ON cs.constructorId = c.constructorId
    Race }o--|| ConstructorResult : "RaceHasConstructorResults" %% FROM races r JOIN constructorResults cr ON cr.raceId = r.raceId
    Constructor }o--|| ConstructorResult : "ConstructorHasConstructorResults" %% FROM constructors c JOIN constructorResults cr ON cr.constructorId = c.constructorId
```