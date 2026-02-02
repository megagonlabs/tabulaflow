```sql
-- Database: european_football_1

-- Table: divisions (21 rows)
CREATE TABLE divisions (
    division TEXT NOT NULL PRIMARY KEY,
        -- <example>'B1'</example>
    name TEXT NULL,
        -- <example>'Division 1A'</example>
    country TEXT NULL
        -- <example>'Belgium'</example>
);

-- Table: matchs (123404 rows)
CREATE TABLE matchs (
    Div TEXT NULL,
        -- <example>'B1'</example>
        -- <fk> -> divisions.division</fk>
    Date DATE NULL,
        -- <example>'2020-08-08'</example>
    HomeTeam TEXT NULL,
        -- <example>'Club Brugge'</example>
    AwayTeam TEXT NULL,
        -- <example>'Charleroi'</example>
    FTHG INTEGER NULL,
        -- <example>0</example>
    FTAG INTEGER NULL,
        -- <example>1</example>
    FTR TEXT NULL,
        -- <values>{'A', 'D', 'H'}</values>
    season INTEGER NULL,
        -- <example>2021</example>
    FOREIGN KEY (Div) REFERENCES divisions(division)
);
```