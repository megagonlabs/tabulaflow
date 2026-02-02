```sql
-- Database: simpson_episodes

-- Table: Award (75 rows)
CREATE TABLE Award (
    award_id INTEGER NULL PRIMARY KEY,
        -- <example>325</example>
    organization TEXT NULL,
        -- <example>'Primetime Emmy Awards'</example>
    year INTEGER NULL,
        -- <example>2009</example>
    award_category TEXT NULL,
        -- <example>'Primetime Emmy'</example>
    award TEXT NULL,
        -- <example>'Outstanding Voice-Over Performance'</example>
    person TEXT NULL,
        -- <example>'Dan Castellaneta'</example>
        -- <fk> -> Person.name</fk>
    role TEXT NULL,
        -- <example>'executive producer'</example>
    episode_id TEXT NULL,
        -- <example>'S20-E18'</example>
        -- <fk> -> Episode.episode_id</fk>
    season TEXT NULL,
    song TEXT NULL,
    result TEXT NULL,
        -- <values>{'Nominee', 'Winner'}</values>
    FOREIGN KEY (person) REFERENCES Person(name),
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id)
);

-- Table: Character_Award (12 rows)
CREATE TABLE Character_Award (
    award_id INTEGER NULL,
        -- <example>325</example>
        -- <fk> -> Award.award_id</fk>
    character TEXT NULL,
        -- <values>{'Homer Simpson', 'Kent Brockman', 'Lenny', 'Moe Szyslak', 'Mr. Burns', 'Smithers'}</values>
    FOREIGN KEY (award_id) REFERENCES Award(award_id)
);

-- Table: Credit (4557 rows)
CREATE TABLE Credit (
    episode_id TEXT NULL,
        -- <example>'S20-E10'</example>
        -- <fk> -> Episode.episode_id</fk>
    category TEXT NULL,
        -- <values>{'Animation Department', 'Art Department', 'Cast', 'Casting Department', 'Directed by', 'Editorial Department', 'General', 'Music Department', 'Other crew', 'Produced by', 'Production Management', 'Script and Continuity Department', 'Second Unit Director or Assistant Director', 'Sound Department', 'Thanks', 'Visual Effects by', 'Writing Credits'}</values>
    person TEXT NULL,
        -- <example>'Bonita Pietila'</example>
        -- <fk> -> Person.name</fk>
    role TEXT NULL,
        -- <example>'casting'</example>
    credited TEXT NULL,
        -- <values>{'false', 'true'}</values>
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id),
    FOREIGN KEY (person) REFERENCES Person(name)
);

-- Table: Episode (21 rows)
CREATE TABLE Episode (
    episode_id TEXT NULL PRIMARY KEY,
        -- <example>'S20-E1'</example>
    season INTEGER NULL,
        -- <example>20</example>
    episode INTEGER NULL,
        -- <example>1</example>
    number_in_series INTEGER NULL,
        -- <example>421</example>
    title TEXT NULL,
        -- <example>'Sex, Pies and Idiot Scrapes'</example>
    summary TEXT NULL,
        -- <example>'Homer and Ned go into business together as bounty ...unters, and Marge takes a job at an erotic bakery.'</example>
    air_date TEXT NULL,
        -- <example>'2008-09-28'</example>
    episode_image TEXT NULL,
        -- <example>'https://m.media-amazon.com/images/M/MV5BMTYwMzk2Nj...FtZTgwMzA2MDQ2MjE@._V1_UX224_CR0,0,224,126_AL_.jpg'</example>
    rating REAL NULL,
        -- <example>7.200</example>
    votes INTEGER NULL
        -- <example>1192</example>
);

-- Table: Keyword (307 rows)
CREATE TABLE Keyword (
    episode_id TEXT NULL,
        -- <example>'S20-E1'</example>
        -- <fk> -> Episode.episode_id</fk>
    keyword TEXT NULL,
        -- <example>'1930s to 2020s'</example>
    PRIMARY KEY (episode_id, keyword),
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id)
);

-- Table: Person (369 rows)
CREATE TABLE Person (
    name TEXT NULL PRIMARY KEY,
        -- <example>'Adam Greeley'</example>
    birthdate TEXT NULL,
        -- <example>'1963-05-04'</example>
    birth_name TEXT NULL,
        -- <example>'Marc Edward Wilmore'</example>
    birth_place TEXT NULL,
        -- <example>'USA'</example>
    birth_region TEXT NULL,
        -- <example>'California'</example>
    birth_country TEXT NULL,
        -- <values>{'Canada', 'Czechoslovakia', 'France', 'Iran', 'Ireland', 'North Korea', 'Philippines', 'UK', 'USA'}</values>
    height_meters REAL NULL,
        -- <example>1.850</example>
    nickname TEXT NULL
        -- <example>'Jim'</example>
);

-- Table: Vote (210 rows)
CREATE TABLE Vote (
    episode_id TEXT NULL,
        -- <example>'S20-E1'</example>
        -- <fk> -> Episode.episode_id</fk>
    stars INTEGER NULL,
        -- <example>2</example>
    votes INTEGER NULL,
        -- <example>16</example>
    percent REAL NULL,
        -- <example>1.300</example>
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id)
);
```