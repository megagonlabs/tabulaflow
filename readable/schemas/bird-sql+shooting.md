```sql
-- Database: shooting

-- Table: incidents (219 rows)
CREATE TABLE incidents (
    case_number TEXT NOT NULL PRIMARY KEY,
        -- <example>'031347-2015'</example>
    date DATE NOT NULL,
        -- <example>'2015/2/9'</example>
    location TEXT NOT NULL,
        -- <example>'7400 Bonnie View Road'</example>
    subject_statuses TEXT NOT NULL,
        -- <values>{'1 Deceased 1 Injured', '2 Injured', 'Deceased Injured', 'Deceased', 'Injured', 'Other', 'Shoot and Miss'}</values>
    subject_weapon TEXT NOT NULL,
        -- <example>'Vehicle'</example>
    subjects TEXT NOT NULL,
        -- <example>'Luster, Desmond Dwayne B/M'</example>
    subject_count INTEGER NOT NULL,
        -- <example>1</example>
    officers TEXT NOT NULL
        -- <example>'Tollerton, Aaron W/M'</example>
);

-- Table: officers (370 rows)
CREATE TABLE officers (
    case_number TEXT NOT NULL,
        -- <example>'44523A'</example>
        -- <fk> -> incidents.case_number</fk>
    race TEXT NULL,
        -- <values>{'A', 'B', 'L', 'W'}</values>
    gender TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    last_name TEXT NOT NULL,
        -- <example>'Patino'</example>
    first_name TEXT NULL,
        -- <example>'Michael'</example>
    full_name TEXT NOT NULL,
        -- <example>'Patino, Michael'</example>
    FOREIGN KEY (case_number) REFERENCES incidents(case_number)
);

-- Table: subjects (223 rows)
CREATE TABLE subjects (
    case_number TEXT NOT NULL,
        -- <example>'44523A'</example>
        -- <fk> -> incidents.case_number</fk>
    race TEXT NOT NULL,
        -- <values>{'A', 'B', 'L', 'W'}</values>
    gender TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    last_name TEXT NOT NULL,
        -- <example>'Curry'</example>
    first_name TEXT NULL,
        -- <example>'James'</example>
    full_name TEXT NOT NULL,
        -- <example>'Curry, James'</example>
    FOREIGN KEY (case_number) REFERENCES incidents(case_number)
);
```