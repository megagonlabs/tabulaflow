```sql
-- Database: trains

-- Table: cars (63 rows)
CREATE TABLE cars (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    train_id INTEGER,  -- e.g. 1; FK -> trains.id
    position INTEGER,  -- e.g. 1
    shape TEXT,  -- values: {'bucket', 'ellipse', 'hexagon', 'rectangle', 'u_shaped'}
    len TEXT,  -- values: {'long', 'short'}
    sides TEXT,  -- values: {'double', 'not_double'}
    roof TEXT,  -- values: {'arc', 'flat', 'jagged', 'none', 'peaked'}
    wheels INTEGER,  -- e.g. 2
    load_shape TEXT,  -- values: {'circle', 'diamond', 'hexagon', 'rectangle', 'triangle'}
    load_num INTEGER,  -- e.g. 1
    FOREIGN KEY (train_id) REFERENCES trains(id)
);

-- Table: trains (20 rows)
CREATE TABLE trains (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    direction TEXT  -- values: {'east', 'west'}
);
```