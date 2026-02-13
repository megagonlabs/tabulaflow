```sql
-- Database: car_retails

/*
Schema: NULLTable: customers
Rows: 122
Sample rows:
| customerNumber   | customerName               | contactLastName   | contactFirstName   | phone        | addressLine1                 | addressLine2   | city      | state    | postalCode   | country   | salesRepEmployeeNumber   | creditLimit   |
|------------------|----------------------------|-------------------|--------------------|--------------|------------------------------|----------------|-----------|----------|--------------|-----------|--------------------------|---------------|
| 103              | Atelier graphique          | Schmitt           | Carine             | 40.32.2555   | 54, rue Royale               | [NULL]         | Nantes    | [NULL]   | 44000        | France    | 1370.0                   | 21000.0       |
| 112              | Signal Gift Stores         | King              | Jean               | 7025551838   | 8489 Strong St.              | [NULL]         | Las Vegas | NV       | 83030        | USA       | 1166.0                   | 71800.0       |
| 114              | Australian Collectors, Co. | Ferguson          | Peter              | 03 9520 4555 | 636 St Kilda Road            | Level 3        | Melbourne | Victoria | 3004         | Australia | 1611.0                   | 117300.0      |
| 119              | La Rochelle Gifts          | Labrune           | Janine             | 40.67.8555   | 67, rue des Cinquante Otages | [NULL]         | Nantes    | [NULL]   | 44000        | France    | 1370.0                   | 118200.0      |
| 121              | Baane Mini Imports         | Bergulfsen        | Jonas              | 07-98 9555   | Erling Skakkes gate 78       | [NULL]         | Stavern   | [NULL]   | 4110         | Norway    | 1504.0                   | 81700.0       |
| ...              | ...                        | ...               | ...                | ...          | ...                          | ...            | ...       | ...      | ...          | ...       | ...                      | ...           |
*/
CREATE TABLE customers (
    customerNumber INTEGER NOT NULL PRIMARY KEY,
        -- <example>103</example>
    customerName TEXT NOT NULL,
        -- <example>'Atelier graphique'</example>
    contactLastName TEXT NOT NULL,
        -- <example>'Schmitt'</example>
    contactFirstName TEXT NOT NULL,
        -- <example>'Carine '</example>
    phone TEXT NOT NULL,
        -- <example>'40.32.2555'</example>
    addressLine1 TEXT NOT NULL,
        -- <example>'54, rue Royale'</example>
    addressLine2 TEXT NULL,
        -- <example>'Level 3'</example>
    city TEXT NOT NULL,
        -- <example>'Nantes'</example>
    state TEXT NULL,
        -- <example>'NV'</example>
    postalCode TEXT NULL,
        -- <example>'44000'</example>
    country TEXT NOT NULL,
        -- <example>'France'</example>
    salesRepEmployeeNumber INTEGER NULL,
        -- <example>1370</example>
        -- <fk> -> employees.employeeNumber</fk>
    creditLimit REAL NOT NULL,
        -- <example>21000.000</example>
    FOREIGN KEY (salesRepEmployeeNumber) REFERENCES employees(employeeNumber)
);

/*
Schema: NULLTable: employees
Rows: 23
Sample rows:
| employeeNumber   | lastName   | firstName   | extension   | email                           | officeCode   | reportsTo   | jobTitle             |
|------------------|------------|-------------|-------------|---------------------------------|--------------|-------------|----------------------|
| 1002             | Murphy     | Diane       | x5800       | dmurphy@classicmodelcars.com    | 1            | [NULL]      | President            |
| 1056             | Patterson  | Mary        | x4611       | mpatterso@classicmodelcars.com  | 1            | 1002.0      | VP Sales             |
| 1076             | Firrelli   | Jeff        | x9273       | jfirrelli@classicmodelcars.com  | 1            | 1002.0      | VP Marketing         |
| 1088             | Patterson  | William     | x4871       | wpatterson@classicmodelcars.com | 6            | 1056.0      | Sales Manager (APAC) |
| 1102             | Bondur     | Gerard      | x5408       | gbondur@classicmodelcars.com    | 4            | 1056.0      | Sale Manager (EMEA)  |
| ...              | ...        | ...         | ...         | ...                             | ...          | ...         | ...                  |
*/
CREATE TABLE employees (
    employeeNumber INTEGER NOT NULL PRIMARY KEY,
        -- <example>1002</example>
    lastName TEXT NOT NULL,
        -- <example>'Murphy'</example>
    firstName TEXT NOT NULL,
        -- <example>'Diane'</example>
    extension TEXT NOT NULL,
        -- <example>'x5800'</example>
    email TEXT NOT NULL,
        -- <example>'dmurphy@classicmodelcars.com'</example>
    officeCode TEXT NOT NULL,
        -- <values>{'1', '2', '3', '4', '5', '6', '7'}</values>
        -- <fk> -> offices.officeCode</fk>
    reportsTo INTEGER NULL,
        -- <example>1002</example>
        -- <fk> -> employees.employeeNumber</fk>
    jobTitle TEXT NOT NULL,
        -- <values>{'President', 'Sale Manager (EMEA)', 'Sales Manager (APAC)', 'Sales Manager (NA)', 'Sales Rep', 'VP Marketing', 'VP Sales'}</values>
    FOREIGN KEY (officeCode) REFERENCES offices(officeCode),
    FOREIGN KEY (reportsTo) REFERENCES employees(employeeNumber)
);

/*
Schema: NULLTable: offices
Rows: 7
All rows:
|   officeCode | city          | phone            | addressLine1             | addressLine2   | state      | country   | postalCode   | territory   |
|--------------|---------------|------------------|--------------------------|----------------|------------|-----------|--------------|-------------|
|            1 | San Francisco | +1 650 219 4782  | 100 Market Street        | Suite 300      | CA         | USA       | 94080        | NA          |
|            2 | Boston        | +1 215 837 0825  | 1550 Court Place         | Suite 102      | MA         | USA       | 02107        | NA          |
|            3 | NYC           | +1 212 555 3000  | 523 East 53rd Street     | apt. 5A        | NY         | USA       | 10022        | NA          |
|            4 | Paris         | +33 14 723 4404  | 43 Rue Jouffroy D'abbans | [NULL]         | [NULL]     | France    | 75017        | EMEA        |
|            5 | Tokyo         | +81 33 224 5000  | 4-1 Kioicho              | [NULL]         | Chiyoda-Ku | Japan     | 102-8578     | Japan       |
|            6 | Sydney        | +61 2 9264 2451  | 5-11 Wentworth Avenue    | Floor #2       | [NULL]     | Australia | NSW 2010     | APAC        |
|            7 | London        | +44 20 7877 2041 | 25 Old Broad Street      | Level 7        | [NULL]     | UK        | EC2N 1HN     | EMEA        |
*/
CREATE TABLE offices (
    officeCode TEXT NOT NULL PRIMARY KEY,
        -- <values>{'1', '2', '3', '4', '5', '6', '7'}</values>
    city TEXT NOT NULL,
        -- <values>{'Boston', 'London', 'NYC', 'Paris', 'San Francisco', 'Sydney', 'Tokyo'}</values>
    phone TEXT NOT NULL,
        -- <values>{'+1 212 555 3000', '+1 215 837 0825', '+1 650 219 4782', '+33 14 723 4404', '+44 20 7877 2041', '+61 2 9264 2451', '+81 33 224 5000'}</values>
    addressLine1 TEXT NOT NULL,
        -- <values>{'100 Market Street', '1550 Court Place', '25 Old Broad Street', '4-1 Kioicho', '43 Rue Jouffroy D'abbans', '5-11 Wentworth Avenue', '523 East 53rd Street'}</values>
    addressLine2 TEXT NULL,
        -- <values>{'Floor #2', 'Level 7', 'Suite 102', 'Suite 300', 'apt. 5A'}</values>
    state TEXT NULL,
        -- <values>{'CA', 'Chiyoda-Ku', 'MA', 'NY'}</values>
    country TEXT NOT NULL,
        -- <values>{'Australia', 'France', 'Japan', 'UK', 'USA'}</values>
    postalCode TEXT NOT NULL,
        -- <values>{'02107', '10022', '102-8578', '75017', '94080', 'EC2N 1HN', 'NSW 2010'}</values>
    territory TEXT NOT NULL
        -- <values>{'APAC', 'EMEA', 'Japan', 'NA'}</values>
);

/*
Schema: NULLTable: orderdetails
Rows: 2996
Sample rows:
| orderNumber   | productCode   | quantityOrdered   | priceEach   | orderLineNumber   |
|---------------|---------------|-------------------|-------------|-------------------|
| 10100         | S18_1749      | 30                | 136.0       | 3                 |
| 10100         | S18_2248      | 50                | 55.09       | 2                 |
| 10100         | S18_4409      | 22                | 75.46       | 4                 |
| 10100         | S24_3969      | 49                | 35.29       | 1                 |
| 10101         | S18_2325      | 25                | 108.06      | 4                 |
| ...           | ...           | ...               | ...         | ...               |
*/
CREATE TABLE orderdetails (
    orderNumber INTEGER NOT NULL,
        -- <example>10100</example>
        -- <fk> -> orders.orderNumber</fk>
    productCode TEXT NOT NULL,
        -- <example>'S18_1749'</example>
        -- <fk> -> products.productCode</fk>
    quantityOrdered INTEGER NOT NULL,
        -- <example>30</example>
    priceEach REAL NOT NULL,
        -- <example>136.000</example>
    orderLineNumber INTEGER NOT NULL,
        -- <example>3</example>
    PRIMARY KEY (orderNumber, productCode),
    FOREIGN KEY (productCode) REFERENCES products(productCode),
    FOREIGN KEY (orderNumber) REFERENCES orders(orderNumber)
);

/*
Schema: NULLTable: orders
Rows: 326
Sample rows:
| orderNumber   | orderDate   | requiredDate   | shippedDate   | status   | comments               | customerNumber   |
|---------------|-------------|----------------|---------------|----------|------------------------|------------------|
| 10100         | 2003-01-06  | 2003-01-13     | 2003-01-10    | Shipped  | [NULL]                 | 363              |
| 10101         | 2003-01-09  | 2003-01-18     | 2003-01-11    | Shipped  | Check on availability. | 128              |
| 10102         | 2003-01-10  | 2003-01-18     | 2003-01-14    | Shipped  | [NULL]                 | 181              |
| 10103         | 2003-01-29  | 2003-02-07     | 2003-02-02    | Shipped  | [NULL]                 | 121              |
| 10104         | 2003-01-31  | 2003-02-09     | 2003-02-01    | Shipped  | [NULL]                 | 141              |
| ...           | ...         | ...            | ...           | ...      | ...                    | ...              |
*/
CREATE TABLE orders (
    orderNumber INTEGER NOT NULL PRIMARY KEY,
        -- <example>10100</example>
    orderDate DATE NOT NULL,
        -- <example>'2003-01-06'</example>
    requiredDate DATE NOT NULL,
        -- <example>'2003-01-13'</example>
    shippedDate DATE NULL,
        -- <example>'2003-01-10'</example>
    status TEXT NOT NULL,
        -- <values>{'Cancelled', 'Disputed', 'In Process', 'On Hold', 'Resolved', 'Shipped'}</values>
    comments TEXT NULL,
        -- <example>'Check on availability.'</example>
    customerNumber INTEGER NOT NULL,
        -- <example>363</example>
        -- <fk> -> customers.customerNumber</fk>
    FOREIGN KEY (customerNumber) REFERENCES customers(customerNumber)
);

/*
Schema: NULLTable: payments
Rows: 273
Sample rows:
| customerNumber   | checkNumber   | paymentDate   | amount   |
|------------------|---------------|---------------|----------|
| 103              | HQ336336      | 2004-10-19    | 6066.78  |
| 103              | JM555205      | 2003-06-05    | 14571.44 |
| 103              | OM314933      | 2004-12-18    | 1676.14  |
| 112              | BO864823      | 2004-12-17    | 14191.12 |
| 112              | HQ55022       | 2003-06-06    | 32641.98 |
| ...              | ...           | ...           | ...      |
*/
CREATE TABLE payments (
    customerNumber INTEGER NOT NULL,
        -- <example>103</example>
        -- <fk> -> customers.customerNumber</fk>
    checkNumber TEXT NOT NULL,
        -- <example>'HQ336336'</example>
    paymentDate DATE NOT NULL,
        -- <example>'2004-10-19'</example>
    amount REAL NOT NULL,
        -- <example>6066.780</example>
    PRIMARY KEY (customerNumber, checkNumber),
    FOREIGN KEY (customerNumber) REFERENCES customers(customerNumber)
);

/*
Schema: NULLTable: productlines
Rows: 7
All rows:
| productLine      | textDescription                                                                                                                                                                                             | htmlDescription   | image   |
|------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|---------|
| Classic Cars     | Attention car enthusiasts: Make your wildest car ownership dreams come true. Whether you are looking...spired miniatures, you will find great choices in this category. These replicas feature superb atten | [NULL]            | [NULL]  |
| Motorcycles      | Our motorcycles are state of the art replicas of classic as well as contemporary motorcycle legends ...in stunning details such as official logos, rotating wheels, working kickstand, front suspension, ge | [NULL]            | [NULL]  |
| Planes           | Unique, diecast airplane and helicopter replicas suitable for collections, as well as home, office o...s such as official logos and insignias, rotating jet engines and propellers, retractable wheels, and | [NULL]            | [NULL]  |
| Ships            | The perfect holiday or anniversary gift for executives, clients, friends, and family. These handcraf...will be treasured for generations! They come fully assembled and ready for display in the home or of | [NULL]            | [NULL]  |
| Trains           | Model trains are a rewarding hobby for enthusiasts of all ages. Whether you're looking for collectib...ou'll find a number of great choices for any budget within this category. The interactive aspect of  | [NULL]            | [NULL]  |
| Trucks and Buses | The Truck and Bus models are realistic replicas of buses and specialized trucks produced from the ea...2 to 1:50 scale and include numerous limited edition and several out-of-production vehicles. Materia | [NULL]            | [NULL]  |
| Vintage Cars     | Our Vintage Car models realistically portray automobiles produced from the early 1900s through the 1... and wood. Most of the replicas are in the 1:18 and 1:24 scale sizes, which provide the optimum in d | [NULL]            | [NULL]  |
*/
CREATE TABLE productlines (
    productLine TEXT NOT NULL PRIMARY KEY,
        -- <values>{'Classic Cars', 'Motorcycles', 'Planes', 'Ships', 'Trains', 'Trucks and Buses', 'Vintage Cars'}</values>
    textDescription TEXT NOT NULL,
        -- <values>{'Attention car enthusiasts: Make your wildest car o...this category. These replicas feature superb atten', 'Model trains are a rewarding hobby for enthusiasts...t within this category. The interactive aspect of ', 'Our Vintage Car models realistically portray autom...d 1:24 scale sizes, which provide the optimum in d', 'Our motorcycles are state of the art replicas of c...ng wheels, working kickstand, front suspension, ge', 'The Truck and Bus models are realistic replicas of...on and several out-of-production vehicles. Materia', 'The perfect holiday or anniversary gift for execut... assembled and ready for display in the home or of', 'Unique, diecast airplane and helicopter replicas s...et engines and propellers, retractable wheels, and'}</values>
    htmlDescription TEXT NULL,
    image BLOB NULL
);

/*
Schema: NULLTable: products
Rows: 110
Sample rows:
| productCode   | productName                           | productLine   | productScale   | productVendor            | productDescription                                                                                                                                                                                          | quantityInStock   | buyPrice   | MSRP   |
|---------------|---------------------------------------|---------------|----------------|--------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------|------------|--------|
| S10_1678      | 1969 Harley Davidson Ultimate Chopper | Motorcycles   | 1:10           | Min Lin Diecast          | This replica features working kickstand, front suspension, gear-shift lever, footbrake lever, drive ...l parts are particularly delicate due to their precise scale and require special care and attention. | 7933              | 48.81      | 95.7   |
| S10_1949      | 1952 Alpine Renault 1300              | Classic Cars  | 1:10           | Classic Metal Creations  | Turnable front wheels; steering function; detailed interior; detailed engine; opening hood; opening trunk; opening doors; and detailed chassis.                                                             | 7305              | 98.58      | 214.3  |
| S10_2016      | 1996 Moto Guzzi 1100i                 | Motorcycles   | 1:10           | Highway 66 Mini Classics | Official Moto Guzzi logos and insignias, saddle bags located on side of motorcycle, detailed engine,...il , rotating wheels , working kick stand, diecast metal with plastic parts and baked enamel finish. | 6625              | 68.99      | 118.94 |
| S10_4698      | 2003 Harley-Davidson Eagle Drag Bike  | Motorcycles   | 1:10           | Red Start Diecast        | Model features, official Harley Davidson logos and insignias, detachable rear wheelie bar, heavy die... removable fender, seat and tank cover piece for displaying the superior detail of the v-twin engine | 5582              | 91.02      | 193.66 |
| S10_4757      | 1972 Alfa Romeo GTA                   | Classic Cars  | 1:10           | Motor City Art Classics  | Features include: Turnable front wheels; steering function; detailed interior; detailed engine; opening hood; opening trunk; opening doors; and detailed chassis.                                           | 3252              | 85.68      | 136.0  |
| ...           | ...                                   | ...           | ...            | ...                      | ...                                                                                                                                                                                                         | ...               | ...        | ...    |
*/
CREATE TABLE products (
    productCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'S10_1678'</example>
    productName TEXT NOT NULL,
        -- <example>'1969 Harley Davidson Ultimate Chopper'</example>
    productLine TEXT NOT NULL,
        -- <values>{'Classic Cars', 'Motorcycles', 'Planes', 'Ships', 'Trains', 'Trucks and Buses', 'Vintage Cars'}</values>
        -- <fk> -> productlines.productLine</fk>
    productScale TEXT NOT NULL,
        -- <values>{'1:10', '1:12', '1:18', '1:24', '1:32', '1:50', '1:700', '1:72'}</values>
    productVendor TEXT NOT NULL,
        -- <example>'Min Lin Diecast'</example>
    productDescription TEXT NOT NULL,
        -- <example>'This replica features working kickstand, front sus...cise scale and require special care and attention.'</example>
    quantityInStock INTEGER NOT NULL,
        -- <example>7933</example>
    buyPrice REAL NOT NULL,
        -- <example>48.810</example>
    MSRP REAL NOT NULL,
        -- <example>95.700</example>
    FOREIGN KEY (productLine) REFERENCES productlines(productLine)
);
```