```sql
-- Database: software_company

-- Table: Customers (360000 rows)
CREATE TABLE Customers (
    ID INTEGER PRIMARY KEY,  -- e.g. 0
    SEX TEXT,  -- values: {'Female', 'Male'}
    MARITAL_STATUS TEXT,  -- values: {'Divorced', 'Married-civ-spouse', 'Never-married', 'Other', 'Widowed'}
    GEOID INTEGER,  -- e.g. 61; FK -> Demog.GEOID
    EDUCATIONNUM INTEGER,  -- e.g. 7
    OCCUPATION TEXT,  -- values: {'Adm-clerical', 'Craft-repair', 'Exec-managerial', 'Farming-fishing', 'Handlers-cleaners', 'Machine-op-inspct', 'Other-service', 'Prof-specialty', 'Sales'}
    age INTEGER,  -- e.g. 62
    FOREIGN KEY (GEOID) REFERENCES Demog(GEOID)
);

-- Table: Demog (200 rows)
CREATE TABLE Demog (
    GEOID INTEGER PRIMARY KEY,  -- e.g. 0
    INHABITANTS_K REAL,  -- e.g. 30.046
    INCOME_K REAL,  -- e.g. 2631.470
    A_VAR1 REAL,  -- e.g. 6.084
    A_VAR2 REAL,  -- e.g. 5.790
    A_VAR3 REAL,  -- e.g. 8.595
    A_VAR4 REAL,  -- e.g. 3.935
    A_VAR5 REAL,  -- e.g. 6.362
    A_VAR6 REAL,  -- e.g. 8.626
    A_VAR7 REAL,  -- e.g. 4.624
    A_VAR8 REAL,  -- e.g. 8.324
    A_VAR9 REAL,  -- e.g. 5.233
    A_VAR10 REAL,  -- e.g. 6.232
    A_VAR11 REAL,  -- e.g. 5.205
    A_VAR12 REAL,  -- e.g. 8.231
    A_VAR13 REAL,  -- e.g. 6.746
    A_VAR14 REAL,  -- e.g. 8.679
    A_VAR15 REAL,  -- e.g. 5.292
    A_VAR16 REAL,  -- e.g. 3.500
    A_VAR17 REAL,  -- e.g. 5.512
    A_VAR18 REAL  -- e.g. 5.783
);

-- Table: Mailings1_2 (60000 rows)
CREATE TABLE Mailings1_2 (
    REFID INTEGER PRIMARY KEY,  -- e.g. 0; FK -> Customers.ID
    REF_DATE DATETIME,  -- e.g. '2007-02-01 12:00:00.0'
    RESPONSE TEXT,  -- values: {'false', 'true'}
    FOREIGN KEY (REFID) REFERENCES Customers(ID)
);

-- Table: Sales (3420829 rows)
CREATE TABLE Sales (
    EVENTID INTEGER PRIMARY KEY,  -- e.g. 0
    REFID INTEGER,  -- e.g. 0; FK -> Customers.ID
    EVENT_DATE DATETIME,  -- e.g. '2006-12-21 12:00:00.0'
    AMOUNT REAL,  -- e.g. 17.907
    FOREIGN KEY (REFID) REFERENCES Customers(ID)
);

-- Table: mailings3 (300000 rows)
CREATE TABLE mailings3 (
    REFID INTEGER PRIMARY KEY,  -- e.g. 60000
    REF_DATE DATETIME,  -- e.g. '2007-07-01 12:00:00.0'
    RESPONSE TEXT  -- values: {'false', 'true'}
);
```