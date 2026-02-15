```sql
-- Database: disney

/*
Schema: NULL
Table: characters
Rows: 56
Sample rows:
| movie_title                     | release_date   | hero       | villian    | song                         |
|---------------------------------|----------------|------------|------------|------------------------------|
| Snow White and the Seven Dwarfs | 21-Dec-37      | Snow White | Evil Queen | Some Day My Prince Will Come |
| Pinocchio                       | 7-Feb-40       | Pinocchio  | Stromboli  | When You Wish upon a Star    |
| Fantasia                        | 13-Nov-40      | [NULL]     | Chernabog  | [NULL]                       |
| Dumbo                           | 23-Oct-41      | Dumbo      | Ringmaster | Baby Mine                    |
| Bambi                           | 13-Aug-42      | Bambi      | Hunter     | Love Is a Song               |
| ...                             | ...            | ...        | ...        | ...                          |
*/
CREATE TABLE characters (
    "movie_title" TEXT NOT NULL PRIMARY KEY,
        -- <example>'Aladdin'</example>
    "release_date" TEXT NOT NULL,
        -- <example>'21-Dec-37'</example>
    "hero" TEXT NULL,
        -- <example>'Snow White'</example>
        -- <fk> -> "voice-actors"."character"</fk>
    "villian" TEXT NULL,
        -- <example>'Evil Queen'</example>
    "song" TEXT NULL,
        -- <example>'Some Day My Prince Will Come'</example>
    FOREIGN KEY ("hero") REFERENCES "voice-actors"("character")
);

/*
Schema: NULL
Table: director
Rows: 56
Sample rows:
| name                            | director       |
|---------------------------------|----------------|
| Snow White and the Seven Dwarfs | David Hand     |
| Pinocchio                       | Ben Sharpsteen |
| Fantasia                        | full credits   |
| Dumbo                           | Ben Sharpsteen |
| Bambi                           | David Hand     |
| ...                             | ...            |
*/
CREATE TABLE director (
    "name" TEXT NOT NULL PRIMARY KEY,
        -- <example>'101 Dalmatians'</example>
        -- <fk> -> characters."movie_title"</fk>
    "director" TEXT NOT NULL,
        -- <example>'David Hand'</example>
    FOREIGN KEY ("name") REFERENCES characters("movie_title")
);

/*
Schema: NULL
Table: movies_total_gross
Rows: 579
Sample rows:
| movie_title                     | release_date   | genre     | MPAA_rating   | total_gross   | inflation_adjusted_gross   |
|---------------------------------|----------------|-----------|---------------|---------------|----------------------------|
| Snow White and the Seven Dwarfs | Dec 21, 1937   | Musical   | G             | $184,925,485  | $5,228,953,251             |
| Pinocchio                       | Feb 9, 1940    | Adventure | G             | $84,300,000   | $2,188,229,052             |
| Fantasia                        | Nov 13, 1940   | Musical   | G             | $83,320,000   | $2,187,090,808             |
| Song of the South               | Nov 12, 1946   | Adventure | G             | $65,000,000   | $1,078,510,579             |
| Cinderella                      | Feb 15, 1950   | Drama     | G             | $85,000,000   | $920,608,730               |
| ...                             | ...            | ...       | ...           | ...           | ...                        |
*/
CREATE TABLE movies_total_gross (
    "movie_title" TEXT NOT NULL,
        -- <example>'101 Dalmatians'</example>
        -- <fk> -> characters."movie_title"</fk>
    "release_date" TEXT NOT NULL,
        -- <example>'Jan 25, 1961'</example>
    "genre" TEXT NOT NULL,
        -- <example>'Musical'</example>
    "MPAA_rating" TEXT NOT NULL,
        -- <values>{'', 'G', 'Not Rated', 'PG', 'PG-13', 'R'}</values>
    "total_gross" TEXT NOT NULL,
        -- <example>'$184,925,485'</example>
    "inflation_adjusted_gross" TEXT NOT NULL,
        -- <example>'$5,228,953,251'</example>
    PRIMARY KEY ("movie_title", "release_date"),
    FOREIGN KEY ("movie_title") REFERENCES characters("movie_title")
);

/*
Schema: NULL
Table: revenue
Rows: 26
Sample rows:
| Year   | Studio Entertainment[NI 1]   | Disney Consumer Products[NI 2]   | Disney Interactive[NI 3][Rev 1]   | Walt Disney Parks and Resorts   | Disney Media Networks   | Total   |
|--------|------------------------------|----------------------------------|-----------------------------------|---------------------------------|-------------------------|---------|
| 1991   | 2593.0                       | 724.0                            | [NULL]                            | 2794.0                          | [NULL]                  | 6111    |
| 1992   | 3115.0                       | 1081.0                           | [NULL]                            | 3306.0                          | [NULL]                  | 7502    |
| 1993   | 3673.4                       | 1415.1                           | [NULL]                            | 3440.7                          | [NULL]                  | 8529    |
| 1994   | 4793.0                       | 1798.2                           | [NULL]                            | 3463.6                          | 359                     | 10414   |
| 1995   | 6001.5                       | 2150.0                           | [NULL]                            | 3959.8                          | 414                     | 12525   |
| ...    | ...                          | ...                              | ...                               | ...                             | ...                     | ...     |
*/
CREATE TABLE revenue (
    "Year" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1991</example>
    "Studio Entertainment[NI 1]" REAL NULL,
        -- <example>2593.000</example>
    "Disney Consumer Products[NI 2]" REAL NULL,
        -- <example>724.000</example>
    "Disney Interactive[NI 3][Rev 1]" INTEGER NULL,
        -- <example>174</example>
    "Walt Disney Parks and Resorts" REAL NOT NULL,
        -- <example>2794.000</example>
    "Disney Media Networks" TEXT NULL,
        -- <example>'359'</example>
    "Total" INTEGER NOT NULL
        -- <example>6111</example>
);

/*
Schema: NULL
Table: "voice-actors"
Rows: 922
Sample rows:
| character      | voice-actor     | movie                       |
|----------------|-----------------|-----------------------------|
| Abby Mallard   | Joan Cusack     | Chicken Little              |
| Abigail Gabble | Monica Evans    | The Aristocats              |
| Abis Mal       | Jason Alexander | The Return of Jafar         |
| Abu            | Frank Welker    | Aladdin                     |
| Achilles       | None            | The Hunchback of Notre Dame |
| ...            | ...             | ...                         |
*/
CREATE TABLE "voice-actors" (
    "character" TEXT NOT NULL PRIMARY KEY,
        -- <example>'Abby Mallard'</example>
    "voice-actor" TEXT NOT NULL,
        -- <example>'Joan Cusack'</example>
    "movie" TEXT NOT NULL,
        -- <example>'Chicken Little'</example>
        -- <fk> -> characters."movie_title"</fk>
    FOREIGN KEY ("movie") REFERENCES characters("movie_title")
);
```