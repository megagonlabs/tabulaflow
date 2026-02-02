```sql
-- Database: music_tracker

-- Table: tags (161283 rows)
CREATE TABLE tags (
    index INTEGER NULL PRIMARY KEY,
        -- <example>0</example>
    id INTEGER NULL,
        -- <example>0</example>
        -- <fk> -> torrents.id</fk>
    tag TEXT NULL,
        -- <example>'1970s'</example>
    FOREIGN KEY (id) REFERENCES torrents(id)
);

-- Table: torrents (75719 rows)
CREATE TABLE torrents (
    groupName TEXT NULL,
        -- <example>'superappin&#39;'</example>
    totalSnatched INTEGER NULL,
        -- <example>239</example>
    artist TEXT NULL,
        -- <example>'grandmaster flash & the furious five'</example>
    groupYear INTEGER NULL,
        -- <example>1979</example>
    releaseType TEXT NULL,
        -- <values>{'album', 'anthology', 'bootleg', 'compilation', 'concert recording', 'demo', 'dj mix', 'ep', 'interview', 'live album', 'mixtape', 'remix', 'single', 'soundtrack', 'unknown'}</values>
    groupId INTEGER NULL,
        -- <example>720949</example>
    id INTEGER NULL PRIMARY KEY
        -- <example>0</example>
);
```