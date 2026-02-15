```sql
-- Database: simpson_episodes

/*
Schema: NULL
Table: Award
Rows: 75
Sample rows:
| award_id   | organization          | year   | award_category   | award                                                             | person           | role               | episode_id   | season   | song   | result   |
|------------|-----------------------|--------|------------------|-------------------------------------------------------------------|------------------|--------------------|--------------|----------|--------|----------|
| 325        | Primetime Emmy Awards | 2009   | Primetime Emmy   | Outstanding Voice-Over Performance                                | Dan Castellaneta | [NULL]             | S20-E18      | [NULL]   | [NULL] | Winner   |
| 326        | Primetime Emmy Awards | 2009   | Primetime Emmy   | Outstanding Voice-Over Performance                                | Hank Azaria      | [NULL]             | S20-E16      | [NULL]   | [NULL] | Nominee  |
| 327        | Primetime Emmy Awards | 2009   | Primetime Emmy   | Outstanding Voice-Over Performance                                | Harry Shearer    | [NULL]             | S20-E8       | [NULL]   | [NULL] | Nominee  |
| 328        | Primetime Emmy Awards | 2009   | Primetime Emmy   | Outstanding Animated Program (For Programming Less Than One Hour) | James L. Brooks  | executive producer | S20-E13      | [NULL]   | [NULL] | Nominee  |
| 329        | Primetime Emmy Awards | 2009   | Primetime Emmy   | Outstanding Animated Program (For Programming Less Than One Hour) | Matt Groening    | executive producer | S20-E13      | [NULL]   | [NULL] | Nominee  |
| ...        | ...                   | ...    | ...              | ...                                                               | ...              | ...                | ...          | ...      | ...    | ...      |
*/
CREATE TABLE Award (
    "award_id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>325</example>
    "organization" TEXT NOT NULL,
        -- <example>'Primetime Emmy Awards'</example>
    "year" INTEGER NOT NULL,
        -- <example>2009</example>
    "award_category" TEXT NOT NULL,
        -- <example>'Primetime Emmy'</example>
    "award" TEXT NOT NULL,
        -- <example>'Outstanding Voice-Over Performance'</example>
    "person" TEXT NULL,
        -- <example>'Dan Castellaneta'</example>
        -- <fk> -> Person."name"</fk>
    "role" TEXT NULL,
        -- <example>'executive producer'</example>
    "episode_id" TEXT NULL,
        -- <example>'S20-E18'</example>
        -- <fk> -> Episode."episode_id"</fk>
    "season" TEXT NULL,
    "song" TEXT NULL,
    "result" TEXT NOT NULL,
        -- <values>{'Nominee', 'Winner'}</values>
    FOREIGN KEY ("person") REFERENCES Person("name"),
    FOREIGN KEY ("episode_id") REFERENCES Episode("episode_id")
);

/*
Schema: NULL
Table: Character_Award
Rows: 12
Sample rows:
| award_id   | character     |
|------------|---------------|
| 325        | Homer Simpson |
| 326        | Moe Szyslak   |
| 327        | Kent Brockman |
| 327        | Lenny         |
| 327        | Mr. Burns     |
| ...        | ...           |
*/
CREATE TABLE Character_Award (
    "award_id" INTEGER NOT NULL,
        -- <example>325</example>
        -- <fk> -> Award."award_id"</fk>
    "character" TEXT NOT NULL,
        -- <values>{'Homer Simpson', 'Kent Brockman', 'Lenny', 'Moe Szyslak', 'Mr. Burns', 'Smithers'}</values>
    FOREIGN KEY ("award_id") REFERENCES Award("award_id")
);

/*
Schema: NULL
Table: Credit
Rows: 4557
Sample rows:
| episode_id   | category             | person         | role             | credited   |
|--------------|----------------------|----------------|------------------|------------|
| S20-E10      | Casting Department   | Bonita Pietila | casting          | true       |
| S20-E13      | Casting Department   | Bonita Pietila | casting          | true       |
| S20-E14      | Casting Department   | Bonita Pietila | casting          | true       |
| S20-E4       | Animation Department | Adam Kuhlman   | additional timer | true       |
| S20-E19      | Animation Department | Adam Kuhlman   | additional timer | true       |
| ...          | ...                  | ...            | ...              | ...        |
*/
CREATE TABLE Credit (
    "episode_id" TEXT NOT NULL,
        -- <example>'S20-E10'</example>
        -- <fk> -> Episode."episode_id"</fk>
    "category" TEXT NOT NULL,
        -- <values>{'Animation Department', 'Art Department', 'Cast', 'Casting Department', 'Directed by', 'Editorial Department', 'General', 'Music Department', 'Other crew', 'Produced by', 'Production Management', 'Script and Continuity Department', 'Second Unit Director or Assistant Director', 'Sound Department', 'Thanks', 'Visual Effects by', 'Writing Credits'}</values>
    "person" TEXT NOT NULL,
        -- <example>'Bonita Pietila'</example>
        -- <fk> -> Person."name"</fk>
    "role" TEXT NOT NULL,
        -- <example>'casting'</example>
    "credited" TEXT NOT NULL,
        -- <values>{'false', 'true'}</values>
    FOREIGN KEY ("episode_id") REFERENCES Episode("episode_id"),
    FOREIGN KEY ("person") REFERENCES Person("name")
);

/*
Schema: NULL
Table: Episode
Rows: 21
Sample rows:
| episode_id   | season   | episode   | number_in_series   | title                          | summary                                                                                                                                                                   | air_date   | episode_image                                                                                                        | rating   | votes   |
|--------------|----------|-----------|--------------------|--------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|----------------------------------------------------------------------------------------------------------------------|----------|---------|
| S20-E1       | 20       | 1         | 421                | Sex, Pies and Idiot Scrapes    | Homer and Ned go into business together as bounty hunters, and Marge takes a job at an erotic bakery.                                                                     | 2008-09-28 | https://m.media-amazon.com/images/M/MV5BMTYwMzk2Njg5N15BMl5BanBnXkFtZTgwMzA2MDQ2MjE@._V1_UX224_CR0,0,224,126_AL_.jpg | 7.2      | 1192    |
| S20-E2       | 20       | 2         | 422                | Lost Verizon                   | Bart gets in trouble with Marge after she finds out that he has Denis Leary's cell phone and is using it to make prank phone calls.                                       | 2008-10-05 | https://m.media-amazon.com/images/M/MV5BMjMyNzU4ODMzN15BMl5BanBnXkFtZTgwMTg5MTQ2MjE@._V1_UX224_CR0,0,224,126_AL_.jpg | 7.0      | 1055    |
| S20-E3       | 20       | 3         | 423                | Double, Double, Boy in Trouble | Bart trades lives with his multi-millionaire lookalike, but discovers that his lookalike's life isn't all he thought it would be.                                         | 2008-10-19 | https://m.media-amazon.com/images/M/MV5BMjA1ODM2ODkwM15BMl5BanBnXkFtZTgwOTc5MTQ2MjE@._V1_UX224_CR0,0,224,126_AL_.jpg | 7.0      | 1015    |
| S20-E4       | 20       | 4         | 424                | Treehouse of Horror XIX        | The Simpsons' 19th Halloween Special, with parodies of "Transformers," "Mad Men," and "It's the Great Pumpkin, Charlie Brown."                                            | 2008-11-02 | https://m.media-amazon.com/images/M/MV5BMTgzOTYyNTc2OF5BMl5BanBnXkFtZTgwNjc5MTQ2MjE@._V1_UX224_CR0,0,224,126_AL_.jpg | 7.1      | 1190    |
| S20-E5       | 20       | 5         | 425                | Dangerous Curves               | The Simpsons take a Fourth of July vacation to a cabin hotel, which cause Homer and Marge to reminisce about two episodes from their past where they stayed in the cabin. | 2008-11-09 | https://m.media-amazon.com/images/M/MV5BMjMxOTY4MjQzNl5BMl5BanBnXkFtZTgwMzc5MTQ2MjE@._V1_UX224_CR0,0,224,126_AL_.jpg | 6.5      | 951     |
| ...          | ...      | ...       | ...                | ...                            | ...                                                                                                                                                                       | ...        | ...                                                                                                                  | ...      | ...     |
*/
CREATE TABLE Episode (
    "episode_id" TEXT NOT NULL PRIMARY KEY,
        -- <example>'S20-E1'</example>
    "season" INTEGER NOT NULL,
        -- <example>20</example>
    "episode" INTEGER NOT NULL,
        -- <example>1</example>
    "number_in_series" INTEGER NOT NULL,
        -- <example>421</example>
    "title" TEXT NOT NULL,
        -- <example>'Sex, Pies and Idiot Scrapes'</example>
    "summary" TEXT NOT NULL,
        -- <example>'Homer and Ned go into business together as bounty ...unters, and Marge takes a job at an erotic bakery.'</example>
    "air_date" TEXT NOT NULL,
        -- <example>'2008-09-28'</example>
    "episode_image" TEXT NOT NULL,
        -- <example>'https://m.media-amazon.com/images/M/MV5BMTYwMzk2Nj...FtZTgwMzA2MDQ2MjE@._V1_UX224_CR0,0,224,126_AL_.jpg'</example>
    "rating" REAL NOT NULL,
        -- <example>7.200</example>
    "votes" INTEGER NOT NULL
        -- <example>1192</example>
);

/*
Schema: NULL
Table: Keyword
Rows: 307
Sample rows:
| episode_id   | keyword           |
|--------------|-------------------|
| S20-E1       | 1930s to 2020s    |
| S20-E1       | erotic bakery     |
| S20-E1       | cake              |
| S20-E1       | bullet            |
| S20-E1       | st. patrick's day |
| ...          | ...               |
*/
CREATE TABLE Keyword (
    "episode_id" TEXT NOT NULL,
        -- <example>'S20-E1'</example>
        -- <fk> -> Episode."episode_id"</fk>
    "keyword" TEXT NOT NULL,
        -- <example>'1930s to 2020s'</example>
    PRIMARY KEY ("episode_id", "keyword"),
    FOREIGN KEY ("episode_id") REFERENCES Episode("episode_id")
);

/*
Schema: NULL
Table: Person
Rows: 369
Sample rows:
| name             | birthdate   | birth_name              | birth_place   | birth_region   | birth_country   | height_meters   | nickname   |
|------------------|-------------|-------------------------|---------------|----------------|-----------------|-----------------|------------|
| Marc Wilmore     | 1963-05-04  | Marc Edward Wilmore     | [NULL]        | California     | USA             | [NULL]          | [NULL]     |
| Valentina Garza  | 1975-03-30  | Valentina Lantigua      | USA           | [NULL]         | [NULL]          | [NULL]          | [NULL]     |
| J. Stewart Burns | 1969-12-04  | Joseph Stewart Burns    | USA           | [NULL]         | [NULL]          | [NULL]          | [NULL]     |
| Stephanie Gillis | 1969-10-02  | Stephanie Katina Gillis | USA           | [NULL]         | [NULL]          | [NULL]          | [NULL]     |
| Laurie Biernacki | [NULL]      | Laurie D Templeton      | [NULL]        | [NULL]         | [NULL]          | [NULL]          | [NULL]     |
| ...              | ...         | ...                     | ...           | ...            | ...             | ...             | ...        |
*/
CREATE TABLE Person (
    "name" TEXT NOT NULL PRIMARY KEY,
        -- <example>'Adam Greeley'</example>
    "birthdate" TEXT NULL,
        -- <example>'1963-05-04'</example>
    "birth_name" TEXT NULL,
        -- <example>'Marc Edward Wilmore'</example>
    "birth_place" TEXT NULL,
        -- <example>'USA'</example>
    "birth_region" TEXT NULL,
        -- <example>'California'</example>
    "birth_country" TEXT NULL,
        -- <values>{'Canada', 'Czechoslovakia', 'France', 'Iran', 'Ireland', 'North Korea', 'Philippines', 'UK', 'USA'}</values>
    "height_meters" REAL NULL,
        -- <example>1.850</example>
    "nickname" TEXT NULL
        -- <example>'Jim'</example>
);

/*
Schema: NULL
Table: Vote
Rows: 210
Sample rows:
| episode_id   | stars   | votes   | percent   |
|--------------|---------|---------|-----------|
| S20-E1       | 2       | 16      | 1.3       |
| S20-E1       | 3       | 20      | 1.7       |
| S20-E1       | 4       | 36      | 3.0       |
| S20-E1       | 5       | 49      | 4.1       |
| S20-E1       | 1       | 67      | 5.6       |
| ...          | ...     | ...     | ...       |
*/
CREATE TABLE Vote (
    "episode_id" TEXT NOT NULL,
        -- <example>'S20-E1'</example>
        -- <fk> -> Episode."episode_id"</fk>
    "stars" INTEGER NOT NULL,
        -- <example>2</example>
    "votes" INTEGER NOT NULL,
        -- <example>16</example>
    "percent" REAL NOT NULL,
        -- <example>1.300</example>
    FOREIGN KEY ("episode_id") REFERENCES Episode("episode_id")
);
```