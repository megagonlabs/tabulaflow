```sql
-- Database: superhero

/*
Schema: NULLTable: alignment
Rows: 4
All rows:
|   id | alignment   |
|------|-------------|
|    1 | Good        |
|    2 | Bad         |
|    3 | Neutral     |
|    4 | N/A         |
*/
CREATE TABLE alignment (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    alignment TEXT NOT NULL
        -- <values>{'Bad', 'Good', 'N/A', 'Neutral'}</values>
);

/*
Schema: NULLTable: attribute
Rows: 6
All rows:
|   id | attribute_name   |
|------|------------------|
|    1 | Intelligence     |
|    2 | Strength         |
|    3 | Speed            |
|    4 | Durability       |
|    5 | Power            |
|    6 | Combat           |
*/
CREATE TABLE attribute (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    attribute_name TEXT NOT NULL
        -- <values>{'Combat', 'Durability', 'Intelligence', 'Power', 'Speed', 'Strength'}</values>
);

/*
Schema: NULLTable: colour
Rows: 35
Sample rows:
| id   | colour     |
|------|------------|
| 1    | No Colour  |
| 2    | Amber      |
| 3    | Auburn     |
| 4    | Black      |
| 5    | Black/Blue |
| ...  | ...        |
*/
CREATE TABLE colour (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    colour TEXT NOT NULL
        -- <example>'No Colour'</example>
);

/*
Schema: NULLTable: gender
Rows: 3
All rows:
|   id | gender   |
|------|----------|
|    1 | Male     |
|    2 | Female   |
|    3 | N/A      |
*/
CREATE TABLE gender (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    gender TEXT NOT NULL
        -- <values>{'Female', 'Male', 'N/A'}</values>
);

/*
Schema: NULLTable: hero_attribute
Rows: 3738
Sample rows:
| hero_id   | attribute_id   | attribute_value   |
|-----------|----------------|-------------------|
| 1         | 1              | 80                |
| 2         | 1              | 75                |
| 3         | 1              | 95                |
| 4         | 1              | 80                |
| 5         | 1              | 85                |
| ...       | ...            | ...               |
*/
CREATE TABLE hero_attribute (
    hero_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> superhero.id</fk>
    attribute_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> attribute.id</fk>
    attribute_value INTEGER NOT NULL,
        -- <example>80</example>
    FOREIGN KEY (attribute_id) REFERENCES attribute(id),
    FOREIGN KEY (hero_id) REFERENCES superhero(id)
);

/*
Schema: NULLTable: hero_power
Rows: 5825
Sample rows:
| hero_id   | power_id   |
|-----------|------------|
| 1         | 1          |
| 1         | 18         |
| 1         | 26         |
| 1         | 31         |
| 2         | 2          |
| ...       | ...        |
*/
CREATE TABLE hero_power (
    hero_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> superhero.id</fk>
    power_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> superpower.id</fk>
    FOREIGN KEY (hero_id) REFERENCES superhero(id),
    FOREIGN KEY (power_id) REFERENCES superpower(id)
);

/*
Schema: NULLTable: publisher
Rows: 25
Sample rows:
| id   | publisher_name    |
|------|-------------------|
| 1    |                   |
| 2    | ABC Studios       |
| 3    | Dark Horse Comics |
| 4    | DC Comics         |
| 5    | George Lucas      |
| ...  | ...               |
*/
CREATE TABLE publisher (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    publisher_name TEXT NOT NULL
        -- <example>''</example>
);

/*
Schema: NULLTable: race
Rows: 61
Sample rows:
| id   | race    |
|------|---------|
| 1    | -       |
| 2    | Alien   |
| 3    | Alpha   |
| 4    | Amazon  |
| 5    | Android |
| ...  | ...     |
*/
CREATE TABLE race (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    race TEXT NOT NULL
        -- <example>'-'</example>
);

/*
Schema: NULLTable: superhero
Rows: 750
Sample rows:
| id   | superhero_name   | full_name              | gender_id   | eye_colour_id   | hair_colour_id   | skin_colour_id   | race_id   | publisher_id   | alignment_id   | height_cm   | weight_kg   |
|------|------------------|------------------------|-------------|-----------------|------------------|------------------|-----------|----------------|----------------|-------------|-------------|
| 1    | 3-D Man          | Charles Chandler       | 1           | 9               | 13               | 1                | 1         | 13             | 1              | 188         | 90          |
| 2    | A-Bomb           | Richard Milhouse Jones | 1           | 33              | 1                | 1                | 24        | 13             | 1              | 203         | 441         |
| 3    | Abe Sapien       | Abraham Sapien         | 1           | 7               | 1                | 7                | 33        | 3              | 1              | 191         | 65          |
| 4    | Abin Sur         | -                      | 1           | 7               | 1                | 23               | 55        | 4              | 1              | 185         | 90          |
| 5    | Abomination      | Emil Blonsky           | 1           | 14              | 1                | 1                | 28        | 13             | 2              | 203         | 441         |
| ...  | ...              | ...                    | ...         | ...             | ...              | ...              | ...       | ...            | ...            | ...         | ...         |
*/
CREATE TABLE superhero (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    superhero_name TEXT NOT NULL,
        -- <example>'3-D Man'</example>
    full_name TEXT NULL,
        -- <example>'Charles Chandler'</example>
    gender_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> gender.id</fk>
    eye_colour_id INTEGER NOT NULL,
        -- <example>9</example>
        -- <fk> -> colour.id</fk>
    hair_colour_id INTEGER NOT NULL,
        -- <example>13</example>
        -- <fk> -> colour.id</fk>
    skin_colour_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> colour.id</fk>
    race_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> race.id</fk>
    publisher_id INTEGER NULL,
        -- <example>13</example>
        -- <fk> -> publisher.id</fk>
    alignment_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> alignment.id</fk>
    height_cm INTEGER NULL,
        -- <example>188</example>
    weight_kg INTEGER NULL,
        -- <example>90</example>
    FOREIGN KEY (alignment_id) REFERENCES alignment(id),
    FOREIGN KEY (eye_colour_id) REFERENCES colour(id),
    FOREIGN KEY (gender_id) REFERENCES gender(id),
    FOREIGN KEY (hair_colour_id) REFERENCES colour(id),
    FOREIGN KEY (publisher_id) REFERENCES publisher(id),
    FOREIGN KEY (race_id) REFERENCES race(id),
    FOREIGN KEY (skin_colour_id) REFERENCES colour(id)
);

/*
Schema: NULLTable: superpower
Rows: 167
Sample rows:
| id   | power_name            |
|------|-----------------------|
| 1    | Agility               |
| 2    | Accelerated Healing   |
| 3    | Lantern Power Ring    |
| 4    | Dimensional Awareness |
| 5    | Cold Resistance       |
| ...  | ...                   |
*/
CREATE TABLE superpower (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    power_name TEXT NOT NULL
        -- <example>'Agility'</example>
);
```