```sql
-- Database: debit_card_specializing

-- Table: customers (32461 rows)
CREATE TABLE customers (
    CustomerID INTEGER NOT NULL PRIMARY KEY,
        -- <description>Customer identifier — one per customer; contains no nulls and all 32,461 values are distinct. Observed ID values range from 3 to 53,314.</description>
        -- <example>3</example>
    Segment TEXT NULL,
        -- <description>Customer segment label indicating the customer's account/relationship category used for grouping and analysis.</description>
        -- <values>{'KAM', 'LAM', 'SME'}</values>
    Currency TEXT NULL
        -- <description>Customer account currency — indicates the currency in which the customer's account and transactions are denominated.</description>
        -- <values>{'CZK', 'EUR'}</values>
);

-- Table: gasstations (5716 rows)
CREATE TABLE gasstations (
    GasStationID INTEGER NOT NULL PRIMARY KEY,
        -- <description>Gas station identifier used to reference gas stations from other tables (e.g., in transactions and chain relationships).</description>
        -- <example>44</example>
    ChainID INTEGER NULL,
        -- <description>Gas station chain identifier — indicates which chain a station belongs to; intended to reference gasstations.GasStationID but many values do not match that table.</description>
        -- <example>13</example>
        -- <fk> -> gasstations.GasStationID</fk>
    Country TEXT NULL,
        -- <description>Country of the gas station's location.</description>
        -- <values>{'CZE', 'SVK'}</values>
    Segment TEXT NULL,
        -- <description>Gas station chain segment — categorical label classifying the market positioning of the station’s chain (used to group or filter stations by commercial segment).</description>
        -- <values>{'Discount', 'Noname', 'Other', 'Premium', 'Value for money'}</values>
    FOREIGN KEY (ChainID) REFERENCES gasstations(GasStationID)
);

-- Table: products (591 rows)
CREATE TABLE products (
    ProductID INTEGER NOT NULL PRIMARY KEY,
        -- <description>Product identifier linking a product record to transactions (referenced by transactions_1k.ProductID).</description>
        -- <example>1</example>
    Description TEXT NULL
        -- <description>Product description — short textual label identifying the product or service sold (contains Czech product names, e.g. “Mýtný poplatek”, “Servisní poplatek”, “CNG”).</description>
        -- <example>'Rucní zadání'</example>
);

-- Table: transactions_1k (1000 rows)
CREATE TABLE transactions_1k (
    TransactionID INTEGER NULL PRIMARY KEY,
        -- <description>Transaction identifier — a per-row transaction ID in transactions_1k (sequential integers 1–1000 with no nulls).</description>
        -- <example>1</example>
    Date DATE NULL,
        -- <description>Transaction date — the calendar date when the transaction occurred (observed range in this table: 2012-08-23 through 2012-08-26; no missing values).</description>
        -- <example>'2012-08-24'</example>
    Time TEXT NULL,
        -- <description>Transaction time of day (24-hour HH:MM:SS). Recorded for each row (no missing values); 599 distinct times in 1,000 rows; observed range 00:07:00–23:20:00.</description>
        -- <example>'09:41:00'</example>
    CustomerID INTEGER NULL,
        -- <description>Customer identifier for the transaction — links each transaction to the customer who made it (foreign key to customers).</description>
        -- <example>31543</example>
        -- <fk> -> customers.CustomerID</fk>
    CardID INTEGER NULL,
        -- <description>Debit card identifier for the transaction — identifies the specific debit card used; not unique per row (card IDs can repeat across transactions).</description>
        -- <example>486621</example>
    GasStationID INTEGER NULL,
        -- <description>Gas station identifier for the transaction — identifies the gas station where the purchase occurred.</description>
        -- <example>3704</example>
        -- <fk> -> gasstations.GasStationID</fk>
    ProductID INTEGER NULL,
        -- <description>Identifier of the product purchased in the transaction.</description>
        -- <example>2</example>
        -- <fk> -> products.ProductID</fk>
    Amount INTEGER NULL,
        -- <description>Quantity of items purchased in the transaction — the number of units bought (can be 0 for adjustments); common values include 0, 5 and 25, with observed range 0–264 and mean ≈ 19.7.</description>
        -- <example>28</example>
    Price REAL NULL,
        -- <description>Unit (per-item) price of the product in the transaction — the per‑item amount charged. Used together with Amount to compute the transaction total (Amount × Price).</description>
        -- <example>672.640</example>
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID),
    FOREIGN KEY (GasStationID) REFERENCES gasstations(GasStationID),
    FOREIGN KEY (ProductID) REFERENCES products(ProductID)
);

-- Table: yearmonth (383282 rows)
CREATE TABLE yearmonth (
    CustomerID INTEGER NOT NULL,
        -- <description>Customer identifier that ties each month-level consumption record to a specific customer.</description>
        -- <example>39</example>
        -- <fk> -> customers.CustomerID</fk>
    Date TEXT NOT NULL,
        -- <description>Year–month identifier in YYYYMM format representing the year and month of the consumption record (e.g., 201112). All 383,282 rows conform to the YYYYMM pattern and values span from 201112 to 201311.</description>
        -- <example>'201112'</example>
    Consumption REAL NULL,
        -- <description>Per-customer monthly consumption (aggregated monetary amount for the CustomerID × Date period).</description>
        -- <example>528.300</example>
    PRIMARY KEY (CustomerID, Date),
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID)
);
```