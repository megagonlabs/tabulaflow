```sql
-- Database: shakespeare

-- Table: chapters (945 rows)
CREATE TABLE chapters (
    id INTEGER NULL PRIMARY KEY,
        -- <example>18704</example>
    Act INTEGER NOT NULL,
        -- <example>1</example>
    Scene INTEGER NOT NULL,
        -- <example>1</example>
    Description TEXT NOT NULL,
        -- <example>'DUKE ORSINO’s palace.'</example>
    work_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> works.id</fk>
    FOREIGN KEY (work_id) REFERENCES works(id)
);

-- Table: characters (1266 rows)
CREATE TABLE characters (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    CharName TEXT NOT NULL,
        -- <example>'First Apparition'</example>
    Abbrev TEXT NOT NULL,
        -- <example>'First Apparition'</example>
    Description TEXT NOT NULL
        -- <example>''</example>
);

-- Table: paragraphs (35126 rows)
CREATE TABLE paragraphs (
    id INTEGER NULL PRIMARY KEY,
        -- <example>630863</example>
    ParagraphNum INTEGER NOT NULL,
        -- <example>3</example>
    PlainText TEXT NOT NULL,
        -- <example>'[Enter DUKE ORSINO, CURIO, and other Lords; Musicians attending]'</example>
    character_id INTEGER NOT NULL,
        -- <example>1261</example>
        -- <fk> -> characters.id</fk>
    chapter_id INTEGER NOT NULL,
        -- <example>18704</example>
        -- <fk> -> chapters.id</fk>
    FOREIGN KEY (chapter_id) REFERENCES chapters(id),
    FOREIGN KEY (character_id) REFERENCES characters(id)
);

-- Table: works (43 rows)
CREATE TABLE works (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Title TEXT NOT NULL,
        -- <example>'Twelfth Night'</example>
    LongTitle TEXT NOT NULL,
        -- <example>'Twelfth Night, Or What You Will'</example>
    Date INTEGER NOT NULL,
        -- <example>1599</example>
    GenreType TEXT NOT NULL
        -- <values>{'Comedy', 'History', 'Poem', 'Sonnet', 'Tragedy'}</values>
);
```