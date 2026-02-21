```sql
-- Database: financial

/*
Schema: NULL
Table: ACCOUNT
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
CREATE TABLE ACCOUNT (
    "ACCOUNT_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "DISTRICT_ID" INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> DISTRICT."DISTRICT_ID"</fk>
    "FREQUENCY" TEXT NOT NULL,
        -- <values>{'POPLATEK MESICNE', 'POPLATEK PO OBRATU', 'POPLATEK TYDNE'}</values>
    "DATE" DATE NOT NULL,
        -- <example>'1995-03-24'</example>
    FOREIGN KEY ("DISTRICT_ID") REFERENCES DISTRICT("DISTRICT_ID")
);

/*
Schema: NULL
Table: CARD
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
CREATE TABLE CARD (
    "CARD_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "DISP_ID" INTEGER NOT NULL,
        -- <example>9</example>
        -- <fk> -> DISP."DISP_ID"</fk>
    "TYPE" TEXT NOT NULL,
        -- <values>{'classic', 'gold', 'junior'}</values>
    "ISSUED" DATE NOT NULL,
        -- <example>'1998-10-16'</example>
    FOREIGN KEY ("DISP_ID") REFERENCES DISP("DISP_ID")
);

/*
Schema: NULL
Table: CLIENT
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
CREATE TABLE CLIENT (
    "CLIENT_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "GENDER" TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    "BIRTH_DATE" DATE NOT NULL,
        -- <example>'1970-12-13'</example>
    "DISTRICT_ID" INTEGER NOT NULL,
        -- <example>18</example>
        -- <fk> -> DISTRICT."DISTRICT_ID"</fk>
    FOREIGN KEY ("DISTRICT_ID") REFERENCES DISTRICT("DISTRICT_ID")
);

/*
Schema: NULL
Table: DISP
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
CREATE TABLE DISP (
    "DISP_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "CLIENT_ID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> CLIENT."CLIENT_ID"</fk>
    "ACCOUNT_ID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ACCOUNT."ACCOUNT_ID"</fk>
    "TYPE" TEXT NOT NULL,
        -- <values>{'DISPONENT', 'OWNER'}</values>
    FOREIGN KEY ("ACCOUNT_ID") REFERENCES ACCOUNT("ACCOUNT_ID"),
    FOREIGN KEY ("CLIENT_ID") REFERENCES CLIENT("CLIENT_ID")
);

/*
Schema: NULL
Table: DISTRICT
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
CREATE TABLE DISTRICT (
    "DISTRICT_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "A2" TEXT NOT NULL,
        -- <example>'Hl.m. Praha'</example>
    "A3" TEXT NOT NULL,
        -- <values>{'Prague', 'central Bohemia', 'east Bohemia', 'north Bohemia', 'north Moravia', 'south Bohemia', 'south Moravia', 'west Bohemia'}</values>
    "A4" TEXT NOT NULL,
        -- <example>'1204953'</example>
    "A5" TEXT NOT NULL,
        -- <example>'0'</example>
    "A6" TEXT NOT NULL,
        -- <example>'0'</example>
    "A7" TEXT NOT NULL,
        -- <example>'0'</example>
    "A8" INTEGER NOT NULL,
        -- <example>1</example>
    "A9" INTEGER NOT NULL,
        -- <example>1</example>
    "A10" REAL NOT NULL,
        -- <example>100.000</example>
    "A11" INTEGER NOT NULL,
        -- <example>12541</example>
    "A12" REAL NULL,
        -- <example>0.200</example>
    "A13" REAL NOT NULL,
        -- <example>0.430</example>
    "A14" INTEGER NOT NULL,
        -- <example>167</example>
    "A15" INTEGER NULL,
        -- <example>85677</example>
    "A16" INTEGER NOT NULL
        -- <example>99107</example>
);

/*
Schema: NULL
Table: LOAN
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
CREATE TABLE LOAN (
    "LOAN_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>4959</example>
    "ACCOUNT_ID" INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> ACCOUNT."ACCOUNT_ID"</fk>
    "DATE" DATE NOT NULL,
        -- <example>'1994-01-05'</example>
    "AMOUNT" INTEGER NOT NULL,
        -- <example>80952</example>
    "DURATION" INTEGER NOT NULL,
        -- <example>24</example>
    "PAYMENTS" REAL NOT NULL,
        -- <example>3373.000</example>
    "STATUS" TEXT NOT NULL,
        -- <values>{'A', 'B', 'C', 'D'}</values>
    FOREIGN KEY ("ACCOUNT_ID") REFERENCES ACCOUNT("ACCOUNT_ID")
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
    "ORDER_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>29401</example>
    "ACCOUNT_ID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ACCOUNT."ACCOUNT_ID"</fk>
    "BANK_TO" TEXT NOT NULL,
        -- <values>{'AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST', 'UV', 'WX', 'YZ'}</values>
    "ACCOUNT_TO" INTEGER NOT NULL,
        -- <example>87144583</example>
    "AMOUNT" REAL NOT NULL,
        -- <example>2452.000</example>
    "K_SYMBOL" TEXT NOT NULL,
        -- <values>{'', 'LEASING', 'POJISTNE', 'SIPO', 'UVER'}</values>
    FOREIGN KEY ("ACCOUNT_ID") REFERENCES ACCOUNT("ACCOUNT_ID")
);

/*
Schema: NULL
Table: TRANS
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
CREATE TABLE TRANS (
    "TRANS_ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "ACCOUNT_ID" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ACCOUNT."ACCOUNT_ID"</fk>
    "DATE" DATE NOT NULL,
        -- <example>'1995-03-24'</example>
    "TYPE" TEXT NOT NULL,
        -- <values>{'PRIJEM', 'VYBER', 'VYDAJ'}</values>
    "OPERATION" TEXT NULL,
        -- <values>{'PREVOD NA UCET', 'PREVOD Z UCTU', 'VKLAD', 'VYBER KARTOU', 'VYBER'}</values>
    "AMOUNT" INTEGER NOT NULL,
        -- <example>1000</example>
    "BALANCE" INTEGER NOT NULL,
        -- <example>1000</example>
    "K_SYMBOL" TEXT NULL,
        -- <values>{' ', 'DUCHOD', 'POJISTNE', 'SANKC. UROK', 'SIPO', 'SLUZBY', 'UROK', 'UVER'}</values>
    "BANK" TEXT NULL,
        -- <values>{'AB', 'CD', 'EF', 'GH', 'IJ', 'KL', 'MN', 'OP', 'QR', 'ST', 'UV', 'WX', 'YZ'}</values>
    "ACCOUNT" INTEGER NULL,
        -- <example>41403269</example>
    FOREIGN KEY ("ACCOUNT_ID") REFERENCES ACCOUNT("ACCOUNT_ID")
);
```