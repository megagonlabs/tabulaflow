```sql
-- Database: superstore

/*
Schema: NULLTable: central_superstore
Rows: 4646
Sample rows:
| Row ID   | Order ID       | Order Date   | Ship Date   | Ship Mode      | Customer ID   | Region   | Product ID      | Sales   | Quantity   | Discount   | Profit   |
|----------|----------------|--------------|-------------|----------------|---------------|----------|-----------------|---------|------------|------------|----------|
| 1        | CA-2011-103800 | 2013-01-03   | 2013-01-07  | Standard Class | DP-13000      | Central  | OFF-PA-10000174 | 16.448  | 2          | 0.2        | 5.5512   |
| 2        | CA-2011-112326 | 2013-01-04   | 2013-01-08  | Standard Class | PO-19195      | Central  | OFF-LA-10003223 | 11.784  | 3          | 0.2        | 4.2717   |
| 3        | CA-2011-112326 | 2013-01-04   | 2013-01-08  | Standard Class | PO-19195      | Central  | OFF-ST-10002743 | 272.736 | 3          | 0.2        | -64.7748 |
| 4        | CA-2011-112326 | 2013-01-04   | 2013-01-08  | Standard Class | PO-19195      | Central  | OFF-BI-10004094 | 3.54    | 2          | 0.8        | -5.487   |
| 5        | CA-2011-105417 | 2013-01-07   | 2013-01-12  | Standard Class | VS-21820      | Central  | FUR-FU-10004864 | 76.728  | 3          | 0.6        | -53.7096 |
| ...      | ...            | ...          | ...         | ...            | ...           | ...      | ...             | ...     | ...        | ...        | ...      |
*/
CREATE TABLE central_superstore (
    "Row ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Order ID" TEXT NOT NULL,
        -- <example>'CA-2011-103800'</example>
    "Order Date" DATE NOT NULL,
        -- <example>'2013-01-03'</example>
    "Ship Date" DATE NOT NULL,
        -- <example>'2013-01-07'</example>
    "Ship Mode" TEXT NOT NULL,
        -- <values>{'First Class', 'Same Day', 'Second Class', 'Standard Class'}</values>
    "Customer ID" TEXT NOT NULL,
        -- <example>'DP-13000'</example>
        -- <fk>composite</fk>
    Region TEXT NOT NULL,
        -- <values>{'Central'}</values>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "Product ID" TEXT NOT NULL,
        -- <example>'OFF-PA-10000174'</example>
        -- <fk>composite</fk>
    Sales REAL NOT NULL,
        -- <example>16.448</example>
    Quantity INTEGER NOT NULL,
        -- <example>2</example>
    Discount REAL NOT NULL,
        -- <example>0.200</example>
    Profit REAL NOT NULL,
        -- <example>5.551</example>
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);

/*
Schema: NULLTable: east_superstore
Rows: 5696
Sample rows:
| Row ID   | Order ID       | Order Date   | Ship Date   | Ship Mode      | Customer ID   | Region   | Product ID      | Sales   | Quantity   | Discount   | Profit   |
|----------|----------------|--------------|-------------|----------------|---------------|----------|-----------------|---------|------------|------------|----------|
| 4647     | CA-2011-141817 | 2013-01-05   | 2013-01-12  | Standard Class | MB-18085      | East     | OFF-AR-10003478 | 19.536  | 3          | 0.2        | 4.884    |
| 4648     | CA-2011-130092 | 2013-01-11   | 2013-01-14  | First Class    | SV-20365      | East     | FUR-FU-10000010 | 9.94    | 2          | 0.0        | 3.0814   |
| 4649     | CA-2011-118192 | 2013-01-13   | 2013-01-18  | Standard Class | MM-17920      | East     | OFF-PA-10002947 | 37.408  | 7          | 0.2        | 13.0928  |
| 4650     | CA-2011-118192 | 2013-01-13   | 2013-01-18  | Standard Class | MM-17920      | East     | OFF-BI-10003476 | 3.438   | 2          | 0.7        | -2.5212  |
| 4651     | CA-2011-149524 | 2013-01-14   | 2013-01-15  | First Class    | BS-11590      | East     | FUR-BO-10003433 | 61.96   | 4          | 0.5        | -53.2856 |
| ...      | ...            | ...          | ...         | ...            | ...           | ...      | ...             | ...     | ...        | ...        | ...      |
*/
CREATE TABLE east_superstore (
    "Row ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>4647</example>
    "Order ID" TEXT NOT NULL,
        -- <example>'CA-2011-141817'</example>
    "Order Date" DATE NOT NULL,
        -- <example>'2013-01-05'</example>
    "Ship Date" DATE NOT NULL,
        -- <example>'2013-01-12'</example>
    "Ship Mode" TEXT NOT NULL,
        -- <values>{'First Class', 'Same Day', 'Second Class', 'Standard Class'}</values>
    "Customer ID" TEXT NOT NULL,
        -- <example>'MB-18085'</example>
        -- <fk>composite</fk>
    Region TEXT NOT NULL,
        -- <values>{'East'}</values>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "Product ID" TEXT NOT NULL,
        -- <example>'OFF-AR-10003478'</example>
        -- <fk>composite</fk>
    Sales REAL NOT NULL,
        -- <example>19.536</example>
    Quantity INTEGER NOT NULL,
        -- <example>3</example>
    Discount REAL NOT NULL,
        -- <example>0.200</example>
    Profit REAL NOT NULL,
        -- <example>4.884</example>
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);

/*
Schema: NULLTable: people
Rows: 2501
Sample rows:
| Customer ID   | Customer Name   | Segment   | Country       | City          | State    | Postal Code   | Region   |
|---------------|-----------------|-----------|---------------|---------------|----------|---------------|----------|
| AA-10315      | Alex Avila      | Consumer  | United States | Round Rock    | Texas    | 78664         | Central  |
| AA-10375      | Allen Armold    | Consumer  | United States | Omaha         | Nebraska | 68104         | Central  |
| AA-10480      | Andrew Allen    | Consumer  | United States | Springfield   | Missouri | 65807         | Central  |
| AA-10645      | Anna Andreadi   | Consumer  | United States | Oklahoma City | Oklahoma | 73120         | Central  |
| AB-10015      | Aaron Bergman   | Consumer  | United States | Arlington     | Texas    | 76017         | Central  |
| ...           | ...             | ...       | ...           | ...           | ...      | ...           | ...      |
*/
CREATE TABLE people (
    "Customer ID" TEXT NOT NULL,
        -- <example>'AA-10315'</example>
    "Customer Name" TEXT NOT NULL,
        -- <example>'Alex Avila'</example>
    Segment TEXT NOT NULL,
        -- <values>{'Consumer', 'Corporate', 'Home Office'}</values>
    Country TEXT NOT NULL,
        -- <values>{'United States'}</values>
    City TEXT NOT NULL,
        -- <example>'Round Rock'</example>
    State TEXT NOT NULL,
        -- <example>'Texas'</example>
    "Postal Code" INTEGER NOT NULL,
        -- <example>78664</example>
    Region TEXT NOT NULL,
        -- <values>{'Central', 'East', 'South', 'West'}</values>
    PRIMARY KEY ("Customer ID", Region)
);

/*
Schema: NULLTable: product
Rows: 5298
Sample rows:
| Product ID      | Product Name                                                   | Category   | Sub-Category   | Region   |
|-----------------|----------------------------------------------------------------|------------|----------------|----------|
| FUR-BO-10000330 | Sauder Camden County Barrister Bookcase, Planked Cherry Finish | Furniture  | Bookcases      | West     |
| FUR-BO-10000362 | Sauder Inglewood Library Bookcases                             | Furniture  | Bookcases      | West     |
| FUR-BO-10000468 | O'Sullivan 2-Shelf Heavy-Duty Bookcases                        | Furniture  | Bookcases      | West     |
| FUR-BO-10001337 | O'Sullivan Living Dimensions 2-Shelf Bookcases                 | Furniture  | Bookcases      | West     |
| FUR-BO-10001519 | O'Sullivan 3-Shelf Heavy-Duty Bookcases                        | Furniture  | Bookcases      | West     |
| ...             | ...                                                            | ...        | ...            | ...      |
*/
CREATE TABLE product (
    "Product ID" TEXT NOT NULL,
        -- <example>'FUR-BO-10000112'</example>
    "Product Name" TEXT NOT NULL,
        -- <example>'Sauder Camden County Barrister Bookcase, Planked Cherry Finish'</example>
    Category TEXT NOT NULL,
        -- <values>{'Furniture', 'Office Supplies', 'Technology'}</values>
    "Sub-Category" TEXT NOT NULL,
        -- <values>{'Accessories', 'Appliances', 'Art', 'Binders', 'Bookcases', 'Chairs', 'Copiers', 'Envelopes', 'Fasteners', 'Furnishings', 'Labels', 'Machines', 'Paper', 'Phones', 'Storage', 'Supplies', 'Tables'}</values>
    Region TEXT NOT NULL,
        -- <values>{'Central', 'East', 'South', 'West'}</values>
    PRIMARY KEY ("Product ID", Region)
);

/*
Schema: NULLTable: south_superstore
Rows: 3240
Sample rows:
| Row ID   | Order ID       | Order Date   | Ship Date   | Ship Mode      | Customer ID   | Region   | Product ID      | Sales   | Quantity   | Discount   | Profit   |
|----------|----------------|--------------|-------------|----------------|---------------|----------|-----------------|---------|------------|------------|----------|
| 10343    | CA-2011-106054 | 2013-01-06   | 2013-01-07  | First Class    | JO-15145      | South    | OFF-AR-10002399 | 12.78   | 3          | 0.0        | 5.2398   |
| 10344    | CA-2011-167199 | 2013-01-06   | 2013-01-10  | Standard Class | ME-17320      | South    | FUR-CH-10004063 | 2573.82 | 9          | 0.0        | 746.4078 |
| 10345    | CA-2011-167199 | 2013-01-06   | 2013-01-10  | Standard Class | ME-17320      | South    | OFF-BI-10004632 | 609.98  | 2          | 0.0        | 274.491  |
| 10346    | CA-2011-167199 | 2013-01-06   | 2013-01-10  | Standard Class | ME-17320      | South    | OFF-AR-10001662 | 5.48    | 2          | 0.0        | 1.4796   |
| 10347    | CA-2011-167199 | 2013-01-06   | 2013-01-10  | Standard Class | ME-17320      | South    | TEC-PH-10004977 | 391.98  | 2          | 0.0        | 113.6742 |
| ...      | ...            | ...          | ...         | ...            | ...           | ...      | ...             | ...     | ...        | ...        | ...      |
*/
CREATE TABLE south_superstore (
    "Row ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>10343</example>
    "Order ID" TEXT NOT NULL,
        -- <example>'CA-2011-106054'</example>
    "Order Date" DATE NOT NULL,
        -- <example>'2013-01-06'</example>
    "Ship Date" DATE NOT NULL,
        -- <example>'2013-01-07'</example>
    "Ship Mode" TEXT NOT NULL,
        -- <values>{'First Class', 'Same Day', 'Second Class', 'Standard Class'}</values>
    "Customer ID" TEXT NOT NULL,
        -- <example>'JO-15145'</example>
        -- <fk>composite</fk>
    Region TEXT NOT NULL,
        -- <values>{'South'}</values>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "Product ID" TEXT NOT NULL,
        -- <example>'OFF-AR-10002399'</example>
        -- <fk>composite</fk>
    Sales REAL NOT NULL,
        -- <example>12.780</example>
    Quantity INTEGER NOT NULL,
        -- <example>3</example>
    Discount REAL NOT NULL,
        -- <example>0.000</example>
    Profit REAL NOT NULL,
        -- <example>5.240</example>
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);

/*
Schema: NULLTable: west_superstore
Rows: 6406
Sample rows:
| Row ID   | Order ID       | Order Date   | Ship Date   | Ship Mode      | Customer ID   | Region   | Product ID      | Sales   | Quantity   | Discount   | Profit   |
|----------|----------------|--------------|-------------|----------------|---------------|----------|-----------------|---------|------------|------------|----------|
| 13583    | CA-2011-130813 | 2013-01-06   | 2013-01-08  | Second Class   | LS-17230      | West     | OFF-PA-10002005 | 19.44   | 3          | 0.0        | 9.3312   |
| 13584    | CA-2011-157147 | 2013-01-13   | 2013-01-18  | Standard Class | BD-11605      | West     | OFF-ST-10000078 | 1325.85 | 5          | 0.0        | 238.653  |
| 13585    | CA-2011-157147 | 2013-01-13   | 2013-01-18  | Standard Class | BD-11605      | West     | FUR-BO-10003034 | 333.999 | 3          | 0.15       | 3.9294   |
| 13586    | CA-2011-157147 | 2013-01-13   | 2013-01-18  | Standard Class | BD-11605      | West     | OFF-AR-10003514 | 19.9    | 5          | 0.0        | 6.567    |
| 13587    | CA-2011-123477 | 2013-01-18   | 2013-01-21  | Second Class   | DW-13195      | West     | OFF-AP-10000692 | 64.864  | 4          | 0.2        | 6.4864   |
| ...      | ...            | ...          | ...         | ...            | ...           | ...      | ...             | ...     | ...        | ...        | ...      |
*/
CREATE TABLE west_superstore (
    "Row ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>13583</example>
    "Order ID" TEXT NOT NULL,
        -- <example>'CA-2011-130813'</example>
    "Order Date" DATE NOT NULL,
        -- <example>'2013-01-06'</example>
    "Ship Date" DATE NOT NULL,
        -- <example>'2013-01-08'</example>
    "Ship Mode" TEXT NOT NULL,
        -- <values>{'First Class', 'Same Day', 'Second Class', 'Standard Class'}</values>
    "Customer ID" TEXT NOT NULL,
        -- <example>'LS-17230'</example>
        -- <fk>composite</fk>
    Region TEXT NOT NULL,
        -- <values>{'West'}</values>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "Product ID" TEXT NOT NULL,
        -- <example>'OFF-PA-10002005'</example>
        -- <fk>composite</fk>
    Sales REAL NOT NULL,
        -- <example>19.440</example>
    Quantity INTEGER NOT NULL,
        -- <example>3</example>
    Discount REAL NOT NULL,
        -- <example>0.000</example>
    Profit REAL NOT NULL,
        -- <example>9.331</example>
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);
```