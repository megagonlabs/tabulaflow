```sql
-- Database: european_football_1

-- Table: divisions (21 rows)
CREATE TABLE divisions (
    division TEXT NOT NULL PRIMARY KEY,  -- e.g. 'B1'
    name TEXT,  -- e.g. 'Division 1A'
    country TEXT  -- e.g. 'Belgium'
);

-- Table: matchs (123404 rows)
CREATE TABLE matchs (
    Div TEXT,  -- e.g. 'B1'; FK -> divisions.division
    Date DATE,  -- e.g. '2020-08-08'
    HomeTeam TEXT,  -- e.g. 'Club Brugge'
    AwayTeam TEXT,  -- e.g. 'Charleroi'
    FTHG INTEGER,  -- e.g. 0
    FTAG INTEGER,  -- e.g. 1
    FTR TEXT,  -- values: {'A', 'D', 'H'}
    season INTEGER,  -- e.g. 2021
    FOREIGN KEY (Div) REFERENCES divisions(division)
);
```