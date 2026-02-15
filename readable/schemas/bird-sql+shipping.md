```sql
-- Database: shipping

/*
Schema: NULL
Table: city
Rows: 601
Sample rows:
| city_id   | city_name       | state      | population   | area   |
|-----------|-----------------|------------|--------------|--------|
| 100       | Union City      | New Jersey | 67088        | 1.3    |
| 101       | Huntington Park | California | 61348        | 3.0    |
| 102       | Passaic         | New Jersey | 67861        | 3.1    |
| 103       | Hempstead       | New York   | 56554        | 3.7    |
| 104       | Berwyn          | Illinois   | 54016        | 3.9    |
| ...       | ...             | ...        | ...          | ...    |
*/
CREATE TABLE city (
    "city_id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>100</example>
    "city_name" TEXT NOT NULL,
        -- <example>'Union City'</example>
    "state" TEXT NOT NULL,
        -- <example>'New Jersey'</example>
    "population" INTEGER NOT NULL,
        -- <example>67088</example>
    "area" REAL NOT NULL
        -- <example>1.300</example>
);

/*
Schema: NULL
Table: customer
Rows: 100
Sample rows:
| cust_id   | cust_name                                | annual_revenue   | cust_type    | address                   | city            | state   | zip     | phone          |
|-----------|------------------------------------------|------------------|--------------|---------------------------|-----------------|---------|---------|----------------|
| 193       | Advanced Fabricators                     | 39588651         | manufacturer | 5141 Summit Boulevard     | West Palm Beach | FL      | 33415.0 | (561) 683-3535 |
| 304       | Pard's Trailer Sales                     | 17158109         | wholesaler   | 5910 South 300 West       | Salt Lake City  | UT      | 84107.0 | (801) 262-4864 |
| 314       | Saar Enterprises, Inc.                   | 47403613         | retailer     | 11687 192nd Street        | Council Bluffs  | IA      | 51503.0 | (712) 366-4929 |
| 381       | Autoware Inc                             | 5583961          | wholesaler   | 854 Southwest 12th Avenue | Pompano Beach   | FL      | 33069.0 | (954) 738-4000 |
| 493       | Harry's Hot Rod Auto & Truck Accessories | 11732302         | retailer     | 105 NW 13th St            | Grand Prairie   | TX      | 75050.0 | (972) 263-8080 |
| ...       | ...                                      | ...              | ...          | ...                       | ...             | ...     | ...     | ...            |
*/
CREATE TABLE customer (
    "cust_id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>193</example>
    "cust_name" TEXT NOT NULL,
        -- <example>'Advanced Fabricators'</example>
    "annual_revenue" INTEGER NOT NULL,
        -- <example>39588651</example>
    "cust_type" TEXT NOT NULL,
        -- <values>{'manufacturer', 'retailer', 'wholesaler'}</values>
    "address" TEXT NOT NULL,
        -- <example>'5141 Summit Boulevard'</example>
    "city" TEXT NOT NULL,
        -- <example>'West Palm Beach'</example>
    "state" TEXT NOT NULL,
        -- <example>'FL'</example>
    "zip" REAL NOT NULL,
        -- <example>33415.000</example>
    "phone" TEXT NOT NULL
        -- <example>'(561) 683-3535'</example>
);

/*
Schema: NULL
Table: driver
Rows: 11
Sample rows:
| driver_id   | first_name   | last_name   | address            | city    | state   | zip_code   | phone          |
|-------------|--------------|-------------|--------------------|---------|---------|------------|----------------|
| 20          | Sue          | Newell      | 268 Richmond Ave   | Memphis | TN      | 38106      | (901) 774-6569 |
| 21          | Andrea       | Simons      | 3574 Oak Limb Cv   | Memphis | TN      | 38135      | (901) 384-0984 |
| 22          | Roger        | McHaney     | 1839 S Orleans St  | Memphis | TN      | 38106      | (901) 948-1043 |
| 23          | Zachery      | Hicks       | 3649 Park Lake Dr  | Memphis | TN      | 38118      | (901) 362-6674 |
| 24          | Adel         | Al-Alawi    | 749 E Mckellar Ave | Memphis | TN      | 38106      | (901) 947-4433 |
| ...         | ...          | ...         | ...                | ...     | ...     | ...        | ...            |
*/
CREATE TABLE driver (
    "driver_id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>20</example>
    "first_name" TEXT NOT NULL,
        -- <example>'Sue'</example>
    "last_name" TEXT NOT NULL,
        -- <example>'Newell'</example>
    "address" TEXT NOT NULL,
        -- <example>'268 Richmond Ave'</example>
    "city" TEXT NOT NULL,
        -- <values>{'Memphis'}</values>
    "state" TEXT NOT NULL,
        -- <values>{'TN'}</values>
    "zip_code" INTEGER NOT NULL,
        -- <example>38106</example>
    "phone" TEXT NOT NULL
        -- <example>'(901) 774-6569'</example>
);

/*
Schema: NULL
Table: shipment
Rows: 960
Sample rows:
| ship_id   | cust_id   | weight   | truck_id   | driver_id   | city_id   | ship_date   |
|-----------|-----------|----------|------------|-------------|-----------|-------------|
| 1000      | 3660      | 3528.0   | 1          | 23          | 137       | 2016-01-08  |
| 1001      | 2001      | 11394.0  | 2          | 23          | 186       | 2016-01-18  |
| 1002      | 1669      | 8712.0   | 3          | 27          | 268       | 2016-01-19  |
| 1003      | 989       | 17154.0  | 4          | 23          | 365       | 2016-01-24  |
| 1004      | 2298      | 9279.0   | 5          | 27          | 253       | 2016-01-26  |
| ...       | ...       | ...      | ...        | ...         | ...       | ...         |
*/
CREATE TABLE shipment (
    "ship_id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1000</example>
    "cust_id" INTEGER NOT NULL,
        -- <example>3660</example>
        -- <fk> -> customer."cust_id"</fk>
    "weight" REAL NOT NULL,
        -- <example>3528.000</example>
    "truck_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> truck."truck_id"</fk>
    "driver_id" INTEGER NOT NULL,
        -- <example>23</example>
        -- <fk> -> driver."driver_id"</fk>
    "city_id" INTEGER NOT NULL,
        -- <example>137</example>
        -- <fk> -> city."city_id"</fk>
    "ship_date" TEXT NOT NULL,
        -- <example>'2016-01-08'</example>
    FOREIGN KEY ("cust_id") REFERENCES customer("cust_id"),
    FOREIGN KEY ("city_id") REFERENCES city("city_id"),
    FOREIGN KEY ("driver_id") REFERENCES driver("driver_id"),
    FOREIGN KEY ("truck_id") REFERENCES truck("truck_id")
);

/*
Schema: NULL
Table: truck
Rows: 12
Sample rows:
| truck_id   | make      | model_year   |
|------------|-----------|--------------|
| 1          | Peterbilt | 2005         |
| 2          | Mack      | 2006         |
| 3          | Peterbilt | 2007         |
| 4          | Kenworth  | 2007         |
| 5          | Mack      | 2008         |
| ...        | ...       | ...          |
*/
CREATE TABLE truck (
    "truck_id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "make" TEXT NOT NULL,
        -- <values>{'Kenworth', 'Mack', 'Peterbilt'}</values>
    "model_year" INTEGER NOT NULL
        -- <example>2005</example>
);
```