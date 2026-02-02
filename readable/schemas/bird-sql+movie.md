```sql
-- Database: movie

-- Table: actor (2713 rows)
CREATE TABLE actor (
    ActorID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NULL,
        -- <example>'John Travolta'</example>
    "Date of Birth" DATE NULL,
        -- <example>'1954-02-18'</example>
    "Birth City" TEXT NULL,
        -- <example>'Englewood'</example>
    "Birth Country" TEXT NULL,
        -- <example>'USA'</example>
    "Height (Inches)" INTEGER NULL,
        -- <example>74</example>
    Biography TEXT NULL,
        -- <example>'John Joseph Travolta was born in Englewood, New Je.... Travolta started acting appearing in a local ...'</example>
    Gender TEXT NULL,
        -- <values>{'Female', 'Male'}</values>
    Ethnicity TEXT NULL,
        -- <values>{'African American', 'American-Irish', 'American-South African', 'Argentine', 'Armenian', 'Asian American', 'Asian', 'Israeli', 'Japanese-American', 'Latino', 'Lebanese', 'Mixed', 'Native American', 'Polish', 'Puerto Rican', 'South African', 'White'}</values>
    NetWorth TEXT NULL
        -- <example>'$250,000,000.00'</example>
);

-- Table: characters (4312 rows)
CREATE TABLE characters (
    MovieID INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> movie.MovieID</fk>
    ActorID INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> actor.ActorID</fk>
    "Character Name" TEXT NULL,
        -- <example>'James'</example>
    creditOrder INTEGER NULL,
        -- <example>1</example>
    pay TEXT NULL,
        -- <values>{'$100,000,000.00', '$29,000,000.00', '$5,000,000.00', '$50,000,000.00', '$55,000,000.00', '$60,000,000.00', '$65,000,000.00', '$68,000,000.00', '$70,000,000.00', '$75,000,000.00'}</values>
    screentime TEXT NULL,
        -- <values>{'0:02:45', '0:03:30', '0:04:15', '0:04:30', '0:08:45', '0:29:00', '0:32:15', '0:32:30'}</values>
    PRIMARY KEY (MovieID, ActorID),
    FOREIGN KEY (ActorID) REFERENCES actor(ActorID),
    FOREIGN KEY (MovieID) REFERENCES movie(MovieID)
);

-- Table: movie (634 rows)
CREATE TABLE movie (
    MovieID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Title TEXT NULL,
        -- <example>'Look Who's Talking'</example>
    "MPAA Rating" TEXT NULL,
        -- <values>{'G', 'PG', 'PG-13', 'R'}</values>
    Budget INTEGER NULL,
        -- <example>7500000</example>
    Gross INTEGER NULL,
        -- <example>296000000</example>
    "Release Date" TEXT NULL,
        -- <example>'1989-10-12'</example>
    Genre TEXT NULL,
        -- <example>'Romance'</example>
    Runtime INTEGER NULL,
        -- <example>93</example>
    Rating REAL NULL,
        -- <example>5.900</example>
    "Rating Count" INTEGER NULL,
        -- <example>73638</example>
    Summary TEXT NULL
        -- <example>'After a single, career-minded woman is left on her...of the newborn boy is narrated through voice-over.'</example>
);
```