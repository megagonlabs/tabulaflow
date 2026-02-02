```sql
-- Database: shipping

-- Table: city (601 rows)
CREATE TABLE city (
    city_id INTEGER NULL PRIMARY KEY,
        -- <example>100</example>
    city_name TEXT NULL,
        -- <example>'Union City'</example>
    state TEXT NULL,
        -- <example>'New Jersey'</example>
    population INTEGER NULL,
        -- <example>67088</example>
    area REAL NULL
        -- <example>1.300</example>
);

-- Table: customer (100 rows)
CREATE TABLE customer (
    cust_id INTEGER NULL PRIMARY KEY,
        -- <example>193</example>
    cust_name TEXT NULL,
        -- <example>'Advanced Fabricators'</example>
    annual_revenue INTEGER NULL,
        -- <example>39588651</example>
    cust_type TEXT NULL,
        -- <values>{'manufacturer', 'retailer', 'wholesaler'}</values>
    address TEXT NULL,
        -- <example>'5141 Summit Boulevard'</example>
    city TEXT NULL,
        -- <example>'West Palm Beach'</example>
    state TEXT NULL,
        -- <example>'FL'</example>
    zip REAL NULL,
        -- <example>33415.000</example>
    phone TEXT NULL
        -- <example>'(561) 683-3535'</example>
);

-- Table: driver (11 rows)
CREATE TABLE driver (
    driver_id INTEGER NULL PRIMARY KEY,
        -- <example>20</example>
    first_name TEXT NULL,
        -- <example>'Sue'</example>
    last_name TEXT NULL,
        -- <example>'Newell'</example>
    address TEXT NULL,
        -- <example>'268 Richmond Ave'</example>
    city TEXT NULL,
        -- <values>{'Memphis'}</values>
    state TEXT NULL,
        -- <values>{'TN'}</values>
    zip_code INTEGER NULL,
        -- <example>38106</example>
    phone TEXT NULL
        -- <example>'(901) 774-6569'</example>
);

-- Table: shipment (960 rows)
CREATE TABLE shipment (
    ship_id INTEGER NULL PRIMARY KEY,
        -- <example>1000</example>
    cust_id INTEGER NULL,
        -- <example>3660</example>
        -- <fk> -> customer.cust_id</fk>
    weight REAL NULL,
        -- <example>3528.000</example>
    truck_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> truck.truck_id</fk>
    driver_id INTEGER NULL,
        -- <example>23</example>
        -- <fk> -> driver.driver_id</fk>
    city_id INTEGER NULL,
        -- <example>137</example>
        -- <fk> -> city.city_id</fk>
    ship_date TEXT NULL,
        -- <example>'2016-01-08'</example>
    FOREIGN KEY (cust_id) REFERENCES customer(cust_id),
    FOREIGN KEY (city_id) REFERENCES city(city_id),
    FOREIGN KEY (driver_id) REFERENCES driver(driver_id),
    FOREIGN KEY (truck_id) REFERENCES truck(truck_id)
);

-- Table: truck (12 rows)
CREATE TABLE truck (
    truck_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    make TEXT NULL,
        -- <values>{'Kenworth', 'Mack', 'Peterbilt'}</values>
    model_year INTEGER NULL
        -- <example>2005</example>
);
```