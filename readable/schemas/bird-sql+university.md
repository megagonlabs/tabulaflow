```sql
-- Database: university

-- Table: country (74 rows)
CREATE TABLE country (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    country_name TEXT  -- e.g. 'Argentina'
);

-- Table: ranking_criteria (21 rows)
CREATE TABLE ranking_criteria (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    ranking_system_id INTEGER,  -- e.g. 1; FK -> ranking_system.id
    criteria_name TEXT,  -- e.g. 'Teaching'
    FOREIGN KEY (ranking_system_id) REFERENCES ranking_system(id)
);

-- Table: ranking_system (3 rows)
CREATE TABLE ranking_system (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    system_name TEXT  -- values: {'Center for World University Rankings', 'Shanghai Ranking', 'Times Higher Education World University Ranking'}
);

-- Table: university (1247 rows)
CREATE TABLE university (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    country_id INTEGER,  -- e.g. 73; FK -> country.id
    university_name TEXT,  -- e.g. 'Harvard University'
    FOREIGN KEY (country_id) REFERENCES country(id)
);

-- Table: university_ranking_year (29612 rows)
CREATE TABLE university_ranking_year (
    university_id INTEGER,  -- e.g. 1; FK -> university.id
    ranking_criteria_id INTEGER,  -- e.g. 1; FK -> ranking_criteria.id
    year INTEGER,  -- e.g. 2011
    score INTEGER,  -- e.g. 100
    FOREIGN KEY (ranking_criteria_id) REFERENCES ranking_criteria(id),
    FOREIGN KEY (university_id) REFERENCES university(id)
);

-- Table: university_year (1085 rows)
CREATE TABLE university_year (
    university_id INTEGER,  -- e.g. 1; FK -> university.id
    year INTEGER,  -- e.g. 2011
    num_students INTEGER,  -- e.g. 20152
    student_staff_ratio REAL,  -- e.g. 8.900
    pct_international_students INTEGER,  -- e.g. 25
    pct_female_students INTEGER,  -- e.g. 33
    FOREIGN KEY (university_id) REFERENCES university(id)
);
```