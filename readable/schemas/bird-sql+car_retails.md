```sql
-- Database: car_retails

-- Table: customers (122 rows)
CREATE TABLE customers (
    customerNumber INTEGER NOT NULL PRIMARY KEY,  -- e.g. 103
    customerName TEXT NOT NULL,  -- e.g. 'Atelier graphique'
    contactLastName TEXT NOT NULL,  -- e.g. 'Schmitt'
    contactFirstName TEXT NOT NULL,  -- e.g. 'Carine '
    phone TEXT NOT NULL,  -- e.g. '40.32.2555'
    addressLine1 TEXT NOT NULL,  -- e.g. '54, rue Royale'
    addressLine2 TEXT,  -- e.g. 'Level 3'
    city TEXT NOT NULL,  -- e.g. 'Nantes'
    state TEXT,  -- e.g. 'NV'
    postalCode TEXT,  -- e.g. '44000'
    country TEXT NOT NULL,  -- e.g. 'France'
    salesRepEmployeeNumber INTEGER,  -- e.g. 1370; FK -> employees.employeeNumber
    creditLimit REAL,  -- e.g. 21000.000
    FOREIGN KEY (salesRepEmployeeNumber) REFERENCES employees(employeeNumber)
);

-- Table: employees (23 rows)
CREATE TABLE employees (
    employeeNumber INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1002
    lastName TEXT NOT NULL,  -- e.g. 'Murphy'
    firstName TEXT NOT NULL,  -- e.g. 'Diane'
    extension TEXT NOT NULL,  -- e.g. 'x5800'
    email TEXT NOT NULL,  -- e.g. 'dmurphy@classicmodelcars.com'
    officeCode TEXT NOT NULL,  -- values: {'1', '2', '3', '4', '5', '6', '7'}; FK -> offices.officeCode
    reportsTo INTEGER,  -- e.g. 1002; FK -> employees.employeeNumber
    jobTitle TEXT NOT NULL,  -- values: {'President', 'Sale Manager (EMEA)', 'Sales Manager (APAC)', 'Sales Manager (NA)', 'Sales Rep', 'VP Marketing', 'VP Sales'}
    FOREIGN KEY (officeCode) REFERENCES offices(officeCode),
    FOREIGN KEY (reportsTo) REFERENCES employees(employeeNumber)
);

-- Table: offices (7 rows)
CREATE TABLE offices (
    officeCode TEXT NOT NULL PRIMARY KEY,  -- values: {'1', '2', '3', '4', '5', '6', '7'}
    city TEXT NOT NULL,  -- values: {'Boston', 'London', 'NYC', 'Paris', 'San Francisco', 'Sydney', 'Tokyo'}
    phone TEXT NOT NULL,  -- values: {'+1 212 555 3000', '+1 215 837 0825', '+1 650 219 4782', '+33 14 723 4404', '+44 20 7877 2041', '+61 2 9264 2451', '+81 33 224 5000'}
    addressLine1 TEXT NOT NULL,  -- values: {'100 Market Street', '1550 Court Place', '25 Old Broad Street', '4-1 Kioicho', '43 Rue Jouffroy D'abbans', '5-11 Wentworth Avenue', '523 East 53rd Street'}
    addressLine2 TEXT,  -- values: {'Floor #2', 'Level 7', 'Suite 102', 'Suite 300', 'apt. 5A'}
    state TEXT,  -- values: {'CA', 'Chiyoda-Ku', 'MA', 'NY'}
    country TEXT NOT NULL,  -- values: {'Australia', 'France', 'Japan', 'UK', 'USA'}
    postalCode TEXT NOT NULL,  -- values: {'02107', '10022', '102-8578', '75017', '94080', 'EC2N 1HN', 'NSW 2010'}
    territory TEXT NOT NULL  -- values: {'APAC', 'EMEA', 'Japan', 'NA'}
);

-- Table: orderdetails (2996 rows)
CREATE TABLE orderdetails (
    orderNumber INTEGER NOT NULL,  -- e.g. 10100; FK -> orders.orderNumber
    productCode TEXT NOT NULL,  -- e.g. 'S18_1749'; FK -> products.productCode
    quantityOrdered INTEGER NOT NULL,  -- e.g. 30
    priceEach REAL NOT NULL,  -- e.g. 136.000
    orderLineNumber INTEGER NOT NULL,  -- e.g. 3
    PRIMARY KEY (orderNumber, productCode),
    FOREIGN KEY (productCode) REFERENCES products(productCode),
    FOREIGN KEY (orderNumber) REFERENCES orders(orderNumber)
);

-- Table: orders (326 rows)
CREATE TABLE orders (
    orderNumber INTEGER NOT NULL PRIMARY KEY,  -- e.g. 10100
    orderDate DATE NOT NULL,  -- e.g. '2003-01-06'
    requiredDate DATE NOT NULL,  -- e.g. '2003-01-13'
    shippedDate DATE,  -- e.g. '2003-01-10'
    status TEXT NOT NULL,  -- values: {'Cancelled', 'Disputed', 'In Process', 'On Hold', 'Resolved', 'Shipped'}
    comments TEXT,  -- e.g. 'Check on availability.'
    customerNumber INTEGER NOT NULL,  -- e.g. 363; FK -> customers.customerNumber
    FOREIGN KEY (customerNumber) REFERENCES customers(customerNumber)
);

-- Table: payments (273 rows)
CREATE TABLE payments (
    customerNumber INTEGER NOT NULL,  -- e.g. 103; FK -> customers.customerNumber
    checkNumber TEXT NOT NULL,  -- e.g. 'HQ336336'
    paymentDate DATE NOT NULL,  -- e.g. '2004-10-19'
    amount REAL NOT NULL,  -- e.g. 6066.780
    PRIMARY KEY (customerNumber, checkNumber),
    FOREIGN KEY (customerNumber) REFERENCES customers(customerNumber)
);

-- Table: productlines (7 rows)
CREATE TABLE productlines (
    productLine TEXT NOT NULL PRIMARY KEY,  -- values: {'Classic Cars', 'Motorcycles', 'Planes', 'Ships', 'Trains', 'Trucks and Buses', 'Vintage Cars'}
    textDescription TEXT,  -- values: {'Attention car enthusiasts: Make your wildest car o...this category. These replicas feature superb atten', 'Model trains are a rewarding hobby for enthusiasts...t within this category. The interactive aspect of ', 'Our Vintage Car models realistically portray autom...d 1:24 scale sizes, which provide the optimum in d', 'Our motorcycles are state of the art replicas of c...ng wheels, working kickstand, front suspension, ge', 'The Truck and Bus models are realistic replicas of...on and several out-of-production vehicles. Materia', 'The perfect holiday or anniversary gift for execut... assembled and ready for display in the home or of', 'Unique, diecast airplane and helicopter replicas s...et engines and propellers, retractable wheels, and'}
    htmlDescription TEXT,
    image BLOB
);

-- Table: products (110 rows)
CREATE TABLE products (
    productCode TEXT NOT NULL PRIMARY KEY,  -- e.g. 'S10_1678'
    productName TEXT NOT NULL,  -- e.g. '1969 Harley Davidson Ultimate Chopper'
    productLine TEXT NOT NULL,  -- values: {'Classic Cars', 'Motorcycles', 'Planes', 'Ships', 'Trains', 'Trucks and Buses', 'Vintage Cars'}; FK -> productlines.productLine
    productScale TEXT NOT NULL,  -- values: {'1:10', '1:12', '1:18', '1:24', '1:32', '1:50', '1:700', '1:72'}
    productVendor TEXT NOT NULL,  -- e.g. 'Min Lin Diecast'
    productDescription TEXT NOT NULL,  -- e.g. 'This replica features working kickstand, front sus...cise scale and require special care and attention.'
    quantityInStock INTEGER NOT NULL,  -- e.g. 7933
    buyPrice REAL NOT NULL,  -- e.g. 48.810
    MSRP REAL NOT NULL,  -- e.g. 95.700
    FOREIGN KEY (productLine) REFERENCES productlines(productLine)
);
```