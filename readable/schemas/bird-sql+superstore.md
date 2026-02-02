```sql
-- Database: superstore

-- Table: central_superstore (4646 rows)
CREATE TABLE central_superstore (
    "Row ID" INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    "Order ID" TEXT NULL,
        -- <example>'CA-2011-103800'</example>
    "Order Date" DATE NULL,
        -- <example>'2013-01-03'</example>
    "Ship Date" DATE NULL,
        -- <example>'2013-01-07'</example>
    "Ship Mode" TEXT NULL,
        -- <values>{'First Class', 'Same Day', 'Second Class', 'Standard Class'}</values>
    "Customer ID" TEXT NULL,
        -- <example>'DP-13000'</example>
        -- <fk>composite</fk>
    Region TEXT NULL,
        -- <values>{'Central'}</values>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "Product ID" TEXT NULL,
        -- <example>'OFF-PA-10000174'</example>
        -- <fk>composite</fk>
    Sales REAL NULL,
        -- <example>16.448</example>
    Quantity INTEGER NULL,
        -- <example>2</example>
    Discount REAL NULL,
        -- <example>0.200</example>
    Profit REAL NULL,
        -- <example>5.551</example>
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);

-- Table: east_superstore (5696 rows)
CREATE TABLE east_superstore (
    "Row ID" INTEGER NULL PRIMARY KEY,
        -- <example>4647</example>
    "Order ID" TEXT NULL,
        -- <example>'CA-2011-141817'</example>
    "Order Date" DATE NULL,
        -- <example>'2013-01-05'</example>
    "Ship Date" DATE NULL,
        -- <example>'2013-01-12'</example>
    "Ship Mode" TEXT NULL,
        -- <values>{'First Class', 'Same Day', 'Second Class', 'Standard Class'}</values>
    "Customer ID" TEXT NULL,
        -- <example>'MB-18085'</example>
        -- <fk>composite</fk>
    Region TEXT NULL,
        -- <values>{'East'}</values>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "Product ID" TEXT NULL,
        -- <example>'OFF-AR-10003478'</example>
        -- <fk>composite</fk>
    Sales REAL NULL,
        -- <example>19.536</example>
    Quantity INTEGER NULL,
        -- <example>3</example>
    Discount REAL NULL,
        -- <example>0.200</example>
    Profit REAL NULL,
        -- <example>4.884</example>
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);

-- Table: people (2501 rows)
CREATE TABLE people (
    "Customer ID" TEXT NULL,
        -- <example>'AA-10315'</example>
    "Customer Name" TEXT NULL,
        -- <example>'Alex Avila'</example>
    Segment TEXT NULL,
        -- <values>{'Consumer', 'Corporate', 'Home Office'}</values>
    Country TEXT NULL,
        -- <values>{'United States'}</values>
    City TEXT NULL,
        -- <example>'Round Rock'</example>
    State TEXT NULL,
        -- <example>'Texas'</example>
    "Postal Code" INTEGER NULL,
        -- <example>78664</example>
    Region TEXT NULL,
        -- <values>{'Central', 'East', 'South', 'West'}</values>
    PRIMARY KEY ("Customer ID", Region)
);

-- Table: product (5298 rows)
CREATE TABLE product (
    "Product ID" TEXT NULL,
        -- <example>'FUR-BO-10000112'</example>
    "Product Name" TEXT NULL,
        -- <example>'Sauder Camden County Barrister Bookcase, Planked Cherry Finish'</example>
    Category TEXT NULL,
        -- <values>{'Furniture', 'Office Supplies', 'Technology'}</values>
    "Sub-Category" TEXT NULL,
        -- <values>{'Accessories', 'Appliances', 'Art', 'Binders', 'Bookcases', 'Chairs', 'Copiers', 'Envelopes', 'Fasteners', 'Furnishings', 'Labels', 'Machines', 'Paper', 'Phones', 'Storage', 'Supplies', 'Tables'}</values>
    Region TEXT NULL,
        -- <values>{'Central', 'East', 'South', 'West'}</values>
    PRIMARY KEY ("Product ID", Region)
);

-- Table: south_superstore (3240 rows)
CREATE TABLE south_superstore (
    "Row ID" INTEGER NULL PRIMARY KEY,
        -- <example>10343</example>
    "Order ID" TEXT NULL,
        -- <example>'CA-2011-106054'</example>
    "Order Date" DATE NULL,
        -- <example>'2013-01-06'</example>
    "Ship Date" DATE NULL,
        -- <example>'2013-01-07'</example>
    "Ship Mode" TEXT NULL,
        -- <values>{'First Class', 'Same Day', 'Second Class', 'Standard Class'}</values>
    "Customer ID" TEXT NULL,
        -- <example>'JO-15145'</example>
        -- <fk>composite</fk>
    Region TEXT NULL,
        -- <values>{'South'}</values>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "Product ID" TEXT NULL,
        -- <example>'OFF-AR-10002399'</example>
        -- <fk>composite</fk>
    Sales REAL NULL,
        -- <example>12.780</example>
    Quantity INTEGER NULL,
        -- <example>3</example>
    Discount REAL NULL,
        -- <example>0.000</example>
    Profit REAL NULL,
        -- <example>5.240</example>
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);

-- Table: west_superstore (6406 rows)
CREATE TABLE west_superstore (
    "Row ID" INTEGER NULL PRIMARY KEY,
        -- <example>13583</example>
    "Order ID" TEXT NULL,
        -- <example>'CA-2011-130813'</example>
    "Order Date" DATE NULL,
        -- <example>'2013-01-06'</example>
    "Ship Date" DATE NULL,
        -- <example>'2013-01-08'</example>
    "Ship Mode" TEXT NULL,
        -- <values>{'First Class', 'Same Day', 'Second Class', 'Standard Class'}</values>
    "Customer ID" TEXT NULL,
        -- <example>'LS-17230'</example>
        -- <fk>composite</fk>
    Region TEXT NULL,
        -- <values>{'West'}</values>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "Product ID" TEXT NULL,
        -- <example>'OFF-PA-10002005'</example>
        -- <fk>composite</fk>
    Sales REAL NULL,
        -- <example>19.440</example>
    Quantity INTEGER NULL,
        -- <example>3</example>
    Discount REAL NULL,
        -- <example>0.000</example>
    Profit REAL NULL,
        -- <example>9.331</example>
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);
```