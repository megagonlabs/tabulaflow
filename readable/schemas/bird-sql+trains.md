```sql
-- Database: trains

/*
Schema: NULLTable: cars
Rows: 63
Sample rows:
| id   | train_id   | position   | shape     | len   | sides      | roof   | wheels   | load_shape   | load_num   |
|------|------------|------------|-----------|-------|------------|--------|----------|--------------|------------|
| 1    | 1          | 1          | rectangle | short | not_double | none   | 2        | circle       | 1          |
| 2    | 1          | 2          | rectangle | long  | not_double | none   | 3        | hexagon      | 1          |
| 3    | 1          | 3          | rectangle | short | not_double | peaked | 2        | triangle     | 1          |
| 4    | 1          | 4          | rectangle | long  | not_double | none   | 2        | rectangle    | 3          |
| 5    | 2          | 1          | rectangle | short | not_double | flat   | 2        | circle       | 2          |
| ...  | ...        | ...        | ...       | ...   | ...        | ...    | ...      | ...          | ...        |
*/
CREATE TABLE cars (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    train_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> trains.id</fk>
    position INTEGER NOT NULL,
        -- <example>1</example>
    shape TEXT NOT NULL,
        -- <values>{'bucket', 'ellipse', 'hexagon', 'rectangle', 'u_shaped'}</values>
    len TEXT NOT NULL,
        -- <values>{'long', 'short'}</values>
    sides TEXT NOT NULL,
        -- <values>{'double', 'not_double'}</values>
    roof TEXT NOT NULL,
        -- <values>{'arc', 'flat', 'jagged', 'none', 'peaked'}</values>
    wheels INTEGER NOT NULL,
        -- <example>2</example>
    load_shape TEXT NOT NULL,
        -- <values>{'circle', 'diamond', 'hexagon', 'rectangle', 'triangle'}</values>
    load_num INTEGER NOT NULL,
        -- <example>1</example>
    FOREIGN KEY (train_id) REFERENCES trains(id)
);

/*
Schema: NULLTable: trains
Rows: 20
Sample rows:
| id   | direction   |
|------|-------------|
| 1    | east        |
| 2    | east        |
| 3    | east        |
| 4    | east        |
| 5    | east        |
| ...  | ...         |
*/
CREATE TABLE trains (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    direction TEXT NOT NULL
        -- <values>{'east', 'west'}</values>
);
```