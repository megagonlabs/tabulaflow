```sql
-- Database: financial

-- Table: account (4500 rows)
CREATE TABLE account (
    account_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    district_id INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> district.district_id</fk>
    frequency TEXT NOT NULL,
        -- <values>{'POPLATEK MESICNE', 'POPLATEK PO OBRATU', 'POPLATEK TYDNE'}</values>
    date DATE NOT NULL,
        -- <example>'1995-03-24'</example>
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

-- Table: card (892 rows)
CREATE TABLE card (
    card_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    disp_id INTEGER NOT NULL,
        -- <example>9</example>
        -- <fk> -> disp.disp_id</fk>
    type TEXT NOT NULL,
        -- <values>{'classic', 'gold', 'junior'}</values>
    issued DATE NOT NULL,
        -- <example>'1998-10-16'</example>
    FOREIGN KEY (disp_id) REFERENCES disp(disp_id)
);

-- Table: client (5369 rows)
CREATE TABLE client (
    client_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    gender TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    birth_date DATE NOT NULL,
        -- <example>'1970-12-13'</example>
    district_id INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> district.district_id</fk>
    FOREIGN KEY (district_id) REFERENCES district(district_id)
);

-- Table: disp (5369 rows)
CREATE TABLE disp (
    disp_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    client_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> client.client_id</fk>
    account_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> account.account_id</fk>
    type TEXT NOT NULL,
        -- <values>{'DISPONENT', 'OWNER'}</values>
    FOREIGN KEY (account_id) REFERENCES account(account_id),
    FOREIGN KEY (client_id) REFERENCES client(client_id)
);

-- Table: district (77 rows)
CREATE TABLE district (
    district_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    A2 TEXT NOT NULL,
        -- <example>'Hl.m. Praha'</example>
    A3 TEXT NOT NULL,
        -- <values>{'Prague', 'central Bohemia', 'east Bohemia', 'north Bohemia', 'north Moravia', 'south Bohemia', 'south Moravia', 'west Bohemia'}</values>
    A4 TEXT NOT NULL,
        -- <example>'1204953'</example>
    A5 TEXT NOT NULL,
        -- <example>'0'</example>
    A6 TEXT NOT NULL,
        -- <example>'0'</example>
    A7 TEXT NOT NULL,
        -- <example>'0'</example>
    A8 INTEGER NOT NULL,
        -- <example>1</example>
    A9 INTEGER NOT NULL,
        -- <example>1</example>
    A10 REAL NOT NULL,
        -- <example>100.000</example>
    A11 INTEGER NOT NULL,
        -- <example>12541</example>
    A12 REAL NULL,
        -- <example>0.200</example>
    A13 REAL NOT NULL,
        -- <example>0.430</example>
    A14 INTEGER NOT NULL,
        -- <example>167</example>
    A15 INTEGER NULL,
        -- <example>85677</example>
    A16 INTEGER NOT NULL
        -- <example>99107</example>
);

-- Table: loan (682 rows)
CREATE TABLE loan (
    loan_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>4959</example>
    account_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> account.account_id</fk>
    date DATE NOT NULL,
        -- <example>'1994-01-05'</example>
    amount INTEGER NOT NULL,
        -- <example>80952</example>
    duration INTEGER NOT NULL,
        -- <example>24</example>
    payments REAL NOT NULL,
        -- <example>3373.000</example>
    status TEXT NOT NULL,
        -- <values>{'A', 'B', 'C', 'D'}</values>
    FOREIGN KEY (account_id) REFERENCES account(account_id)
);

-- Table: order (6471 rows)
CREATE TABLE order (
    order_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>29401</example>
    account_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> account.account_id</fk>
    bank_to TEXT NOT NULL,
        -- <values>{'AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST', 'UV', 'WX', 'YZ'}</values>
    account_to INTEGER NOT NULL,
        -- <example>87144583</example>
    amount REAL NOT NULL,
        -- <example>2452.000</example>
    k_symbol TEXT NOT NULL,
        -- <values>{'', 'LEASING', 'POJISTNE', 'SIPO', 'UVER'}</values>
    FOREIGN KEY (account_id) REFERENCES account(account_id)
);

-- Table: trans (1056320 rows)
CREATE TABLE trans (
    trans_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    account_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> account.account_id</fk>
    date DATE NOT NULL,
        -- <example>'1995-03-24'</example>
    type TEXT NOT NULL,
        -- <values>{'PRIJEM', 'VYBER', 'VYDAJ'}</values>
    operation TEXT NULL,
        -- <values>{'PREVOD NA UCET', 'PREVOD Z UCTU', 'VKLAD', 'VYBER KARTOU', 'VYBER'}</values>
    amount INTEGER NOT NULL,
        -- <example>1000</example>
    balance INTEGER NOT NULL,
        -- <example>1000</example>
    k_symbol TEXT NULL,
        -- <values>{' ', 'DUCHOD', 'POJISTNE', 'SANKC. UROK', 'SIPO', 'SLUZBY', 'UROK', 'UVER'}</values>
    bank TEXT NULL,
        -- <values>{'AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST', 'UV', 'WX', 'YZ'}</values>
    account INTEGER NULL,
        -- <example>41403269</example>
    FOREIGN KEY (account_id) REFERENCES account(account_id)
);
```