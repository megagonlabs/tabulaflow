```sql
-- Database: law_episode

-- Table: Award (22 rows)
CREATE TABLE Award (
    award_id INTEGER NULL PRIMARY KEY,
        -- <example>258</example>
    organization TEXT NULL,
        -- <values>{'American Bar Association Silver Gavel Awards for Media and the Arts', 'Edgar Allan Poe Awards', 'International Monitor Awards', 'Primetime Emmy Awards'}</values>
    year INTEGER NULL,
        -- <example>1999</example>
    award_category TEXT NULL,
        -- <values>{'Edgar', 'Monitor', 'Primetime Emmy', 'Silver Gavel Award'}</values>
    award TEXT NULL,
        -- <values>{'Best Television Episode', 'Film Originated Television Series - Best Achievement', 'Outstanding Costume Design for a Series', 'Outstanding Directing for a Drama Series', 'Outstanding Guest Actress in a Drama Series', 'Outstanding Sound Mixing for a Drama Series', 'Television'}</values>
    series TEXT NULL,
        -- <values>{'Law and Order'}</values>
    episode_id TEXT NULL,
        -- <values>{'tt0629149', 'tt0629228', 'tt0629248', 'tt0629291', 'tt0629397', 'tt0629398', 'tt0629422'}</values>
        -- <fk> -> Episode.episode_id</fk>
    person_id TEXT NULL,
        -- <example>'nm0937725'</example>
        -- <fk> -> Person.person_id</fk>
    role TEXT NULL,
        -- <values>{'Katrina Ludlow', 'director', 'production mixer', 're-recording mixer', 'story', 'teleplay', 'teleplay, story', 'writer'}</values>
    result TEXT NULL,
        -- <values>{'Nominee', 'Winner'}</values>
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id),
    FOREIGN KEY (person_id) REFERENCES Person(person_id)
);

-- Table: Credit (2231 rows)
CREATE TABLE Credit (
    episode_id TEXT NULL,
        -- <example>'tt0629146'</example>
        -- <fk> -> Episode.episode_id</fk>
    person_id TEXT NULL,
        -- <example>'nm0000973'</example>
        -- <fk> -> Person.person_id</fk>
    category TEXT NULL,
        -- <values>{'Additional Crew', 'Art Department', 'Camera and Electrical Department', 'Cast', 'Casting Department', 'Costume and Wardrobe Department', 'Directed by', 'Editorial Department', 'Film Editing by', 'General', 'Location Management', 'Makeup Department', 'Music Department', 'Produced by', 'Production Management', 'Script and Continuity Department', 'Sound Department', 'Stunts', 'Transportation Department', 'Writing Credits'}</values>
    role TEXT NULL,
        -- <example>'technical advisor'</example>
    credited TEXT NULL,
        -- <values>{'false', 'true'}</values>
    PRIMARY KEY (episode_id, person_id),
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id),
    FOREIGN KEY (person_id) REFERENCES Person(person_id)
);

-- Table: Episode (24 rows)
CREATE TABLE Episode (
    episode_id TEXT NULL PRIMARY KEY,
        -- <example>'tt0629146'</example>
    series TEXT NULL,
        -- <values>{'Law and Order'}</values>
    season INTEGER NULL,
        -- <example>9</example>
    episode INTEGER NULL,
        -- <example>1</example>
    number_in_series INTEGER NULL,
        -- <example>182</example>
    title TEXT NULL,
        -- <example>'Cherished'</example>
    summary TEXT NULL,
        -- <example>'New assistant DA Abbie Carmichael aggressively inv...cy, gravely ill children, and an unethical doctor.'</example>
    air_date DATE NULL,
        -- <example>'1998-09-23'</example>
    episode_image TEXT NULL,
        -- <example>'https://m.media-amazon.com/images/M/MV5BODFmZmI2YT...deQXVyMjMzNzMxMTA@._V1_UY126_CR7,0,224,126_AL_.jpg'</example>
    rating REAL NULL,
        -- <example>7.900</example>
    votes INTEGER NULL
        -- <example>203</example>
);

-- Table: Keyword (33 rows)
CREATE TABLE Keyword (
    episode_id TEXT NULL,
        -- <values>{'tt0629239', 'tt0629397', 'tt0629420'}</values>
        -- <fk> -> Episode.episode_id</fk>
    keyword TEXT NULL,
        -- <example>'nun'</example>
    PRIMARY KEY (episode_id, keyword),
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id)
);

-- Table: Person (800 rows)
CREATE TABLE Person (
    person_id TEXT NULL PRIMARY KEY,
        -- <example>'nm0000210'</example>
    name TEXT NULL,
        -- <example>'Julia Roberts'</example>
    birthdate DATE NULL,
        -- <example>'1967-10-28'</example>
    birth_name TEXT NULL,
        -- <example>'Julia Fiona Roberts'</example>
    birth_place TEXT NULL,
        -- <example>'Smyrna'</example>
    birth_region TEXT NULL,
        -- <example>'Georgia'</example>
    birth_country TEXT NULL,
        -- <example>'USA'</example>
    height_meters REAL NULL,
        -- <example>1.730</example>
    nickname TEXT NULL
        -- <example>'Jules'</example>
);

-- Table: Vote (240 rows)
CREATE TABLE Vote (
    episode_id TEXT NULL,
        -- <example>'tt0629204'</example>
        -- <fk> -> Episode.episode_id</fk>
    stars INTEGER NULL,
        -- <example>10</example>
    votes INTEGER NULL,
        -- <example>36</example>
    percent REAL NULL,
        -- <example>17.700</example>
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id)
);
```