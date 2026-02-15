```sql
-- Database: shakespeare

/*
Schema: NULL
Table: chapters
Rows: 945
Sample rows:
| id    | Act   | Scene   | Description           | work_id   |
|-------|-------|---------|-----------------------|-----------|
| 18704 | 1     | 1       | DUKE ORSINO’s palace. | 1         |
| 18705 | 1     | 2       | The sea-coast.        | 1         |
| 18706 | 1     | 3       | OLIVIA’S house.       | 1         |
| 18707 | 1     | 4       | DUKE ORSINO’s palace. | 1         |
| 18708 | 1     | 5       | OLIVIA’S house.       | 1         |
| ...   | ...   | ...     | ...                   | ...       |
*/
CREATE TABLE chapters (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>18704</example>
    "Act" INTEGER NOT NULL,
        -- <example>1</example>
    "Scene" INTEGER NOT NULL,
        -- <example>1</example>
    "Description" TEXT NOT NULL,
        -- <example>'DUKE ORSINO’s palace.'</example>
    "work_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> works."id"</fk>
    FOREIGN KEY ("work_id") REFERENCES works("id")
);

/*
Schema: NULL
Table: characters
Rows: 1266
Sample rows:
| id   | CharName          | Abbrev            | Description   |
|------|-------------------|-------------------|---------------|
| 1    | First Apparition  | First Apparition  |               |
| 2    | First Citizen     | First Citizen     |               |
| 3    | First Conspirator | First Conspirator |               |
| 4    | First Gentleman   | First Gentleman   |               |
| 5    | First Goth        | First Goth        |               |
| ...  | ...               | ...               | ...           |
*/
CREATE TABLE characters (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "CharName" TEXT NOT NULL,
        -- <example>'First Apparition'</example>
    "Abbrev" TEXT NOT NULL,
        -- <example>'First Apparition'</example>
    "Description" TEXT NOT NULL
        -- <example>''</example>
);

/*
Schema: NULL
Table: paragraphs
Rows: 35126
Sample rows:
| id     | ParagraphNum   | PlainText                                                        | character_id   | chapter_id   |
|--------|----------------|------------------------------------------------------------------|----------------|--------------|
| 630863 | 3              | [Enter DUKE ORSINO, CURIO, and other Lords; Musicians attending] | 1261           | 18704        |
| 630864 | 4              | If music be the food of love, play on;
Give me excess of it, that, surfeiting,
The appetite may sick...ement and low price,
Even in a minute: so full of shapes is fancy
That it alone is high fantastical.                                                                  | 840            | 18704        |
| 630865 | 19             | Will you go hunt, my lord?                                       | 297            | 18704        |
| 630866 | 20             | What, Curio?                                                     | 840            | 18704        |
| 630867 | 21             | The hart.                                                        | 297            | 18704        |
| ...    | ...            | ...                                                              | ...            | ...          |
*/
CREATE TABLE paragraphs (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>630863</example>
    "ParagraphNum" INTEGER NOT NULL,
        -- <example>3</example>
    "PlainText" TEXT NOT NULL,
        -- <example>'[Enter DUKE ORSINO, CURIO, and other Lords; Musicians attending]'</example>
    "character_id" INTEGER NOT NULL,
        -- <example>1261</example>
        -- <fk> -> characters."id"</fk>
    "chapter_id" INTEGER NOT NULL,
        -- <example>18704</example>
        -- <fk> -> chapters."id"</fk>
    FOREIGN KEY ("chapter_id") REFERENCES chapters("id"),
    FOREIGN KEY ("character_id") REFERENCES characters("id")
);

/*
Schema: NULL
Table: works
Rows: 43
Sample rows:
| id   | Title                     | LongTitle                       | Date   | GenreType   |
|------|---------------------------|---------------------------------|--------|-------------|
| 1    | Twelfth Night             | Twelfth Night, Or What You Will | 1599   | Comedy      |
| 2    | All's Well That Ends Well | All's Well That Ends Well       | 1602   | Comedy      |
| 3    | Antony and Cleopatra      | Antony and Cleopatra            | 1606   | Tragedy     |
| 4    | As You Like It            | As You Like It                  | 1599   | Comedy      |
| 5    | Comedy of Errors          | The Comedy of Errors            | 1589   | Comedy      |
| ...  | ...                       | ...                             | ...    | ...         |
*/
CREATE TABLE works (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Title" TEXT NOT NULL,
        -- <example>'Twelfth Night'</example>
    "LongTitle" TEXT NOT NULL,
        -- <example>'Twelfth Night, Or What You Will'</example>
    "Date" INTEGER NOT NULL,
        -- <example>1599</example>
    "GenreType" TEXT NOT NULL
        -- <values>{'Comedy', 'History', 'Poem', 'Sonnet', 'Tragedy'}</values>
);
```