```sql
-- Database: sales

-- Table: Customers (19759 rows)
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

-- Table: Employees (22 rows)
CREATE TABLE Employees (
    EmployeeID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    FirstName TEXT NOT NULL,
        -- <example>'Abraham'</example>
    MiddleInitial TEXT NULL,
        -- <example>'e'</example>
    LastName TEXT NOT NULL
        -- <example>'Bennet'</example>
);

-- Table: Products (504 rows)
CREATE TABLE Products (
    ProductID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NOT NULL,
        -- <example>'Adjustable Race'</example>
    Price REAL NULL
        -- <example>1.600</example>
);

-- Table: Sales (6715221 rows)
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