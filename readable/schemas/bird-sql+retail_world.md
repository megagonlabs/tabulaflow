```sql
-- Database: retail_world

/*
Schema: NULLTable: Categories
Rows: 8
All rows:
|   CategoryID | CategoryName   | Description                                                |
|--------------|----------------|------------------------------------------------------------|
|            1 | Beverages      | Soft drinks, coffees, teas, beers, and ales                |
|            2 | Condiments     | Sweet and savory sauces, relishes, spreads, and seasonings |
|            3 | Confections    | Desserts, candies, and sweet breads                        |
|            4 | Dairy Products | Cheeses                                                    |
|            5 | Grains/Cereals | Breads, crackers, pasta, and cereal                        |
|            6 | Meat/Poultry   | Prepared meats                                             |
|            7 | Produce        | Dried fruit and bean curd                                  |
|            8 | Seafood        | Seaweed and fish                                           |
*/
CREATE TABLE Categories (
    CategoryID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    CategoryName TEXT NOT NULL,
        -- <values>{'Beverages', 'Condiments', 'Confections', 'Dairy Products', 'Grains/Cereals', 'Meat/Poultry', 'Produce', 'Seafood'}</values>
    Description TEXT NOT NULL
        -- <values>{'Breads, crackers, pasta, and cereal', 'Cheeses', 'Desserts, candies, and sweet breads', 'Dried fruit and bean curd', 'Prepared meats', 'Seaweed and fish', 'Soft drinks, coffees, teas, beers, and ales', 'Sweet and savory sauces, relishes, spreads, and seasonings'}</values>
);

/*
Schema: NULLTable: Customers
Rows: 91
Sample rows:
| CustomerID   | CustomerName                       | ContactName        | Address                       | City        | PostalCode   | Country   |
|--------------|------------------------------------|--------------------|-------------------------------|-------------|--------------|-----------|
| 1            | Alfreds Futterkiste                | Maria Anders       | Obere Str. 57                 | Berlin      | 12209        | Germany   |
| 2            | Ana Trujillo Emparedados y helados | Ana Trujillo       | Avda. de la Constitución 2222 | México D.F. | 5021         | Mexico    |
| 3            | Antonio Moreno Taquería            | Antonio Moreno     | Mataderos 2312                | México D.F. | 5023         | Mexico    |
| 4            | Around the Horn                    | Thomas Hardy       | 120 Hanover Sq.               | London      | WA1 1DP      | UK        |
| 5            | Berglunds snabbköp                 | Christina Berglund | Berguvsvägen 8                | Luleå       | S-958 22     | Sweden    |
| ...          | ...                                | ...                | ...                           | ...         | ...          | ...       |
*/
CREATE TABLE Customers (
    CustomerID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    CustomerName TEXT NOT NULL,
        -- <example>'Alfreds Futterkiste'</example>
    ContactName TEXT NOT NULL,
        -- <example>'Maria Anders'</example>
    Address TEXT NOT NULL,
        -- <example>'Obere Str. 57'</example>
    City TEXT NOT NULL,
        -- <example>'Berlin'</example>
    PostalCode TEXT NOT NULL,
        -- <example>'12209'</example>
    Country TEXT NOT NULL
        -- <example>'Germany'</example>
);

/*
Schema: NULLTable: Employees
Rows: 10
All rows:
|   EmployeeID | LastName   | FirstName   | BirthDate   | Photo       | Notes                                                                                                                                                                                                       |
|--------------|------------|-------------|-------------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|            1 | Davolio    | Nancy       | 1968-12-08  | EmpID1.pic  | Education includes a BA in psychology from Colorado State University. She also completed (The Art of the Cold Call). Nancy is a member of 'Toastmasters International'.                                     |
|            2 | Fuller     | Andrew      | 1952-02-19  | EmpID2.pic  | Andrew received his BTS commercial and a Ph.D. in international marketing from the University of Dal...s Management Roundtable, the Seattle Chamber of Commerce, and the Pacific Rim Importers Association. |
|            3 | Leverling  | Janet       | 1963-08-30  | EmpID3.pic  | Janet has a BS degree in chemistry from Boston College). She has also completed a certificate progra...retailing management. Janet was hired as a sales associate and was promoted to sales representative. |
|            4 | Peacock    | Margaret    | 1958-09-19  | EmpID4.pic  | Margaret holds a BA in English literature from Concordia College and an MA from the American Institu...She was temporarily assigned to the London office before returning to her permanent post in Seattle. |
|            5 | Buchanan   | Steven      | 1955-03-04  | EmpID5.pic  | Steven Buchanan graduated from St. Andrews University, Scotland, with a BSC degree. Upon joining the...the courses 'Successful Telemarketing' and 'International Sales Management'. He is fluent in French. |
|            6 | Suyama     | Michael     | 1963-07-02  | EmpID6.pic  | Michael is a graduate of Sussex University (MA, economics) and the University of California at Los A...ales Professional'. He is fluent in Japanese and can read and write French, Portuguese, and Spanish. |
|            7 | King       | Robert      | 1960-05-29  | EmpID7.pic  | Robert King served in the Peace Corps and traveled extensively before completing his degree in Engli...ny. After completing a course entitled 'Selling in Europe', he was transferred to the London office. |
|            8 | Callahan   | Laura       | 1958-01-09  | EmpID8.pic  | Laura received a BA in psychology from the University of Washington. She has also completed a course in business French. She reads and writes French.                                                       |
|            9 | Dodsworth  | Anne        | 1969-07-02  | EmpID9.pic  | Anne has a BA degree in English from St. Lawrence College. She is fluent in French and German.                                                                                                              |
|           10 | West       | Adam        | 1928-09-19  | EmpID10.pic | An old chum.                                                                                                                                                                                                |
*/
CREATE TABLE Employees (
    EmployeeID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    LastName TEXT NOT NULL,
        -- <values>{'Buchanan', 'Callahan', 'Davolio', 'Dodsworth', 'Fuller', 'King', 'Leverling', 'Peacock', 'Suyama', 'West'}</values>
    FirstName TEXT NOT NULL,
        -- <values>{'Adam', 'Andrew', 'Anne', 'Janet', 'Laura', 'Margaret', 'Michael', 'Nancy', 'Robert', 'Steven'}</values>
    BirthDate DATE NOT NULL,
        -- <example>'1968-12-08'</example>
    Photo TEXT NOT NULL,
        -- <values>{'EmpID1.pic', 'EmpID10.pic', 'EmpID2.pic', 'EmpID3.pic', 'EmpID4.pic', 'EmpID5.pic', 'EmpID6.pic', 'EmpID7.pic', 'EmpID8.pic', 'EmpID9.pic'}</values>
    Notes TEXT NOT NULL
        -- <values>{'An old chum.', 'Andrew received his BTS commercial and a Ph.D. in ...mmerce, and the Pacific Rim Importers Association.', 'Anne has a BA degree in English from St. Lawrence College. She is fluent in French and German.', 'Education includes a BA in psychology from Colorad...Nancy is a member of 'Toastmasters International'.', 'Janet has a BS degree in chemistry from Boston Col...ssociate and was promoted to sales representative.', 'Laura received a BA in psychology from the Univers...e in business French. She reads and writes French.', 'Margaret holds a BA in English literature from Con...before returning to her permanent post in Seattle.', 'Michael is a graduate of Sussex University (MA, ec...an read and write French, Portuguese, and Spanish.', 'Robert King served in the Peace Corps and traveled... Europe', he was transferred to the London office.', 'Steven Buchanan graduated from St. Andrews Univers...ational Sales Management'. He is fluent in French.'}</values>
);

/*
Schema: NULLTable: OrderDetails
Rows: 518
Sample rows:
| OrderDetailID   | OrderID   | ProductID   | Quantity   |
|-----------------|-----------|-------------|------------|
| 1               | 10248     | 11          | 12         |
| 2               | 10248     | 42          | 10         |
| 3               | 10248     | 72          | 5          |
| 4               | 10249     | 14          | 9          |
| 5               | 10249     | 51          | 40         |
| ...             | ...       | ...         | ...        |
*/
CREATE TABLE OrderDetails (
    OrderDetailID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    OrderID INTEGER NOT NULL,
        -- <example>10248</example>
        -- <fk> -> Orders.OrderID</fk>
    ProductID INTEGER NOT NULL,
        -- <example>11</example>
        -- <fk> -> Products.ProductID</fk>
    Quantity INTEGER NOT NULL,
        -- <example>12</example>
    FOREIGN KEY (OrderID) REFERENCES Orders(OrderID),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);

/*
Schema: NULLTable: Orders
Rows: 196
Sample rows:
| OrderID   | CustomerID   | EmployeeID   | OrderDate   | ShipperID   |
|-----------|--------------|--------------|-------------|-------------|
| 10248     | 90           | 5            | 1996-07-04  | 3           |
| 10249     | 81           | 6            | 1996-07-05  | 1           |
| 10250     | 34           | 4            | 1996-07-08  | 2           |
| 10251     | 84           | 3            | 1996-07-08  | 1           |
| 10252     | 76           | 4            | 1996-07-09  | 2           |
| ...       | ...          | ...          | ...         | ...         |
*/
CREATE TABLE Orders (
    OrderID INTEGER NOT NULL PRIMARY KEY,
        -- <example>10248</example>
    CustomerID INTEGER NOT NULL,
        -- <example>90</example>
        -- <fk> -> Customers.CustomerID</fk>
    EmployeeID INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> Employees.EmployeeID</fk>
    OrderDate DATETIME NOT NULL,
        -- <example>'1996-07-04'</example>
    ShipperID INTEGER NOT NULL,
        -- <example>3</example>
        -- <fk> -> Shippers.ShipperID</fk>
    FOREIGN KEY (EmployeeID) REFERENCES Employees(EmployeeID),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (ShipperID) REFERENCES Shippers(ShipperID)
);

/*
Schema: NULLTable: Products
Rows: 77
Sample rows:
| ProductID   | ProductName                  | SupplierID   | CategoryID   | Unit                | Price   |
|-------------|------------------------------|--------------|--------------|---------------------|---------|
| 1           | Chais                        | 1            | 1            | 10 boxes x 20 bags  | 18.0    |
| 2           | Chang                        | 1            | 1            | 24 - 12 oz bottles  | 19.0    |
| 3           | Aniseed Syrup                | 1            | 2            | 12 - 550 ml bottles | 10.0    |
| 4           | Chef Anton's Cajun Seasoning | 2            | 2            | 48 - 6 oz jars      | 22.0    |
| 5           | Chef Anton's Gumbo Mix       | 2            | 2            | 36 boxes            | 21.35   |
| ...         | ...                          | ...          | ...          | ...                 | ...     |
*/
CREATE TABLE Products (
    ProductID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    ProductName TEXT NOT NULL,
        -- <example>'Chais'</example>
    SupplierID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Suppliers.SupplierID</fk>
    CategoryID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Categories.CategoryID</fk>
    Unit TEXT NOT NULL,
        -- <example>'10 boxes x 20 bags'</example>
    Price REAL NOT NULL,
        -- <example>18.000</example>
    FOREIGN KEY (CategoryID) REFERENCES Categories(CategoryID),
    FOREIGN KEY (SupplierID) REFERENCES Suppliers(SupplierID)
);

/*
Schema: NULLTable: Shippers
Rows: 3
All rows:
|   ShipperID | ShipperName      | Phone          |
|-------------|------------------|----------------|
|           1 | Speedy Express   | (503) 555-9831 |
|           2 | United Package   | (503) 555-3199 |
|           3 | Federal Shipping | (503) 555-9931 |
*/
CREATE TABLE Shippers (
    ShipperID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    ShipperName TEXT NOT NULL,
        -- <values>{'Federal Shipping', 'Speedy Express', 'United Package'}</values>
    Phone TEXT NOT NULL
        -- <values>{'(503) 555-3199', '(503) 555-9831', '(503) 555-9931'}</values>
);

/*
Schema: NULLTable: Suppliers
Rows: 29
Sample rows:
| SupplierID   | SupplierName                       | ContactName                | Address                   | City        | PostalCode   | Country   | Phone          |
|--------------|------------------------------------|----------------------------|---------------------------|-------------|--------------|-----------|----------------|
| 1            | Exotic Liquid                      | Charlotte Cooper           | 49 Gilbert St.            | Londona     | EC1 4SD      | UK        | (171) 555-2222 |
| 2            | New Orleans Cajun Delights         | Shelley Burke              | P.O. Box 78934            | New Orleans | 70117        | USA       | (100) 555-4822 |
| 3            | Grandma Kelly's Homestead          | Regina Murphy              | 707 Oxford Rd.            | Ann Arbor   | 48104        | USA       | (313) 555-5735 |
| 4            | Tokyo Traders                      | Yoshi Nagase               | 9-8 Sekimai Musashino-shi | Tokyo       | 100          | Japan     | (03) 3555-5011 |
| 5            | Cooperativa de Quesos 'Las Cabras' | Antonio del Valle Saavedra | Calle del Rosal 4         | Oviedo      | 33007        | Spain     | (98) 598 76 54 |
| ...          | ...                                | ...                        | ...                       | ...         | ...          | ...       | ...            |
*/
CREATE TABLE Suppliers (
    SupplierID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    SupplierName TEXT NOT NULL,
        -- <example>'Exotic Liquid'</example>
    ContactName TEXT NOT NULL,
        -- <example>'Charlotte Cooper'</example>
    Address TEXT NOT NULL,
        -- <example>'49 Gilbert St.'</example>
    City TEXT NOT NULL,
        -- <example>'Londona'</example>
    PostalCode TEXT NOT NULL,
        -- <example>'EC1 4SD'</example>
    Country TEXT NOT NULL,
        -- <example>'UK'</example>
    Phone TEXT NOT NULL
        -- <example>'(171) 555-2222'</example>
);
```