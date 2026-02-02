```sql
-- Database: language_corpus

-- Table: biwords (21587486 rows)
CREATE TABLE biwords (
    lid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> langs.lid</fk>
    w1st INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> words.wid</fk>
    w2nd INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> words.wid</fk>
    occurrences INTEGER NULL,
        -- <example>4</example>
    PRIMARY KEY (lid, w1st, w2nd),
    FOREIGN KEY (w2nd) REFERENCES words(wid),
    FOREIGN KEY (w1st) REFERENCES words(wid),
    FOREIGN KEY (lid) REFERENCES langs(lid)
);

-- Table: langs (1 rows)
CREATE TABLE langs (
    lid INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    lang TEXT NULL,
        -- <values>{'ca'}</values>
    locale TEXT NULL,
        -- <values>{'ca_ES'}</values>
    pages INTEGER NULL,
        -- <example>1129144</example>
    words INTEGER NULL
        -- <example>2764996</example>
);

-- Table: langs_words (2764996 rows)
CREATE TABLE langs_words (
    lid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> langs.lid</fk>
    wid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> words.wid</fk>
    occurrences INTEGER NULL,
        -- <example>242</example>
    PRIMARY KEY (lid, wid),
    FOREIGN KEY (wid) REFERENCES words(wid),
    FOREIGN KEY (lid) REFERENCES langs(lid)
);

-- Table: pages (1129144 rows)
CREATE TABLE pages (
    pid INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    lid INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> langs.lid</fk>
    page INTEGER NULL,
        -- <example>1</example>
    revision INTEGER NULL,
        -- <example>28236978</example>
    title TEXT NULL,
        -- <example>'Àbac'</example>
    words INTEGER NULL,
        -- <example>1081</example>
    FOREIGN KEY (lid) REFERENCES langs(lid)
);

-- Table: pages_words (129131916 rows)
CREATE TABLE pages_words (
    pid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> pages.pid</fk>
    wid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> words.wid</fk>
    occurrences INTEGER NULL,
        -- <example>30</example>
    PRIMARY KEY (pid, wid),
    FOREIGN KEY (wid) REFERENCES words(wid),
    FOREIGN KEY (pid) REFERENCES pages(pid)
);

-- Table: words (2764996 rows)
CREATE TABLE words (
    wid INTEGER NULL PRIMARY KEY,
        -- <example>2148990</example>
    word TEXT NULL,
        -- <example>'+,2'</example>
    occurrences INTEGER NULL
        -- <example>242</example>
);
```