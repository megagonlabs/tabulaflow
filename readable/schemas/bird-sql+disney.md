```sql
-- Database: disney

-- Table: characters (56 rows)
CREATE TABLE characters (
    movie_title TEXT NULL PRIMARY KEY,
        -- <example>'Aladdin'</example>
    release_date TEXT NULL,
        -- <example>'21-Dec-37'</example>
    hero TEXT NULL,
        -- <example>'Snow White'</example>
        -- <fk> -> "voice-actors".character</fk>
    villian TEXT NULL,
        -- <example>'Evil Queen'</example>
    song TEXT NULL,
        -- <example>'Some Day My Prince Will Come'</example>
    FOREIGN KEY (hero) REFERENCES "voice-actors"(character)
);

-- Table: director (56 rows)
CREATE TABLE director (
    name TEXT NULL PRIMARY KEY,
        -- <example>'101 Dalmatians'</example>
        -- <fk> -> characters.movie_title</fk>
    director TEXT NULL,
        -- <example>'David Hand'</example>
    FOREIGN KEY (name) REFERENCES characters(movie_title)
);

-- Table: movies_total_gross (579 rows)
CREATE TABLE movies_total_gross (
    movie_title TEXT NULL,
        -- <example>'101 Dalmatians'</example>
        -- <fk> -> characters.movie_title</fk>
    release_date TEXT NULL,
        -- <example>'Jan 25, 1961'</example>
    genre TEXT NULL,
        -- <example>'Musical'</example>
    MPAA_rating TEXT NULL,
        -- <values>{'', 'G', 'Not Rated', 'PG', 'PG-13', 'R'}</values>
    total_gross TEXT NULL,
        -- <example>'$184,925,485'</example>
    inflation_adjusted_gross TEXT NULL,
        -- <example>'$5,228,953,251'</example>
    PRIMARY KEY (movie_title, release_date),
    FOREIGN KEY (movie_title) REFERENCES characters(movie_title)
);

-- Table: revenue (26 rows)
CREATE TABLE revenue (
    Year INTEGER NULL PRIMARY KEY,
        -- <example>1991</example>
    "Studio Entertainment[NI 1]" REAL NULL,
        -- <example>2593.000</example>
    "Disney Consumer Products[NI 2]" REAL NULL,
        -- <example>724.000</example>
    "Disney Interactive[NI 3][Rev 1]" INTEGER NULL,
        -- <example>174</example>
    "Walt Disney Parks and Resorts" REAL NULL,
        -- <example>2794.000</example>
    "Disney Media Networks" TEXT NULL,
        -- <example>'359'</example>
    Total INTEGER NULL
        -- <example>6111</example>
);

-- Table: "voice-actors" (922 rows)
CREATE TABLE "voice-actors" (
    character TEXT NULL PRIMARY KEY,
        -- <example>'Abby Mallard'</example>
    "voice-actor" TEXT NULL,
        -- <example>'Joan Cusack'</example>
    movie TEXT NULL,
        -- <example>'Chicken Little'</example>
        -- <fk> -> characters.movie_title</fk>
    FOREIGN KEY (movie) REFERENCES characters(movie_title)
);
```