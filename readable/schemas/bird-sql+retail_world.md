```sql
-- Database: retail_world

-- Table: Categories (8 rows)
CREATE TABLE Categories (
    CategoryID INTEGER PRIMARY KEY,  -- e.g. 1
    CategoryName TEXT,  -- values: {'Beverages', 'Condiments', 'Confections', 'Dairy Products', 'Grains/Cereals', 'Meat/Poultry', 'Produce', 'Seafood'}
    Description TEXT  -- values: {'Breads, crackers, pasta, and cereal', 'Cheeses', 'Desserts, candies, and sweet breads', 'Dried fruit and bean curd', 'Prepared meats', 'Seaweed and fish', 'Soft drinks, coffees, teas, beers, and ales', 'Sweet and savory sauces, relishes, spreads, and seasonings'}
);

-- Table: Customers (91 rows)
CREATE TABLE Customers (
    CustomerID INTEGER PRIMARY KEY,  -- e.g. 1
    CustomerName TEXT,  -- e.g. 'Alfreds Futterkiste'
    ContactName TEXT,  -- e.g. 'Maria Anders'
    Address TEXT,  -- e.g. 'Obere Str. 57'
    City TEXT,  -- e.g. 'Berlin'
    PostalCode TEXT,  -- e.g. '12209'
    Country TEXT  -- e.g. 'Germany'
);

-- Table: Employees (10 rows)
CREATE TABLE Employees (
    EmployeeID INTEGER PRIMARY KEY,  -- e.g. 1
    LastName TEXT,  -- values: {'Buchanan', 'Callahan', 'Davolio', 'Dodsworth', 'Fuller', 'King', 'Leverling', 'Peacock', 'Suyama', 'West'}
    FirstName TEXT,  -- values: {'Adam', 'Andrew', 'Anne', 'Janet', 'Laura', 'Margaret', 'Michael', 'Nancy', 'Robert', 'Steven'}
    BirthDate DATE,  -- e.g. '1968-12-08'
    Photo TEXT,  -- values: {'EmpID1.pic', 'EmpID10.pic', 'EmpID2.pic', 'EmpID3.pic', 'EmpID4.pic', 'EmpID5.pic', 'EmpID6.pic', 'EmpID7.pic', 'EmpID8.pic', 'EmpID9.pic'}
    Notes TEXT  -- values: {'An old chum.', 'Andrew received his BTS commercial and a Ph.D. in ...mmerce, and the Pacific Rim Importers Association.', 'Anne has a BA degree in English from St. Lawrence College. She is fluent in French and German.', 'Education includes a BA in psychology from Colorad...Nancy is a member of 'Toastmasters International'.', 'Janet has a BS degree in chemistry from Boston Col...ssociate and was promoted to sales representative.', 'Laura received a BA in psychology from the Univers...e in business French. She reads and writes French.', 'Margaret holds a BA in English literature from Con...before returning to her permanent post in Seattle.', 'Michael is a graduate of Sussex University (MA, ec...an read and write French, Portuguese, and Spanish.', 'Robert King served in the Peace Corps and traveled... Europe', he was transferred to the London office.', 'Steven Buchanan graduated from St. Andrews Univers...ational Sales Management'. He is fluent in French.'}
);

-- Table: OrderDetails (518 rows)
CREATE TABLE OrderDetails (
    OrderDetailID INTEGER PRIMARY KEY,  -- e.g. 1
    OrderID INTEGER,  -- e.g. 10248; FK -> Orders.OrderID
    ProductID INTEGER,  -- e.g. 11; FK -> Products.ProductID
    Quantity INTEGER,  -- e.g. 12
    FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);

-- Table: Orders (196 rows)
CREATE TABLE Orders (
    OrderID INTEGER PRIMARY KEY,  -- e.g. 10248
    CustomerID INTEGER,  -- e.g. 90; FK -> Customers.CustomerID
    EmployeeID INTEGER,  -- e.g. 5; FK -> Employees.EmployeeID
    OrderDate DATETIME,  -- e.g. '1996-07-04'
    ShipperID INTEGER,  -- e.g. 3; FK -> Shippers.ShipperID
    FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (ShipperID) REFERENCES Shippers(ShipperID)
);

-- Table: Products (77 rows)
CREATE TABLE Products (
    ProductID INTEGER PRIMARY KEY,  -- e.g. 1
    ProductName TEXT,  -- e.g. 'Chais'
    SupplierID INTEGER,  -- e.g. 1; FK -> Suppliers.SupplierID
    CategoryID INTEGER,  -- e.g. 1; FK -> Categories.CategoryID
    Unit TEXT,  -- e.g. '10 boxes x 20 bags'
    Price REAL,  -- e.g. 18.000
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID),
    FOREIGN KEY (SupplierID) REFERENCES Suppliers(SupplierID)
);

-- Table: Shippers (3 rows)
CREATE TABLE Shippers (
    ShipperID INTEGER PRIMARY KEY,  -- e.g. 1
    ShipperName TEXT,  -- values: {'Federal Shipping', 'Speedy Express', 'United Package'}
    Phone TEXT  -- values: {'(503) 555-3199', '(503) 555-9831', '(503) 555-9931'}
);

-- Table: Suppliers (29 rows)
CREATE TABLE Suppliers (
    SupplierID INTEGER PRIMARY KEY,  -- e.g. 1
    SupplierName TEXT,  -- e.g. 'Exotic Liquid'
    ContactName TEXT,  -- e.g. 'Charlotte Cooper'
    Address TEXT,  -- e.g. '49 Gilbert St.'
    City TEXT,  -- e.g. 'Londona'
    PostalCode TEXT,  -- e.g. 'EC1 4SD'
    Country TEXT,  -- e.g. 'UK'
    Phone TEXT  -- e.g. '(171) 555-2222'
);
```