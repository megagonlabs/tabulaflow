```sql
-- Database: superhero

/*
Schema: NULL
Table: alignment
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
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Alignment identifier — unique primary key for the alignment lookup table, used to reference a character's moral alignment (e.g., Good, Bad, Neutral) and referenced by superhero.alignment_id.</description>
        -- <example>1</example>
    "alignment" TEXT NOT NULL
        -- <description>Character moral alignment — the superhero's moral and ethical stance used to categorize their overall attitude and behavior (e.g., acting altruistically, self‑interestedly, or neutrally).</description>
        -- <values>{'Bad', 'Good', 'N/A', 'Neutral'}</values>
);

/*
Schema: NULL
Table: attribute
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
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Attribute identifier — unique primary key for each attribute, used to reference attributes from other tables (e.g., hero_attribute.attribute_id).</description>
        -- <example>1</example>
    "attribute_name" TEXT NOT NULL
        -- <description>Superhero attribute name — the name of a characteristic or capability used to describe and compare a hero's abilities (a physical or mental trait).</description>
        -- <values>{'Combat', 'Durability', 'Intelligence', 'Power', 'Speed', 'Strength'}</values>
);

/*
Schema: NULL
Table: colour
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
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Colour identifier</description>
        -- <example>1</example>
    "colour" TEXT NOT NULL
        -- <description>Superhero color — color used to describe a hero's skin, eye, hair or similar visual attributes (e.g., 'Purple', 'Black/Blue', 'Blue/White').</description>
        -- <example>'No Colour'</example>
);

/*
Schema: NULL
Table: gender
Rows: 3
All rows:
|   id | gender   |
|------|----------|
|    1 | Male     |
|    2 | Female   |
|    3 | N/A      |
*/
CREATE TABLE gender (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Gender identifier — unique identifier for rows in the gender lookup table (maps to entries like Male, Female, N/A).</description>
        -- <example>1</example>
    "gender" TEXT NOT NULL
        -- <description>Superhero gender label — a lookup/reference value describing a hero's gender (referenced by superhero.gender_id).</description>
        -- <values>{'Female', 'Male', 'N/A'}</values>
);

/*
Schema: NULL
Table: hero_attribute
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
    "hero_id" INTEGER NOT NULL,
        -- <description>Hero identifier linking an attribute-value record to the superhero it describes.</description>
        -- <example>1</example>
        -- <fk> -> superhero."id"</fk>
    "attribute_id" INTEGER NOT NULL,
        -- <description>Attribute identifier linking this row to attribute.id — a foreign key that specifies which attribute (e.g., Strength, Intelligence, Speed) the attribute_value applies to.</description>
        -- <example>1</example>
        -- <fk> -> attribute."id"</fk>
    "attribute_value" INTEGER NOT NULL,
        -- <description>Numeric score for a hero's level in the specified attribute — a higher value indicates greater proficiency or power for that hero-attribute pair.</description>
        -- <example>80</example>
    FOREIGN KEY ("attribute_id") REFERENCES attribute("id"),
    FOREIGN KEY ("hero_id") REFERENCES superhero("id")
);

/*
Schema: NULL
Table: hero_power
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
    "hero_id" INTEGER NOT NULL,
        -- <description>Hero identifier (foreign key to superhero.id) linking each power entry to the corresponding superhero.</description>
        -- <example>1</example>
        -- <fk> -> superhero."id"</fk>
    "power_id" INTEGER NOT NULL,
        -- <description>Reference to a hero's superpower — identifies the specific ability assigned to the hero (powers are the character's distinct abilities, separate from broader attributes).</description>
        -- <example>1</example>
        -- <fk> -> superpower."id"</fk>
    FOREIGN KEY ("hero_id") REFERENCES superhero("id"),
    FOREIGN KEY ("power_id") REFERENCES superpower("id")
);

/*
Schema: NULL
Table: publisher
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
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Publisher identifier — unique identifier for each publisher record.</description>
        -- <example>1</example>
    "publisher_name" TEXT NOT NULL
        -- <description>Publisher name — the name of the company or organization that published the character's title (e.g., Wildstorm, South Park, IDW Publishing). May be blank when unknown.</description>
        -- <example>''</example>
);

/*
Schema: NULL
Table: race
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
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Race identifier — unique identifier for entries in the race lookup table.</description>
        -- <example>1</example>
    "race" TEXT NOT NULL
        -- <description>Superhero race/species — the character's biological or cultural group (fictional or real-world), e.g., Amazon, Martian, Korugaran.</description>
        -- <example>'-'</example>
);

/*
Schema: NULL
Table: superhero
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
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for a superhero, used to reference the superhero from other tables (e.g., hero_attribute, hero_power).</description>
        -- <example>1</example>
    "superhero_name" TEXT NOT NULL,
        -- <description>Superhero name — the primary display name or alias used to identify a character (the name readers/players would commonly use; e.g., 'She-Thing', 'Valerie Hart', '3-D Man').</description>
        -- <example>'3-D Man'</example>
    "full_name" TEXT NULL,
        -- <description>Superhero's full personal name (given name and surname); may be NULL when the real name is unknown or not provided.</description>
        -- <example>'Charles Chandler'</example>
    "gender_id" INTEGER NOT NULL,
        -- <description>Hero gender identifier linking each superhero to the gender lookup table (gender.id).</description>
        -- <example>1</example>
        -- <fk> -> gender."id"</fk>
    "eye_colour_id" INTEGER NOT NULL,
        -- <description>Eye color identifier linking the superhero to the colour table (foreign key to colour.id).</description>
        -- <example>9</example>
        -- <fk> -> colour."id"</fk>
    "hair_colour_id" INTEGER NOT NULL,
        -- <description>Hair-colour identifier linking each superhero to a row in the colour table (foreign key -> colour.id).</description>
        -- <example>13</example>
        -- <fk> -> colour."id"</fk>
    "skin_colour_id" INTEGER NOT NULL,
        -- <description>Skin color identifier linking the hero to the colour table (foreign key to colour.id) used to look up the hero's skin color name.</description>
        -- <example>1</example>
        -- <fk> -> colour."id"</fk>
    "race_id" INTEGER NULL,
        -- <description>Race reference linking to race.id; NULL when the superhero's race is unknown.</description>
        -- <example>1</example>
        -- <fk> -> race."id"</fk>
    "publisher_id" INTEGER NULL,
        -- <description>Publisher identifier for the superhero — the foreign-key id that associates a hero with their publisher record.</description>
        -- <example>13</example>
        -- <fk> -> publisher."id"</fk>
    "alignment_id" INTEGER NULL,
        -- <description>Alignment identifier linking the superhero to the alignment table (foreign key to alignment.id), indicating the character's moral/ethical stance (e.g., Good, Bad, Neutral). Use NULL when the alignment is unknown or not recorded.</description>
        -- <example>1</example>
        -- <fk> -> alignment."id"</fk>
    "height_cm" INTEGER NULL,
        -- <description>Superhero height (centimetres); NULL or 0 indicates the height is missing.</description>
        -- <example>188</example>
    "weight_kg" INTEGER NULL,
        -- <description>Superhero weight (kilograms). NULL or 0 indicates the weight is missing.</description>
        -- <example>90</example>
    FOREIGN KEY ("alignment_id") REFERENCES alignment("id"),
    FOREIGN KEY ("eye_colour_id") REFERENCES colour("id"),
    FOREIGN KEY ("gender_id") REFERENCES gender("id"),
    FOREIGN KEY ("hair_colour_id") REFERENCES colour("id"),
    FOREIGN KEY ("publisher_id") REFERENCES publisher("id"),
    FOREIGN KEY ("race_id") REFERENCES race("id"),
    FOREIGN KEY ("skin_colour_id") REFERENCES colour("id")
);

/*
Schema: NULL
Table: superpower
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
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Superpower identifier used to reference a specific superpower across the database (e.g., referenced by hero_power.power_id).</description>
        -- <example>1</example>
    "power_name" TEXT NOT NULL
        -- <description>Superpower name — the canonical/display name of a superpower used to identify a hero's ability (examples: 'Agility', 'Lantern Power Ring', 'Size Changing').</description>
        -- <example>'Agility'</example>
);
```