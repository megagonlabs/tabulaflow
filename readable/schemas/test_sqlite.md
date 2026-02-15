```sql
-- Database: test_db

/*
Schema: NULL
Table: orders
Rows: 4
All rows:
|   id |   user_id |   amount |
|------|-----------|----------|
|    1 |         1 |   100    |
|    2 |         1 |   150.5  |
|    3 |         2 |   200    |
|    4 |         2 |    75.25 |
*/
CREATE TABLE orders (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "user_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> users."id"</fk>
    "amount" REAL NOT NULL,
        -- <example>100.000</example>
    FOREIGN KEY ("user_id") REFERENCES users("id")
);

/*
Schema: NULL
Table: users
Rows: 3
All rows:
|   id | name    | age    |
|------|---------|--------|
|    1 | Alice   | 25.0   |
|    2 | Bob     | 30.0   |
|    3 | Charlie | [NULL] |
*/
CREATE TABLE users (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "name" VARCHAR NOT NULL,
        -- <values>{'Alice', 'Bob', 'Charlie'}</values>
    "age" INTEGER NULL
        -- <example>25</example>
);
```