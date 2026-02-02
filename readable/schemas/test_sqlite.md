```sql
-- Database: test_db

-- Table: orders (4 rows)
CREATE TABLE orders (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    user_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> users.id</fk>
    amount REAL NULL,
        -- <example>100.000</example>
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Table: users (3 rows)
CREATE TABLE users (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    name VARCHAR NULL,
        -- <values>{'Alice', 'Bob', 'Charlie'}</values>
    age INTEGER NULL
        -- <example>25</example>
);
```