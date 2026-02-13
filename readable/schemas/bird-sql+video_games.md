```sql
-- Database: video_games

/*
Schema: NULLTable: game
Rows: 11317
Sample rows:
| id   | genre_id   | game_name                                                          |
|------|------------|--------------------------------------------------------------------|
| 44   | 4          | 2 Games in 1: Sonic Advance & ChuChu Rocket!                       |
| 45   | 4          | 2 Games in 1: Sonic Battle & ChuChu Rocket!                        |
| 46   | 4          | 2 Games in 1: Sonic Pinball Party & Columns Crown                  |
| 47   | 5          | 2 Games in 1: SpongeBob SquarePants: SuperSponge & Rugrats Go Wild |
| 48   | 4          | 2 in 1 Combo Pack: Sonic Heroes / Super Monkey Ball Deluxe         |
| ...  | ...        | ...                                                                |
*/
CREATE TABLE game (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>44</example>
    genre_id INTEGER NOT NULL,
        -- <example>4</example>
        -- <fk> -> genre.id</fk>
    game_name TEXT NOT NULL,
        -- <example>'2 Games in 1: Sonic Advance & ChuChu Rocket!'</example>
    FOREIGN KEY (genre_id) REFERENCES genre(id)
);

/*
Schema: NULLTable: game_platform
Rows: 16326
Sample rows:
| id   | game_publisher_id   | platform_id   | release_year   |
|------|---------------------|---------------|----------------|
| 1    | 8564                | 4             | 2007           |
| 2    | 9852                | 4             | 2007           |
| 3    | 11063               | 7             | 2006           |
| 4    | 9065                | 15            | 2011           |
| 5    | 9544                | 15            | 2011           |
| ...  | ...                 | ...           | ...            |
*/
CREATE TABLE game_platform (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    game_publisher_id INTEGER NOT NULL,
        -- <example>8564</example>
        -- <fk> -> game_publisher.id</fk>
    platform_id INTEGER NOT NULL,
        -- <example>4</example>
        -- <fk> -> platform.id</fk>
    release_year INTEGER NOT NULL,
        -- <example>2007</example>
    FOREIGN KEY (game_publisher_id) REFERENCES game_publisher(id),
    FOREIGN KEY (platform_id) REFERENCES platform(id)
);

/*
Schema: NULLTable: game_publisher
Rows: 11732
Sample rows:
| id   | game_id   | publisher_id   |
|------|-----------|----------------|
| 1    | 10866     | 369            |
| 2    | 9244      | 369            |
| 3    | 5464      | 369            |
| 4    | 10868     | 369            |
| 5    | 7282      | 369            |
| ...  | ...       | ...            |
*/
CREATE TABLE game_publisher (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    game_id INTEGER NOT NULL,
        -- <example>10866</example>
        -- <fk> -> game.id</fk>
    publisher_id INTEGER NOT NULL,
        -- <example>369</example>
        -- <fk> -> publisher.id</fk>
    FOREIGN KEY (game_id) REFERENCES game(id),
    FOREIGN KEY (publisher_id) REFERENCES publisher(id)
);

/*
Schema: NULLTable: genre
Rows: 12
Sample rows:
| id   | genre_name   |
|------|--------------|
| 1    | Action       |
| 2    | Adventure    |
| 3    | Fighting     |
| 4    | Misc         |
| 5    | Platform     |
| ...  | ...          |
*/
CREATE TABLE genre (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    genre_name TEXT NOT NULL
        -- <example>'Action'</example>
);

/*
Schema: NULLTable: platform
Rows: 31
Sample rows:
| id   | platform_name   |
|------|-----------------|
| 1    | Wii             |
| 2    | NES             |
| 3    | GB              |
| 4    | DS              |
| 5    | X360            |
| ...  | ...             |
*/
CREATE TABLE platform (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    platform_name TEXT NOT NULL
        -- <example>'Wii'</example>
);

/*
Schema: NULLTable: publisher
Rows: 577
Sample rows:
| id   | publisher_name               |
|------|------------------------------|
| 1    | 10TACLE Studios              |
| 2    | 1C Company                   |
| 3    | 20th Century Fox Video Games |
| 4    | 2D Boy                       |
| 5    | 3DO                          |
| ...  | ...                          |
*/
CREATE TABLE publisher (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    publisher_name TEXT NOT NULL
        -- <example>'10TACLE Studios'</example>
);

/*
Schema: NULLTable: region
Rows: 4
All rows:
|   id | region_name   |
|------|---------------|
|    1 | North America |
|    2 | Europe        |
|    3 | Japan         |
|    4 | Other         |
*/
CREATE TABLE region (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    region_name TEXT NOT NULL
        -- <values>{'Europe', 'Japan', 'North America', 'Other'}</values>
);

/*
Schema: NULLTable: region_sales
Rows: 65320
Sample rows:
| region_id   | game_platform_id   | num_sales   |
|-------------|--------------------|-------------|
| 1           | 50                 | 3.5         |
| 1           | 51                 | 1.43        |
| 1           | 52                 | 0.51        |
| 1           | 53                 | 0.27        |
| 1           | 54                 | 0.48        |
| ...         | ...                | ...         |
*/
CREATE TABLE region_sales (
    region_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> region.id</fk>
    game_platform_id INTEGER NOT NULL,
        -- <example>50</example>
        -- <fk> -> game_platform.id</fk>
    num_sales REAL NOT NULL,
        -- <example>3.500</example>
    FOREIGN KEY (game_platform_id) REFERENCES game_platform(id),
    FOREIGN KEY (region_id) REFERENCES region(id)
);
```