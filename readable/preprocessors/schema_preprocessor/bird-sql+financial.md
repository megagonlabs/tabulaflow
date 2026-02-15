```sql
-- Database: financial

/*
Schema: NULL
Table: account
Rows: 4500
Sample rows:
| account_id   | district_id   | frequency        | date       |
|--------------|---------------|------------------|------------|
| 1            | 18            | POPLATEK MESICNE | 1995-03-24 |
| 2            | 1             | POPLATEK MESICNE | 1993-02-26 |
| 3            | 5             | POPLATEK MESICNE | 1997-07-07 |
| 4            | 12            | POPLATEK MESICNE | 1996-02-21 |
| 5            | 15            | POPLATEK MESICNE | 1997-05-30 |
| ...          | ...           | ...              | ...        |
*/
CREATE TABLE account (
    "account_id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Account identifier — primary key of the account table; uniquely identifies each account and is used to link account-related records (transactions, loans, dispositions, orders).</description>
        -- <example>1</example>
    "district_id" INTEGER NOT NULL,
        -- <description>Branch district identifier — the district where the account's branch is located.</description>
        -- <example>18</example>
        -- <fk> -> district."district_id"</fk>
    "frequency" TEXT NOT NULL,
        -- <description>Account fee billing frequency — indicates how often the account’s service/maintenance fee is charged (e.g., monthly, weekly, or per transaction).</description>
        -- <values>{'POPLATEK MESICNE', 'POPLATEK PO OBRATU', 'POPLATEK TYDNE'}</values>
    "date" DATE NOT NULL,
        -- <description>Account creation date — the date when the account was opened.</description>
        -- <example>'1995-03-24'</example>
    FOREIGN KEY ("district_id") REFERENCES district("district_id")
);

/*
Schema: NULL
Table: card
Rows: 892
Sample rows:
| card_id   | disp_id   | type    | issued     |
|-----------|-----------|---------|------------|
| 1         | 9         | gold    | 1998-10-16 |
| 2         | 19        | classic | 1998-03-13 |
| 3         | 41        | gold    | 1995-09-03 |
| 4         | 42        | classic | 1998-11-26 |
| 5         | 51        | junior  | 1995-04-24 |
| ...       | ...       | ...     | ...        |
*/
CREATE TABLE card (
    "card_id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Credit card identifier — unique identifier for each card record.</description>
        -- <example>1</example>
    "disp_id" INTEGER NOT NULL,
        -- <description>Disposition identifier for the card — identifies the client-account disposition (for example OWNER or DISPONENT) associated with this card.</description>
        -- <example>9</example>
        -- <fk> -> disp."disp_id"</fk>
    "type" TEXT NOT NULL,
        -- <description>Card tier indicating the class/level of the credit card (clarifies customer/service level; e.g., junior = entry-level, classic = standard, gold = premium).</description>
        -- <values>{'classic', 'gold', 'junior'}</values>
    "issued" DATE NOT NULL,
        -- <description>Credit card issue date — the date the card was issued (e.g., 1998-10-16).</description>
        -- <example>'1998-10-16'</example>
    FOREIGN KEY ("disp_id") REFERENCES disp("disp_id")
);

/*
Schema: NULL
Table: client
Rows: 5369
Sample rows:
| client_id   | gender   | birth_date   | district_id   |
|-------------|----------|--------------|---------------|
| 1           | F        | 1970-12-13   | 18            |
| 2           | M        | 1945-02-04   | 1             |
| 3           | F        | 1940-10-09   | 1             |
| 4           | M        | 1956-12-01   | 5             |
| 5           | F        | 1960-07-03   | 5             |
| ...         | ...      | ...          | ...           |
*/
CREATE TABLE client (
    "client_id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique client identifier.</description>
        -- <example>1</example>
    "gender" TEXT NOT NULL,
        -- <description>Client gender — the client's recorded sex used for demographic segmentation and analysis.</description>
        -- <values>{'F', 'M'}</values>
    "birth_date" DATE NOT NULL,
        -- <description>Client date of birth — the client's date of birth, used to compute age and support age-based analyses or eligibility checks.</description>
        -- <example>'1970-12-13'</example>
    "district_id" INTEGER NOT NULL,
        -- <description>Client district identifier (the branch/district where the client is registered).</description>
        -- <example>18</example>
        -- <fk> -> district."district_id"</fk>
    FOREIGN KEY ("district_id") REFERENCES district("district_id")
);

/*
Schema: NULL
Table: disp
Rows: 5369
Sample rows:
| disp_id   | client_id   | account_id   | type      |
|-----------|-------------|--------------|-----------|
| 1         | 1           | 1            | OWNER     |
| 2         | 2           | 2            | OWNER     |
| 3         | 3           | 2            | DISPONENT |
| 4         | 4           | 3            | OWNER     |
| 5         | 5           | 3            | DISPONENT |
| ...       | ...         | ...          | ...       |
*/
CREATE TABLE disp (
    "disp_id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Disposition identifier — the unique id for each disposition record in the disp table.</description>
        -- <example>1</example>
    "client_id" INTEGER NOT NULL,
        -- <description>Client identifier for the disposition — identifies the client associated with this account (e.g., owner or disponent).</description>
        -- <example>1</example>
        -- <fk> -> client."client_id"</fk>
    "account_id" INTEGER NOT NULL,
        -- <description>Account identifier linking this disposition record to its associated account.</description>
        -- <example>1</example>
        -- <fk> -> account."account_id"</fk>
    "type" TEXT NOT NULL,
        -- <description>Account disposition role indicating the client's relationship to the account and the rights that role confers (owner has full control; disponent has limited operating authority).</description>
        -- <values>{'DISPONENT', 'OWNER'}</values>
    FOREIGN KEY ("account_id") REFERENCES account("account_id"),
    FOREIGN KEY ("client_id") REFERENCES client("client_id")
);

/*
Schema: NULL
Table: district
Rows: 77
Sample rows:
| district_id   | A2          | A3              | A4      | A5   | A6   | A7   | A8   | A9   | A10   | A11   | A12   | A13   | A14   | A15   | A16   |
|---------------|-------------|-----------------|---------|------|------|------|------|------|-------|-------|-------|-------|-------|-------|-------|
| 1             | Hl.m. Praha | Prague          | 1204953 | 0    | 0    | 0    | 1    | 1    | 100.0 | 12541 | 0.2   | 0.43  | 167   | 85677 | 99107 |
| 2             | Benesov     | central Bohemia | 88884   | 80   | 26   | 6    | 2    | 5    | 46.7  | 8507  | 1.6   | 1.85  | 132   | 2159  | 2674  |
| 3             | Beroun      | central Bohemia | 75232   | 55   | 26   | 4    | 1    | 5    | 41.7  | 8980  | 1.9   | 2.21  | 111   | 2824  | 2813  |
| 4             | Kladno      | central Bohemia | 149893  | 63   | 29   | 6    | 2    | 6    | 67.4  | 9753  | 4.6   | 5.05  | 109   | 5244  | 5892  |
| 5             | Kolin       | central Bohemia | 95616   | 65   | 30   | 4    | 1    | 6    | 51.4  | 9307  | 3.8   | 4.43  | 118   | 2616  | 3040  |
| ...           | ...         | ...             | ...     | ...  | ...  | ...  | ...  | ...  | ...   | ...   | ...   | ...   | ...   | ...   | ...   |
*/
CREATE TABLE district (
    "district_id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>district identifier for the bank branch location</description>
        -- <example>1</example>
    "A2" TEXT NOT NULL,
        -- <description>District name — the name of the district where the bank branch is located.</description>
        -- <example>'Hl.m. Praha'</example>
    "A3" TEXT NOT NULL,
        -- <description>District region — the name of the larger administrative region that contains the district.</description>
        -- <values>{'Prague', 'central Bohemia', 'east Bohemia', 'north Bohemia', 'north Moravia', 'south Bohemia', 'south Moravia', 'west Bohemia'}</values>
    "A4" TEXT NOT NULL,
        -- <description>Total number of inhabitants in the district (district population).</description>
        -- <example>'1204953'</example>
    "A5" TEXT NOT NULL,
        -- <description>Count of municipalities in the district with fewer than 500 inhabitants.</description>
        -- <example>'0'</example>
    "A6" TEXT NOT NULL,
        -- <description>Number of municipalities in the district with 500–1,999 inhabitants.</description>
        -- <example>'0'</example>
    "A7" TEXT NOT NULL,
        -- <description>Count of municipalities in the district with 2,000–9,999 inhabitants</description>
        -- <example>'0'</example>
    "A8" INTEGER NOT NULL,
        -- <description>Count of municipalities in the district with more than 10,000 inhabitants.</description>
        -- <example>1</example>
    "A10" REAL NOT NULL,
        -- <description>Share of district population living in urban areas (percentage, 0–100).</description>
        -- <example>100.000</example>
    "A11" INTEGER NOT NULL,
        -- <description>Average salary of employees in the district (unit/currency not specified).</description>
        -- <example>12541</example>
    "A12" REAL NULL,
        -- <description>1995 district unemployment rate — the share of unemployed residents in the district for 1995 (expressed as a proportion; e.g., 0.20 = 20%).</description>
        -- <example>0.200</example>
    "A13" REAL NOT NULL,
        -- <description>1996 district unemployment rate — percentage of the district's population that was unemployed in 1996.</description>
        -- <example>0.430</example>
    "A14" INTEGER NOT NULL,
        -- <description>Number of entrepreneurs per 1,000 inhabitants in the district.</description>
        -- <example>167</example>
    "A15" INTEGER NULL,
        -- <description>Number of recorded crimes in 1995 for the district.</description>
        -- <example>85677</example>
    "A16" INTEGER NOT NULL
        -- <description>Count of crimes committed in the district in 1996.</description>
        -- <example>99107</example>
);

/*
Schema: NULL
Table: loan
Rows: 682
Sample rows:
| loan_id   | account_id   | date       | amount   | duration   | payments   | status   |
|-----------|--------------|------------|----------|------------|------------|----------|
| 4959      | 2            | 1994-01-05 | 80952    | 24         | 3373.0     | A        |
| 4961      | 19           | 1996-04-29 | 30276    | 12         | 2523.0     | B        |
| 4962      | 25           | 1997-12-08 | 30276    | 12         | 2523.0     | A        |
| 4967      | 37           | 1998-10-14 | 318480   | 60         | 5308.0     | D        |
| 4968      | 38           | 1998-04-19 | 110736   | 48         | 2307.0     | C        |
| ...       | ...          | ...        | ...      | ...        | ...        | ...      |
*/
CREATE TABLE loan (
    "loan_id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique loan identifier for each loan record (table primary key).</description>
        -- <example>4959</example>
    "account_id" INTEGER NOT NULL,
        -- <description>Account associated with the loan — identifies which account the loan belongs to and is used to join loan records to the account table.</description>
        -- <example>2</example>
        -- <fk> -> account."account_id"</fk>
    "date" DATE NOT NULL,
        -- <description>Loan approval date — the date the loan was approved (when the loan was granted).</description>
        -- <example>'1994-01-05'</example>
    "amount" INTEGER NOT NULL,
        -- <description>Approved loan principal at origination, expressed in US dollars.</description>
        -- <example>80952</example>
    "duration" INTEGER NOT NULL,
        -- <description>Loan duration in months (length of the loan repayment period).</description>
        -- <example>24</example>
    "payments" REAL NOT NULL,
        -- <description>Monthly scheduled repayment amount for the loan — the amount the borrower is required to pay each month (monetary units).</description>
        -- <example>3373.000</example>
    "status" TEXT NOT NULL,
        -- <description>Loan repayment status — coded indicator of the loan’s repayment state (A = finished, no problems; B = finished, loan not paid; C = active and current; D = active and delinquent).</description>
        -- <values>{'A', 'B', 'C', 'D'}</values>
    FOREIGN KEY ("account_id") REFERENCES account("account_id")
);

/*
Schema: NULL
Table: order
Rows: 6471
Sample rows:
| order_id   | account_id   | bank_to   | account_to   | amount   | k_symbol   |
|------------|--------------|-----------|--------------|----------|------------|
| 29401      | 1            | YZ        | 87144583     | 2452.0   | SIPO       |
| 29402      | 2            | ST        | 89597016     | 3372.7   | UVER       |
| 29403      | 2            | QR        | 13943797     | 7266.0   | SIPO       |
| 29404      | 3            | WX        | 83084338     | 1135.0   | SIPO       |
| 29405      | 3            | CD        | 24485939     | 327.0    |            |
| ...        | ...          | ...       | ...          | ...      | ...        |
*/
CREATE TABLE order (
    "order_id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique order identifier — the primary key that uniquely identifies each payment order record in the order table.</description>
        -- <example>29401</example>
    "account_id" INTEGER NOT NULL,
        -- <description>Account identifier for the order — identifies the account that submitted or is charged by the payment order.</description>
        -- <example>1</example>
        -- <fk> -> account."account_id"</fk>
    "bank_to" TEXT NOT NULL,
        -- <description>Recipient bank code — two-letter code identifying the receiving bank for the payment.</description>
        -- <values>{'AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST', 'UV', 'WX', 'YZ'}</values>
    "account_to" INTEGER NOT NULL,
        -- <description>Recipient account number — the destination account for the payment; used together with bank_to to identify the full recipient bank account.</description>
        -- <example>87144583</example>
    "amount" REAL NOT NULL,
        -- <description>Debited amount for the payment order — the money withdrawn from the originating account when the order was executed.</description>
        -- <example>2452.000</example>
    "k_symbol" TEXT NOT NULL,
        -- <description>Payment purpose code — a short label that characterizes the purpose of the outgoing order (e.g., SIPO = household payment, POJISTNE = insurance, LEASING = leasing, UVER = loan repayment).</description>
        -- <values>{'', 'LEASING', 'POJISTNE', 'SIPO', 'UVER'}</values>
    FOREIGN KEY ("account_id") REFERENCES account("account_id")
);

/*
Schema: NULL
Table: trans
Rows: 1056320
Sample rows:
| trans_id   | account_id   | date       | type   | operation     | amount   | balance   | k_symbol   | bank   | account    |
|------------|--------------|------------|--------|---------------|----------|-----------|------------|--------|------------|
| 1          | 1            | 1995-03-24 | PRIJEM | VKLAD         | 1000     | 1000      | [NULL]     | [NULL] | [NULL]     |
| 5          | 1            | 1995-04-13 | PRIJEM | PREVOD Z UCTU | 3679     | 4679      | [NULL]     | AB     | 41403269.0 |
| 6          | 1            | 1995-05-13 | PRIJEM | PREVOD Z UCTU | 3679     | 20977     | [NULL]     | AB     | 41403269.0 |
| 7          | 1            | 1995-06-13 | PRIJEM | PREVOD Z UCTU | 3679     | 26835     | [NULL]     | AB     | 41403269.0 |
| 8          | 1            | 1995-07-13 | PRIJEM | PREVOD Z UCTU | 3679     | 30415     | [NULL]     | AB     | 41403269.0 |
| ...        | ...          | ...        | ...    | ...           | ...      | ...       | ...        | ...    | ...        |
*/
CREATE TABLE trans (
    "trans_id" INTEGER NOT NULL PRIMARY KEY,
        -- <description>Transaction identifier for individual transaction records.</description>
        -- <example>1</example>
    "account_id" INTEGER NOT NULL,
        -- <description>Account identifier linking a transaction to the account that performed it.</description>
        -- <example>1</example>
        -- <fk> -> account."account_id"</fk>
    "date" DATE NOT NULL,
        -- <description>Transaction date — the calendar date when the transaction was made (the posting date).</description>
        -- <example>'1995-03-24'</example>
    "type" TEXT NOT NULL,
        -- <description>Transaction direction indicator — whether the record is an inflow (credit) or an outflow (withdrawal).</description>
        -- <values>{'PRIJEM', 'VYBER', 'VYDAJ'}</values>
    "operation" TEXT NULL,
        -- <description>transaction method indicating how the transaction was carried out (the mode or channel of the transaction, e.g., cash deposit, cash withdrawal, card withdrawal, incoming transfer from another account, outgoing transfer to another account).</description>
        -- <values>{'PREVOD NA UCET', 'PREVOD Z UCTU', 'VKLAD', 'VYBER KARTOU', 'VYBER'}</values>
    "amount" INTEGER NOT NULL,
        -- <description>Transaction amount — monetary value of the individual transaction in USD; consult the trans.type column to tell whether this amount was a credit (PRIJEM) or a debit/withdrawal (VYDAJ/VYBER).</description>
        -- <example>1000</example>
    "balance" INTEGER NOT NULL,
        -- <description>Account balance after transaction (amount in USD), i.e., the account's balance immediately following that transaction.</description>
        -- <example>1000</example>
    "k_symbol" TEXT NULL,
        -- <description>Transaction purpose label — a short text classification indicating the reason or purpose of the transaction (used to categorize transactions for reporting and accounting).</description>
        -- <values>{' ', 'DUCHOD', 'POJISTNE', 'SANKC. UROK', 'SIPO', 'SLUZBY', 'UROK', 'UVER'}</values>
    "bank" TEXT NULL,
        -- <description>Counterparty bank code — a two‑letter code identifying the other party’s bank for the transaction.</description>
        -- <values>{'AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST', 'UV', 'WX', 'YZ'}</values>
    "account" INTEGER NULL,
        -- <description>counterparty account number — the account number of the transaction partner (populated for transfers/remittances and other inter-account operations; typically used together with the partner bank code; NULL for many cash/card operations).</description>
        -- <example>41403269</example>
    FOREIGN KEY ("account_id") REFERENCES account("account_id")
);
```