```sql
-- Database: test_db

-- Table: orders (4 rows)
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,  -- e.g. 1
    user_id INTEGER,  -- e.g. 1; FK -> users.id
    amount REAL,  -- e.g. 100.000
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Table: users (3 rows)
CREATE TABLE users (
    id INTEGER PRIMARY KEY,  -- e.g. 1
    name VARCHAR,  -- values: {'Alice', 'Bob', 'Charlie'}
    age INTEGER  -- e.g. 25
);
```