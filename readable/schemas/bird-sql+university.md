```sql
-- Database: university

/*
Schema: NULLTable: country
Rows: 74
Sample rows:
| id   | country_name   |
|------|----------------|
| 1    | Argentina      |
| 2    | Australia      |
| 3    | Austria        |
| 4    | Bangladesh     |
| 5    | Belarus        |
| ...  | ...            |
*/
CREATE TABLE country (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    country_name TEXT NOT NULL
        -- <example>'Argentina'</example>
);

/*
Schema: NULLTable: ranking_criteria
Rows: 21
Sample rows:
| id   | ranking_system_id   | criteria_name   |
|------|---------------------|-----------------|
| 1    | 1                   | Teaching        |
| 2    | 1                   | International   |
| 3    | 1                   | Research        |
| 4    | 1                   | Citations       |
| 5    | 1                   | Income          |
| ...  | ...                 | ...             |
*/
CREATE TABLE ranking_criteria (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    ranking_system_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ranking_system.id</fk>
    criteria_name TEXT NOT NULL,
        -- <example>'Teaching'</example>
    FOREIGN KEY (ranking_system_id) REFERENCES ranking_system(id)
);

/*
Schema: NULLTable: ranking_system
Rows: 3
All rows:
|   id | system_name                                     |
|------|-------------------------------------------------|
|    1 | Times Higher Education World University Ranking |
|    2 | Shanghai Ranking                                |
|    3 | Center for World University Rankings            |
*/
CREATE TABLE ranking_system (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    system_name TEXT NOT NULL
        -- <values>{'Center for World University Rankings', 'Shanghai Ranking', 'Times Higher Education World University Ranking'}</values>
);

/*
Schema: NULLTable: university
Rows: 1247
Sample rows:
| id   | country_id   | university_name                       |
|------|--------------|---------------------------------------|
| 1    | 73           | Harvard University                    |
| 2    | 73           | Massachusetts Institute of Technology |
| 3    | 73           | Stanford University                   |
| 4    | 72           | University of Cambridge               |
| 5    | 73           | California Institute of Technology    |
| ...  | ...          | ...                                   |
*/
CREATE TABLE university (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    country_id INTEGER NOT NULL,
        -- <example>73</example>
        -- <fk> -> country.id</fk>
    university_name TEXT NOT NULL,
        -- <example>'Harvard University'</example>
    FOREIGN KEY (country_id) REFERENCES country(id)
);

/*
Schema: NULLTable: university_ranking_year
Rows: 29612
Sample rows:
| university_id   | ranking_criteria_id   | year   | score   |
|-----------------|-----------------------|--------|---------|
| 1               | 1                     | 2011   | 100     |
| 5               | 1                     | 2011   | 98      |
| 2               | 1                     | 2011   | 98      |
| 3               | 1                     | 2011   | 98      |
| 6               | 1                     | 2011   | 91      |
| ...             | ...                   | ...    | ...     |
*/
CREATE TABLE university_ranking_year (
    university_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> university.id</fk>
    ranking_criteria_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> ranking_criteria.id</fk>
    year INTEGER NOT NULL,
        -- <example>2011</example>
    score INTEGER NULL,
        -- <example>100</example>
    FOREIGN KEY (ranking_criteria_id) REFERENCES ranking_criteria(id),
    FOREIGN KEY (university_id) REFERENCES university(id)
);

/*
Schema: NULLTable: university_year
Rows: 1085
Sample rows:
| university_id   | year   | num_students   | student_staff_ratio   | pct_international_students   | pct_female_students   |
|-----------------|--------|----------------|-----------------------|------------------------------|-----------------------|
| 1               | 2011   | 20152          | 8.9                   | 25                           | [NULL]                |
| 5               | 2011   | 2243           | 6.9                   | 27                           | 33.0                  |
| 2               | 2011   | 11074          | 9.0                   | 33                           | 37.0                  |
| 3               | 2011   | 15596          | 7.8                   | 22                           | 42.0                  |
| 6               | 2011   | 7929           | 8.4                   | 27                           | 45.0                  |
| ...             | ...    | ...            | ...                   | ...                          | ...                   |
*/
CREATE TABLE university_year (
    university_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> university.id</fk>
    year INTEGER NOT NULL,
        -- <example>2011</example>
    num_students INTEGER NOT NULL,
        -- <example>20152</example>
    student_staff_ratio REAL NOT NULL,
        -- <example>8.900</example>
    pct_international_students INTEGER NOT NULL,
        -- <example>25</example>
    pct_female_students INTEGER NULL,
        -- <example>33</example>
    FOREIGN KEY (university_id) REFERENCES university(id)
);
```