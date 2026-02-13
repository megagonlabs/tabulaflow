```sql
-- Database: cars

/*
Table: country
Rows: 3
All rows:
|   origin | country   |
|----------|-----------|
|        1 | USA       |
|        2 | Europe    |
|        3 | Japan     |
*/
CREATE TABLE country (
    origin INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    country TEXT NOT NULL
        -- <values>{'Europe', 'Japan', 'USA'}</values>
);

/*
Table: data
Rows: 398
Sample rows:
| ID   | mpg   | cylinders   | displacement   | horsepower   | weight   | acceleration   | model   | car_name                  |
|------|-------|-------------|----------------|--------------|----------|----------------|---------|---------------------------|
| 1    | 18.0  | 8           | 307.0          | 130          | 3504     | 12.0           | 70      | chevrolet chevelle malibu |
| 2    | 15.0  | 8           | 350.0          | 165          | 3693     | 11.5           | 70      | buick skylark 320         |
| 3    | 18.0  | 8           | 318.0          | 150          | 3436     | 11.0           | 70      | plymouth satellite        |
| 4    | 16.0  | 8           | 304.0          | 150          | 3433     | 12.0           | 70      | amc rebel sst             |
| 5    | 17.0  | 8           | 302.0          | 140          | 3449     | 10.5           | 70      | ford torino               |
| ...  | ...   | ...         | ...            | ...          | ...      | ...            | ...     | ...                       |
*/
CREATE TABLE data (
    ID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> price.ID</fk>
    mpg REAL NOT NULL,
        -- <example>18.000</example>
    cylinders INTEGER NOT NULL,
        -- <example>8</example>
    displacement REAL NOT NULL,
        -- <example>307.000</example>
    horsepower INTEGER NOT NULL,
        -- <example>130</example>
    weight INTEGER NOT NULL,
        -- <example>3504</example>
    acceleration REAL NOT NULL,
        -- <example>12.000</example>
    model INTEGER NOT NULL,
        -- <example>70</example>
    car_name TEXT NOT NULL,
        -- <example>'chevrolet chevelle malibu'</example>
    FOREIGN KEY (ID) REFERENCES price(ID)
);

/*
Table: price
Rows: 398
Sample rows:
| ID   | price       |
|------|-------------|
| 1    | 25561.59078 |
| 2    | 24221.42273 |
| 3    | 27240.84373 |
| 4    | 33684.96888 |
| 5    | 20000.0     |
| ...  | ...         |
*/
CREATE TABLE price (
    ID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    price REAL NOT NULL
        -- <example>25561.591</example>
);

/*
Table: production
Rows: 692
Sample rows:
| ID   | model_year   | country   |
|------|--------------|-----------|
| 1    | 1970         | 1         |
| 1    | 1971         | 1         |
| 2    | 1970         | 1         |
| 3    | 1970         | 1         |
| 4    | 1970         | 1         |
| ...  | ...          | ...       |
*/
CREATE TABLE production (
    ID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> data.ID</fk>
        -- <fk> -> price.ID</fk>
    model_year INTEGER NOT NULL,
        -- <example>1970</example>
    country INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> country.origin</fk>
    PRIMARY KEY (ID, model_year),
    FOREIGN KEY (country) REFERENCES country(origin),
    FOREIGN KEY (ID) REFERENCES data(ID),
    FOREIGN KEY (ID) REFERENCES price(ID)
);
```