```sql
-- Database: computer_student

-- Table: advisedBy (113 rows)
CREATE TABLE advisedBy (
    p_id INTEGER NULL,
        -- <example>6</example>
        -- <fk>composite</fk>
    p_id_dummy INTEGER NULL,
        -- <example>5</example>
        -- <fk>composite</fk>
    PRIMARY KEY (p_id, p_id_dummy),
    FOREIGN KEY (p_id, p_id_dummy) REFERENCES person(p_id, p_id)
);

-- Table: course (132 rows)
CREATE TABLE course (
    course_id INTEGER NULL PRIMARY KEY,
        -- <example>0</example>
    courseLevel TEXT NULL
        -- <values>{'Level_300', 'Level_400', 'Level_500'}</values>
);

-- Table: person (278 rows)
CREATE TABLE person (
    p_id INTEGER NULL PRIMARY KEY,
        -- <example>3</example>
    professor INTEGER NULL,
        -- <example>0</example>
    student INTEGER NULL,
        -- <example>1</example>
    hasPosition TEXT NULL,
        -- <values>{'0', 'Faculty', 'Faculty_adj', 'Faculty_aff', 'Faculty_eme'}</values>
    inPhase TEXT NULL,
        -- <values>{'0', 'Post_Generals', 'Post_Quals', 'Pre_Quals'}</values>
    yearsInProgram TEXT NULL
        -- <example>'0'</example>
);

-- Table: taughtBy (189 rows)
CREATE TABLE taughtBy (
    course_id INTEGER NULL,
        -- <example>0</example>
        -- <fk> -> course.course_id</fk>
    p_id INTEGER NULL,
        -- <example>40</example>
        -- <fk> -> person.p_id</fk>
    PRIMARY KEY (course_id, p_id),
    FOREIGN KEY (p_id) REFERENCES person(p_id),
    FOREIGN KEY (course_id) REFERENCES course(course_id)
);
```