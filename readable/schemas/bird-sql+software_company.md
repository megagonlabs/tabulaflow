```sql
-- Database: software_company

/*
Schema: NULLTable: Customers
Rows: 360000
Sample rows:
| ID   | SEX    | MARITAL_STATUS     | GEOID   | EDUCATIONNUM   | OCCUPATION        | age   |
|------|--------|--------------------|---------|----------------|-------------------|-------|
| 0    | Male   | Never-married      | 61      | 7              | Machine-op-inspct | 62    |
| 1    | Male   | Married-civ-spouse | 70      | 3              | Handlers-cleaners | 78    |
| 2    | Male   | Never-married      | 53      | 7              | Machine-op-inspct | 69    |
| 3    | Female | Divorced           | 79      | 4              | Exec-managerial   | 53    |
| 4    | Male   | Married-civ-spouse | 46      | 4              | Handlers-cleaners | 85    |
| ...  | ...    | ...                | ...     | ...            | ...               | ...   |
*/
CREATE TABLE Customers (
    ID INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    SEX TEXT NOT NULL,
        -- <values>{'Female', 'Male'}</values>
    MARITAL_STATUS TEXT NOT NULL,
        -- <values>{'Divorced', 'Married-civ-spouse', 'Never-married', 'Other', 'Widowed'}</values>
    GEOID INTEGER NOT NULL,
        -- <example>61</example>
        -- <fk> -> Demog.GEOID</fk>
    EDUCATIONNUM INTEGER NOT NULL,
        -- <example>7</example>
    OCCUPATION TEXT NOT NULL,
        -- <values>{'Adm-clerical', 'Craft-repair', 'Exec-managerial', 'Farming-fishing', 'Handlers-cleaners', 'Machine-op-inspct', 'Other-service', 'Prof-specialty', 'Sales'}</values>
    age INTEGER NOT NULL,
        -- <example>62</example>
    FOREIGN KEY (GEOID) REFERENCES Demog(GEOID)
);

/*
Schema: NULLTable: Demog
Rows: 200
Sample rows:
| GEOID   | INHABITANTS_K   | INCOME_K   | A_VAR1   | A_VAR2   | A_VAR3   | A_VAR4   | A_VAR5   | A_VAR6   | A_VAR7   | A_VAR8   | A_VAR9   | A_VAR10   | A_VAR11   | A_VAR12   | A_VAR13   | A_VAR14   | A_VAR15   | A_VAR16   | A_VAR17   | A_VAR18   |
|---------|-----------------|------------|----------|----------|----------|----------|----------|----------|----------|----------|----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| 0       | 30.046          | 2631.47    | 6.084    | 5.79     | 8.595    | 3.935    | 6.362    | 8.626    | 4.624    | 8.324    | 5.233    | 6.232     | 5.205     | 8.231     | 6.746     | 8.679     | 5.292     | 3.5       | 5.512     | 5.783     |
| 1       | 36.25           | 3012.75    | 4.604    | 8.309    | 6.007    | 5.938    | 8.773    | 3.579    | 6.349    | 4.694    | 6.884    | 7.062     | 7.319     | 3.72      | 6.405     | 7.202     | 4.932     | 7.969     | 8.15      | 5.633     |
| 2       | 47.645          | 2192.41    | 4.911    | 8.557    | 5.934    | 6.494    | 9.172    | 3.202    | 6.157    | 4.822    | 7.942    | 7.901     | 7.928     | 2.33      | 6.029     | 6.455     | 4.72      | 8.564     | 8.342     | 4.938     |
| 3       | 15.417          | 2343.51    | 6.2      | 5.623    | 8.55     | 3.959    | 6.52     | 8.089    | 4.32     | 8.694    | 5.217    | 6.627     | 5.493     | 8.73      | 6.713     | 8.851     | 5.198     | 3.313     | 5.076     | 5.796     |
| 4       | 18.104          | 2694.33    | 2.867    | 4.155    | 5.951    | 6.765    | 7.846    | 5.578    | 2.41     | 8.007    | 6.703    | 7.467     | 3.827     | 7.153     | 7.105     | 8.161     | 6.535     | 6.093     | 7.246     | 8.433     |
| ...     | ...             | ...        | ...      | ...      | ...      | ...      | ...      | ...      | ...      | ...      | ...      | ...       | ...       | ...       | ...       | ...       | ...       | ...       | ...       | ...       |
*/
CREATE TABLE Demog (
    GEOID INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    INHABITANTS_K REAL NOT NULL,
        -- <example>30.046</example>
    INCOME_K REAL NOT NULL,
        -- <example>2631.470</example>
    A_VAR1 REAL NOT NULL,
        -- <example>6.084</example>
    A_VAR2 REAL NOT NULL,
        -- <example>5.790</example>
    A_VAR3 REAL NOT NULL,
        -- <example>8.595</example>
    A_VAR4 REAL NOT NULL,
        -- <example>3.935</example>
    A_VAR5 REAL NOT NULL,
        -- <example>6.362</example>
    A_VAR6 REAL NOT NULL,
        -- <example>8.626</example>
    A_VAR7 REAL NOT NULL,
        -- <example>4.624</example>
    A_VAR8 REAL NOT NULL,
        -- <example>8.324</example>
    A_VAR9 REAL NOT NULL,
        -- <example>5.233</example>
    A_VAR10 REAL NOT NULL,
        -- <example>6.232</example>
    A_VAR11 REAL NOT NULL,
        -- <example>5.205</example>
    A_VAR12 REAL NOT NULL,
        -- <example>8.231</example>
    A_VAR13 REAL NOT NULL,
        -- <example>6.746</example>
    A_VAR14 REAL NOT NULL,
        -- <example>8.679</example>
    A_VAR15 REAL NOT NULL,
        -- <example>5.292</example>
    A_VAR16 REAL NOT NULL,
        -- <example>3.500</example>
    A_VAR17 REAL NOT NULL,
        -- <example>5.512</example>
    A_VAR18 REAL NOT NULL
        -- <example>5.783</example>
);

/*
Schema: NULLTable: Mailings1_2
Rows: 60000
Sample rows:
| REFID   | REF_DATE              | RESPONSE   |
|---------|-----------------------|------------|
| 0       | 2007-02-01 12:00:00.0 | false      |
| 1       | 2007-02-01 12:00:00.0 | false      |
| 2       | 2007-02-01 12:00:00.0 | false      |
| 3       | 2007-02-01 12:00:00.0 | true       |
| 4       | 2007-02-01 12:00:00.0 | false      |
| ...     | ...                   | ...        |
*/
CREATE TABLE Mailings1_2 (
    REFID INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
        -- <fk> -> Customers.ID</fk>
    REF_DATE DATETIME NOT NULL,
        -- <example>'2007-02-01 12:00:00.0'</example>
    RESPONSE TEXT NOT NULL,
        -- <values>{'false', 'true'}</values>
    FOREIGN KEY (REFID) REFERENCES Customers(ID)
);

/*
Schema: NULLTable: Sales
Rows: 3420829
Sample rows:
| EVENTID   | REFID   | EVENT_DATE            | AMOUNT   |
|-----------|---------|-----------------------|----------|
| 0         | 0       | 2006-12-21 12:00:00.0 | 17.907   |
| 1         | 0       | 2006-12-25 12:00:00.0 | 17.401   |
| 2         | 0       | 2007-01-26 12:00:00.0 | 13.277   |
| 3         | 0       | 2006-12-26 12:00:00.0 | 13.197   |
| 4         | 0       | 2007-01-17 12:00:00.0 | 15.001   |
| ...       | ...     | ...                   | ...      |
*/
CREATE TABLE Sales (
    EVENTID INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    REFID INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> Customers.ID</fk>
    EVENT_DATE DATETIME NOT NULL,
        -- <example>'2006-12-21 12:00:00.0'</example>
    AMOUNT REAL NOT NULL,
        -- <example>17.907</example>
    FOREIGN KEY (REFID) REFERENCES Customers(ID)
);

/*
Schema: NULLTable: mailings3
Rows: 300000
Sample rows:
| REFID   | REF_DATE              | RESPONSE   |
|---------|-----------------------|------------|
| 60000   | 2007-07-01 12:00:00.0 | false      |
| 60001   | 2007-07-01 12:00:00.0 | false      |
| 60002   | 2007-07-01 12:00:00.0 | false      |
| 60003   | 2007-07-01 12:00:00.0 | false      |
| 60004   | 2007-07-01 12:00:00.0 | false      |
| ...     | ...                   | ...        |
*/
CREATE TABLE mailings3 (
    REFID INTEGER NOT NULL PRIMARY KEY,
        -- <example>60000</example>
    REF_DATE DATETIME NOT NULL,
        -- <example>'2007-07-01 12:00:00.0'</example>
    RESPONSE TEXT NOT NULL
        -- <values>{'false', 'true'}</values>
);
```