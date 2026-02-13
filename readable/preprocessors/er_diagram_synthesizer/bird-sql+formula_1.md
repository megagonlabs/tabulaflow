```mermaid
erDiagram
    Race {
        table races "Core race metadata: season year, round, circuit link, name, date/time, and reference URL."
    }
    Driver {
        table drivers "Core driver identity and demographics: code/number, name, DOB, nationality, and URL."
    }
    Constructor {
        table constructors "Core constructor/team identity: reference key, name, nationality, and URL."
    }
    Circuit {
        table circuits "Venue details including location, country, latitude/longitude, altitude, and URL."
    }
    Season {
        table seasons "Season reference by year and URL."
    }
    RaceResult {
        table results "Per-race, per-driver result with grid/finish data, timing metrics, points, and status reference."
    }
    QualifyingSessionResult {
        table qualifying "Per-race qualifying entry with driver/constructor, position, and Q1/Q2/Q3 times."
    }
    LapTime {
        table lapTimes "Per-lap timing and position for a driver in a race (composite PK: raceId, driverId, lap)."
    }
    PitStop {
        table pitStops "Per-stop timing for a driver in a race (composite PK: raceId, driverId, stop)."
    }
    DriverStanding {
        table driverStandings "Per-race cumulative driver standings with points, position, positionText, and wins."
    }
    ConstructorStanding {
        table constructorStandings "Per-race cumulative constructor standings with points, position, positionText, and wins."
    }
    ConstructorRaceResult {
        table constructorResults "Per-race constructor result/points and optional status text."
    }
    Status {
        table status "Lookup of race result statuses."
    }

    %% FROM races r JOIN seasons s ON r.year = s.year
    Season |o--|{ Race : "RaceInSeason"

    %% FROM races r JOIN circuits c ON r.circuitId = c.circuitId
    Circuit |o--|{ Race : "RaceAtCircuit"

    %% FROM races ra JOIN results rr ON rr.raceId = ra.raceId
    Race |o--|{ RaceResult : "RaceHasRaceResults"

    %% FROM drivers d JOIN results rr ON rr.driverId = d.driverId
    Driver |o--|{ RaceResult : "DriverHasRaceResults"

    %% FROM constructors c JOIN results rr ON rr.constructorId = c.constructorId
    Constructor |o--|{ RaceResult : "ConstructorHasRaceResults"

    %% FROM results rr JOIN status s ON rr.statusId = s.statusId
    RaceResult }|--o| Status : "RaceResultHasStatus"

    %% FROM races r JOIN lapTimes lt ON lt.raceId = r.raceId
    Race |o--|{ LapTime : "RaceHasLapTimes"

    %% FROM drivers d JOIN lapTimes lt ON lt.driverId = d.driverId
    Driver |o--|{ LapTime : "DriverHasLapTimes"

    %% FROM races r JOIN pitStops ps ON ps.raceId = r.raceId
    Race |o--|{ PitStop : "RaceHasPitStops"

    %% FROM drivers d JOIN pitStops ps ON ps.driverId = d.driverId
    Driver |o--|{ PitStop : "DriverHasPitStops"

    %% FROM races r JOIN qualifying q ON q.raceId = r.raceId
    Race |o--|{ QualifyingSessionResult : "RaceHasQualifyingResults"

    %% FROM drivers d JOIN qualifying q ON q.driverId = d.driverId
    Driver |o--|{ QualifyingSessionResult : "DriverHasQualifyingResults"

    %% FROM constructors c JOIN qualifying q ON q.constructorId = c.constructorId
    Constructor |o--|{ QualifyingSessionResult : "ConstructorHasQualifyingResults"

    %% FROM races r JOIN driverStandings ds ON ds.raceId = r.raceId
    Race |o--|{ DriverStanding : "RaceHasDriverStandings"

    %% FROM drivers d JOIN driverStandings ds ON ds.driverId = d.driverId
    Driver |o--|{ DriverStanding : "DriverHasDriverStandings"

    %% FROM races r JOIN constructorStandings cs ON cs.raceId = r.raceId
    Race |o--|{ ConstructorStanding : "RaceHasConstructorStandings"

    %% FROM constructors c JOIN constructorStandings cs ON cs.constructorId = c.constructorId
    Constructor |o--|{ ConstructorStanding : "ConstructorHasConstructorStandings"

    %% FROM races r JOIN constructorResults cr ON cr.raceId = r.raceId
    Race |o--|{ ConstructorRaceResult : "RaceHasConstructorRaceResults"

    %% FROM constructors c JOIN constructorResults cr ON cr.constructorId = c.constructorId
    Constructor |o--|{ ConstructorRaceResult : "ConstructorHasConstructorRaceResults"
```