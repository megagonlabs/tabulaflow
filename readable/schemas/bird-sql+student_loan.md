```sql
-- Database: student_loan

-- Table: bool (2 rows)
CREATE TABLE bool (
    name TEXT NOT NULL PRIMARY KEY
        -- <values>{'neg', 'pos'}</values>
);

-- Table: disabled (95 rows)
CREATE TABLE disabled (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student114'</example>
        -- <fk> -> person.name</fk>
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: enlist (306 rows)
CREATE TABLE enlist (
    name TEXT NOT NULL,
        -- <example>'student40'</example>
        -- <fk> -> person.name</fk>
    organ TEXT NOT NULL,
        -- <values>{'air_force', 'army', 'fire_department', 'foreign_legion', 'marines', 'navy', 'peace_corps'}</values>
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: enrolled (1194 rows)
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

-- Table: filed_for_bankrupcy (96 rows)
CREATE TABLE filed_for_bankrupcy (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student122'</example>
        -- <fk> -> person.name</fk>
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: longest_absense_from_school (1000 rows)
CREATE TABLE longest_absense_from_school (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student1'</example>
        -- <fk> -> person.name</fk>
    month INTEGER NULL,
        -- <example>0</example>
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: male (497 rows)
CREATE TABLE male (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student1'</example>
        -- <fk> -> person.name</fk>
    FOREIGN KEY (name) REFERENCES person(name)
);

-- Table: no_payment_due (1000 rows)
CREATE TABLE no_payment_due (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student1'</example>
        -- <fk> -> person.name</fk>
    bool TEXT NULL,
        -- <values>{'neg', 'pos'}</values>
        -- <fk> -> bool.name</fk>
    FOREIGN KEY (name) REFERENCES person(name),
    FOREIGN KEY (bool) REFERENCES bool(name)
);

-- Table: person (1000 rows)
CREATE TABLE person (
    name TEXT NOT NULL PRIMARY KEY
        -- <example>'student1'</example>
);

-- Table: unemployed (98 rows)
CREATE TABLE unemployed (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'student1000'</example>
        -- <fk> -> person.name</fk>
    FOREIGN KEY (name) REFERENCES person(name)
);
```