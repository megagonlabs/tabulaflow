```sql
-- Database: cars

-- Table: country (3 rows)
CREATE TABLE country (
    origin INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    country TEXT NULL
        -- <values>{'Europe', 'Japan', 'USA'}</values>
);

-- Table: data (398 rows)
CREATE TABLE data (
    ID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> price.ID</fk>
    mpg REAL NULL,
        -- <example>18.000</example>
    cylinders INTEGER NULL,
        -- <example>8</example>
    displacement REAL NULL,
        -- <example>307.000</example>
    horsepower INTEGER NULL,
        -- <example>130</example>
    weight INTEGER NULL,
        -- <example>3504</example>
    acceleration REAL NULL,
        -- <example>12.000</example>
    model INTEGER NULL,
        -- <example>70</example>
    car_name TEXT NULL,
        -- <example>'chevrolet chevelle malibu'</example>
    FOREIGN KEY (ID) REFERENCES price(ID)
);

-- Table: price (398 rows)
CREATE TABLE price (
    ID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    price REAL NULL
        -- <example>25561.591</example>
);

-- Table: production (692 rows)
CREATE TABLE production (
    ID INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> data.ID</fk>
        -- <fk> -> price.ID</fk>
    model_year INTEGER NULL,
        -- <example>1970</example>
    country INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> country.origin</fk>
    PRIMARY KEY (ID, model_year),
    FOREIGN KEY (country) REFERENCES country(origin),
    FOREIGN KEY (ID) REFERENCES data(ID),
    FOREIGN KEY (ID) REFERENCES price(ID)
);
```