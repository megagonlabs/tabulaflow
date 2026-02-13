```sql
-- Database: student_loan

/*
Table: bool
Rows: 2
All rows:
| name   |
|--------|
| neg    |
| pos    |
*/
CREATE TABLE bool (
    name TEXT NOT NULL PRIMARY KEY
        -- <values>{'neg', 'pos'}</values>
);

/*
Table: disabled
Rows: 95
Sample rows:
| name       |
|------------|
| student114 |
| student125 |
| student142 |
| student155 |
| student156 |
| ...        |
*/
CREATE TABLE disabled (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student114'</example>
        -- <fk> -> person.name</fk>
    FOREIGN KEY (name) REFERENCES person(name)
);

/*
Table: enlist
Rows: 306
Sample rows:
| name       | organ           |
|------------|-----------------|
| student40  | fire_department |
| student51  | fire_department |
| student109 | fire_department |
| student139 | fire_department |
| student148 | fire_department |
| ...        | ...             |
*/
CREATE TABLE enlist (
    name TEXT NOT NULL,
        -- <example>'student40'</example>
        -- <fk> -> person.name</fk>
    organ TEXT NOT NULL,
        -- <values>{'air_force', 'army', 'fire_department', 'foreign_legion', 'marines', 'navy', 'peace_corps'}</values>
    FOREIGN KEY (name) REFERENCES person(name)
);

/*
Table: enrolled
Rows: 1194
Sample rows:
| name       | school   | month   |
|------------|----------|---------|
| student10  | smc      | 1       |
| student101 | ucb      | 1       |
| student122 | ucsd     | 1       |
| student154 | ucb      | 1       |
| student161 | ucsd     | 1       |
| ...        | ...      | ...     |
*/
CREATE TABLE enrolled (
    name TEXT NOT NULL,
        -- <example>'student1'</example>
        -- <fk> -> person.name</fk>
    school TEXT NOT NULL,
        -- <values>{'occ', 'smc', 'ucb', 'uci', 'ucla', 'ucsd'}</values>
    month INTEGER NOT NULL,
        -- <example>1</example>
    PRIMARY KEY (name, school),
    FOREIGN KEY (name) REFERENCES person(name)
);

/*
Table: filed_for_bankrupcy
Rows: 96
Sample rows:
| name       |
|------------|
| student122 |
| student126 |
| student136 |
| student145 |
| student148 |
| ...        |
*/
CREATE TABLE filed_for_bankrupcy (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student122'</example>
        -- <fk> -> person.name</fk>
    FOREIGN KEY (name) REFERENCES person(name)
);

/*
Table: longest_absense_from_school
Rows: 1000
Sample rows:
| name       | month   |
|------------|---------|
| student10  | 0       |
| student102 | 0       |
| student110 | 0       |
| student111 | 0       |
| student114 | 0       |
| ...        | ...     |
*/
CREATE TABLE longest_absense_from_school (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student1'</example>
        -- <fk> -> person.name</fk>
    month INTEGER NOT NULL,
        -- <example>0</example>
    FOREIGN KEY (name) REFERENCES person(name)
);

/*
Table: male
Rows: 497
Sample rows:
| name       |
|------------|
| student1   |
| student101 |
| student102 |
| student103 |
| student105 |
| ...        |
*/
CREATE TABLE male (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student1'</example>
        -- <fk> -> person.name</fk>
    FOREIGN KEY (name) REFERENCES person(name)
);

/*
Table: no_payment_due
Rows: 1000
Sample rows:
| name       | bool   |
|------------|--------|
| student10  | neg    |
| student101 | neg    |
| student103 | neg    |
| student107 | neg    |
| student110 | neg    |
| ...        | ...    |
*/
CREATE TABLE no_payment_due (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student1'</example>
        -- <fk> -> person.name</fk>
    bool TEXT NOT NULL,
        -- <values>{'neg', 'pos'}</values>
        -- <fk> -> bool.name</fk>
    FOREIGN KEY (name) REFERENCES person(name),
    FOREIGN KEY (bool) REFERENCES bool(name)
);

/*
Table: person
Rows: 1000
Sample rows:
| name        |
|-------------|
| student1    |
| student10   |
| student100  |
| student1000 |
| student101  |
| ...         |
*/
CREATE TABLE person (
    name TEXT NOT NULL PRIMARY KEY
        -- <example>'student1'</example>
);

/*
Table: unemployed
Rows: 98
Sample rows:
| name        |
|-------------|
| student1000 |
| student102  |
| student106  |
| student109  |
| student118  |
| ...         |
*/
CREATE TABLE unemployed (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student1000'</example>
        -- <fk> -> person.name</fk>
    FOREIGN KEY (name) REFERENCES person(name)
);
```