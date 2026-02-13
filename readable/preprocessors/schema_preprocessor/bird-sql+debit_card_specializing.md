```sql
-- Database: debit_card_specializing

/*
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
    CustomerID INTEGER NOT NULL PRIMARY KEY,
        -- <description>Customer identifier linking a customer record to related tables (used to associate transactions and monthly consumption with a specific customer).</description>
        -- <example>3</example>
    Segment TEXT NOT NULL,
        -- <description>Customer segment — the customer's client/market category used to classify accounts by client type.</description>
        -- <values>{'KAM', 'LAM', 'SME'}</values>
    Currency TEXT NOT NULL
        -- <description>Customer account currency — the currency in which the customer's account and related transactions are denominated.</description>
        -- <values>{'CZK', 'EUR'}</values>
);

/*
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
    GasStationID INTEGER NOT NULL PRIMARY KEY,
        -- <description>Gas station identifier used to link transactions to the station and to represent chain membership (referenced by transactions_1k.GasStationID and by gasstations.ChainID).</description>
        -- <example>44</example>
    ChainID INTEGER NOT NULL,
        -- <description>Gas station chain identifier linking a station to its parent chain (used to group stations by chain; typically a self-referential reference to gasstations.GasStationID).</description>
        -- <example>13</example>
        -- <fk> -> gasstations.GasStationID</fk>
        -- <fk> -> products.ProductID</fk>
    Country TEXT NOT NULL,
        -- <description>Country of the gas station’s location, used for regional grouping and filtering.</description>
        -- <values>{'CZE', 'SVK'}</values>
    Segment TEXT NOT NULL,
        -- <description>Gas station chain segment — categorical label indicating the chain's market positioning.</description>
        -- <values>{'Discount', 'Noname', 'Other', 'Premium', 'Value for money'}</values>
    FOREIGN KEY (ChainID) REFERENCES gasstations(GasStationID),
    FOREIGN KEY (ChainID) REFERENCES products(ProductID)
);

/*
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
    ProductID INTEGER NOT NULL PRIMARY KEY,
        -- <description>Product identifier used to reference product records from other tables (e.g., transactions).</description>
        -- <example>1</example>
    Description TEXT NOT NULL
        -- <description>Product description — a short human-readable name or label for the product (e.g., 'Rucní zadání', 'Nafta', 'Special').</description>
        -- <example>'Rucní zadání'</example>
);

/*
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
    TransactionID INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for each transaction.</description>
        -- <example>1</example>
    Date DATE NOT NULL,
        -- <description>Transaction date — the calendar date on which the transaction occurred (ISO YYYY-MM-DD).</description>
        -- <example>'2012-08-24'</example>
    Time TEXT NOT NULL,
        -- <description>Transaction time — the clock time when each transaction occurred, recorded in hours:minutes:seconds (e.g., 14:28:00).</description>
        -- <example>'09:41:00'</example>
    CustomerID INTEGER NOT NULL,
        -- <description>Customer identifier for the transaction — the customer who made the purchase.</description>
        -- <example>31543</example>
        -- <fk> -> customers.CustomerID</fk>
    CardID INTEGER NOT NULL,
        -- <description>Debit card identifier linking the transaction to the specific card used.</description>
        -- <example>486621</example>
    GasStationID INTEGER NOT NULL,
        -- <description>Gas station identifier — foreign key to gasstations.GasStationID indicating the station where the transaction occurred.</description>
        -- <example>3704</example>
        -- <fk> -> gasstations.GasStationID</fk>
    ProductID INTEGER NOT NULL,
        -- <description>Product identifier for the item purchased in the transaction (foreign key to products.ProductID).</description>
        -- <example>2</example>
        -- <fk> -> products.ProductID</fk>
    Amount INTEGER NOT NULL,
        -- <description>Quantity purchased in the transaction — integer number of units (e.g., liters or items); combine with Price (the transaction total) to derive a per‑unit price if needed.</description>
        -- <example>28</example>
    Price REAL NOT NULL,
        -- <description>Unit price of the purchased product in the transaction; multiply by Amount to obtain the transaction line total.</description>
        -- <example>672.640</example>
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID),
    FOREIGN KEY (GasStationID) REFERENCES gasstations(GasStationID),
    FOREIGN KEY (ProductID) REFERENCES products(ProductID)
);

/*
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
    CustomerID INTEGER NOT NULL,
        -- <description>Customer identifier (foreign key to customers.CustomerID; part of the yearmonth table's composite primary key).</description>
        -- <example>39</example>
        -- <fk> -> customers.CustomerID</fk>
    Date TEXT NOT NULL,
        -- <description>Year–month period of the record, encoded as YYYYMM (four-digit year followed by two-digit month); examples: '201205', '201302', '201304'.</description>
        -- <example>'201112'</example>
    Consumption REAL NOT NULL,
        -- <description>Monthly consumption amount per customer (total monetary consumption for the specified year‑month).</description>
        -- <example>528.300</example>
    PRIMARY KEY (CustomerID, Date),
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID)
);
```