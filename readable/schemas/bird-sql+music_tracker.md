```sql
-- Database: music_tracker

/*
Schema: NULLTable: tags
Rows: 161283
Sample rows:
| index   | id   | tag      |
|---------|------|----------|
| 0       | 0    | 1970s    |
| 1       | 0    | funk     |
| 2       | 0    | disco    |
| 3       | 2    | 1970s    |
| 4       | 2    | new.york |
| ...     | ...  | ...      |
*/
CREATE TABLE tags (
    index INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    id INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> torrents.id</fk>
    tag TEXT NOT NULL,
        -- <example>'1970s'</example>
    FOREIGN KEY (id) REFERENCES torrents(id)
);

/*
Schema: NULLTable: torrents
Rows: 75719
Sample rows:
| groupName                      | totalSnatched   | artist                               | groupYear   | releaseType   | groupId   | id   |
|--------------------------------|-----------------|--------------------------------------|-------------|---------------|-----------|------|
| superappin&#39;                | 239             | grandmaster flash & the furious five | 1979        | single        | 720949    | 0    |
| spiderap / a corona jam        | 156             | ron hunt & ronnie g & the sm crew    | 1979        | single        | 728752    | 1    |
| rapper&#39;s delight           | 480             | sugarhill gang                       | 1979        | single        | 18513     | 2    |
| rap-o clap-o / el rap-o clap-o | 200             | joe bataan                           | 1979        | single        | 756236    | 3    |
| christmas rappin&#39;          | 109             | kurtis blow                          | 1979        | single        | 71818958  | 4    |
| ...                            | ...             | ...                                  | ...         | ...           | ...       | ...  |
*/
CREATE TABLE torrents (
    groupName TEXT NOT NULL,
        -- <example>'superappin&#39;'</example>
    totalSnatched INTEGER NOT NULL,
        -- <example>239</example>
    artist TEXT NOT NULL,
        -- <example>'grandmaster flash & the furious five'</example>
    groupYear INTEGER NOT NULL,
        -- <example>1979</example>
    releaseType TEXT NOT NULL,
        -- <values>{'album', 'anthology', 'bootleg', 'compilation', 'concert recording', 'demo', 'dj mix', 'ep', 'interview', 'live album', 'mixtape', 'remix', 'single', 'soundtrack', 'unknown'}</values>
    groupId INTEGER NOT NULL,
        -- <example>720949</example>
    id INTEGER NOT NULL PRIMARY KEY
        -- <example>0</example>
);
```