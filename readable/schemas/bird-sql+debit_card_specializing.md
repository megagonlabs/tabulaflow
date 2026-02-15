```sql
-- Database: debit_card_specializing

/*
Schema: NULL
Table: customers
Rows: 32461
Sample rows:
| CustomerID   | Segment   | Currency   |
|--------------|-----------|------------|
| 3            | SME       | EUR        |
| 5            | LAM       | EUR        |
| 6            | SME       | EUR        |
| 7            | LAM       | EUR        |
| 9            | SME       | EUR        |
| ...          | ...       | ...        |
*/
CREATE TABLE customers (
    "CustomerID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>3</example>
    "Segment" TEXT NOT NULL,
        -- <values>{'KAM', 'LAM', 'SME'}</values>
    "Currency" TEXT NOT NULL
        -- <values>{'CZK', 'EUR'}</values>
);

/*
Schema: NULL
Table: gasstations
Rows: 5716
Sample rows:
| GasStationID   | ChainID   | Country   | Segment         |
|----------------|-----------|-----------|-----------------|
| 44             | 13        | CZE       | Value for money |
| 45             | 6         | CZE       | Premium         |
| 46             | 23        | CZE       | Other           |
| 47             | 33        | CZE       | Premium         |
| 48             | 4         | CZE       | Premium         |
| ...            | ...       | ...       | ...             |
*/
CREATE TABLE gasstations (
    "GasStationID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>44</example>
    "ChainID" INTEGER NOT NULL,
        -- <example>13</example>
    "Country" TEXT NOT NULL,
        -- <values>{'CZE', 'SVK'}</values>
    "Segment" TEXT NOT NULL
        -- <values>{'Discount', 'Noname', 'Other', 'Premium', 'Value for money'}</values>
);

/*
Schema: NULL
Table: products
Rows: 591
Sample rows:
| ProductID   | Description   |
|-------------|---------------|
| 1           | Rucní zadání  |
| 2           | Nafta         |
| 3           | Special       |
| 4           | Super         |
| 5           | Natural       |
| ...         | ...           |
*/
CREATE TABLE products (
    "ProductID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Description" TEXT NOT NULL
        -- <example>'Rucní zadání'</example>
);

/*
Schema: NULL
Table: transactions_1k
Rows: 1000
Sample rows:
| TransactionID   | Date       | Time     | CustomerID   | CardID   | GasStationID   | ProductID   | Amount   | Price   |
|-----------------|------------|----------|--------------|----------|----------------|-------------|----------|---------|
| 1               | 2012-08-24 | 09:41:00 | 31543        | 486621   | 3704           | 2           | 28       | 672.64  |
| 2               | 2012-08-24 | 10:03:00 | 46707        | 550134   | 3704           | 2           | 18       | 430.72  |
| 3               | 2012-08-24 | 10:03:00 | 46707        | 550134   | 3704           | 23          | 1        | 121.99  |
| 4               | 2012-08-24 | 13:53:00 | 7654         | 684220   | 656            | 5           | 5        | 120.74  |
| 5               | 2012-08-24 | 08:49:00 | 17373        | 536109   | 741            | 2           | 28       | 645.05  |
| ...             | ...        | ...      | ...          | ...      | ...            | ...         | ...      | ...     |
*/
CREATE TABLE transactions_1k (
    "TransactionID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Date" DATE NOT NULL,
        -- <example>'2012-08-24'</example>
    "Time" TEXT NOT NULL,
        -- <example>'09:41:00'</example>
    "CustomerID" INTEGER NOT NULL,
        -- <example>31543</example>
    "CardID" INTEGER NOT NULL,
        -- <example>486621</example>
    "GasStationID" INTEGER NOT NULL,
        -- <example>3704</example>
    "ProductID" INTEGER NOT NULL,
        -- <example>2</example>
    "Amount" INTEGER NOT NULL,
        -- <example>28</example>
    "Price" REAL NOT NULL
        -- <example>672.640</example>
);

/*
Schema: NULL
Table: yearmonth
Rows: 383282
Sample rows:
| CustomerID   | Date   | Consumption   |
|--------------|--------|---------------|
| 5            | 201207 | 528.3         |
| 5            | 201302 | 1598.28       |
| 5            | 201303 | 1931.36       |
| 5            | 201304 | 1497.14       |
| 6            | 201203 | 51.06         |
| ...          | ...    | ...           |
*/
CREATE TABLE yearmonth (
    "CustomerID" INTEGER NOT NULL,
        -- <example>39</example>
        -- <fk> -> customers."CustomerID"</fk>
    "Date" TEXT NOT NULL,
        -- <example>'201112'</example>
    "Consumption" REAL NOT NULL,
        -- <example>528.300</example>
    PRIMARY KEY ("CustomerID", "Date"),
    FOREIGN KEY ("CustomerID") REFERENCES customers("CustomerID")
);
```