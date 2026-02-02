```sql
-- Database: olympics

-- Table: city (42 rows)
CREATE TABLE city (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    city_name TEXT NULL
        -- <example>'Barcelona'</example>
);

-- Table: competitor_event (260971 rows)
CREATE TABLE competitor_event (
    event_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> event.id</fk>
    competitor_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> games_competitor.id</fk>
    medal_id INTEGER NULL,
        -- <example>4</example>
        -- <fk> -> medal.id</fk>
    FOREIGN KEY (competitor_id) REFERENCES games_competitor(id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (medal_id) REFERENCES medal(id)
);

-- Table: event (757 rows)
CREATE TABLE event (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    sport_id INTEGER NULL,
        -- <example>9</example>
        -- <fk> -> sport.id</fk>
    event_name TEXT NULL,
        -- <example>'Basketball Men's Basketball'</example>
    FOREIGN KEY (sport_id) REFERENCES sport(id)
);

-- Table: games (51 rows)
CREATE TABLE games (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    games_year INTEGER NULL,
        -- <example>1992</example>
    games_name TEXT NULL,
        -- <example>'1992 Summer'</example>
    season TEXT NULL
        -- <values>{'Summer', 'Winter'}</values>
);

-- Table: games_city (52 rows)
CREATE TABLE games_city (
    games_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> games.id</fk>
    city_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> city.id</fk>
    FOREIGN KEY (city_id) REFERENCES city(id),
    FOREIGN KEY (games_id) REFERENCES games(id)
);

-- Table: games_competitor (180252 rows)
CREATE TABLE games_competitor (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    games_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> games.id</fk>
    person_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> person.id</fk>
    age INTEGER NULL,
        -- <example>24</example>
    FOREIGN KEY (games_id) REFERENCES games(id),
    FOREIGN KEY (person_id) REFERENCES person(id)
);

-- Table: medal (4 rows)
CREATE TABLE medal (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    medal_name TEXT NULL
        -- <values>{'Bronze', 'Gold', 'NA', 'Silver'}</values>
);

-- Table: noc_region (231 rows)
CREATE TABLE noc_region (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    noc TEXT NULL,
        -- <example>'AFG'</example>
    region_name TEXT NULL
        -- <example>'Afghanistan'</example>
);

-- Table: person (128854 rows)
CREATE TABLE person (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    full_name TEXT NULL,
        -- <example>'A Dijiang'</example>
    gender TEXT NULL,
        -- <values>{'F', 'M'}</values>
    height INTEGER NULL,
        -- <example>180</example>
    weight INTEGER NULL
        -- <example>80</example>
);

-- Table: person_region (130521 rows)
CREATE TABLE person_region (
    person_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> person.id</fk>
    region_id INTEGER NULL,
        -- <example>42</example>
        -- <fk> -> noc_region.id</fk>
    FOREIGN KEY (person_id) REFERENCES person(id),
    FOREIGN KEY (region_id) REFERENCES noc_region(id)
);

-- Table: sport (66 rows)
CREATE TABLE sport (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    sport_name TEXT NULL
        -- <example>'Aeronautics'</example>
);
```