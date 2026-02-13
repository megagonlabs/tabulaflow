```sql
-- Database: language_corpus

/*
Schema: NULLTable: biwords
Rows: 21587486
Sample rows:
| lid   | w1st   | w2nd   | occurrences   |
|-------|--------|--------|---------------|
| 1     | 1      | 2      | 4             |
| 1     | 1      | 4      | 3             |
| 1     | 1      | 25     | 13            |
| 1     | 1      | 34     | 29            |
| 1     | 1      | 51     | 14            |
| ...   | ...    | ...    | ...           |
*/
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
    occurrences INTEGER NOT NULL,
        -- <example>4</example>
    PRIMARY KEY (lid, w1st, w2nd),
    FOREIGN KEY (w2nd) REFERENCES words(wid),
    FOREIGN KEY (w1st) REFERENCES words(wid),
    FOREIGN KEY (lid) REFERENCES langs(lid)
);

/*
Schema: NULLTable: langs
Rows: 1
All rows:
|   lid | lang   | locale   |   pages |   words |
|-------|--------|----------|---------|---------|
|     1 | ca     | ca_ES    | 1129144 | 2764996 |
*/
CREATE TABLE langs (
    lid INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    lang TEXT NOT NULL,
        -- <values>{'ca'}</values>
    locale TEXT NOT NULL,
        -- <values>{'ca_ES'}</values>
    pages INTEGER NOT NULL,
        -- <example>1129144</example>
    words INTEGER NOT NULL
        -- <example>2764996</example>
);

/*
Schema: NULLTable: langs_words
Rows: 2764996
Sample rows:
| lid   | wid   | occurrences   |
|-------|-------|---------------|
| 1     | 1     | 242           |
| 1     | 2     | 16841         |
| 1     | 3     | 48700         |
| 1     | 4     | 49897         |
| 1     | 5     | 60220         |
| ...   | ...   | ...           |
*/
CREATE TABLE langs_words (
    lid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> langs.lid</fk>
    wid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> words.wid</fk>
    occurrences INTEGER NOT NULL,
        -- <example>242</example>
    PRIMARY KEY (lid, wid),
    FOREIGN KEY (wid) REFERENCES words(wid),
    FOREIGN KEY (lid) REFERENCES langs(lid)
);

/*
Schema: NULLTable: pages
Rows: 1129144
Sample rows:
| pid   | lid   | page   | revision   | title    | words   |
|-------|-------|--------|------------|----------|---------|
| 1     | 1     | 1      | 28236978   | Àbac     | 1081    |
| 2     | 1     | 2      | 24086480   | Abadia   | 68      |
| 3     | 1     | 8      | 26230310   | Adagi    | 304     |
| 4     | 1     | 9      | 28374033   | Adam     | 453     |
| 5     | 1     | 10     | 28336725   | Addicció | 1468    |
| ...   | ...   | ...    | ...        | ...      | ...     |
*/
CREATE TABLE pages (
    pid INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    lid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> langs.lid</fk>
    page INTEGER NOT NULL,
        -- <example>1</example>
    revision INTEGER NOT NULL,
        -- <example>28236978</example>
    title TEXT NOT NULL,
        -- <example>'Àbac'</example>
    words INTEGER NOT NULL,
        -- <example>1081</example>
    FOREIGN KEY (lid) REFERENCES langs(lid)
);

/*
Schema: NULLTable: pages_words
Rows: 129131916
Sample rows:
| pid   | wid   | occurrences   |
|-------|-------|---------------|
| 1     | 1     | 30            |
| 1     | 2     | 8             |
| 1     | 3     | 2             |
| 1     | 4     | 5             |
| 1     | 5     | 2             |
| ...   | ...   | ...           |
*/
CREATE TABLE pages_words (
    pid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> pages.pid</fk>
    wid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> words.wid</fk>
    occurrences INTEGER NOT NULL,
        -- <example>30</example>
    PRIMARY KEY (pid, wid),
    FOREIGN KEY (wid) REFERENCES words(wid),
    FOREIGN KEY (pid) REFERENCES pages(pid)
);

/*
Schema: NULLTable: words
Rows: 2764996
Sample rows:
| wid   | word   | occurrences   |
|-------|--------|---------------|
| 1     | àbac   | 242           |
| 2     | xinès  | 16841         |
| 3     | llatí  | 48700         |
| 4     | grec   | 49897         |
| 5     | antic  | 60220         |
| ...   | ...    | ...           |
*/
CREATE TABLE words (
    wid INTEGER NOT NULL PRIMARY KEY,
        -- <example>2148990</example>
    word TEXT NOT NULL,
        -- <example>'+,2'</example>
    occurrences INTEGER NOT NULL
        -- <example>242</example>
);
```