```sql
-- Database: university

-- Table: country (74 rows)
CREATE TABLE country (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    country_name TEXT NULL
        -- <example>'Argentina'</example>
);

-- Table: ranking_criteria (21 rows)
CREATE TABLE ranking_criteria (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    ranking_system_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> ranking_system.id</fk>
    criteria_name TEXT NULL,
        -- <example>'Teaching'</example>
    FOREIGN KEY (ranking_system_id) REFERENCES ranking_system(id)
);

-- Table: ranking_system (3 rows)
CREATE TABLE ranking_system (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    system_name TEXT NULL
        -- <values>{'Center for World University Rankings', 'Shanghai Ranking', 'Times Higher Education World University Ranking'}</values>
);

-- Table: university (1247 rows)
CREATE TABLE university (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    country_id INTEGER NULL,
        -- <example>73</example>
        -- <fk> -> country.id</fk>
    university_name TEXT NULL,
        -- <example>'Harvard University'</example>
    FOREIGN KEY (country_id) REFERENCES country(id)
);

-- Table: university_ranking_year (29612 rows)
CREATE TABLE university_ranking_year (
    university_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> university.id</fk>
    ranking_criteria_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> ranking_criteria.id</fk>
    year INTEGER NULL,
        -- <example>2011</example>
    score INTEGER NULL,
        -- <example>100</example>
    FOREIGN KEY (ranking_criteria_id) REFERENCES ranking_criteria(id),
    FOREIGN KEY (university_id) REFERENCES university(id)
);

-- Table: university_year (1085 rows)
CREATE TABLE university_year (
    university_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> university.id</fk>
    year INTEGER NULL,
        -- <example>2011</example>
    num_students INTEGER NULL,
        -- <example>20152</example>
    student_staff_ratio REAL NULL,
        -- <example>8.900</example>
    pct_international_students INTEGER NULL,
        -- <example>25</example>
    pct_female_students INTEGER NULL,
        -- <example>33</example>
    FOREIGN KEY (university_id) REFERENCES university(id)
);
```