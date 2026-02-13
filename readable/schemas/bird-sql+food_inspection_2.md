```sql
-- Database: food_inspection_2

/*
Table: employee
Rows: 75
Sample rows:
| employee_id   | first_name   | last_name   | address               | city    | state   | zip   | phone          | title      | salary   | supervisor   |
|---------------|--------------|-------------|-----------------------|---------|---------|-------|----------------|------------|----------|--------------|
| 103705        | Anastasia    | Hansen      | 6023 S Elizabeth St   | Chicago | IL      | 60636 | (773) 424-8729 | Sanitarian | 79300    | 177316       |
| 104633        | Joshua       | Rosa        | 5000 N Wolcott Ave    | Chicago | IL      | 60640 | (773) 293-6409 | Sanitarian | 82000    | 186742       |
| 106581        | Zach         | Barber      | 7522 N Oleander Ave   | Chicago | IL      | 60631 | (219) 473-0757 | Sanitarian | 79900    | 179582       |
| 111559        | Lisa         | Tillman     | 5529 S Dorchester Ave | Chicago | IL      | 60637 | (773) 424-5470 | Sanitarian | 84700    | 182205       |
| 112202        | Bob          | Benson      | 7011 S Campbell Ave   | Chicago | IL      | 60629 | (773) 891-8653 | Sanitarian | 81900    | 182205       |
| ...           | ...          | ...         | ...                   | ...     | ...     | ...   | ...            | ...        | ...      | ...          |
*/
CREATE TABLE employee (
    employee_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>103705</example>
    first_name TEXT NOT NULL,
        -- <example>'Anastasia'</example>
    last_name TEXT NOT NULL,
        -- <example>'Hansen'</example>
    address TEXT NOT NULL,
        -- <example>'6023 S Elizabeth St'</example>
    city TEXT NOT NULL,
        -- <values>{'Chicago', 'Hoffman Estates', 'Park Forest'}</values>
    state TEXT NOT NULL,
        -- <values>{'IL'}</values>
    zip INTEGER NOT NULL,
        -- <example>60636</example>
    phone TEXT NOT NULL,
        -- <example>'(773) 424-8729'</example>
    title TEXT NOT NULL,
        -- <values>{'Division Manager', 'Sanitarian', 'Supervisor'}</values>
    salary INTEGER NOT NULL,
        -- <example>79300</example>
    supervisor INTEGER NOT NULL,
        -- <example>177316</example>
        -- <fk> -> employee.employee_id</fk>
    FOREIGN KEY (supervisor) REFERENCES employee(employee_id)
);

/*
Table: establishment
Rows: 31642
Sample rows:
| license_no   | dba_name                               | aka_name   | facility_type   | risk_level   | address            | city    | state   | zip   | latitude         | longitude         | ward   |
|--------------|----------------------------------------|------------|-----------------|--------------|--------------------|---------|---------|-------|------------------|-------------------|--------|
| 1            | HARVEST CRUSADES MINISTRIES            | [NULL]     | Special Event   | 2            | 118 N CENTRAL AVE  | CHICAGO | IL      | 60644 | 41.8828450747188 | -87.7650954520439 | 29     |
| 2            | COSI                                   | [NULL]     | Restaurant      | 1            | 230 W MONROE ST    | CHICAGO | IL      | 60606 | 41.8807571586472 | -87.6347092983425 | 42     |
| 9            | XANDO COFFEE & BAR / COSI SANDWICH BAR | [NULL]     | Restaurant      | 1            | 116 S MICHIGAN AVE | CHICAGO | IL      | 60603 | 41.8803958382596 | -87.6245017215946 | 42     |
| 40           | COSI                                   | [NULL]     | Restaurant      | 1            | 233 N MICHIGAN AVE | CHICAGO | IL      | 60601 | 41.8865673708869 | -87.6243846705971 | 42     |
| 43           | COSI                                   | [NULL]     | [NULL]          | 3            | 28 E JACKSON BLVD  | CHICAGO | IL      | 60604 | 41.8783416120634 | -87.6266749914868 | 42     |
| ...          | ...                                    | ...        | ...             | ...          | ...                | ...     | ...     | ...   | ...              | ...               | ...    |
*/
CREATE TABLE establishment (
    license_no INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    dba_name TEXT NOT NULL,
        -- <example>'HARVEST CRUSADES MINISTRIES'</example>
    aka_name TEXT NULL,
        -- <example>'COSI'</example>
    facility_type TEXT NULL,
        -- <example>'Special Event'</example>
    risk_level INTEGER NULL,
        -- <example>2</example>
    address TEXT NOT NULL,
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

/*
Table: inspection
Rows: 143870
Sample rows:
| inspection_id   | inspection_date   | inspection_type       | results   | employee_id   | license_no   | followup_to   |
|-----------------|-------------------|-----------------------|-----------|---------------|--------------|---------------|
| 44247           | 2010-01-05        | Complaint             | Pass      | 141319        | 1222441      | [NULL]        |
| 44248           | 2010-01-21        | Canvass               | Pass      | 143902        | 1336561      | [NULL]        |
| 44249           | 2010-01-21        | Canvass Re-Inspection | Pass      | 143487        | 1334073      | 67871.0       |
| 44250           | 2010-02-09        | Canvass               | Pass      | 104633        | 1144381      | [NULL]        |
| 44251           | 2010-02-09        | Canvass               | Pass      | 104633        | 1144380      | [NULL]        |
| ...             | ...               | ...                   | ...       | ...           | ...          | ...           |
*/
CREATE TABLE inspection (
    inspection_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>44247</example>
    inspection_date DATE NOT NULL,
        -- <example>'2010-01-05'</example>
    inspection_type TEXT NULL,
        -- <example>'Complaint'</example>
    results TEXT NOT NULL,
        -- <values>{'Business Not Located', 'Fail', 'No Entry', 'Not Ready', 'Out of Business', 'Pass w/ Conditions', 'Pass'}</values>
    employee_id INTEGER NOT NULL,
        -- <example>141319</example>
        -- <fk> -> employee.employee_id</fk>
    license_no INTEGER NOT NULL,
        -- <example>1222441</example>
        -- <fk> -> establishment.license_no</fk>
    followup_to INTEGER NULL,
        -- <example>67871</example>
        -- <fk> -> inspection.inspection_id</fk>
    FOREIGN KEY (employee_id) REFERENCES employee(employee_id),
    FOREIGN KEY (license_no) REFERENCES establishment(license_no),
    FOREIGN KEY (followup_to) REFERENCES inspection(inspection_id)
);

/*
Table: inspection_point
Rows: 46
Sample rows:
| point_id   | Description                                                                                              | category        | code               | fine   | point_level   |
|------------|----------------------------------------------------------------------------------------------------------|-----------------|--------------------|--------|---------------|
| 1          | Source sound condition, no spoilage, foods properly labeled, shellfish tags in place                     | Food Protection | 7-38-005 (B) (B-2) | 500    | Critical      |
| 2          | Facilities to maintain proper temperature                                                                | Food Protection | 7-38-005 (B) (B-2) | 500    | Critical      |
| 3          | Potentially hazardous food meets temperature requirement during storage, preparation display and service | Food Protection | 7-38-005 (A)       | 500    | Critical      |
| 4          | Source of cross contamination controlled i.e. cutting boards, food handlers, utensils, etc               | Food Protection | 7-38-005 (A)       | 500    | Critical      |
| 5          | Personnel with infections restricted: no open sores, wounds, etc                                         | Food Protection | 7-38-010 (A) (B)   | 500    | Critical      |
| ...        | ...                                                                                                      | ...             | ...                | ...    | ...           |
*/
CREATE TABLE inspection_point (
    point_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Description TEXT NOT NULL,
        -- <example>'Source sound condition, no spoilage, foods properly labeled, shellfish tags in place'</example>
    category TEXT NOT NULL,
        -- <example>'Food Protection'</example>
    code TEXT NOT NULL,
        -- <example>'7-38-005 (B) (B-2)'</example>
    fine INTEGER NOT NULL,
        -- <example>500</example>
    point_level TEXT NOT NULL
        -- <values>{'Critical', 'Minor   ', 'Serious '}</values>
);

/*
Table: violation
Rows: 525709
Sample rows:
| inspection_id   | point_id   | fine   | inspector_comment                                                                                                                                                                                           |
|-----------------|------------|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 44247           | 30         | 100    | All food not stored in the original container shall be stored in properly labeled containers.  OBSERVED SEVERAL FOODS IN COOLERS WITHOUT A LABEL AND DATE.  MUST LABEL AND DATE ALL PREPARED FOODS.         |
| 44247           | 32         | 100    | OBSERVED TORN DOOR GASKET ON DOOR OF 'CHILL ISLE' REACH-IN COOLER.  MUST REPLACE.  OBSERVED EXPOSED ...IDE OF THE DRESSING COOLER AND ON WIRE RACKS IN THE BASEMENT WALK-IN COOLER.  MUST REMOVE CARDBOARD. |
| 44247           | 33         | 100    | All food and non-food contact surfaces of equipment and all food storage utensils shall be thoroughl...TAIL CLEAN THE WIRE RACKS OF THE BASEMENT WALK-IN COOLER AND INTERIOR OF BASEMENT ICE CREAM FREEZER. |
| 44247           | 34         | 100    | The floors shall be constructed per code, be smooth and easily cleaned, and be kept clean and in good repair.  DETAIL CLEAN THE FLOOR IN THE FRONT PREP AREA.                                               |
| 44247           | 37         | 100    | Toilet rooms shall be completely enclosed and shall be vented to the outside air or mechanically ventilated.  VENTILATION FAN IN THE BASEMENT RESTROOM IS NOT OPERATIONAL.  MUST REPAIR.                    |
| ...             | ...        | ...    | ...                                                                                                                                                                                                         |
*/
CREATE TABLE violation (
    inspection_id INTEGER NOT NULL,
        -- <example>44247</example>
        -- <fk> -> inspection.inspection_id</fk>
    point_id INTEGER NOT NULL,
        -- <example>30</example>
        -- <fk> -> inspection_point.point_id</fk>
    fine INTEGER NOT NULL,
        -- <example>100</example>
    inspector_comment TEXT NULL,
        -- <example>'All food not stored in the original container shal...AND DATE.  MUST LABEL AND DATE ALL PREPARED FOODS.'</example>
    PRIMARY KEY (inspection_id, point_id),
    FOREIGN KEY (inspection_id) REFERENCES inspection(inspection_id),
    FOREIGN KEY (point_id) REFERENCES inspection_point(point_id)
);
```