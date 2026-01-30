```sql
-- Database: shooting

-- Table: incidents (219 rows)
CREATE TABLE incidents (
    case_number TEXT NOT NULL PRIMARY KEY,  -- e.g. '031347-2015'
    date DATE NOT NULL,  -- e.g. '2015/2/9'
    location TEXT NOT NULL,  -- e.g. '7400 Bonnie View Road'
    subject_statuses TEXT NOT NULL,  -- values: {'1 Deceased 1 Injured', '2 Injured', 'Deceased Injured', 'Deceased', 'Injured', 'Other', 'Shoot and Miss'}
    subject_weapon TEXT NOT NULL,  -- e.g. 'Vehicle'
    subjects TEXT NOT NULL,  -- e.g. 'Luster, Desmond Dwayne B/M'
    subject_count INTEGER NOT NULL,  -- e.g. 1
    officers TEXT NOT NULL  -- e.g. 'Tollerton, Aaron W/M'
);

-- Table: officers (370 rows)
CREATE TABLE officers (
    case_number TEXT NOT NULL,  -- e.g. '44523A'; FK -> incidents.case_number
    race TEXT,  -- values: {'A', 'B', 'L', 'W'}
    gender TEXT NOT NULL,  -- values: {'F', 'M'}
    last_name TEXT NOT NULL,  -- e.g. 'Patino'
    first_name TEXT,  -- e.g. 'Michael'
    full_name TEXT NOT NULL,  -- e.g. 'Patino, Michael'
    FOREIGN KEY (case_number) REFERENCES incidents(case_number)
);

-- Table: subjects (223 rows)
CREATE TABLE subjects (
    case_number TEXT NOT NULL,  -- e.g. '44523A'; FK -> incidents.case_number
    race TEXT NOT NULL,  -- values: {'A', 'B', 'L', 'W'}
    gender TEXT NOT NULL,  -- values: {'F', 'M'}
    last_name TEXT NOT NULL,  -- e.g. 'Curry'
    first_name TEXT,  -- e.g. 'James'
    full_name TEXT NOT NULL,  -- e.g. 'Curry, James'
    FOREIGN KEY (case_number) REFERENCES incidents(case_number)
);
```