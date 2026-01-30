```sql
-- Database: cs_semester

-- Table: RA (35 rows)
CREATE TABLE RA (
    student_id INTEGER,  -- e.g. 2; FK -> student.student_id
    capability INTEGER,  -- e.g. 2
    prof_id INTEGER,  -- e.g. 7; FK -> prof.prof_id
    salary TEXT,  -- values: {'free', 'high', 'low', 'med'}
    PRIMARY KEY (student_id, prof_id),
    FOREIGN KEY (prof_id) REFERENCES prof(prof_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);

-- Table: course (13 rows)
CREATE TABLE course (
    course_id INTEGER PRIMARY KEY,  -- e.g. 1
    name TEXT,  -- e.g. 'Machine Learning Theory'
    credit INTEGER,  -- e.g. 3
    diff INTEGER  -- e.g. 3
);

-- Table: prof (10 rows)
CREATE TABLE prof (
    prof_id INTEGER PRIMARY KEY,  -- e.g. 1
    gender TEXT,  -- values: {'Female', 'Male'}
    first_name TEXT,  -- values: {'Bernhard', 'Hattie', 'Mateo', 'Merwyn', 'Millie', 'Nathaniel', 'Ogdon', 'Rosamond', 'Sauveur', 'Zhihua'}
    last_name TEXT,  -- values: {'Conkay', 'Cunningham', 'Ewenson', 'Medmore', 'Molen', 'Pigford', 'Skyme', 'Smythin', 'Zhou', 'Zywicki'}
    email TEXT,  -- values: {'bmolen4@hku.hk', 'hsmythin9@hku.hk', 'mconkay3@ucla.edu', 'mcunningham6@stanford.edu', 'mmedmore8@hku.hk', 'npigford0@hku.hk', 'ozywicki2@hku.hk', 'rewenson7@hku.hk', 'sskyme5@columbia.edu', 'zzhihua@hku.hk'}
    popularity INTEGER,  -- e.g. 3
    teachingability INTEGER,  -- e.g. 5
    graduate_from TEXT  -- values: {'Beijing Polytechnic University', 'Carnegie Mellon University', 'ETH Zurich', 'Massachusetts Institute of Technology', 'Miyazaki Municipal University', 'Mount Aloysius College', 'Princeton University', 'University of Boston', 'University of Pennsylvania', 'University of Washington'}
);

-- Table: registration (101 rows)
CREATE TABLE registration (
    course_id INTEGER,  -- e.g. 1; FK -> course.course_id
    student_id INTEGER,  -- e.g. 2; FK -> student.student_id
    grade TEXT,  -- values: {'A', 'B', 'C', 'D'}
    sat INTEGER,  -- e.g. 5
    PRIMARY KEY (course_id, student_id),
    FOREIGN KEY (course_id) REFERENCES course(course_id),
    FOREIGN KEY (student_id) REFERENCES student(student_id)
);

-- Table: student (38 rows)
CREATE TABLE student (
    student_id INTEGER PRIMARY KEY,  -- e.g. 1
    f_name TEXT,  -- e.g. 'Kerry'
    l_name TEXT,  -- e.g. 'Pryor'
    phone_number TEXT,  -- e.g. '(243) 6836472'
    email TEXT,  -- e.g. 'kpryor0@hku.hk'
    intelligence INTEGER,  -- e.g. 5
    gpa REAL,  -- e.g. 2.400
    type TEXT  -- values: {'RPG', 'TPG', 'UG'}
);
```