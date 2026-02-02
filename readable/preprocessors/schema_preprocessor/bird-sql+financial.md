```sql
-- Database: financial

-- Table: account (4500 rows)
CREATE TABLE account (
    account_id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique account identifier — primary key for the account table; used to link accounts to dispositions, transactions, orders and loans.</description>
        -- <example>1</example>
    district_id INTEGER NOT NULL,
        -- <description>Branch district identifier for the account. Identifies the district where the account's branch is located; populated for all 4,500 accounts with 77 distinct districts (IDs 1–77). Most accounts are in 'Hl.m. Praha' (554 accounts).</description>
        -- <example>18</example>
        -- <fk> -> district.district_id</fk>
    frequency TEXT NOT NULL,
        -- <description>Account fee frequency — indicates how often account fees are charged.</description>
        -- <values>{'POPLATEK MESICNE', 'POPLATEK PO OBRATU', 'POPLATEK TYDNE'}</values>
    date DATE NOT NULL,
        -- <description>Account creation date — the account's opening date (range: 1993-01-01 to 1997-12-29).</description>
        -- <example>'1995-03-24'</example>
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

-- Table: card (892 rows)
CREATE TABLE card (
    card_id INTEGER NOT NULL PRIMARY KEY,
        -- <description>card identifier — unique identifier for each credit card record (serves as the table's primary key).</description>
        -- <example>1</example>
    disp_id INTEGER NOT NULL,
        -- <description>Disposition identifier linking the card to a disposition (the client–account role that owns or can use the account). Always populated in this table and all values reference existing disposition records.</description>
        -- <example>9</example>
        -- <fk> -> disp.disp_id</fk>
    type TEXT NOT NULL,
        -- <description>Credit card tier indicating the card’s class and relative privilege level (junior = entry-level, classic = standard, gold = premium).</description>
        -- <values>{'classic', 'gold', 'junior'}</values>
    issued DATE NOT NULL,
        -- <description>Credit card issue date — the date when the card was issued; values span 1993-11-07 to 1998-12-29 with no missing values (892 rows), useful for computing card age or tenure.</description>
        -- <example>'1998-10-16'</example>
    FOREIGN KEY (disp_id) REFERENCES disp(disp_id)
);

-- Table: client (5369 rows)
CREATE TABLE client (
    client_id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique client identifier — a stable ID that identifies each client (primary key); referenced by other tables such as disp.client_id.</description>
        -- <example>1</example>
    gender TEXT NOT NULL,
        -- <description>client gender — recorded client gender/sex</description>
        -- <values>{'F', 'M'}</values>
    birth_date DATE NOT NULL,
        -- <description>Client birth date — the client's date of birth; values in this table span 1911-08-20 to 1987-09-27 (no NULLs), with 4,738 distinct dates among 5,369 clients.</description>
        -- <example>'1970-12-13'</example>
    district_id INTEGER NOT NULL,
        -- <description>client's district identifier — the client's branch/home district (links to district.district_id).</description>
        -- <example>18</example>
        -- <fk> -> district.district_id</fk>
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

-- Table: disp (5369 rows)
CREATE TABLE disp (
    disp_id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Disposition record identifier linking a client to an account (unique per disposition).</description>
        -- <example>1</example>
    client_id INTEGER NOT NULL,
        -- <description>Client identifier linking the disposition row to a client record (every disp row has a non-null client_id; values are unique per disposition and all match existing client records).</description>
        -- <example>1</example>
        -- <fk> -> client.client_id</fk>
    account_id INTEGER NOT NULL,
        -- <description>Account identifier for the account associated with this disposition (links each disposition to an existing account).</description>
        -- <example>1</example>
        -- <fk> -> account.account_id</fk>
    type TEXT NOT NULL,
        -- <description>Disposition role on the account: indicates whether the client is the account owner or an authorized signatory (holds rights on the account).</description>
        -- <values>{'DISPONENT', 'OWNER'}</values>
    FOREIGN KEY (account_id) REFERENCES account(account_id),
    FOREIGN KEY (client_id) REFERENCES client(client_id)
);

-- Table: district (77 rows)
CREATE TABLE district (
    district_id INTEGER NOT NULL PRIMARY KEY,
        -- <description>District identifier for branch location — identifies the geographic district where a bank branch (and clients) are located; used to link district-level attributes (region, population, unemployment, etc.) to accounts and clients.</description>
        -- <example>1</example>
    A2 TEXT NOT NULL,
        -- <description>District name — the name of the administrative district where the bank branch (district) is located.</description>
        -- <example>'Hl.m. Praha'</example>
    A3 TEXT NOT NULL,
        -- <description>Administrative region of the district — the name of the larger geographic/administrative region that contains the district (used to group districts by region).</description>
        -- <values>{'Prague', 'central Bohemia', 'east Bohemia', 'north Bohemia', 'north Moravia', 'south Bohemia', 'south Moravia', 'west Bohemia'}</values>
    A4 TEXT NOT NULL,
        -- <description>Number of inhabitants in the district.</description>
        -- <example>'1204953'</example>
    A5 TEXT NOT NULL,
        -- <description>Count of municipalities in the district with fewer than 500 inhabitants.</description>
        -- <example>'0'</example>
    A6 TEXT NOT NULL,
        -- <description>Number of municipalities in the district with 500–1,999 inhabitants. (Observed values range roughly 0–70 across districts.)</description>
        -- <example>'0'</example>
    A7 TEXT NOT NULL,
        -- <description>Count of municipalities in the district with between 2,000 and 9,999 inhabitants.</description>
        -- <example>'0'</example>
    A8 INTEGER NOT NULL,
        -- <description>Count of municipalities in the district with more than 10,000 inhabitants (observed values 0–5; all 77 districts populated).</description>
        -- <example>1</example>
    A10 REAL NOT NULL,
        -- <description>Percentage of the district population living in urban areas.</description>
        -- <example>100.000</example>
    A11 INTEGER NOT NULL,
        -- <description>average salary of employees in the district — per-district average salary (units not specified); values range 8,110–12,541 across all 77 districts (mean ≈ 9,032).</description>
        -- <example>12541</example>
    A12 REAL NULL,
        -- <description>District unemployment rate in 1995 (proportion of residents unemployed; e.g., 0.20 = 20%).</description>
        -- <example>0.200</example>
    A13 REAL NOT NULL,
        -- <description>Unemployment rate in 1996 for the district (share of residents unemployed). Values are numeric rates — confirm whether they represent proportions (0–1) or percentages (0–100).</description>
        -- <example>0.430</example>
    A14 INTEGER NOT NULL,
        -- <description>Number of entrepreneurs per 1,000 inhabitants in the district.</description>
        -- <example>167</example>
    A15 INTEGER NULL,
        -- <description>number of crimes committed in 1995 for the district (district-level count) — contains one NULL; observed range 818–85,677</description>
        -- <example>85677</example>
    A16 INTEGER NOT NULL
        -- <description>Number of crimes committed in the district during 1996.</description>
        -- <example>99107</example>
);

-- Table: loan (682 rows)
CREATE TABLE loan (
    loan_id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Loan identifier — unique identifier assigned to each loan record (values in this dataset range from 4959 to 7308).</description>
        -- <example>4959</example>
    account_id INTEGER NOT NULL,
        -- <description>Account identifier (foreign key to account.account_id) for the account associated with this loan.</description>
        -- <example>2</example>
        -- <fk> -> account.account_id</fk>
    date DATE NOT NULL,
        -- <description>Loan approval date — the date the loan was approved; values range from 1993-07-05 to 1998-12-08 with no missing values.</description>
        -- <example>'1994-01-05'</example>
    amount INTEGER NOT NULL,
        -- <description>Approved loan amount (the principal approved for the loan, in USD).</description>
        -- <example>80952</example>
    duration INTEGER NOT NULL,
        -- <description>Loan term in months — the length of the loan repayment period (values range 12–60 months; mean ≈36.5; no missing values).</description>
        -- <example>24</example>
    payments REAL NOT NULL,
        -- <description>Monthly loan installment amount — the scheduled payment the borrower must pay each month (non-null; values in this dataset range roughly from 304 to 9,910 with a mean around 4,190).</description>
        -- <example>3373.000</example>
    status TEXT NOT NULL,
        -- <description>Loan repayment status code indicating contract stage and repayment condition: A = finished, no problems; B = finished, loan not paid; C = running (active), OK so far; D = running, client in debt.</description>
        -- <values>{'A', 'B', 'C', 'D'}</values>
    FOREIGN KEY (account_id) REFERENCES account(account_id)
);

-- Table: order (6471 rows)
CREATE TABLE order (
    order_id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Payment order identifier — unique ID for each payment/transfer order record in the orders table.</description>
        -- <example>29401</example>
    account_id INTEGER NOT NULL,
        -- <description>Ordering account identifier — the account that initiated (or is charged by) the payment order.</description>
        -- <example>1</example>
        -- <fk> -> account.account_id</fk>
    bank_to TEXT NOT NULL,
        -- <description>Recipient bank code — two-letter identifier for the payment recipient's bank (unique per bank). Always populated in this table (6,471 rows) with 13 distinct codes (examples: QR, YZ, AB).</description>
        -- <values>{'AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST', 'UV', 'WX', 'YZ'}</values>
    account_to INTEGER NOT NULL,
        -- <description>Recipient (beneficiary) account number — the account number to which the payment is sent; populated for all orders and almost always unique (6,446 distinct values out of 6,471 rows). Values are typically 8 digits (examples: 99149345, 97387158); observed range in the table is roughly 399 to 99,994,200.</description>
        -- <example>87144583</example>
    amount REAL NOT NULL,
        -- <description>Debited amount — the money withdrawn from the customer's account for a payment order.</description>
        -- <example>2452.000</example>
    k_symbol TEXT NOT NULL,
        -- <description>Payment purpose code — short label classifying the purpose/characterization of the payment on the order (e.g., household payment, insurance, leasing, loan repayment). Many rows contain an empty value.</description>
        -- <values>{'', 'LEASING', 'POJISTNE', 'SIPO', 'UVER'}</values>
    FOREIGN KEY (account_id) REFERENCES account(account_id)
);

-- Table: trans (1056320 rows)
CREATE TABLE trans (
    trans_id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique transaction identifier — non-null primary key for each transaction record (observed values range 1 to 3,682,990; all values are distinct).</description>
        -- <example>1</example>
    account_id INTEGER NOT NULL,
        -- <description>Owning account of the transaction.</description>
        -- <example>1</example>
        -- <fk> -> account.account_id</fk>
    date DATE NOT NULL,
        -- <description>Transaction date — the calendar day on which each transaction occurred; values span 1993-01-01 to 1998-12-31 with no missing values (1,056,320 rows, 2,191 distinct dates).</description>
        -- <example>'1995-03-24'</example>
    type TEXT NOT NULL,
        -- <description>transaction direction — indicates whether the transaction increases the account balance (credit) or decreases it (withdrawal/debit); the dataset uses separate codes to distinguish different kinds of outflows.</description>
        -- <values>{'PRIJEM', 'VYBER', 'VYDAJ'}</values>
    operation TEXT NULL,
        -- <description>Transaction mode — short label indicating how the transaction was executed (e.g., transfer to/from account, cash deposit, or card/cash withdrawal). Contains a substantial fraction of NULLs (~17%).</description>
        -- <values>{'PREVOD NA UCET', 'PREVOD Z UCTU', 'VKLAD', 'VYBER KARTOU', 'VYBER'}</values>
    amount INTEGER NOT NULL,
        -- <description>Transaction amount — cash value of the transaction in USD (amount credited or debited). No missing values; observed range 0–87,400 with mean ≈ 5,924 and about 35,890 distinct amounts across 1,056,320 rows.</description>
        -- <example>1000</example>
    balance INTEGER NOT NULL,
        -- <description>Post-transaction account balance — the account balance immediately after each transaction; values can be negative.</description>
        -- <example>1000</example>
    k_symbol TEXT NULL,
        -- <description>Transaction purpose code — a short text code indicating the reason or category of the transaction (e.g., UROK = interest credited; SLUZBY = service charges; POJISTNE = insurance payment; SIPO = household payments; DUCHOD = pension; UVER = loan repayment; SANKC. UROK = penalty/late interest). Many rows are NULL (no purpose recorded).</description>
        -- <values>{' ', 'DUCHOD', 'POJISTNE', 'SANKC. UROK', 'SIPO', 'SLUZBY', 'UROK', 'UVER'}</values>
    bank TEXT NULL,
        -- <description>Partner bank identifier for the transaction — the counterparty bank code associated with a transaction (nullable). Many transactions have no partner bank recorded.</description>
        -- <values>{'AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST', 'UV', 'WX', 'YZ'}</values>
    account INTEGER NULL,
        -- <description>counterparty account number — the partner (recipient/sender) account number for the transaction. Many rows are empty (~72% null); when present there are ~7.7k distinct accounts and a frequent sentinel value 0 (21,881 occurrences), indicating internal or unspecified counterparties.</description>
        -- <example>41403269</example>
    FOREIGN KEY (account_id) REFERENCES account(account_id)
);
```