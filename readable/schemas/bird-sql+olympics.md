```sql
-- Database: olympics

/*
Schema: NULL
Table: city
Rows: 42
Sample rows:
| id   | city_name   |
|------|-------------|
| 1    | Barcelona   |
| 2    | London      |
| 3    | Antwerpen   |
| 4    | Paris       |
| 5    | Calgary     |
| ...  | ...         |
*/
CREATE TABLE city (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "city_name" TEXT NOT NULL
        -- <example>'Barcelona'</example>
);

/*
Schema: NULL
Table: competitor_event
Rows: 260971
Sample rows:
| event_id   | competitor_id   | medal_id   |
|------------|-----------------|------------|
| 1          | 1               | 4          |
| 2          | 2               | 4          |
| 3          | 3               | 4          |
| 4          | 4               | 1          |
| 5          | 5               | 4          |
| ...        | ...             | ...        |
*/
CREATE TABLE competitor_event (
    "event_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> event."id"</fk>
    "competitor_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> games_competitor."id"</fk>
    "medal_id" INTEGER NOT NULL,
        -- <example>4</example>
        -- <fk> -> medal."id"</fk>
    FOREIGN KEY ("competitor_id") REFERENCES games_competitor("id"),
    FOREIGN KEY ("event_id") REFERENCES event("id"),
    FOREIGN KEY ("medal_id") REFERENCES medal("id")
);

/*
Schema: NULL
Table: event
Rows: 757
Sample rows:
| id   | sport_id   | event_name                       |
|------|------------|----------------------------------|
| 1    | 9          | Basketball Men's Basketball      |
| 2    | 33         | Judo Men's Extra-Lightweight     |
| 3    | 25         | Football Men's Football          |
| 4    | 62         | Tug-Of-War Men's Tug-Of-War      |
| 5    | 54         | Speed Skating Women's 500 metres |
| ...  | ...        | ...                              |
*/
CREATE TABLE event (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "sport_id" INTEGER NOT NULL,
        -- <example>9</example>
        -- <fk> -> sport."id"</fk>
    "event_name" TEXT NOT NULL,
        -- <example>'Basketball Men's Basketball'</example>
    FOREIGN KEY ("sport_id") REFERENCES sport("id")
);

/*
Schema: NULL
Table: games
Rows: 51
Sample rows:
| id   | games_year   | games_name   | season   |
|------|--------------|--------------|----------|
| 1    | 1992         | 1992 Summer  | Summer   |
| 2    | 2012         | 2012 Summer  | Summer   |
| 3    | 1920         | 1920 Summer  | Summer   |
| 4    | 1900         | 1900 Summer  | Summer   |
| 5    | 1988         | 1988 Winter  | Winter   |
| ...  | ...          | ...          | ...      |
*/
CREATE TABLE games (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "games_year" INTEGER NOT NULL,
        -- <example>1992</example>
    "games_name" TEXT NOT NULL,
        -- <example>'1992 Summer'</example>
    "season" TEXT NOT NULL
        -- <values>{'Summer', 'Winter'}</values>
);

/*
Schema: NULL
Table: games_city
Rows: 52
Sample rows:
| games_id   | city_id   |
|------------|-----------|
| 1          | 1         |
| 2          | 2         |
| 3          | 3         |
| 4          | 4         |
| 5          | 5         |
| ...        | ...       |
*/
CREATE TABLE games_city (
    "games_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> games."id"</fk>
    "city_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> city."id"</fk>
    FOREIGN KEY ("city_id") REFERENCES city("id"),
    FOREIGN KEY ("games_id") REFERENCES games("id")
);

/*
Schema: NULL
Table: games_competitor
Rows: 180252
Sample rows:
| id   | games_id   | person_id   | age   |
|------|------------|-------------|-------|
| 1    | 1          | 1           | 24    |
| 2    | 2          | 2           | 23    |
| 3    | 3          | 3           | 24    |
| 4    | 4          | 4           | 34    |
| 5    | 5          | 5           | 21    |
| ...  | ...        | ...         | ...   |
*/
CREATE TABLE games_competitor (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "games_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> games."id"</fk>
    "person_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> person."id"</fk>
    "age" INTEGER NOT NULL,
        -- <example>24</example>
    FOREIGN KEY ("games_id") REFERENCES games("id"),
    FOREIGN KEY ("person_id") REFERENCES person("id")
);

/*
Schema: NULL
Table: medal
Rows: 4
All rows:
|   id | medal_name   |
|------|--------------|
|    1 | Gold         |
|    2 | Silver       |
|    3 | Bronze       |
|    4 | NA           |
*/
CREATE TABLE medal (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "medal_name" TEXT NOT NULL
        -- <values>{'Bronze', 'Gold', 'NA', 'Silver'}</values>
);

/*
Schema: NULL
Table: noc_region
Rows: 231
Sample rows:
| id   | noc   | region_name          |
|------|-------|----------------------|
| 1    | AFG   | Afghanistan          |
| 2    | AHO   | Netherlands Antilles |
| 3    | ALB   | Albania              |
| 4    | ALG   | Algeria              |
| 5    | AND   | Andorra              |
| ...  | ...   | ...                  |
*/
CREATE TABLE noc_region (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "noc" TEXT NOT NULL,
        -- <example>'AFG'</example>
    "region_name" TEXT NOT NULL
        -- <example>'Afghanistan'</example>
);

/*
Schema: NULL
Table: person
Rows: 128854
Sample rows:
| id   | full_name                | gender   | height   | weight   |
|------|--------------------------|----------|----------|----------|
| 1    | A Dijiang                | M        | 180      | 80       |
| 2    | A Lamusi                 | M        | 170      | 60       |
| 3    | Gunnar Nielsen Aaby      | M        | 0        | 0        |
| 4    | Edgar Lindenau Aabye     | M        | 0        | 0        |
| 5    | Christine Jacoba Aaftink | F        | 185      | 82       |
| ...  | ...                      | ...      | ...      | ...      |
*/
CREATE TABLE person (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "full_name" TEXT NOT NULL,
        -- <example>'A Dijiang'</example>
    "gender" TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    "height" INTEGER NOT NULL,
        -- <example>180</example>
    "weight" INTEGER NOT NULL
        -- <example>80</example>
);

/*
Schema: NULL
Table: person_region
Rows: 130521
Sample rows:
| person_id   | region_id   |
|-------------|-------------|
| 1           | 42          |
| 2           | 42          |
| 3           | 56          |
| 4           | 56          |
| 5           | 146         |
| ...         | ...         |
*/
CREATE TABLE person_region (
    "person_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> person."id"</fk>
    "region_id" INTEGER NOT NULL,
        -- <example>42</example>
        -- <fk> -> noc_region."id"</fk>
    FOREIGN KEY ("person_id") REFERENCES person("id"),
    FOREIGN KEY ("region_id") REFERENCES noc_region("id")
);

/*
Schema: NULL
Table: sport
Rows: 66
Sample rows:
| id   | sport_name       |
|------|------------------|
| 1    | Aeronautics      |
| 2    | Alpine Skiing    |
| 3    | Alpinism         |
| 4    | Archery          |
| 5    | Art Competitions |
| ...  | ...              |
*/
CREATE TABLE sport (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "sport_name" TEXT NOT NULL
        -- <example>'Aeronautics'</example>
);
```