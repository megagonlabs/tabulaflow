```sql
-- Database: car_retails

-- Table: customers (122 rows)
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
    creditLimit REAL NULL,
        -- <example>21000.000</example>
    FOREIGN KEY (salesRepEmployeeNumber) REFERENCES employees(employeeNumber)
);

-- Table: employees (23 rows)
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

-- Table: offices (7 rows)
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

-- Table: orderdetails (2996 rows)
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

-- Table: orders (326 rows)
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

-- Table: payments (273 rows)
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

-- Table: productlines (7 rows)
CREATE TABLE productlines (
    productLine TEXT NOT NULL PRIMARY KEY,
        -- <values>{'Classic Cars', 'Motorcycles', 'Planes', 'Ships', 'Trains', 'Trucks and Buses', 'Vintage Cars'}</values>
    textDescription TEXT NULL,
        -- <values>{'Attention car enthusiasts: Make your wildest car o...this category. These replicas feature superb atten', 'Model trains are a rewarding hobby for enthusiasts...t within this category. The interactive aspect of ', 'Our Vintage Car models realistically portray autom...d 1:24 scale sizes, which provide the optimum in d', 'Our motorcycles are state of the art replicas of c...ng wheels, working kickstand, front suspension, ge', 'The Truck and Bus models are realistic replicas of...on and several out-of-production vehicles. Materia', 'The perfect holiday or anniversary gift for execut... assembled and ready for display in the home or of', 'Unique, diecast airplane and helicopter replicas s...et engines and propellers, retractable wheels, and'}</values>
    htmlDescription TEXT NULL,
    image BLOB NULL
);

-- Table: products (110 rows)
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