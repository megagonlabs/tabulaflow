```sql
-- Database: cs_semester

/*
Table: RA
Rows: 35
Sample rows:
| student_id   | capability   | prof_id   | salary   |
|--------------|--------------|-----------|----------|
| 16           | 2            | 11        | med      |
| 23           | 5            | 6         | high     |
| 23           | 4            | 11        | high     |
| 20           | 2            | 11        | low      |
| 31           | 3            | 6         | free     |
| ...          | ...          | ...       | ...      |
*/
CREATE TABLE RA (
    student_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> student.student_id</fk>
    capability INTEGER NOT NULL,
        -- <example>2</example>
    prof_id INTEGER NOT NULL,
        -- <example>7</example>
        -- <fk> -> prof.prof_id</fk>
    salary TEXT NOT NULL,
        -- <values>{'free', 'high', 'low', 'med'}</values>
    PRIMARY KEY (student_id, prof_id),
    FOREIGN KEY (prof_id) REFERENCES prof(prof_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);

/*
Table: course
Rows: 13
Sample rows:
| course_id   | name                        | credit   | diff   |
|-------------|-----------------------------|----------|--------|
| 1           | Machine Learning Theory     | 3        | 3      |
| 2           | Intro to Database 1         | 2        | 4      |
| 3           | Intro to Database 2         | 2        | 1      |
| 4           | Natural Language Processing | 3        | 3      |
| 5           | Intro to BlockChain         | 3        | 5      |
| ...         | ...                         | ...      | ...    |
*/
CREATE TABLE course (
    course_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NOT NULL,
        -- <example>'Machine Learning Theory'</example>
    credit INTEGER NOT NULL,
        -- <example>3</example>
    diff INTEGER NOT NULL
        -- <example>3</example>
);

/*
Table: prof
Rows: 10
All rows:
|   prof_id | gender   | first_name   | last_name   | email                     |   popularity |   teachingability | graduate_from                         |
|-----------|----------|--------------|-------------|---------------------------|--------------|-------------------|---------------------------------------|
|         1 | Male     | Nathaniel    | Pigford     | npigford0@hku.hk          |            3 |                 5 | University of Washington              |
|         2 | Male     | Zhihua       | Zhou        | zzhihua@hku.hk            |            2 |                 1 | Beijing Polytechnic University        |
|         3 | Male     | Ogdon        | Zywicki     | ozywicki2@hku.hk          |            2 |                 2 | University of Boston                  |
|         4 | Female   | Merwyn       | Conkay      | mconkay3@ucla.edu         |            3 |                 3 | Carnegie Mellon University            |
|         5 | Male     | Bernhard     | Molen       | bmolen4@hku.hk            |            3 |                 1 | Princeton University                  |
|         6 | Male     | Sauveur      | Skyme       | sskyme5@columbia.edu      |            3 |                 5 | University of Pennsylvania            |
|         7 | Female   | Millie       | Cunningham  | mcunningham6@stanford.edu |            2 |                 5 | Massachusetts Institute of Technology |
|         8 | Female   | Rosamond     | Ewenson     | rewenson7@hku.hk          |            3 |                 1 | Miyazaki Municipal University         |
|         9 | Male     | Mateo        | Medmore     | mmedmore8@hku.hk          |            2 |                 4 | ETH Zurich                            |
|        10 | Male     | Hattie       | Smythin     | hsmythin9@hku.hk          |            2 |                 5 | Mount Aloysius College                |
*/
CREATE TABLE prof (
    prof_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    gender TEXT NOT NULL,
        -- <values>{'Female', 'Male'}</values>
    first_name TEXT NOT NULL,
        -- <values>{'Bernhard', 'Hattie', 'Mateo', 'Merwyn', 'Millie', 'Nathaniel', 'Ogdon', 'Rosamond', 'Sauveur', 'Zhihua'}</values>
    last_name TEXT NOT NULL,
        -- <values>{'Conkay', 'Cunningham', 'Ewenson', 'Medmore', 'Molen', 'Pigford', 'Skyme', 'Smythin', 'Zhou', 'Zywicki'}</values>
    email TEXT NOT NULL,
        -- <values>{'bmolen4@hku.hk', 'hsmythin9@hku.hk', 'mconkay3@ucla.edu', 'mcunningham6@stanford.edu', 'mmedmore8@hku.hk', 'npigford0@hku.hk', 'ozywicki2@hku.hk', 'rewenson7@hku.hk', 'sskyme5@columbia.edu', 'zzhihua@hku.hk'}</values>
    popularity INTEGER NOT NULL,
        -- <example>3</example>
    teachingability INTEGER NOT NULL,
        -- <example>5</example>
    graduate_from TEXT NOT NULL
        -- <values>{'Beijing Polytechnic University', 'Carnegie Mellon University', 'ETH Zurich', 'Massachusetts Institute of Technology', 'Miyazaki Municipal University', 'Mount Aloysius College', 'Princeton University', 'University of Boston', 'University of Pennsylvania', 'University of Washington'}</values>
);

/*
Table: registration
Rows: 101
Sample rows:
| course_id   | student_id   | grade   | sat   |
|-------------|--------------|---------|-------|
| 1           | 7            | A       | 5     |
| 1           | 3            | B       | 4     |
| 1           | 2            | B       | 4     |
| 1           | 31           | B       | 3     |
| 1           | 12           | B       | 4     |
| ...         | ...          | ...     | ...   |
*/
CREATE TABLE registration (
    course_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> course.course_id</fk>
    student_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> student.student_id</fk>
    grade TEXT NULL,
        -- <values>{'A', 'B', 'C', 'D'}</values>
    sat INTEGER NOT NULL,
        -- <example>5</example>
    PRIMARY KEY (course_id, student_id),
    FOREIGN KEY (course_id) REFERENCES course(course_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);

/*
Table: student
Rows: 38
Sample rows:
| student_id   | f_name   | l_name    | phone_number   | email                  | intelligence   | gpa   | type   |
|--------------|----------|-----------|----------------|------------------------|----------------|-------|--------|
| 1            | Kerry    | Pryor     | (243) 6836472  | kpryor0@hku.hk         | 5              | 2.4   | RPG    |
| 2            | Chrysa   | Dine-Hart | (672) 9245255  | cdinehart1@hku.hk      | 2              | 2.7   | TPG    |
| 3            | Elsy     | Shiril    | (521) 7680522  | eshiril2@hku.hk        | 1              | 3.5   | TPG    |
| 4            | Dougie   | Happel    | (192) 6371744  | dhappel3@hku.hk        | 2              | 2.8   | UG     |
| 5            | Ahmed    | Sukbhans  | (805) 4273942  | asukbhans4@cuhk.edu.hk | 1              | 3.9   | UG     |
| ...          | ...      | ...       | ...            | ...                    | ...            | ...   | ...    |
*/
CREATE TABLE student (
    student_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    f_name TEXT NOT NULL,
        -- <example>'Kerry'</example>
    l_name TEXT NOT NULL,
        -- <example>'Pryor'</example>
    phone_number TEXT NOT NULL,
        -- <example>'(243) 6836472'</example>
    email TEXT NOT NULL,
        -- <example>'kpryor0@hku.hk'</example>
    intelligence INTEGER NOT NULL,
        -- <example>5</example>
    gpa REAL NOT NULL,
        -- <example>2.400</example>
    type TEXT NOT NULL
        -- <values>{'RPG', 'TPG', 'UG'}</values>
);
```