```sql
-- Database: image_and_language

-- Table: ATT_CLASSES (699 rows)
CREATE TABLE ATT_CLASSES (
    ATT_CLASS_ID INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    ATT_CLASS TEXT NOT NULL
        -- <example>'building s'</example>
);

-- Table: IMG_OBJ (1750617 rows)
CREATE TABLE IMG_OBJ (
    IMG_ID INTEGER NOT NULL,
        -- <example>1</example>
    OBJ_SAMPLE_ID INTEGER NOT NULL,
        -- <example>1</example>
    OBJ_CLASS_ID INTEGER NULL,
        -- <example>298</example>
        -- <fk> -> OBJ_CLASSES.OBJ_CLASS_ID</fk>
    X INTEGER NULL,
        -- <example>0</example>
    Y INTEGER NULL,
        -- <example>0</example>
    W INTEGER NULL,
        -- <example>799</example>
    H INTEGER NULL,
        -- <example>557</example>
    PRIMARY KEY (IMG_ID, OBJ_SAMPLE_ID),
    FOREIGN KEY (OBJ_CLASS_ID) REFERENCES OBJ_CLASSES(OBJ_CLASS_ID)
);

-- Table: IMG_OBJ_ATT (1074674 rows)
CREATE TABLE IMG_OBJ_ATT (
    IMG_ID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk>composite</fk>
    ATT_CLASS_ID INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> ATT_CLASSES.ATT_CLASS_ID</fk>
    OBJ_SAMPLE_ID INTEGER NOT NULL,
        -- <example>21</example>
        -- <fk>composite</fk>
    PRIMARY KEY (IMG_ID, ATT_CLASS_ID, OBJ_SAMPLE_ID),
    FOREIGN KEY (ATT_CLASS_ID) REFERENCES ATT_CLASSES(ATT_CLASS_ID),
    FOREIGN KEY (IMG_ID, OBJ_SAMPLE_ID) REFERENCES IMG_OBJ(IMG_ID, OBJ_SAMPLE_ID)
);

-- Table: IMG_REL (763159 rows)
CREATE TABLE IMG_REL (
    IMG_ID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    PRED_CLASS_ID INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> PRED_CLASSES.PRED_CLASS_ID</fk>
    OBJ1_SAMPLE_ID INTEGER NOT NULL,
        -- <example>13</example>
        -- <fk>composite</fk>
    OBJ2_SAMPLE_ID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk>composite</fk>
    PRIMARY KEY (IMG_ID, PRED_CLASS_ID, OBJ1_SAMPLE_ID, OBJ2_SAMPLE_ID),
    FOREIGN KEY (PRED_CLASS_ID) REFERENCES PRED_CLASSES(PRED_CLASS_ID),
    FOREIGN KEY (IMG_ID, OBJ1_SAMPLE_ID) REFERENCES IMG_OBJ(IMG_ID, OBJ_SAMPLE_ID),
    FOREIGN KEY (IMG_ID, OBJ2_SAMPLE_ID) REFERENCES IMG_OBJ(IMG_ID, OBJ_SAMPLE_ID)
);

-- Table: OBJ_CLASSES (300 rows)
CREATE TABLE OBJ_CLASSES (
    OBJ_CLASS_ID INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    OBJ_CLASS TEXT NOT NULL
        -- <example>'awning'</example>
);

-- Table: PRED_CLASSES (150 rows)
CREATE TABLE PRED_CLASSES (
    PRED_CLASS_ID INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    PRED_CLASS TEXT NOT NULL
        -- <example>'playing on'</example>
);
```