```sql
-- Database: student_loan

-- Table: bool (2 rows)
CREATE TABLE bool (
    name TEXT NOT NULL PRIMARY KEY  -- values: {'neg', 'pos'}
);

-- Table: disabled (95 rows)
CREATE TABLE disabled (
    name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'student114'; FK -> person.name
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: enlist (306 rows)
CREATE TABLE enlist (
    name TEXT NOT NULL,  -- e.g. 'student40'; FK -> person.name
    organ TEXT NOT NULL,  -- values: {'air_force', 'army', 'fire_department', 'foreign_legion', 'marines', 'navy', 'peace_corps'}
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: enrolled (1194 rows)
CREATE TABLE enrolled (
    name TEXT NOT NULL,  -- e.g. 'student1'; FK -> person.name
    school TEXT NOT NULL,  -- values: {'occ', 'smc', 'ucb', 'uci', 'ucla', 'ucsd'}
    month INTEGER NOT NULL,  -- e.g. 1
    PRIMARY KEY (name, school),
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: filed_for_bankrupcy (96 rows)
CREATE TABLE filed_for_bankrupcy (
    name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'student122'; FK -> person.name
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: longest_absense_from_school (1000 rows)
CREATE TABLE longest_absense_from_school (
    name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'student1'; FK -> person.name
    month INTEGER,  -- e.g. 0
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: male (497 rows)
CREATE TABLE male (
    name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'student1'; FK -> person.name
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: no_payment_due (1000 rows)
CREATE TABLE no_payment_due (
    name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'student1'; FK -> person.name
    bool TEXT,  -- values: {'neg', 'pos'}; FK -> bool.name
    FOREIGN KEY (name) REFERENCES person(name),
    FOREIGN KEY (bool) REFERENCES bool(name)
);

-- Table: person (1000 rows)
CREATE TABLE person (
    name TEXT NOT NULL PRIMARY KEY  -- e.g. 'student1'
);

-- Table: unemployed (98 rows)
CREATE TABLE unemployed (
    name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'student1000'; FK -> person.name
    FOREIGN KEY (name) REFERENCES person(name)
);
```