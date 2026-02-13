```sql
-- Database: sales

/*
Table: Customers
Rows: 19759
Sample rows:
| CustomerID   | FirstName   | MiddleInitial   | LastName   |
|--------------|-------------|-----------------|------------|
| 1            | Aaron       | [NULL]          | Alexander  |
| 2            | Aaron       | [NULL]          | Bryant     |
| 3            | Aaron       | [NULL]          | Butler     |
| 4            | Aaron       | [NULL]          | Chen       |
| 5            | Aaron       | [NULL]          | Coleman    |
| ...          | ...         | ...             | ...        |
*/
CREATE TABLE Customers (
    CustomerID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    FirstName TEXT NOT NULL,
        -- <example>'Aaron'</example>
    MiddleInitial TEXT NULL,
        -- <example>'A'</example>
    LastName TEXT NOT NULL
        -- <example>'Alexander'</example>
);

/*
Table: Employees
Rows: 22
Sample rows:
| EmployeeID   | FirstName   | MiddleInitial   | LastName       |
|--------------|-------------|-----------------|----------------|
| 1            | Abraham     | e               | Bennet         |
| 2            | Reginald    | l               | Blotchet-Halls |
| 3            | Cheryl      | a               | Carson         |
| 4            | Michel      | e               | DeFrance       |
| 5            | Innes       | e               | del Castillo   |
| ...          | ...         | ...             | ...            |
*/
CREATE TABLE Employees (
    EmployeeID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    FirstName TEXT NOT NULL,
        -- <example>'Abraham'</example>
    MiddleInitial TEXT NOT NULL,
        -- <example>'e'</example>
    LastName TEXT NOT NULL
        -- <example>'Bennet'</example>
);

/*
Table: Products
Rows: 504
Sample rows:
| ProductID   | Name                  | Price   |
|-------------|-----------------------|---------|
| 1           | Adjustable Race       | 1.6     |
| 2           | Bearing Ball          | 0.8     |
| 3           | BB Ball Bearing       | 2.4     |
| 4           | Headset Ball Bearings | 0.0     |
| 5           | Blade                 | 189.6   |
| ...         | ...                   | ...     |
*/
CREATE TABLE Products (
    ProductID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NOT NULL,
        -- <example>'Adjustable Race'</example>
    Price REAL NOT NULL
        -- <example>1.600</example>
);

/*
Table: Sales
Rows: 6715221
Sample rows:
| SalesID   | SalesPersonID   | CustomerID   | ProductID   | Quantity   |
|-----------|-----------------|--------------|-------------|------------|
| 1         | 17              | 10482        | 500         | 500        |
| 2         | 5               | 1964         | 306         | 810        |
| 3         | 8               | 12300        | 123         | 123        |
| 4         | 1               | 4182         | 437         | 437        |
| 5         | 14              | 15723        | 246         | 750        |
| ...       | ...             | ...          | ...         | ...        |
*/
CREATE TABLE Sales (
    SalesID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    SalesPersonID INTEGER NOT NULL,
        -- <example>17</example>
        -- <fk> -> Employees.EmployeeID</fk>
    CustomerID INTEGER NOT NULL,
        -- <example>10482</example>
        -- <fk> -> Customers.CustomerID</fk>
    ProductID INTEGER NOT NULL,
        -- <example>500</example>
        -- <fk> -> Products.ProductID</fk>
    Quantity INTEGER NOT NULL,
        -- <example>500</example>
    FOREIGN KEY (SalesPersonID) REFERENCES Employees(EmployeeID),
    FOREIGN KEY (CustomerID) REFERENCES Customers(CustomerID),
    FOREIGN KEY (ProductID) REFERENCES Products(ProductID)
);
```