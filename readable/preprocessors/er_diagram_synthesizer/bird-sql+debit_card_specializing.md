```mermaid
erDiagram
    Transaction {
        table transactions_1k "Core transaction facts including timestamp, foreign keys to customer, gas station, and product, amount, and price."
    }
    Customer {
        table customers "Core customer master data (identifier, segment, currency)."
    }
    GasStation {
        table gasstations "Gas station reference data (identifier, chain ID, country, segment)."
    }
    Product {
        table products "Product catalog with product identifiers and descriptions."
    }
    MonthlyConsumption {
        table yearmonth "Monthly consumption fact table keyed by (CustomerID, Date)."
    }

    Customer |o--|{ Transaction : "CustomerMakesTransactions"
    %% Customers perform zero or more transactions; each transaction belongs to exactly one customer.
    %% SQL join path: `FROM transactions_1k t JOIN customers c ON c.CustomerID = t.CustomerID`

    GasStation |o--|{ Transaction : "TransactionOccursAtGasStation"
    %% Each transaction occurs at a single gas station; a gas station can host many transactions.
    %% SQL join path: `FROM transactions_1k t JOIN gasstations g ON g.GasStationID = t.GasStationID`

    Product |o--|{ Transaction : "TransactionIncludesProduct"
    %% Each transaction references exactly one product; a product can appear on many transactions.
    %% SQL join path: `FROM transactions_1k t JOIN products p ON p.ProductID = t.ProductID`

    Customer |o--|{ MonthlyConsumption : "CustomerHasMonthlyConsumption"
    %% Customers may have monthly consumption records; each monthly record belongs to exactly one customer.
    %% SQL join path: `FROM yearmonth ym JOIN customers c ON c.CustomerID = ym.CustomerID`
```