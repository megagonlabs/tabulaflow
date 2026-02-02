```sql
-- Database: video_games

-- Table: game (11317 rows)
CREATE TABLE game (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>44</example>
    genre_id INTEGER NULL,
        -- <example>4</example>
        -- <fk> -> genre.id</fk>
    game_name TEXT NULL,
        -- <example>'2 Games in 1: Sonic Advance & ChuChu Rocket!'</example>
    FOREIGN KEY (genre_id) REFERENCES genre(id)
);

-- Table: game_platform (16326 rows)
CREATE TABLE game_platform (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    game_publisher_id INTEGER NULL,
        -- <example>8564</example>
        -- <fk> -> game_publisher.id</fk>
    platform_id INTEGER NULL,
        -- <example>4</example>
        -- <fk> -> platform.id</fk>
    release_year INTEGER NULL,
        -- <example>2007</example>
    FOREIGN KEY (game_publisher_id) REFERENCES game_publisher(id),
    FOREIGN KEY (platform_id) REFERENCES platform(id)
);

-- Table: game_publisher (11732 rows)
CREATE TABLE game_publisher (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    game_id INTEGER NULL,
        -- <example>10866</example>
        -- <fk> -> game.id</fk>
    publisher_id INTEGER NULL,
        -- <example>369</example>
        -- <fk> -> publisher.id</fk>
    FOREIGN KEY (game_id) REFERENCES game(id),
    FOREIGN KEY (publisher_id) REFERENCES publisher(id)
);

-- Table: genre (12 rows)
CREATE TABLE genre (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    genre_name TEXT NULL
        -- <example>'Action'</example>
);

-- Table: platform (31 rows)
CREATE TABLE platform (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    platform_name TEXT NULL
        -- <example>'Wii'</example>
);

-- Table: publisher (577 rows)
CREATE TABLE publisher (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    publisher_name TEXT NULL
        -- <example>'10TACLE Studios'</example>
);

-- Table: region (4 rows)
CREATE TABLE region (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    region_name TEXT NULL
        -- <values>{'Europe', 'Japan', 'North America', 'Other'}</values>
);

-- Table: region_sales (65320 rows)
CREATE TABLE region_sales (
    region_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> region.id</fk>
    game_platform_id INTEGER NULL,
        -- <example>50</example>
        -- <fk> -> game_platform.id</fk>
    num_sales REAL NULL,
        -- <example>3.500</example>
    FOREIGN KEY (game_platform_id) REFERENCES game_platform(id),
    FOREIGN KEY (region_id) REFERENCES region(id)
);
```