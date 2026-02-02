```sql
-- Database: retail_world

-- Table: Categories (8 rows)
CREATE TABLE Categories (
    CategoryID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    CategoryName TEXT NULL,
        -- <values>{'Beverages', 'Condiments', 'Confections', 'Dairy Products', 'Grains/Cereals', 'Meat/Poultry', 'Produce', 'Seafood'}</values>
    Description TEXT NULL
        -- <values>{'Breads, crackers, pasta, and cereal', 'Cheeses', 'Desserts, candies, and sweet breads', 'Dried fruit and bean curd', 'Prepared meats', 'Seaweed and fish', 'Soft drinks, coffees, teas, beers, and ales', 'Sweet and savory sauces, relishes, spreads, and seasonings'}</values>
);

-- Table: Customers (91 rows)
CREATE TABLE Customers (
    CustomerID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    CustomerName TEXT NULL,
        -- <example>'Alfreds Futterkiste'</example>
    ContactName TEXT NULL,
        -- <example>'Maria Anders'</example>
    Address TEXT NULL,
        -- <example>'Obere Str. 57'</example>
    City TEXT NULL,
        -- <example>'Berlin'</example>
    PostalCode TEXT NULL,
        -- <example>'12209'</example>
    Country TEXT NULL
        -- <example>'Germany'</example>
);

-- Table: Employees (10 rows)
CREATE TABLE Employees (
    EmployeeID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    LastName TEXT NULL,
        -- <values>{'Buchanan', 'Callahan', 'Davolio', 'Dodsworth', 'Fuller', 'King', 'Leverling', 'Peacock', 'Suyama', 'West'}</values>
    FirstName TEXT NULL,
        -- <values>{'Adam', 'Andrew', 'Anne', 'Janet', 'Laura', 'Margaret', 'Michael', 'Nancy', 'Robert', 'Steven'}</values>
    BirthDate DATE NULL,
        -- <example>'1968-12-08'</example>
    Photo TEXT NULL,
        -- <values>{'EmpID1.pic', 'EmpID10.pic', 'EmpID2.pic', 'EmpID3.pic', 'EmpID4.pic', 'EmpID5.pic', 'EmpID6.pic', 'EmpID7.pic', 'EmpID8.pic', 'EmpID9.pic'}</values>
    Notes TEXT NULL
        -- <values>{'An old chum.', 'Andrew received his BTS commercial and a Ph.D. in ...mmerce, and the Pacific Rim Importers Association.', 'Anne has a BA degree in English from St. Lawrence College. She is fluent in French and German.', 'Education includes a BA in psychology from Colorad...Nancy is a member of 'Toastmasters International'.', 'Janet has a BS degree in chemistry from Boston Col...ssociate and was promoted to sales representative.', 'Laura received a BA in psychology from the Univers...e in business French. She reads and writes French.', 'Margaret holds a BA in English literature from Con...before returning to her permanent post in Seattle.', 'Michael is a graduate of Sussex University (MA, ec...an read and write French, Portuguese, and Spanish.', 'Robert King served in the Peace Corps and traveled... Europe', he was transferred to the London office.', 'Steven Buchanan graduated from St. Andrews Univers...ational Sales Management'. He is fluent in French.'}</values>
);

-- Table: OrderDetails (518 rows)
CREATE TABLE OrderDetails (
    OrderDetailID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    OrderID INTEGER NULL,
        -- <example>10248</example>
        -- <fk> -> Orders.OrderID</fk>
    ProductID INTEGER NULL,
        -- <example>11</example>
        -- <fk> -> Products.ProductID</fk>
    Quantity INTEGER NULL,
        -- <example>12</example>
    FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);

-- Table: Orders (196 rows)
CREATE TABLE Orders (
    OrderID INTEGER NULL PRIMARY KEY,
        -- <example>10248</example>
    CustomerID INTEGER NULL,
        -- <example>90</example>
        -- <fk> -> Customers.CustomerID</fk>
    EmployeeID INTEGER NULL,
        -- <example>5</example>
        -- <fk> -> Employees.EmployeeID</fk>
    OrderDate DATETIME NULL,
        -- <example>'1996-07-04'</example>
    ShipperID INTEGER NULL,
        -- <example>3</example>
        -- <fk> -> Shippers.ShipperID</fk>
    FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (ShipperID) REFERENCES Shippers(ShipperID)
);

-- Table: Products (77 rows)
CREATE TABLE Products (
    ProductID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    ProductName TEXT NULL,
        -- <example>'Chais'</example>
    SupplierID INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Suppliers.SupplierID</fk>
    CategoryID INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Categories.CategoryID</fk>
    Unit TEXT NULL,
        -- <example>'10 boxes x 20 bags'</example>
    Price REAL NULL,
        -- <example>18.000</example>
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID),
    FOREIGN KEY (SupplierID) REFERENCES Suppliers(SupplierID)
);

-- Table: Shippers (3 rows)
CREATE TABLE Shippers (
    ShipperID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    ShipperName TEXT NULL,
        -- <values>{'Federal Shipping', 'Speedy Express', 'United Package'}</values>
    Phone TEXT NULL
        -- <values>{'(503) 555-3199', '(503) 555-9831', '(503) 555-9931'}</values>
);

-- Table: Suppliers (29 rows)
CREATE TABLE Suppliers (
    SupplierID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    SupplierName TEXT NULL,
        -- <example>'Exotic Liquid'</example>
    ContactName TEXT NULL,
        -- <example>'Charlotte Cooper'</example>
    Address TEXT NULL,
        -- <example>'49 Gilbert St.'</example>
    City TEXT NULL,
        -- <example>'Londona'</example>
    PostalCode TEXT NULL,
        -- <example>'EC1 4SD'</example>
    Country TEXT NULL,
        -- <example>'UK'</example>
    Phone TEXT NULL
        -- <example>'(171) 555-2222'</example>
);
```