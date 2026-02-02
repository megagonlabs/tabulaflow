```sql
-- Database: software_company

-- Table: Customers (360000 rows)
CREATE TABLE Customers (
    ID INTEGER NULL PRIMARY KEY,
        -- <example>0</example>
    SEX TEXT NULL,
        -- <values>{'Female', 'Male'}</values>
    MARITAL_STATUS TEXT NULL,
        -- <values>{'Divorced', 'Married-civ-spouse', 'Never-married', 'Other', 'Widowed'}</values>
    GEOID INTEGER NULL,
        -- <example>61</example>
        -- <fk> -> Demog.GEOID</fk>
    EDUCATIONNUM INTEGER NULL,
        -- <example>7</example>
    OCCUPATION TEXT NULL,
        -- <values>{'Adm-clerical', 'Craft-repair', 'Exec-managerial', 'Farming-fishing', 'Handlers-cleaners', 'Machine-op-inspct', 'Other-service', 'Prof-specialty', 'Sales'}</values>
    age INTEGER NULL,
        -- <example>62</example>
    FOREIGN KEY (GEOID) REFERENCES Demog(GEOID)
);

-- Table: Demog (200 rows)
CREATE TABLE Demog (
    GEOID INTEGER NULL PRIMARY KEY,
        -- <example>0</example>
    INHABITANTS_K REAL NULL,
        -- <example>30.046</example>
    INCOME_K REAL NULL,
        -- <example>2631.470</example>
    A_VAR1 REAL NULL,
        -- <example>6.084</example>
    A_VAR2 REAL NULL,
        -- <example>5.790</example>
    A_VAR3 REAL NULL,
        -- <example>8.595</example>
    A_VAR4 REAL NULL,
        -- <example>3.935</example>
    A_VAR5 REAL NULL,
        -- <example>6.362</example>
    A_VAR6 REAL NULL,
        -- <example>8.626</example>
    A_VAR7 REAL NULL,
        -- <example>4.624</example>
    A_VAR8 REAL NULL,
        -- <example>8.324</example>
    A_VAR9 REAL NULL,
        -- <example>5.233</example>
    A_VAR10 REAL NULL,
        -- <example>6.232</example>
    A_VAR11 REAL NULL,
        -- <example>5.205</example>
    A_VAR12 REAL NULL,
        -- <example>8.231</example>
    A_VAR13 REAL NULL,
        -- <example>6.746</example>
    A_VAR14 REAL NULL,
        -- <example>8.679</example>
    A_VAR15 REAL NULL,
        -- <example>5.292</example>
    A_VAR16 REAL NULL,
        -- <example>3.500</example>
    A_VAR17 REAL NULL,
        -- <example>5.512</example>
    A_VAR18 REAL NULL
        -- <example>5.783</example>
);

-- Table: Mailings1_2 (60000 rows)
CREATE TABLE Mailings1_2 (
    REFID INTEGER NULL PRIMARY KEY,
        -- <example>0</example>
        -- <fk> -> Customers.ID</fk>
    REF_DATE DATETIME NULL,
        -- <example>'2007-02-01 12:00:00.0'</example>
    RESPONSE TEXT NULL,
        -- <values>{'false', 'true'}</values>
    FOREIGN KEY (REFID) REFERENCES Customers(ID)
);

-- Table: Sales (3420829 rows)
CREATE TABLE Sales (
    EVENTID INTEGER NULL PRIMARY KEY,
        -- <example>0</example>
    REFID INTEGER NULL,
        -- <example>0</example>
        -- <fk> -> Customers.ID</fk>
    EVENT_DATE DATETIME NULL,
        -- <example>'2006-12-21 12:00:00.0'</example>
    AMOUNT REAL NULL,
        -- <example>17.907</example>
    FOREIGN KEY (REFID) REFERENCES Customers(ID)
);

-- Table: mailings3 (300000 rows)
CREATE TABLE mailings3 (
    REFID INTEGER NULL PRIMARY KEY,
        -- <example>60000</example>
    REF_DATE DATETIME NULL,
        -- <example>'2007-07-01 12:00:00.0'</example>
    RESPONSE TEXT NULL
        -- <values>{'false', 'true'}</values>
);
```