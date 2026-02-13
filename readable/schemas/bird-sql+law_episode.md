```sql
-- Database: law_episode

/*
Table: Award
Rows: 22
Sample rows:
| award_id   | organization                 | year   | award_category   | award                                                | series        | episode_id   | person_id   | role   | result   |
|------------|------------------------------|--------|------------------|------------------------------------------------------|---------------|--------------|-------------|--------|----------|
| 258        | International Monitor Awards | 1999   | Monitor          | Film Originated Television Series - Best Achievement | Law and Order | tt0629149    | nm0937725   | [NULL] | Winner   |
| 259        | International Monitor Awards | 1999   | Monitor          | Film Originated Television Series - Best Achievement | Law and Order | tt0629149    | nm0792309   | [NULL] | Winner   |
| 260        | International Monitor Awards | 1999   | Monitor          | Film Originated Television Series - Best Achievement | Law and Order | tt0629149    | nm0049569   | [NULL] | Winner   |
| 261        | International Monitor Awards | 1999   | Monitor          | Film Originated Television Series - Best Achievement | Law and Order | tt0629149    | nm0371065   | [NULL] | Winner   |
| 262        | International Monitor Awards | 1999   | Monitor          | Film Originated Television Series - Best Achievement | Law and Order | tt0629149    | nm0288886   | [NULL] | Winner   |
| ...        | ...                          | ...    | ...              | ...                                                  | ...           | ...          | ...         | ...    | ...      |
*/
CREATE TABLE Award (
    award_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>258</example>
    organization TEXT NOT NULL,
        -- <values>{'American Bar Association Silver Gavel Awards for Media and the Arts', 'Edgar Allan Poe Awards', 'International Monitor Awards', 'Primetime Emmy Awards'}</values>
    year INTEGER NOT NULL,
        -- <example>1999</example>
    award_category TEXT NOT NULL,
        -- <values>{'Edgar', 'Monitor', 'Primetime Emmy', 'Silver Gavel Award'}</values>
    award TEXT NOT NULL,
        -- <values>{'Best Television Episode', 'Film Originated Television Series - Best Achievement', 'Outstanding Costume Design for a Series', 'Outstanding Directing for a Drama Series', 'Outstanding Guest Actress in a Drama Series', 'Outstanding Sound Mixing for a Drama Series', 'Television'}</values>
    series TEXT NOT NULL,
        -- <values>{'Law and Order'}</values>
    episode_id TEXT NOT NULL,
        -- <values>{'tt0629149', 'tt0629228', 'tt0629248', 'tt0629291', 'tt0629397', 'tt0629398', 'tt0629422'}</values>
        -- <fk> -> Episode.episode_id</fk>
    person_id TEXT NOT NULL,
        -- <example>'nm0937725'</example>
        -- <fk> -> Person.person_id</fk>
    role TEXT NULL,
        -- <values>{'Katrina Ludlow', 'director', 'production mixer', 're-recording mixer', 'story', 'teleplay', 'teleplay, story', 'writer'}</values>
    result TEXT NOT NULL,
        -- <values>{'Nominee', 'Winner'}</values>
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id),
    FOREIGN KEY (person_id) REFERENCES Person(person_id)
);

/*
Table: Credit
Rows: 2231
Sample rows:
| episode_id   | person_id   | category        | role                                      | credited   |
|--------------|-------------|-----------------|-------------------------------------------|------------|
| tt0629204    | nm0226352   | Additional Crew | technical advisor                         | true       |
| tt0629204    | nm0506974   | Additional Crew | production accountant                     | true       |
| tt0629204    | nm4103116   | Additional Crew | production accountant                     | true       |
| tt0629204    | nm0645048   | Additional Crew | president of NBC West Coast               | true       |
| tt0629204    | nm5632505   | Additional Crew | executive assistant to executive producer | true       |
| ...          | ...         | ...             | ...                                       | ...        |
*/
CREATE TABLE Credit (
    episode_id TEXT NOT NULL,
        -- <example>'tt0629146'</example>
        -- <fk> -> Episode.episode_id</fk>
    person_id TEXT NOT NULL,
        -- <example>'nm0000973'</example>
        -- <fk> -> Person.person_id</fk>
    category TEXT NOT NULL,
        -- <values>{'Additional Crew', 'Art Department', 'Camera and Electrical Department', 'Cast', 'Casting Department', 'Costume and Wardrobe Department', 'Directed by', 'Editorial Department', 'Film Editing by', 'General', 'Location Management', 'Makeup Department', 'Music Department', 'Produced by', 'Production Management', 'Script and Continuity Department', 'Sound Department', 'Stunts', 'Transportation Department', 'Writing Credits'}</values>
    role TEXT NOT NULL,
        -- <example>'technical advisor'</example>
    credited TEXT NOT NULL,
        -- <values>{'false', 'true'}</values>
    PRIMARY KEY (episode_id, person_id),
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id),
    FOREIGN KEY (person_id) REFERENCES Person(person_id)
);

/*
Table: Episode
Rows: 24
Sample rows:
| episode_id   | series        | season   | episode   | number_in_series   | title     | summary                                                                                                                                                                                                     | air_date   | episode_image                                                                                                                                        | rating   | votes   |
|--------------|---------------|----------|-----------|--------------------|-----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|------------------------------------------------------------------------------------------------------------------------------------------------------|----------|---------|
| tt0629204    | Law and Order | 9        | 1         | 182                | Cherished | New assistant DA Abbie Carmichael aggressively investigates an infant's death and helps uncover a conspiracy involving a Russian adoption agency, gravely ill children, and an unethical doctor.            | 1998-09-23 | https://m.media-amazon.com/images/M/MV5BODFmZmI2YTgtN2Y2Mi00ODA1LThjOTAtOTAzZWFmMTgyMjJjXkEyXkFqcGdeQXVyMjMzNzMxMTA@._V1_UY126_CR7,0,224,126_AL_.jpg | 7.9      | 203     |
| tt0629228    | Law and Order | 9        | 2         | 183                | DWB       | White police officers are accused of beating and dragging an African American man to his death. McCo...le facing pressure from Federal prosecutors, who want to make a deal with one of the guilty parties. | 1998-10-07 | https://m.media-amazon.com/images/M/MV5BNWEyM2NkZjktN2YwOS00ODMyLWI1NzItYjRlYWQ1NjU2Yzc3XkEyXkFqcGdeQXVyMjMzNzMxMTA@._V1_UY126_CR3,0,224,126_AL_.jpg | 7.9      | 177     |
| tt0629170    | Law and Order | 9        | 3         | 184                | Bait      | A teenager who was shot in a drug deal gone bad claims to have been coerced into working as an informant for a corrupt narcotics officer.                                                                   | 1998-10-14 | https://m.media-amazon.com/images/M/MV5BYzI5ZDU4NzUtYzE0My00MTE5LWE1NzItNzU5MzI3NGMxYzAwXkEyXkFqcGdeQXVyMjMzNzMxMTA@._V1_UY126_CR2,0,224,126_AL_.jpg | 7.6      | 159     |
| tt0629266    | Law and Order | 9        | 4         | 185                | Flight    | Prosecutors have trouble making a case against a father accused of injecting his son with deadly bacteria, so Jack is forced to play hardball with the bio-supplier that may have supplied him with it.     | 1998-10-21 | https://m.media-amazon.com/images/M/MV5BMmVlZWZlOWEtYjQ0MC00YmE5LTgwZGQtNzI5YjljOGJiNmQzXkEyXkFqcGdeQXVyMjMzNzMxMTA@._V1_UY126_CR1,0,224,126_AL_.jpg | 7.9      | 165     |
| tt0629149    | Law and Order | 9        | 5         | 186                | Agony     | After a woman is brutally attacked, the police believe they have stumbled on a serial killer. Prosecutors struggle with how to put him away for life with little evidence.                                  | 1998-11-04 | https://m.media-amazon.com/images/M/MV5BMzQ2ZmI1OGEtMDhkMi00NjM3LThlZWYtN2FlZTdjNmYwYmFjXkEyXkFqcGdeQXVyMjMzNzMxMTA@._V1_UY126_CR2,0,224,126_AL_.jpg | 8.2      | 187     |
| ...          | ...           | ...      | ...       | ...                | ...       | ...                                                                                                                                                                                                         | ...        | ...                                                                                                                                                  | ...      | ...     |
*/
CREATE TABLE Episode (
    episode_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'tt0629146'</example>
    series TEXT NOT NULL,
        -- <values>{'Law and Order'}</values>
    season INTEGER NOT NULL,
        -- <example>9</example>
    episode INTEGER NOT NULL,
        -- <example>1</example>
    number_in_series INTEGER NOT NULL,
        -- <example>182</example>
    title TEXT NOT NULL,
        -- <example>'Cherished'</example>
    summary TEXT NOT NULL,
        -- <example>'New assistant DA Abbie Carmichael aggressively inv...cy, gravely ill children, and an unethical doctor.'</example>
    air_date DATE NOT NULL,
        -- <example>'1998-09-23'</example>
    episode_image TEXT NOT NULL,
        -- <example>'https://m.media-amazon.com/images/M/MV5BODFmZmI2YT...deQXVyMjMzNzMxMTA@._V1_UY126_CR7,0,224,126_AL_.jpg'</example>
    rating REAL NOT NULL,
        -- <example>7.900</example>
    votes INTEGER NOT NULL
        -- <example>203</example>
);

/*
Table: Keyword
Rows: 33
Sample rows:
| episode_id   | keyword               |
|--------------|-----------------------|
| tt0629239    | nun                   |
| tt0629239    | priest                |
| tt0629420    | police officer        |
| tt0629420    | police officer killed |
| tt0629420    | police officer shot   |
| ...          | ...                   |
*/
CREATE TABLE Keyword (
    episode_id TEXT NOT NULL,
        -- <values>{'tt0629239', 'tt0629397', 'tt0629420'}</values>
        -- <fk> -> Episode.episode_id</fk>
    keyword TEXT NOT NULL,
        -- <example>'nun'</example>
    PRIMARY KEY (episode_id, keyword),
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id)
);

/*
Table: Person
Rows: 800
Sample rows:
| person_id   | name               | birthdate   | birth_name            | birth_place   | birth_region   | birth_country   | height_meters   | nickname   |
|-------------|--------------------|-------------|-----------------------|---------------|----------------|-----------------|-----------------|------------|
| nm0000210   | Julia Roberts      | 1967-10-28  | Julia Fiona Roberts   | Smyrna        | Georgia        | USA             | 1.73            | Jules      |
| nm0049569   | Rene Balcer        | 1954-02-09  | Rene Chenevert Balcer | Montreal      | Quebec         | Canada          | [NULL]          | [NULL]     |
| nm0288886   | Billy Fox          | [NULL]      | [NULL]                | [NULL]        | [NULL]         | [NULL]          | [NULL]          | [NULL]     |
| nm0538744   | Constantine Makris | [NULL]      | [NULL]                | [NULL]        | [NULL]         | [NULL]          | [NULL]          | Gus        |
| nm0578294   | Thomas Meloeny     | [NULL]      | [NULL]                | [NULL]        | [NULL]         | [NULL]          | [NULL]          | [NULL]     |
| ...         | ...                | ...         | ...                   | ...           | ...            | ...             | ...             | ...        |
*/
CREATE TABLE Person (
    person_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'nm0000210'</example>
    name TEXT NOT NULL,
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

/*
Table: Vote
Rows: 240
Sample rows:
| episode_id   | stars   | votes   | percent   |
|--------------|---------|---------|-----------|
| tt0629204    | 10      | 36      | 17.7      |
| tt0629204    | 9       | 39      | 19.2      |
| tt0629204    | 8       | 64      | 31.5      |
| tt0629204    | 7       | 35      | 17.2      |
| tt0629204    | 6       | 13      | 6.4       |
| ...          | ...     | ...     | ...       |
*/
CREATE TABLE Vote (
    episode_id TEXT NOT NULL,
        -- <example>'tt0629204'</example>
        -- <fk> -> Episode.episode_id</fk>
    stars INTEGER NOT NULL,
        -- <example>10</example>
    votes INTEGER NOT NULL,
        -- <example>36</example>
    percent REAL NOT NULL,
        -- <example>17.700</example>
    FOREIGN KEY (episode_id) REFERENCES Episode(episode_id)
);
```