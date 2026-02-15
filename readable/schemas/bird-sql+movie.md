```sql
-- Database: movie

/*
Schema: NULL
Table: actor
Rows: 2713
Sample rows:
| ActorID   | Name            | Date of Birth   | Birth City   | Birth Country   | Height (Inches)   | Biography                                                                                                                                                                                                   | Gender   | Ethnicity   | NetWorth        |
|-----------|-----------------|-----------------|--------------|-----------------|-------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|-------------|-----------------|
| 1         | John Travolta   | 1954-02-18      | Englewood    | USA             | 74.0              | John Joseph Travolta was born in Englewood, New Jersey, one of six children of Helen Travolta (n�e H...repair shop called Travolta Tires in Hillsdale, NJ. Travolta started acting appearing in a local ... | Male     | White       | $250,000,000.00 |
| 2         | Kirstie Alley   | 1951-01-12      | Wichita      | USA             | 67.0              | [NULL]                                                                                                                                                                                                      | Female   | White       | $40,000,000.00  |
| 3         | Olympia Dukakis | 1931-06-20      | Lowell       | USA             | 63.0              | Long a vital, respected lady of the classic and contemporary stage this grand lady did not become a ...tic comedy Moonstruck (1987). Since then movie (and TV) fans have discovered what the East coast ... | Female   | White       | $6,000,000.00   |
| 4         | George Segal    | 1934-02-13      | Great Neck   | USA             | 71.0              | [NULL]                                                                                                                                                                                                      | Male     | White       | $10,000,000.00  |
| 5         | Abe Vigoda      | 1921-02-24      | Brooklyn     | USA             | 73.0              | [NULL]                                                                                                                                                                                                      | Male     | White       | $10,000,000.00  |
| ...       | ...             | ...             | ...          | ...             | ...               | ...                                                                                                                                                                                                         | ...      | ...         | ...             |
*/
CREATE TABLE actor (
    "ActorID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Name" TEXT NULL,
        -- <example>'John Travolta'</example>
    "Date of Birth" DATE NULL,
        -- <example>'1954-02-18'</example>
    "Birth City" TEXT NULL,
        -- <example>'Englewood'</example>
    "Birth Country" TEXT NULL,
        -- <example>'USA'</example>
    "Height (Inches)" INTEGER NULL,
        -- <example>74</example>
    "Biography" TEXT NULL,
        -- <example>'John Joseph Travolta was born in Englewood, New Je.... Travolta started acting appearing in a local ...'</example>
    "Gender" TEXT NULL,
        -- <values>{'Female', 'Male'}</values>
    "Ethnicity" TEXT NULL,
        -- <values>{'African American', 'American-Irish', 'American-South African', 'Argentine', 'Armenian', 'Asian American', 'Asian', 'Israeli', 'Japanese-American', 'Latino', 'Lebanese', 'Mixed', 'Native American', 'Polish', 'Puerto Rican', 'South African', 'White'}</values>
    "NetWorth" TEXT NULL
        -- <example>'$250,000,000.00'</example>
);

/*
Schema: NULL
Table: characters
Rows: 4312
Sample rows:
| MovieID   | ActorID   | Character Name   | creditOrder   | pay    | screentime   |
|-----------|-----------|------------------|---------------|--------|--------------|
| 1         | 1         | James            | 1             | [NULL] | [NULL]       |
| 1         | 2         | Mollie           | 2             | [NULL] | [NULL]       |
| 1         | 3         | Rosie            | 3             | [NULL] | [NULL]       |
| 1         | 4         | Albert           | 4             | [NULL] | [NULL]       |
| 1         | 5         | Grandpa          | 5             | [NULL] | [NULL]       |
| ...       | ...       | ...              | ...           | ...    | ...          |
*/
CREATE TABLE characters (
    "MovieID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> movie."MovieID"</fk>
    "ActorID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> actor."ActorID"</fk>
    "Character Name" TEXT NOT NULL,
        -- <example>'James'</example>
    "creditOrder" INTEGER NOT NULL,
        -- <example>1</example>
    "pay" TEXT NULL,
        -- <values>{'$100,000,000.00', '$29,000,000.00', '$5,000,000.00', '$50,000,000.00', '$55,000,000.00', '$60,000,000.00', '$65,000,000.00', '$68,000,000.00', '$70,000,000.00', '$75,000,000.00'}</values>
    "screentime" TEXT NULL,
        -- <values>{'0:02:45', '0:03:30', '0:04:15', '0:04:30', '0:08:45', '0:29:00', '0:32:15', '0:32:30'}</values>
    PRIMARY KEY ("MovieID", "ActorID"),
    FOREIGN KEY ("ActorID") REFERENCES actor("ActorID"),
    FOREIGN KEY ("MovieID") REFERENCES movie("MovieID")
);

/*
Schema: NULL
Table: movie
Rows: 634
Sample rows:
| MovieID   | Title                      | MPAA Rating   | Budget   | Gross     | Release Date   | Genre   | Runtime   | Rating   | Rating Count   | Summary                                                                                                                                                                                                     |
|-----------|----------------------------|---------------|----------|-----------|----------------|---------|-----------|----------|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 1         | Look Who's Talking         | PG-13         | 7500000  | 296000000 | 1989-10-12     | Romance | 93        | 5.9      | 73638          | After a single, career-minded woman is left on her own to give birth to the child of a married man, ...nce in a cab driver. Meanwhile, the point-of-view of the newborn boy is narrated through voice-over. |
| 2         | Driving Miss Daisy         | PG            | 7500000  | 145793296 | 1989-12-13     | Comedy  | 99        | 7.4      | 91075          | An old Jewish woman and her African-American chauffeur in the American South have a relationship that grows and improves over the years.                                                                    |
| 3         | Turner & Hooch             | PG            | 13000000 | 71079915  | 1989-07-28     | Crime   | 100       | 7.2      | 91415          | Det. Scott Turner (Tom Hanks) is an uptight, by-the-book police officer. When his friend Amos Reed (...reluctantly inherits the man's dog. Turner adjusts to life with the dog to help solve a murder case. |
| 4         | Born on the Fourth of July | R             | 14000000 | 161001698 | 1989-12-20     | War     | 145       | 7.2      | 91415          | The biography of Ron Kovic. Paralyzed in the Vietnam war, he becomes an anti-war and pro-human rights political activist after feeling betrayed by the country he fought for.                               |
| 5         | Field of Dreams            | PG            | 15000000 | 84431625  | 1989-04-21     | Drama   | 107       | 7.5      | 101702         | An Iowa corn farmer, hearing voices, interprets them as a command to build a baseball diamond in his fields; he does, and the 1919 Chicago White Sox come.                                                  |
| ...       | ...                        | ...           | ...      | ...       | ...            | ...     | ...       | ...      | ...            | ...                                                                                                                                                                                                         |
*/
CREATE TABLE movie (
    "MovieID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Title" TEXT NOT NULL,
        -- <example>'Look Who's Talking'</example>
    "MPAA Rating" TEXT NOT NULL,
        -- <values>{'G', 'PG', 'PG-13', 'R'}</values>
    "Budget" INTEGER NOT NULL,
        -- <example>7500000</example>
    "Gross" INTEGER NULL,
        -- <example>296000000</example>
    "Release Date" TEXT NOT NULL,
        -- <example>'1989-10-12'</example>
    "Genre" TEXT NOT NULL,
        -- <example>'Romance'</example>
    "Runtime" INTEGER NOT NULL,
        -- <example>93</example>
    "Rating" REAL NULL,
        -- <example>5.900</example>
    "Rating Count" INTEGER NULL,
        -- <example>73638</example>
    "Summary" TEXT NOT NULL
        -- <example>'After a single, career-minded woman is left on her...of the newborn boy is narrated through voice-over.'</example>
);
```