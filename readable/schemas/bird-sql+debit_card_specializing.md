```sql
-- Database: debit_card_specializing

-- Table: customers (32461 rows)
CREATE TABLE customers (
    CustomerID INTEGER NOT NULL PRIMARY KEY,
        -- <example>3</example>
    Segment TEXT NULL,
        -- <values>{'KAM', 'LAM', 'SME'}</values>
    Currency TEXT NULL
        -- <values>{'CZK', 'EUR'}</values>
);

-- Table: gasstations (5716 rows)
CREATE TABLE gasstations (
    GasStationID INTEGER NOT NULL PRIMARY KEY,
        -- <example>44</example>
    ChainID INTEGER NULL,
        -- <example>13</example>
    Country TEXT NULL,
        -- <values>{'CZE', 'SVK'}</values>
    Segment TEXT NULL
        -- <values>{'Discount', 'Noname', 'Other', 'Premium', 'Value for money'}</values>
);

-- Table: products (591 rows)
CREATE TABLE products (
    ProductID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Description TEXT NULL
        -- <example>'Rucní zadání'</example>
);

-- Table: transactions_1k (1000 rows)
CREATE TABLE transactions_1k (
    TransactionID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Date DATE NULL,
        -- <example>'2012-08-24'</example>
    Time TEXT NULL,
        -- <example>'09:41:00'</example>
    CustomerID INTEGER NULL,
        -- <example>31543</example>
    CardID INTEGER NULL,
        -- <example>486621</example>
    GasStationID INTEGER NULL,
        -- <example>3704</example>
    ProductID INTEGER NULL,
        -- <example>2</example>
    Amount INTEGER NULL,
        -- <example>28</example>
    Price REAL NULL
        -- <example>672.640</example>
);

-- Table: yearmonth (383282 rows)
CREATE TABLE yearmonth (
    CustomerID INTEGER NOT NULL,
        -- <example>39</example>
        -- <fk> -> customers.CustomerID</fk>
    Date TEXT NOT NULL,
        -- <example>'201112'</example>
    Consumption REAL NULL,
        -- <example>528.300</example>
    PRIMARY KEY (CustomerID, Date),
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID)
);
```