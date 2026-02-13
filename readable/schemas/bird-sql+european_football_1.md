```sql
-- Database: european_football_1

/*
Schema: NULLTable: divisions
Rows: 21
Sample rows:
| division   | name             | country     |
|------------|------------------|-------------|
| B1         | Division 1A      | Belgium     |
| D1         | Bundesliga       | Deutschland |
| D2         | 2. Bundesliga    | Deutschland |
| E0         | Premier League   | England     |
| E1         | EFL Championship | England     |
| ...        | ...              | ...         |
*/
CREATE TABLE divisions (
    division TEXT NOT NULL PRIMARY KEY,
        -- <example>'B1'</example>
    name TEXT NOT NULL,
        -- <example>'Division 1A'</example>
    country TEXT NOT NULL
        -- <example>'Belgium'</example>
);

/*
Schema: NULLTable: matchs
Rows: 123404
Sample rows:
| Div   | Date       | HomeTeam    | AwayTeam      | FTHG   | FTAG   | FTR   | season   |
|-------|------------|-------------|---------------|--------|--------|-------|----------|
| B1    | 2020-08-08 | Club Brugge | Charleroi     | 0      | 1      | A     | 2021     |
| B1    | 2020-08-08 | Antwerp     | Mouscron      | 1      | 1      | D     | 2021     |
| B1    | 2020-08-08 | Standard    | Cercle Brugge | 1      | 0      | H     | 2021     |
| B1    | 2020-08-09 | St Truiden  | Gent          | 2      | 1      | H     | 2021     |
| B1    | 2020-08-09 | Waregem     | Genk          | 1      | 2      | A     | 2021     |
| ...   | ...        | ...         | ...           | ...    | ...    | ...   | ...      |
*/
CREATE TABLE matchs (
    Div TEXT NOT NULL,
        -- <example>'B1'</example>
        -- <fk> -> divisions.division</fk>
    Date DATE NOT NULL,
        -- <example>'2020-08-08'</example>
    HomeTeam TEXT NOT NULL,
        -- <example>'Club Brugge'</example>
    AwayTeam TEXT NOT NULL,
        -- <example>'Charleroi'</example>
    FTHG INTEGER NOT NULL,
        -- <example>0</example>
    FTAG INTEGER NOT NULL,
        -- <example>1</example>
    FTR TEXT NOT NULL,
        -- <values>{'A', 'D', 'H'}</values>
    season INTEGER NOT NULL,
        -- <example>2021</example>
    FOREIGN KEY (Div) REFERENCES divisions(division)
);
```