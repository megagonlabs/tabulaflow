```sql
-- Database: cars

-- Table: country (3 rows)
CREATE TABLE country (
    origin INTEGER PRIMARY KEY,  -- e.g. 1
    country TEXT  -- values: {'Europe', 'Japan', 'USA'}
);

-- Table: data (398 rows)
CREATE TABLE data (
    ID INTEGER PRIMARY KEY,  -- e.g. 1; FK -> price.ID
    mpg REAL,  -- e.g. 18.000
    cylinders INTEGER,  -- e.g. 8
    displacement REAL,  -- e.g. 307.000
    horsepower INTEGER,  -- e.g. 130
    weight INTEGER,  -- e.g. 3504
    acceleration REAL,  -- e.g. 12.000
    model INTEGER,  -- e.g. 70
    car_name TEXT,  -- e.g. 'chevrolet chevelle malibu'
    FOREIGN KEY (ID) REFERENCES price(ID)
);

-- Table: price (398 rows)
CREATE TABLE price (
    ID INTEGER PRIMARY KEY,  -- e.g. 1
    price REAL  -- e.g. 25561.591
);

-- Table: production (692 rows)
CREATE TABLE production (
    ID INTEGER,  -- e.g. 1; FK -> data.ID; FK -> price.ID
    model_year INTEGER,  -- e.g. 1970
    country INTEGER,  -- e.g. 1; FK -> country.origin
    PRIMARY KEY (ID, model_year),
    FOREIGN KEY (country) REFERENCES country(origin),
    FOREIGN KEY (ID) REFERENCES data(ID),
    FOREIGN KEY (ID) REFERENCES price(ID)
);
```