```sql
-- Database: trains

-- Table: cars (63 rows)
CREATE TABLE cars (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    train_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> trains.id</fk>
    position INTEGER NULL,
        -- <example>1</example>
    shape TEXT NULL,
        -- <values>{'bucket', 'ellipse', 'hexagon', 'rectangle', 'u_shaped'}</values>
    len TEXT NULL,
        -- <values>{'long', 'short'}</values>
    sides TEXT NULL,
        -- <values>{'double', 'not_double'}</values>
    roof TEXT NULL,
        -- <values>{'arc', 'flat', 'jagged', 'none', 'peaked'}</values>
    wheels INTEGER NULL,
        -- <example>2</example>
    load_shape TEXT NULL,
        -- <values>{'circle', 'diamond', 'hexagon', 'rectangle', 'triangle'}</values>
    load_num INTEGER NULL,
        -- <example>1</example>
    FOREIGN KEY (train_id) REFERENCES trains(id)
);

-- Table: trains (20 rows)
CREATE TABLE trains (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    direction TEXT NULL
        -- <values>{'east', 'west'}</values>
);
```