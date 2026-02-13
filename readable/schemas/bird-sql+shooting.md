```sql
-- Database: shooting

/*
Table: incidents
Rows: 219
Sample rows:
| case_number   | date       | location                    | subject_statuses   | subject_weapon   | subjects                   | subject_count   | officers             |
|---------------|------------|-----------------------------|--------------------|------------------|----------------------------|-----------------|----------------------|
| 031347-2015   | 2015/2/9   | 7400 Bonnie View Road       | Deceased           | Vehicle          | Luster, Desmond Dwayne B/M | 1               | Tollerton, Aaron W/M |
| 072458-2016   | 2016/3/26  | 8218 Willoughby Boulevard   | Shoot and Miss     | Shotgun          | Gilstrap, Bryan B/M        | 1               | Cardenas, Steven L/M |
| 089985-2016   | 2016/4/16  | 4800 Columbia Ave           | Shoot and Miss     | Handgun          | Unknown L/M                | 1               | Ruben, Fredirick W/M |
| 1004453N      | 2004/12/29 | 2400 Walnut Hill Lane       | Shoot and Miss     | Vehicle          | Evans, Jerry W/M           | 1               | Nguyen, Buu A/M      |
| 100577T       | 2007/2/12  | 3847 Timberglen Road, #3116 | Deceased           | Handgun          | Mims, Carlton B/M          | 1               | Ragsdale, Barry W/M  |
| ...           | ...        | ...                         | ...                | ...              | ...                        | ...             | ...                  |
*/
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

/*
Table: officers
Rows: 370
Sample rows:
| case_number   | race   | gender   | last_name   | first_name   | full_name        |
|---------------|--------|----------|-------------|--------------|------------------|
| 44523A        | L      | M        | Patino      | Michael      | Patino, Michael  |
| 44523A        | W      | M        | Fillingim   | Brian        | Fillingim, Brian |
| 121982X       | L      | M        | Padilla     | Gilbert      | Padilla, Gilbert |
| 605484T       | W      | M        | Poston      | Jerry        | Poston, Jerry    |
| 384832T       | B      | M        | Mondy       | Michael      | Mondy, Michael   |
| ...           | ...    | ...      | ...         | ...          | ...              |
*/
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

/*
Table: subjects
Rows: 223
Sample rows:
| case_number   | race   | gender   | last_name   | first_name   | full_name       |
|---------------|--------|----------|-------------|--------------|-----------------|
| 44523A        | L      | M        | Curry       | James        | Curry, James    |
| 121982X       | L      | M        | Chavez      | Gabriel      | Chavez, Gabriel |
| 605484T       | L      | M        | Salinas     | Nick         | Salinas, Nick   |
| 384832T       | B      | M        | Smith       | James        | Smith, James    |
| 384832T       | B      | M        | Dews        | Antonio      | Dews, Antonio   |
| ...           | ...    | ...      | ...         | ...          | ...             |
*/
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