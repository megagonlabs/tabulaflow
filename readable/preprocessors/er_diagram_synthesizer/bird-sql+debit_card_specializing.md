```mermaid
erDiagram
    Transaction {
        table transactions_1k "Core transaction fact rows and foreign-key-like references (CustomerID, GasStationID, ProductID)."
    }
    Customer {
        table customers "Customer master data (segment, currency)."
    }
    GasStation {
        table gasstations "Gas station master data (ChainID, Country, Segment)."
    }
    Product {
        table products "Product catalog entries (description)."
    }
    CustomerMonthlyConsumption {
        table yearmonth "Per-customer monthly consumption summary rows (one row per customer-month)."
    }
    Customer |o--|{ Transaction : "CustomerMakesTransactions"
    GasStation |o--|{ Transaction : "TransactionOccursAtGasStation"
    Product |o--|{ Transaction : "TransactionInvolvesProduct"
    Customer |o--|{ CustomerMonthlyConsumption : "CustomerHasMonthlyConsumption"
    CustomerMonthlyConsumption |o--o{ Transaction : "TransactionRollsUpIntoMonthlyConsumption"
```