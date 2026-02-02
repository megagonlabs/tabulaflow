```sql
-- Database: regional_sales

-- Table: Customers (50 rows)
CREATE TABLE Customers (
    CustomerID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    "Customer Names" TEXT NULL
        -- <example>'Avon Corp'</example>
);

-- Table: Products (47 rows)
CREATE TABLE Products (
    ProductID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    "Product Name" TEXT NULL
        -- <example>'Cookware'</example>
);

-- Table: Regions (48 rows)
CREATE TABLE Regions (
    StateCode TEXT NULL PRIMARY KEY,
        -- <example>'AL'</example>
    State TEXT NULL,
        -- <example>'Alabama'</example>
    Region TEXT NULL
        -- <values>{'Midwest', 'Northeast', 'South', 'West'}</values>
);

-- Table: "Sales Orders" (7991 rows)
CREATE TABLE "Sales Orders" (
    OrderNumber TEXT NULL PRIMARY KEY,
        -- <example>'SO - 0001000'</example>
    "Sales Channel" TEXT NULL,
        -- <values>{'Distributor', 'In-Store', 'Online', 'Wholesale'}</values>
    WarehouseCode TEXT NULL,
        -- <values>{'WARE-MKL1006', 'WARE-NBV1002', 'WARE-NMK1003', 'WARE-PUJ1005', 'WARE-UHY1004', 'WARE-XYS1001'}</values>
    ProcuredDate TEXT NULL,
        -- <values>{'10/27/18', '12/1/19', '12/31/17', '2/4/19', '3/10/20', '4/10/18', '5/15/19', '6/18/20', '7/19/18', '8/23/19', '9/26/20'}</values>
    OrderDate TEXT NULL,
        -- <example>'5/31/18'</example>
    ShipDate TEXT NULL,
        -- <example>'6/14/18'</example>
    DeliveryDate TEXT NULL,
        -- <example>'6/19/18'</example>
    CurrencyCode TEXT NULL,
        -- <values>{'USD'}</values>
    _SalesTeamID INTEGER NULL,
        -- <example>6</example>
        -- <fk> -> "Sales Team".SalesTeamID</fk>
    _CustomerID INTEGER NULL,
        -- <example>15</example>
        -- <fk> -> Customers.CustomerID</fk>
    _StoreID INTEGER NULL,
        -- <example>259</example>
        -- <fk> -> "Store Locations".StoreID</fk>
    _ProductID INTEGER NULL,
        -- <example>12</example>
        -- <fk> -> Products.ProductID</fk>
    "Order Quantity" INTEGER NULL,
        -- <example>5</example>
    "Discount Applied" REAL NULL,
        -- <example>0.075</example>
    "Unit Price" TEXT NULL,
        -- <example>'1,963.10'</example>
    "Unit Cost" TEXT NULL,
        -- <example>'1,001.18'</example>
    FOREIGN KEY (_ProductID) REFERENCES Products(ProductID),
    FOREIGN KEY (_StoreID) REFERENCES "Store Locations"(StoreID),
    FOREIGN KEY (_CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (_SalesTeamID) REFERENCES "Sales Team"(SalesTeamID)
);

-- Table: "Sales Team" (28 rows)
CREATE TABLE "Sales Team" (
    SalesTeamID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    "Sales Team" TEXT NULL,
        -- <example>'Adam Hernandez'</example>
    Region TEXT NULL
        -- <values>{'Midwest', 'Northeast', 'South', 'West'}</values>
);

-- Table: "Store Locations" (367 rows)
CREATE TABLE "Store Locations" (
    StoreID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    "City Name" TEXT NULL,
        -- <example>'Birmingham'</example>
    County TEXT NULL,
        -- <example>'Shelby County/Jefferson County'</example>
    StateCode TEXT NULL,
        -- <example>'AL'</example>
        -- <fk> -> Regions.StateCode</fk>
    State TEXT NULL,
        -- <example>'Alabama'</example>
    Type TEXT NULL,
        -- <values>{'Borough', 'CDP', 'City', 'Consolidated Government', 'Metropolitan Government', 'Other', 'Town', 'Township', 'Unified Government', 'Urban County '}</values>
    Latitude REAL NULL,
        -- <example>33.527</example>
    Longitude REAL NULL,
        -- <example>-86.799</example>
    AreaCode INTEGER NULL,
        -- <example>205</example>
    Population INTEGER NULL,
        -- <example>212461</example>
    "Household Income" INTEGER NULL,
        -- <example>89972</example>
    "Median Income" INTEGER NULL,
        -- <example>31061</example>
    "Land Area" INTEGER NULL,
        -- <example>378353942</example>
    "Water Area" INTEGER NULL,
        -- <example>6591013</example>
    "Time Zone" TEXT NULL,
        -- <values>{'America/Boise', 'America/Chicago', 'America/Denver', 'America/Detroit', 'America/Indiana/Indianapolis', 'America/Los Angeles', 'America/New York', 'America/Phoenix', 'Pacific/Honolulu'}</values>
    FOREIGN KEY (StateCode) REFERENCES Regions(StateCode)
);
```