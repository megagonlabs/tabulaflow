```sql
-- Database: computer_student

-- Table: advisedBy (113 rows)
CREATE TABLE advisedBy (
    p_id INTEGER,  -- e.g. 6; FK (composite)
    p_id_dummy INTEGER,  -- e.g. 5; FK (composite)
    PRIMARY KEY (p_id, p_id_dummy),
    FOREIGN KEY (p_id, p_id_dummy) REFERENCES person(p_id, p_id)
);

-- Table: course (132 rows)
CREATE TABLE course (
    course_id INTEGER PRIMARY KEY,  -- e.g. 0
    courseLevel TEXT  -- values: {'Level_300', 'Level_400', 'Level_500'}
);

-- Table: person (278 rows)
CREATE TABLE person (
    p_id INTEGER PRIMARY KEY,  -- e.g. 3
    professor INTEGER,  -- e.g. 0
    student INTEGER,  -- e.g. 1
    hasPosition TEXT,  -- values: {'0', 'Faculty', 'Faculty_adj', 'Faculty_aff', 'Faculty_eme'}
    inPhase TEXT,  -- values: {'0', 'Post_Generals', 'Post_Quals', 'Pre_Quals'}
    yearsInProgram TEXT  -- e.g. '0'
);

-- Table: taughtBy (189 rows)
CREATE TABLE taughtBy (
    course_id INTEGER,  -- e.g. 0; FK -> course.course_id
    p_id INTEGER,  -- e.g. 40; FK -> person.p_id
    PRIMARY KEY (course_id, p_id),
    FOREIGN KEY (p_id) REFERENCES person(p_id),
    FOREIGN KEY (course_id) REFERENCES course(course_id)
);
```