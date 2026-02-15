```sql
-- Database: regional_sales

/*
Schema: NULL
Table: Customers
Rows: 50
Sample rows:
| CustomerID   | Customer Names   |
|--------------|------------------|
| 1            | Avon Corp        |
| 2            | WakeFern         |
| 3            | Elorac, Corp     |
| 4            | ETUDE Ltd        |
| 5            | Procter Corp     |
| ...          | ...              |
*/
CREATE TABLE Customers (
    "CustomerID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Customer Names" TEXT NOT NULL
        -- <example>'Avon Corp'</example>
);

/*
Schema: NULL
Table: Products
Rows: 47
Sample rows:
| ProductID   | Product Name       |
|-------------|--------------------|
| 1           | Cookware           |
| 2           | Photo Frames       |
| 3           | Table Lamps        |
| 4           | Serveware          |
| 5           | Bathroom Furniture |
| ...         | ...                |
*/
CREATE TABLE Products (
    "ProductID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Product Name" TEXT NOT NULL
        -- <example>'Cookware'</example>
);

/*
Schema: NULL
Table: Regions
Rows: 48
Sample rows:
| StateCode   | State      | Region   |
|-------------|------------|----------|
| AL          | Alabama    | South    |
| AR          | Arkansas   | South    |
| AZ          | Arizona    | West     |
| CA          | California | West     |
| CO          | Colorado   | West     |
| ...         | ...        | ...      |
*/
CREATE TABLE Regions (
    "StateCode" TEXT NOT NULL PRIMARY KEY,
        -- <example>'AL'</example>
    "State" TEXT NOT NULL,
        -- <example>'Alabama'</example>
    "Region" TEXT NOT NULL
        -- <values>{'Midwest', 'Northeast', 'South', 'West'}</values>
);

/*
Schema: NULL
Table: "Sales Orders"
Rows: 7991
Sample rows:
| OrderNumber   | Sales Channel   | WarehouseCode   | ProcuredDate   | OrderDate   | ShipDate   | DeliveryDate   | CurrencyCode   | _SalesTeamID   | _CustomerID   | _StoreID   | _ProductID   | Order Quantity   | Discount Applied   | Unit Price   | Unit Cost   |
|---------------|-----------------|-----------------|----------------|-------------|------------|----------------|----------------|----------------|---------------|------------|--------------|------------------|--------------------|--------------|-------------|
| SO - 000101   | In-Store        | WARE-UHY1004    | 12/31/17       | 5/31/18     | 6/14/18    | 6/19/18        | USD            | 6              | 15            | 259        | 12           | 5                | 0.075              | 1,963.10     | 1,001.18    |
| SO - 000102   | Online          | WARE-NMK1003    | 12/31/17       | 5/31/18     | 6/22/18    | 7/2/18         | USD            | 14             | 20            | 196        | 27           | 3                | 0.075              | 3,939.60     | 3,348.66    |
| SO - 000103   | Distributor     | WARE-UHY1004    | 12/31/17       | 5/31/18     | 6/21/18    | 7/1/18         | USD            | 21             | 16            | 213        | 16           | 1                | 0.05               | 1,775.50     | 781.22      |
| SO - 000104   | Wholesale       | WARE-NMK1003    | 12/31/17       | 5/31/18     | 6/2/18     | 6/7/18         | USD            | 28             | 48            | 107        | 23           | 8                | 0.075              | 2,324.90     | 1,464.69    |
| SO - 000105   | Distributor     | WARE-NMK1003    | 4/10/18        | 5/31/18     | 6/16/18    | 6/26/18        | USD            | 22             | 49            | 111        | 26           | 8                | 0.1                | 1,822.40     | 1,476.14    |
| ...           | ...             | ...             | ...            | ...         | ...        | ...            | ...            | ...            | ...           | ...        | ...          | ...              | ...                | ...          | ...         |
*/
CREATE TABLE "Sales Orders" (
    "OrderNumber" TEXT NOT NULL PRIMARY KEY,
        -- <example>'SO - 0001000'</example>
    "Sales Channel" TEXT NOT NULL,
        -- <values>{'Distributor', 'In-Store', 'Online', 'Wholesale'}</values>
    "WarehouseCode" TEXT NOT NULL,
        -- <values>{'WARE-MKL1006', 'WARE-NBV1002', 'WARE-NMK1003', 'WARE-PUJ1005', 'WARE-UHY1004', 'WARE-XYS1001'}</values>
    "ProcuredDate" TEXT NOT NULL,
        -- <values>{'10/27/18', '12/1/19', '12/31/17', '2/4/19', '3/10/20', '4/10/18', '5/15/19', '6/18/20', '7/19/18', '8/23/19', '9/26/20'}</values>
    "OrderDate" TEXT NOT NULL,
        -- <example>'5/31/18'</example>
    "ShipDate" TEXT NOT NULL,
        -- <example>'6/14/18'</example>
    "DeliveryDate" TEXT NOT NULL,
        -- <example>'6/19/18'</example>
    "CurrencyCode" TEXT NOT NULL,
        -- <values>{'USD'}</values>
    "_SalesTeamID" INTEGER NOT NULL,
        -- <example>6</example>
        -- <fk> -> "Sales Team"."SalesTeamID"</fk>
    "_CustomerID" INTEGER NOT NULL,
        -- <example>15</example>
        -- <fk> -> Customers."CustomerID"</fk>
    "_StoreID" INTEGER NOT NULL,
        -- <example>259</example>
        -- <fk> -> "Store Locations"."StoreID"</fk>
    "_ProductID" INTEGER NOT NULL,
        -- <example>12</example>
        -- <fk> -> Products."ProductID"</fk>
    "Order Quantity" INTEGER NOT NULL,
        -- <example>5</example>
    "Discount Applied" REAL NOT NULL,
        -- <example>0.075</example>
    "Unit Price" TEXT NOT NULL,
        -- <example>'1,963.10'</example>
    "Unit Cost" TEXT NOT NULL,
        -- <example>'1,001.18'</example>
    FOREIGN KEY ("_ProductID") REFERENCES Products("ProductID"),
    FOREIGN KEY ("_StoreID") REFERENCES "Store Locations"("StoreID"),
    FOREIGN KEY ("_CustomerID") REFERENCES Customers("CustomerID"),
    FOREIGN KEY ("_SalesTeamID") REFERENCES "Sales Team"("SalesTeamID")
);

/*
Schema: NULL
Table: "Sales Team"
Rows: 28
Sample rows:
| SalesTeamID   | Sales Team      | Region    |
|---------------|-----------------|-----------|
| 1             | Adam Hernandez  | Northeast |
| 2             | Keith Griffin   | Northeast |
| 3             | Jerry Green     | West      |
| 4             | Chris Armstrong | Northeast |
| 5             | Stephen Payne   | South     |
| ...           | ...             | ...       |
*/
CREATE TABLE "Sales Team" (
    "SalesTeamID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Sales Team" TEXT NOT NULL,
        -- <example>'Adam Hernandez'</example>
    "Region" TEXT NOT NULL
        -- <values>{'Midwest', 'Northeast', 'South', 'West'}</values>
);

/*
Schema: NULL
Table: "Store Locations"
Rows: 367
Sample rows:
| StoreID   | City Name   | County                          | StateCode   | State    | Type   | Latitude   | Longitude   | AreaCode   | Population   | Household Income   | Median Income   | Land Area   | Water Area   | Time Zone       |
|-----------|-------------|---------------------------------|-------------|----------|--------|------------|-------------|------------|--------------|--------------------|-----------------|-------------|--------------|-----------------|
| 1         | Birmingham  | Shelby County/Jefferson County  | AL          | Alabama  | City   | 33.52744   | -86.79905   | 205        | 212461       | 89972              | 31061           | 378353942   | 6591013      | America/Chicago |
| 2         | Huntsville  | Limestone County/Madison County | AL          | Alabama  | City   | 34.69901   | -86.67298   | 256        | 190582       | 78554              | 48775           | 552604579   | 3452021      | America/Chicago |
| 3         | Mobile      | Mobile County                   | AL          | Alabama  | City   | 30.69436   | -88.04305   | 251        | 194288       | 76170              | 38776           | 361044263   | 105325210    | America/Chicago |
| 4         | Montgomery  | Montgomery County               | AL          | Alabama  | City   | 32.36681   | -86.29997   | 334        | 200602       | 79866              | 42927           | 413985435   | 4411954      | America/Chicago |
| 5         | Little Rock | Pulaski County                  | AR          | Arkansas | City   | 34.74648   | -92.28959   | 501        | 197992       | 79902              | 46085           | 307398785   | 6758644      | America/Chicago |
| ...       | ...         | ...                             | ...         | ...      | ...    | ...        | ...         | ...        | ...          | ...                | ...             | ...         | ...          | ...             |
*/
CREATE TABLE "Store Locations" (
    "StoreID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "City Name" TEXT NOT NULL,
        -- <example>'Birmingham'</example>
    "County" TEXT NOT NULL,
        -- <example>'Shelby County/Jefferson County'</example>
    "StateCode" TEXT NOT NULL,
        -- <example>'AL'</example>
        -- <fk> -> Regions."StateCode"</fk>
    "State" TEXT NOT NULL,
        -- <example>'Alabama'</example>
    "Type" TEXT NOT NULL,
        -- <values>{'Borough', 'CDP', 'City', 'Consolidated Government', 'Metropolitan Government', 'Other', 'Town', 'Township', 'Unified Government', 'Urban County '}</values>
    "Latitude" REAL NOT NULL,
        -- <example>33.527</example>
    "Longitude" REAL NOT NULL,
        -- <example>-86.799</example>
    "AreaCode" INTEGER NOT NULL,
        -- <example>205</example>
    "Population" INTEGER NOT NULL,
        -- <example>212461</example>
    "Household Income" INTEGER NOT NULL,
        -- <example>89972</example>
    "Median Income" INTEGER NOT NULL,
        -- <example>31061</example>
    "Land Area" INTEGER NOT NULL,
        -- <example>378353942</example>
    "Water Area" INTEGER NOT NULL,
        -- <example>6591013</example>
    "Time Zone" TEXT NOT NULL,
        -- <values>{'America/Boise', 'America/Chicago', 'America/Denver', 'America/Detroit', 'America/Indiana/Indianapolis', 'America/Los Angeles', 'America/New York', 'America/Phoenix', 'Pacific/Honolulu'}</values>
    FOREIGN KEY ("StateCode") REFERENCES Regions("StateCode")
);
```