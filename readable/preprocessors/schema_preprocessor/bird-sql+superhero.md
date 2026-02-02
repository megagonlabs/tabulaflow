```sql
-- Database: superhero

-- Table: alignment (4 rows)
CREATE TABLE alignment (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Alignment identifier — unique primary key for the alignment table that identifies each moral/ethical stance label.</description>
        -- <example>1</example>
    alignment TEXT NULL
        -- <description>Character moral/ethical alignment that describes the hero's typical attitude and behavior.</description>
        -- <values>{'Bad', 'Good', 'N/A', 'Neutral'}</values>
);

-- Table: attribute (6 rows)
CREATE TABLE attribute (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Attribute identifier — unique id for each attribute (six rows, values 1–6, no nulls).</description>
        -- <example>1</example>
    attribute_name TEXT NULL
        -- <description>Attribute name — label identifying a measurable superhero characteristic used to evaluate and compare heroes; referenced by hero_attribute to store per-hero attribute scores.</description>
        -- <values>{'Combat', 'Durability', 'Intelligence', 'Power', 'Speed', 'Strength'}</values>
);

-- Table: colour (35 rows)
CREATE TABLE colour (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Colour identifier — unique identifier for each row in the colour table.</description>
        -- <example>1</example>
    colour TEXT NULL
        -- <description>Color name lookup for superhero appearance (used for skin, eye and hair colors); contains labels such as 'Purple', 'Black/Blue', 'Blue/White' and combined names like 'Yellow/Red'.</description>
        -- <example>'No Colour'</example>
);

-- Table: gender (3 rows)
CREATE TABLE gender (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Identifier for entries in the gender lookup table.</description>
        -- <example>1</example>
    gender TEXT NULL
        -- <description>Character gender label — records each superhero's reported gender for categorization, filtering, and analysis.</description>
        -- <values>{'Female', 'Male', 'N/A'}</values>
);

-- Table: hero_attribute (3738 rows)
CREATE TABLE hero_attribute (
    hero_id INTEGER NULL,
        -- <description>hero identifier — identifies which superhero the attribute record applies to.</description>
        -- <example>1</example>
        -- <fk> -> superhero.id</fk>
    attribute_id INTEGER NULL,
        -- <description>Attribute reference linking a hero to a specific attribute (for example: Intelligence, Strength, Speed, Power, Combat, Durability).</description>
        -- <example>1</example>
        -- <fk> -> attribute.id</fk>
    attribute_value INTEGER NULL,
        -- <description>Attribute rating — an integer score representing a hero's level for the linked attribute; higher values mean greater ability (observed range 5–100).</description>
        -- <example>80</example>
    FOREIGN KEY (attribute_id) REFERENCES attribute(id),
    FOREIGN KEY (hero_id) REFERENCES superhero(id)
);

-- Table: hero_power (5825 rows)
CREATE TABLE hero_power (
    hero_id INTEGER NULL,
        -- <description>Hero identifier (foreign key to superhero.id) — identifies the hero associated with this power; populated for all 5,825 rows and covers 652 distinct heroes with no orphaned references.</description>
        -- <example>1</example>
        -- <fk> -> superhero.id</fk>
    power_id INTEGER NULL,
        -- <description>Superpower identifier — the superpower assigned to a hero (links each hero_power row to a specific entry in superpower). All 5,825 rows have a non‑null, valid power_id; 167 distinct power_ids are used and there are no orphaned references.</description>
        -- <example>1</example>
        -- <fk> -> superpower.id</fk>
    FOREIGN KEY (hero_id) REFERENCES superhero(id),
    FOREIGN KEY (power_id) REFERENCES superpower(id)
);

-- Table: publisher (25 rows)
CREATE TABLE publisher (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Publisher identifier — unique primary key for the publisher table, used to identify each publisher record.</description>
        -- <example>1</example>
    publisher_name TEXT NULL
        -- <description>Publisher name — the publisher's official name (one record per publisher). Values are unique across the table (25 distinct names); there are no NULLs and one row contains an empty string.</description>
        -- <example>''</example>
);

-- Table: race (61 rows)
CREATE TABLE race (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for each race; referenced by superhero.race_id to link heroes to their race.</description>
        -- <example>1</example>
    race TEXT NULL
        -- <description>Race/species — the named race, species, or group (real or fictional) a superhero belongs to. Example values include Amazon, Martian, Korugaran, Bizarro; the race table contains 61 distinct entries.</description>
        -- <example>'-'</example>
);

-- Table: superhero (750 rows)
CREATE TABLE superhero (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for each superhero — the table's primary key (750 distinct non-null values observed, ranging from 1 to 756).</description>
        -- <example>1</example>
    superhero_name TEXT NULL,
        -- <description>Superhero name — the hero's primary display name used to identify a character (e.g., "3-D Man", "A-Bomb", "Abe Sapien"). Mostly unique across the table (743 distinct values out of 750 rows) and contains no empty/null entries.</description>
        -- <example>'3-D Man'</example>
    full_name TEXT NULL,
        -- <description>Civilian or real full name of the superhero (given and family name), when known — many records are blank or unknown.</description>
        -- <example>'Charles Chandler'</example>
    gender_id INTEGER NULL,
        -- <description>Reference to the superhero's gender (foreign key to gender.id).</description>
        -- <example>1</example>
        -- <fk> -> gender.id</fk>
    eye_colour_id INTEGER NULL,
        -- <description>Eye colour identifier (FK to colour.id) — indicates each hero's eye color; populated for all 750 heroes with 21 distinct colour IDs. Most frequent values include Blue, No Colour and Brown.</description>
        -- <example>9</example>
        -- <fk> -> colour.id</fk>
    hair_colour_id INTEGER NULL,
        -- <description>Hair colour reference (FK to colour.id) — links each superhero to the colour table entry that describes their hair colour. Most rows are populated (750/750) with 26 distinct hair colours; the most common value is “No Colour” (246 rows), followed by Black and Blond.</description>
        -- <example>13</example>
        -- <fk> -> colour.id</fk>
    skin_colour_id INTEGER NULL,
        -- <description>Superhero skin color identifier (references the colour lookup); most records use the placeholder 'No Colour' and the rest map to specific skin colours (e.g., Green, Blue, Red variants).</description>
        -- <example>1</example>
        -- <fk> -> colour.id</fk>
    race_id INTEGER NULL,
        -- <description>Foreign-key to race.id identifying a hero's race (e.g., Human, Mutant). Populated for most rows (746/750); 61 distinct race values; 4 NULLs.</description>
        -- <example>1</example>
        -- <fk> -> race.id</fk>
    publisher_id INTEGER NULL,
        -- <description>Publisher reference — foreign key to publisher.id identifying the superhero's publisher; mostly populated with 747 of 750 rows non‑NULL and 25 distinct publishers (top: Marvel Comics, DC Comics).</description>
        -- <example>13</example>
        -- <fk> -> publisher.id</fk>
    alignment_id INTEGER NULL,
        -- <description>Hero alignment reference — identifies a superhero’s moral alignment (links to the alignment lookup). Mostly populated: Good (504), Bad (212), Neutral (28); 6 rows NULL.</description>
        -- <example>1</example>
        -- <fk> -> alignment.id</fk>
    height_cm INTEGER NULL,
        -- <description>Height in centimeters — recorded measurement of a hero's height. Contains many zeros used as missing-value markers and a small number of extreme outliers, so values should be validated before analysis.</description>
        -- <example>188</example>
    weight_kg INTEGER NULL,
        -- <description>Superhero weight in kilograms — contains real measurements but also NULLs, many zero values used as missing-placeholders, and a few extreme outliers (e.g. 90,000,000) that appear to be data errors.</description>
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
        -- <description>Superpower identifier — unique identifier for each superpower record; referenced by hero_power.power_id to link heroes to powers.</description>
        -- <example>1</example>
    power_name TEXT NULL
        -- <description>Superpower name — the canonical name/label for a superpower (examples: 'Agility', 'Power Suit', 'Size Changing'). All 167 rows are populated and distinct in this dataset.</description>
        -- <example>'Agility'</example>
);
```