```sql
-- Database: cs_semester

-- Table: RA (35 rows)
CREATE TABLE RA (
    student_id INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> student.student_id</fk>
    capability INTEGER NULL,
        -- <example>2</example>
    prof_id INTEGER NULL,
        -- <example>7</example>
        -- <fk> -> prof.prof_id</fk>
    salary TEXT NULL,
        -- <values>{'free', 'high', 'low', 'med'}</values>
    PRIMARY KEY (student_id, prof_id),
    FOREIGN KEY (prof_id) REFERENCES prof(prof_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);

-- Table: course (13 rows)
CREATE TABLE course (
    course_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NULL,
        -- <example>'Machine Learning Theory'</example>
    credit INTEGER NULL,
        -- <example>3</example>
    diff INTEGER NULL
        -- <example>3</example>
);

-- Table: prof (10 rows)
CREATE TABLE prof (
    prof_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    gender TEXT NULL,
        -- <values>{'Female', 'Male'}</values>
    first_name TEXT NULL,
        -- <values>{'Bernhard', 'Hattie', 'Mateo', 'Merwyn', 'Millie', 'Nathaniel', 'Ogdon', 'Rosamond', 'Sauveur', 'Zhihua'}</values>
    last_name TEXT NULL,
        -- <values>{'Conkay', 'Cunningham', 'Ewenson', 'Medmore', 'Molen', 'Pigford', 'Skyme', 'Smythin', 'Zhou', 'Zywicki'}</values>
    email TEXT NULL,
        -- <values>{'bmolen4@hku.hk', 'hsmythin9@hku.hk', 'mconkay3@ucla.edu', 'mcunningham6@stanford.edu', 'mmedmore8@hku.hk', 'npigford0@hku.hk', 'ozywicki2@hku.hk', 'rewenson7@hku.hk', 'sskyme5@columbia.edu', 'zzhihua@hku.hk'}</values>
    popularity INTEGER NULL,
        -- <example>3</example>
    teachingability INTEGER NULL,
        -- <example>5</example>
    graduate_from TEXT NULL
        -- <values>{'Beijing Polytechnic University', 'Carnegie Mellon University', 'ETH Zurich', 'Massachusetts Institute of Technology', 'Miyazaki Municipal University', 'Mount Aloysius College', 'Princeton University', 'University of Boston', 'University of Pennsylvania', 'University of Washington'}</values>
);

-- Table: registration (101 rows)
CREATE TABLE registration (
    course_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> course.course_id</fk>
    student_id INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> student.student_id</fk>
    grade TEXT NULL,
        -- <values>{'A', 'B', 'C', 'D'}</values>
    sat INTEGER NULL,
        -- <example>5</example>
    PRIMARY KEY (course_id, student_id),
    FOREIGN KEY (course_id) REFERENCES course(course_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);

-- Table: student (38 rows)
CREATE TABLE student (
    student_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    f_name TEXT NULL,
        -- <example>'Kerry'</example>
    l_name TEXT NULL,
        -- <example>'Pryor'</example>
    phone_number TEXT NULL,
        -- <example>'(243) 6836472'</example>
    email TEXT NULL,
        -- <example>'kpryor0@hku.hk'</example>
    intelligence INTEGER NULL,
        -- <example>5</example>
    gpa REAL NULL,
        -- <example>2.400</example>
    type TEXT NULL
        -- <values>{'RPG', 'TPG', 'UG'}</values>
);
```