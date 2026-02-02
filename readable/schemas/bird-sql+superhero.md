```sql
-- Database: superhero

-- Table: alignment (4 rows)
CREATE TABLE alignment (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    alignment TEXT NULL
        -- <values>{'Bad', 'Good', 'N/A', 'Neutral'}</values>
);

-- Table: attribute (6 rows)
CREATE TABLE attribute (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    attribute_name TEXT NULL
        -- <values>{'Combat', 'Durability', 'Intelligence', 'Power', 'Speed', 'Strength'}</values>
);

-- Table: colour (35 rows)
CREATE TABLE colour (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    colour TEXT NULL
        -- <example>'No Colour'</example>
);

-- Table: gender (3 rows)
CREATE TABLE gender (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    gender TEXT NULL
        -- <values>{'Female', 'Male', 'N/A'}</values>
);

-- Table: hero_attribute (3738 rows)
CREATE TABLE hero_attribute (
    hero_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> superhero.id</fk>
    attribute_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> attribute.id</fk>
    attribute_value INTEGER NULL,
        -- <example>80</example>
    FOREIGN KEY (attribute_id) REFERENCES attribute(id),
    FOREIGN KEY (hero_id) REFERENCES superhero(id)
);

-- Table: hero_power (5825 rows)
CREATE TABLE hero_power (
    hero_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> superhero.id</fk>
    power_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> superpower.id</fk>
    FOREIGN KEY (hero_id) REFERENCES superhero(id),
    FOREIGN KEY (power_id) REFERENCES superpower(id)
);

-- Table: publisher (25 rows)
CREATE TABLE publisher (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    publisher_name TEXT NULL
        -- <example>''</example>
);

-- Table: race (61 rows)
CREATE TABLE race (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    race TEXT NULL
        -- <example>'-'</example>
);

-- Table: superhero (750 rows)
CREATE TABLE superhero (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    superhero_name TEXT NULL,
        -- <example>'3-D Man'</example>
    full_name TEXT NULL,
        -- <example>'Charles Chandler'</example>
    gender_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> gender.id</fk>
    eye_colour_id INTEGER NULL,
        -- <example>9</example>
        -- <fk> -> colour.id</fk>
    hair_colour_id INTEGER NULL,
        -- <example>13</example>
        -- <fk> -> colour.id</fk>
    skin_colour_id INTEGER NULL,
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

-- Table: superpower (167 rows)
CREATE TABLE superpower (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    power_name TEXT NULL
        -- <example>'Agility'</example>
);
```