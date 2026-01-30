```sql
-- Database: shipping

-- Table: city (601 rows)
CREATE TABLE city (
    city_id INTEGER PRIMARY KEY,  -- e.g. 100
    city_name TEXT,  -- e.g. 'Union City'
    state TEXT,  -- e.g. 'New Jersey'
    population INTEGER,  -- e.g. 67088
    area REAL  -- e.g. 1.300
);

-- Table: customer (100 rows)
CREATE TABLE customer (
    cust_id INTEGER PRIMARY KEY,  -- e.g. 193
    cust_name TEXT,  -- e.g. 'Advanced Fabricators'
    annual_revenue INTEGER,  -- e.g. 39588651
    cust_type TEXT,  -- values: {'manufacturer', 'retailer', 'wholesaler'}
    address TEXT,  -- e.g. '5141 Summit Boulevard'
    city TEXT,  -- e.g. 'West Palm Beach'
    state TEXT,  -- e.g. 'FL'
    zip REAL,  -- e.g. 33415.000
    phone TEXT  -- e.g. '(561) 683-3535'
);

-- Table: driver (11 rows)
CREATE TABLE driver (
    driver_id INTEGER PRIMARY KEY,  -- e.g. 20
    first_name TEXT,  -- e.g. 'Sue'
    last_name TEXT,  -- e.g. 'Newell'
    address TEXT,  -- e.g. '268 Richmond Ave'
    city TEXT,  -- values: {'Memphis'}
    state TEXT,  -- values: {'TN'}
    zip_code INTEGER,  -- e.g. 38106
    phone TEXT  -- e.g. '(901) 774-6569'
);

-- Table: shipment (960 rows)
CREATE TABLE shipment (
    ship_id INTEGER PRIMARY KEY,  -- e.g. 1000
    cust_id INTEGER,  -- e.g. 3660; FK -> customer.cust_id
    weight REAL,  -- e.g. 3528.000
    truck_id INTEGER,  -- e.g. 1; FK -> truck.truck_id
    driver_id INTEGER,  -- e.g. 23; FK -> driver.driver_id
    city_id INTEGER,  -- e.g. 137; FK -> city.city_id
    ship_date TEXT,  -- e.g. '2016-01-08'
    FOREIGN KEY (cust_id) REFERENCES customer(cust_id),
    FOREIGN KEY (city_id) REFERENCES city(city_id),
    FOREIGN KEY (driver_id) REFERENCES driver(driver_id),
    FOREIGN KEY (truck_id) REFERENCES truck(truck_id)
);

-- Table: truck (12 rows)
CREATE TABLE truck (
    truck_id INTEGER PRIMARY KEY,  -- e.g. 1
    make TEXT,  -- values: {'Kenworth', 'Mack', 'Peterbilt'}
    model_year INTEGER  -- e.g. 2005
);
```