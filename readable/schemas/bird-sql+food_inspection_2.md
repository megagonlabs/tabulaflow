```sql
-- Database: food_inspection_2

-- Table: employee (75 rows)
CREATE TABLE employee (
    employee_id INTEGER NULL PRIMARY KEY,
        -- <example>103705</example>
    first_name TEXT NULL,
        -- <example>'Anastasia'</example>
    last_name TEXT NULL,
        -- <example>'Hansen'</example>
    address TEXT NULL,
        -- <example>'6023 S Elizabeth St'</example>
    city TEXT NULL,
        -- <values>{'Chicago', 'Hoffman Estates', 'Park Forest'}</values>
    state TEXT NULL,
        -- <values>{'IL'}</values>
    zip INTEGER NULL,
        -- <example>60636</example>
    phone TEXT NULL,
        -- <example>'(773) 424-8729'</example>
    title TEXT NULL,
        -- <values>{'Division Manager', 'Sanitarian', 'Supervisor'}</values>
    salary INTEGER NULL,
        -- <example>79300</example>
    supervisor INTEGER NULL,
        -- <example>177316</example>
        -- <fk> -> employee.employee_id</fk>
    FOREIGN KEY (supervisor) REFERENCES employee(employee_id)
);

-- Table: establishment (31642 rows)
CREATE TABLE establishment (
    license_no INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    dba_name TEXT NULL,
        -- <example>'HARVEST CRUSADES MINISTRIES'</example>
    aka_name TEXT NULL,
        -- <example>'COSI'</example>
    facility_type TEXT NULL,
        -- <example>'Special Event'</example>
    risk_level INTEGER NULL,
        -- <example>2</example>
    address TEXT NULL,
        -- <example>'118 N CENTRAL AVE '</example>
    city TEXT NULL,
        -- <values>{'ALSIP  ', 'BERWYN ', 'BURNHAM', 'CHICAGO', 'CHicago', 'CICERO ', 'Chicago', 'GLENCOE', 'JUSTICE', 'LOMBARD', 'MAYWOOD', 'Maywood', 'SKOKIE ', 'SUMMIT ', 'WORTH  ', 'chicago'}</values>
    state TEXT NULL,
        -- <values>{'IL'}</values>
    zip INTEGER NULL,
        -- <example>60644</example>
    latitude REAL NULL,
        -- <example>41.883</example>
    longitude REAL NULL,
        -- <example>-87.765</example>
    ward INTEGER NULL
        -- <example>29</example>
);

-- Table: inspection (143870 rows)
CREATE TABLE inspection (
    inspection_id INTEGER NULL PRIMARY KEY,
        -- <example>44247</example>
    inspection_date DATE NULL,
        -- <example>'2010-01-05'</example>
    inspection_type TEXT NULL,
        -- <example>'Complaint'</example>
    results TEXT NULL,
        -- <values>{'Business Not Located', 'Fail', 'No Entry', 'Not Ready', 'Out of Business', 'Pass w/ Conditions', 'Pass'}</values>
    employee_id INTEGER NULL,
        -- <example>141319</example>
        -- <fk> -> employee.employee_id</fk>
    license_no INTEGER NULL,
        -- <example>1222441</example>
        -- <fk> -> establishment.license_no</fk>
    followup_to INTEGER NULL,
        -- <example>67871</example>
        -- <fk> -> inspection.inspection_id</fk>
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    FOREIGN KEY (license_no) REFERENCES establishment(license_no),
    FOREIGN KEY (followup_to) REFERENCES inspection(inspection_id)
);

-- Table: inspection_point (46 rows)
CREATE TABLE inspection_point (
    point_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Description TEXT NULL,
        -- <example>'Source sound condition, no spoilage, foods properly labeled, shellfish tags in place'</example>
    category TEXT NULL,
        -- <example>'Food Protection'</example>
    code TEXT NULL,
        -- <example>'7-38-005 (B) (B-2)'</example>
    fine INTEGER NULL,
        -- <example>500</example>
    point_level TEXT NULL
        -- <values>{'Critical', 'Minor   ', 'Serious '}</values>
);

-- Table: violation (525709 rows)
CREATE TABLE violation (
    inspection_id INTEGER NULL,
        -- <example>44247</example>
        -- <fk> -> inspection.inspection_id</fk>
    point_id INTEGER NULL,
        -- <example>30</example>
        -- <fk> -> inspection_point.point_id</fk>
    fine INTEGER NULL,
        -- <example>100</example>
    inspector_comment TEXT NULL,
        -- <example>'All food not stored in the original container shal...AND DATE.  MUST LABEL AND DATE ALL PREPARED FOODS.'</example>
    PRIMARY KEY (inspection_id, point_id),
    FOREIGN KEY (inspection_id) REFERENCES inspection(inspection_id),
    FOREIGN KEY (point_id) REFERENCES inspection_point(point_id)
);
```