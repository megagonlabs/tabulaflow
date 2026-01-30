```sql
-- Database: superstore

-- Table: central_superstore (4646 rows)
CREATE TABLE central_superstore (
    "Row ID" INTEGER PRIMARY KEY,  -- e.g. 1
    "Order ID" TEXT,  -- e.g. 'CA-2011-103800'
    "Order Date" DATE,  -- e.g. '2013-01-03'
    "Ship Date" DATE,  -- e.g. '2013-01-07'
    "Ship Mode" TEXT,  -- values: {'First Class', 'Same Day', 'Second Class', 'Standard Class'}
    "Customer ID" TEXT,  -- e.g. 'DP-13000'; FK (composite)
    Region TEXT,  -- values: {'Central'}; FK (composite); FK (composite)
    "Product ID" TEXT,  -- e.g. 'OFF-PA-10000174'; FK (composite)
    Sales REAL,  -- e.g. 16.448
    Quantity INTEGER,  -- e.g. 2
    Discount REAL,  -- e.g. 0.200
    Profit REAL,  -- e.g. 5.551
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);

-- Table: east_superstore (5696 rows)
CREATE TABLE east_superstore (
    "Row ID" INTEGER PRIMARY KEY,  -- e.g. 4647
    "Order ID" TEXT,  -- e.g. 'CA-2011-141817'
    "Order Date" DATE,  -- e.g. '2013-01-05'
    "Ship Date" DATE,  -- e.g. '2013-01-12'
    "Ship Mode" TEXT,  -- values: {'First Class', 'Same Day', 'Second Class', 'Standard Class'}
    "Customer ID" TEXT,  -- e.g. 'MB-18085'; FK (composite)
    Region TEXT,  -- values: {'East'}; FK (composite); FK (composite)
    "Product ID" TEXT,  -- e.g. 'OFF-AR-10003478'; FK (composite)
    Sales REAL,  -- e.g. 19.536
    Quantity INTEGER,  -- e.g. 3
    Discount REAL,  -- e.g. 0.200
    Profit REAL,  -- e.g. 4.884
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);

-- Table: people (2501 rows)
CREATE TABLE people (
    "Customer ID" TEXT,  -- e.g. 'AA-10315'
    "Customer Name" TEXT,  -- e.g. 'Alex Avila'
    Segment TEXT,  -- values: {'Consumer', 'Corporate', 'Home Office'}
    Country TEXT,  -- values: {'United States'}
    City TEXT,  -- e.g. 'Round Rock'
    State TEXT,  -- e.g. 'Texas'
    "Postal Code" INTEGER,  -- e.g. 78664
    Region TEXT,  -- values: {'Central', 'East', 'South', 'West'}
    PRIMARY KEY ("Customer ID", Region)
);

-- Table: product (5298 rows)
CREATE TABLE product (
    "Product ID" TEXT,  -- e.g. 'FUR-BO-10000112'
    "Product Name" TEXT,  -- e.g. 'Sauder Camden County Barrister Bookcase, Planked Cherry Finish'
    Category TEXT,  -- values: {'Furniture', 'Office Supplies', 'Technology'}
    "Sub-Category" TEXT,  -- values: {'Accessories', 'Appliances', 'Art', 'Binders', 'Bookcases', 'Chairs', 'Copiers', 'Envelopes', 'Fasteners', 'Furnishings', 'Labels', 'Machines', 'Paper', 'Phones', 'Storage', 'Supplies', 'Tables'}
    Region TEXT,  -- values: {'Central', 'East', 'South', 'West'}
    PRIMARY KEY ("Product ID", Region)
);

-- Table: south_superstore (3240 rows)
CREATE TABLE south_superstore (
    "Row ID" INTEGER PRIMARY KEY,  -- e.g. 10343
    "Order ID" TEXT,  -- e.g. 'CA-2011-106054'
    "Order Date" DATE,  -- e.g. '2013-01-06'
    "Ship Date" DATE,  -- e.g. '2013-01-07'
    "Ship Mode" TEXT,  -- values: {'First Class', 'Same Day', 'Second Class', 'Standard Class'}
    "Customer ID" TEXT,  -- e.g. 'JO-15145'; FK (composite)
    Region TEXT,  -- values: {'South'}; FK (composite); FK (composite)
    "Product ID" TEXT,  -- e.g. 'OFF-AR-10002399'; FK (composite)
    Sales REAL,  -- e.g. 12.780
    Quantity INTEGER,  -- e.g. 3
    Discount REAL,  -- e.g. 0.000
    Profit REAL,  -- e.g. 5.240
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);

-- Table: west_superstore (6406 rows)
CREATE TABLE west_superstore (
    "Row ID" INTEGER PRIMARY KEY,  -- e.g. 13583
    "Order ID" TEXT,  -- e.g. 'CA-2011-130813'
    "Order Date" DATE,  -- e.g. '2013-01-06'
    "Ship Date" DATE,  -- e.g. '2013-01-08'
    "Ship Mode" TEXT,  -- values: {'First Class', 'Same Day', 'Second Class', 'Standard Class'}
    "Customer ID" TEXT,  -- e.g. 'LS-17230'; FK (composite)
    Region TEXT,  -- values: {'West'}; FK (composite); FK (composite)
    "Product ID" TEXT,  -- e.g. 'OFF-PA-10002005'; FK (composite)
    Sales REAL,  -- e.g. 19.440
    Quantity INTEGER,  -- e.g. 3
    Discount REAL,  -- e.g. 0.000
    Profit REAL,  -- e.g. 9.331
    FOREIGN KEY ("Customer ID", Region) REFERENCES people("Customer ID", Region),
    FOREIGN KEY ("Product ID", Region) REFERENCES product("Product ID", Region)
);
```