```sql
-- Database: olympics

-- Table: city (42 rows)
CREATE TABLE city (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    city_name TEXT  -- e.g. 'Barcelona'
);

-- Table: competitor_event (260971 rows)
CREATE TABLE competitor_event (
    event_id INTEGER,  -- e.g. 1; FK -> event.id
    competitor_id INTEGER,  -- e.g. 1; FK -> games_competitor.id
    medal_id INTEGER,  -- e.g. 4; FK -> medal.id
    FOREIGN KEY (competitor_id) REFERENCES games_competitor(id),
    FOREIGN KEY (event_id) REFERENCES event(id),
    FOREIGN KEY (medal_id) REFERENCES medal(id)
);

-- Table: event (757 rows)
CREATE TABLE event (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    sport_id INTEGER,  -- e.g. 9; FK -> sport.id
    event_name TEXT,  -- e.g. 'Basketball Men's Basketball'
    FOREIGN KEY (sport_id) REFERENCES sport(id)
);

-- Table: games (51 rows)
CREATE TABLE games (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    games_year INTEGER,  -- e.g. 1992
    games_name TEXT,  -- e.g. '1992 Summer'
    season TEXT  -- values: {'Summer', 'Winter'}
);

-- Table: games_city (52 rows)
CREATE TABLE games_city (
    games_id INTEGER,  -- e.g. 1; FK -> games.id
    city_id INTEGER,  -- e.g. 1; FK -> city.id
    FOREIGN KEY (city_id) REFERENCES city(id),
    FOREIGN KEY (games_id) REFERENCES games(id)
);

-- Table: games_competitor (180252 rows)
CREATE TABLE games_competitor (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    games_id INTEGER,  -- e.g. 1; FK -> games.id
    person_id INTEGER,  -- e.g. 1; FK -> person.id
    age INTEGER,  -- e.g. 24
    FOREIGN KEY (games_id) REFERENCES games(id),
    FOREIGN KEY (person_id) REFERENCES person(id)
);

-- Table: medal (4 rows)
CREATE TABLE medal (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    medal_name TEXT  -- values: {'Bronze', 'Gold', 'NA', 'Silver'}
);

-- Table: noc_region (231 rows)
CREATE TABLE noc_region (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    noc TEXT,  -- e.g. 'AFG'
    region_name TEXT  -- e.g. 'Afghanistan'
);

-- Table: person (128854 rows)
CREATE TABLE person (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    full_name TEXT,  -- e.g. 'A Dijiang'
    gender TEXT,  -- values: {'F', 'M'}
    height INTEGER,  -- e.g. 180
    weight INTEGER  -- e.g. 80
);

-- Table: person_region (130521 rows)
CREATE TABLE person_region (
    person_id INTEGER,  -- e.g. 1; FK -> person.id
    region_id INTEGER,  -- e.g. 42; FK -> noc_region.id
    FOREIGN KEY (person_id) REFERENCES person(id),
    FOREIGN KEY (region_id) REFERENCES noc_region(id)
);

-- Table: sport (66 rows)
CREATE TABLE sport (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    sport_name TEXT  -- e.g. 'Aeronautics'
);
```