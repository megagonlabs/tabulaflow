```mermaid
erDiagram
    Account {
        table account "Core account attributes (district, statement frequency, open date)."
    }
    Client {
        table client "Core client demographics and district reference."
    }
    District {
        table district "District master data and metrics (A2–A16)."
    }
    Disposition {
        table disp "Junction/authorization records connecting clients to accounts with role type."
    }
    Card {
        table card "Card issuance linked to a disposition (authorization)."
    }
    Loan {
        table loan "Loan records referencing the owning account."
    }
    PaymentOrder {
        table order "Outgoing payment order details (beneficiary bank/account, amount, k_symbol)."
    }
    Transaction {
        table trans "Transactional movements on accounts (type, operation, amounts, balances)."
    }

    Account ||--o{ District : "AccountAssignedToDistrict"
    %% Each account is assigned to exactly one district; a district can have many accounts.
    %% SQL join path: `FROM account JOIN district ON account.district_id = district.district_id`

    Client ||--o{ District : "ClientLocatedInDistrict"
    %% Each client resides in exactly one district; a district can have many clients.
    %% SQL join path: `FROM client JOIN district ON client.district_id = district.district_id`

    Client }o--|| Disposition : "ClientHasDisposition"
    %% A client can hold multiple authorizations (dispositions); each disposition belongs to exactly one client.
    %% SQL join path: `FROM disp JOIN client ON disp.client_id = client.client_id`

    Account }o--|| Disposition : "AccountHasDisposition"
    %% An account can have multiple client authorizations; each disposition is for exactly one account.
    %% SQL join path: `FROM account JOIN disp ON account.account_id = disp.account_id`

    Disposition }o--|| Card : "DispositionHasCard"
    %% A disposition (authorization) can have multiple cards issued; each card is issued for exactly one disposition.
    %% SQL join path: `FROM disp JOIN card ON card.disp_id = disp.disp_id`

    Account }o--|| Loan : "AccountHasLoan"
    %% An account can have multiple loans; each loan is attached to exactly one account.
    %% SQL join path: `FROM account JOIN loan ON account.account_id = loan.account_id`

    Account }o--|| PaymentOrder : "AccountHasPaymentOrder"
    %% An account can have multiple payment orders; each payment order originates from exactly one account.
    %% SQL join path: `FROM account JOIN "order" ON account.account_id = "order".account_id`

    Account }o--|| Transaction : "AccountHasTransaction"
    %% An account can have many transactions; each transaction is recorded on exactly one account.
    %% SQL join path: `FROM account JOIN trans ON account.account_id = trans.account_id`
```