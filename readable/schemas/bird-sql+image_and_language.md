```sql
-- Database: image_and_language

/*
Schema: NULL
Table: ATT_CLASSES
Rows: 699
Sample rows:
| ATT_CLASS_ID   | ATT_CLASS   |
|----------------|-------------|
| 0              | building s  |
| 1              | indoors     |
| 2              | cluttered   |
| 3              | park        |
| 4              | two story   |
| ...            | ...         |
*/
CREATE TABLE ATT_CLASSES (
    "ATT_CLASS_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    "ATT_CLASS" TEXT NOT NULL
        -- <example>'building s'</example>
);

/*
Schema: NULL
Table: IMG_OBJ
Rows: 1750617
Sample rows:
| IMG_ID   | OBJ_SAMPLE_ID   | OBJ_CLASS_ID   | X   | Y   | W   | H   |
|----------|-----------------|----------------|-----|-----|-----|-----|
| 1        | 1               | 298            | 0   | 0   | 799 | 557 |
| 1        | 2               | 246            | 78  | 308 | 722 | 290 |
| 1        | 3               | 293            | 1   | 0   | 222 | 538 |
| 1        | 4               | 239            | 439 | 283 | 359 | 258 |
| 1        | 5               | 295            | 0   | 1   | 135 | 535 |
| ...      | ...             | ...            | ... | ... | ... | ... |
*/
CREATE TABLE IMG_OBJ (
    "IMG_ID" INTEGER NOT NULL,
        -- <example>1</example>
    "OBJ_SAMPLE_ID" INTEGER NOT NULL,
        -- <example>1</example>
    "OBJ_CLASS_ID" INTEGER NOT NULL,
        -- <example>298</example>
        -- <fk> -> OBJ_CLASSES."OBJ_CLASS_ID"</fk>
    "X" INTEGER NOT NULL,
        -- <example>0</example>
    "Y" INTEGER NOT NULL,
        -- <example>0</example>
    "W" INTEGER NOT NULL,
        -- <example>799</example>
    "H" INTEGER NOT NULL,
        -- <example>557</example>
    PRIMARY KEY ("IMG_ID", "OBJ_SAMPLE_ID"),
    FOREIGN KEY ("OBJ_CLASS_ID") REFERENCES OBJ_CLASSES("OBJ_CLASS_ID")
);

/*
Schema: NULL
Table: IMG_OBJ_ATT
Rows: 1074674
Sample rows:
| IMG_ID   | ATT_CLASS_ID   | OBJ_SAMPLE_ID   |
|----------|----------------|-----------------|
| 1113     | 0              | 21              |
| 1113     | 0              | 22              |
| 1113     | 0              | 23              |
| 1113     | 0              | 24              |
| 1113     | 0              | 25              |
| ...      | ...            | ...             |
*/
CREATE TABLE IMG_OBJ_ATT (
    "IMG_ID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk>composite</fk>
    "ATT_CLASS_ID" INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> ATT_CLASSES."ATT_CLASS_ID"</fk>
    "OBJ_SAMPLE_ID" INTEGER NOT NULL,
        -- <example>21</example>
        -- <fk>composite</fk>
    PRIMARY KEY ("IMG_ID", "ATT_CLASS_ID", "OBJ_SAMPLE_ID"),
    FOREIGN KEY ("ATT_CLASS_ID") REFERENCES ATT_CLASSES("ATT_CLASS_ID"),
    FOREIGN KEY ("IMG_ID", "OBJ_SAMPLE_ID") REFERENCES IMG_OBJ("IMG_ID", "OBJ_SAMPLE_ID")
);

/*
Schema: NULL
Table: IMG_REL
Rows: 763159
Sample rows:
| IMG_ID   | PRED_CLASS_ID   | OBJ1_SAMPLE_ID   | OBJ2_SAMPLE_ID   |
|----------|-----------------|------------------|------------------|
| 675      | 0               | 13               | 1                |
| 1193     | 0               | 12               | 34               |
| 3447     | 0               | 4                | 5                |
| 2316535  | 0               | 17               | 9                |
| 2316535  | 0               | 33               | 8                |
| ...      | ...             | ...              | ...              |
*/
CREATE TABLE IMG_REL (
    "IMG_ID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "PRED_CLASS_ID" INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> PRED_CLASSES."PRED_CLASS_ID"</fk>
    "OBJ1_SAMPLE_ID" INTEGER NOT NULL,
        -- <example>13</example>
        -- <fk>composite</fk>
    "OBJ2_SAMPLE_ID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk>composite</fk>
    PRIMARY KEY ("IMG_ID", "PRED_CLASS_ID", "OBJ1_SAMPLE_ID", "OBJ2_SAMPLE_ID"),
    FOREIGN KEY ("PRED_CLASS_ID") REFERENCES PRED_CLASSES("PRED_CLASS_ID"),
    FOREIGN KEY ("IMG_ID", "OBJ1_SAMPLE_ID") REFERENCES IMG_OBJ("IMG_ID", "OBJ_SAMPLE_ID"),
    FOREIGN KEY ("IMG_ID", "OBJ2_SAMPLE_ID") REFERENCES IMG_OBJ("IMG_ID", "OBJ_SAMPLE_ID")
);

/*
Schema: NULL
Table: OBJ_CLASSES
Rows: 300
Sample rows:
| OBJ_CLASS_ID   | OBJ_CLASS   |
|----------------|-------------|
| 0              | awning      |
| 1              | goggles     |
| 2              | dot         |
| 3              | kitchen     |
| 4              | feathers    |
| ...            | ...         |
*/
CREATE TABLE OBJ_CLASSES (
    "OBJ_CLASS_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    "OBJ_CLASS" TEXT NOT NULL
        -- <example>'awning'</example>
);

/*
Schema: NULL
Table: PRED_CLASSES
Rows: 150
Sample rows:
| PRED_CLASS_ID   | PRED_CLASS   |
|-----------------|--------------|
| 0               | playing on   |
| 1               | looking a    |
| 2               | to left of   |
| 3               | beyond       |
| 4               | covers       |
| ...             | ...          |
*/
CREATE TABLE PRED_CLASSES (
    "PRED_CLASS_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    "PRED_CLASS" TEXT NOT NULL
        -- <example>'playing on'</example>
);
```