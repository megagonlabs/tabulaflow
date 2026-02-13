```sql
-- Database: computer_student

/*
Schema: NULLTable: advisedBy
Rows: 113
Sample rows:
| p_id   | p_id_dummy   |
|--------|--------------|
| 96     | 5            |
| 118    | 5            |
| 183    | 5            |
| 263    | 5            |
| 362    | 5            |
| ...    | ...          |
*/
CREATE TABLE advisedBy (
    p_id INTEGER NOT NULL,
        -- <example>6</example>
        -- <fk>composite</fk>
    p_id_dummy INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk>composite</fk>
    PRIMARY KEY (p_id, p_id_dummy),
    FOREIGN KEY (p_id, p_id_dummy) REFERENCES person(p_id, p_id)
);

/*
Schema: NULLTable: course
Rows: 132
Sample rows:
| course_id   | courseLevel   |
|-------------|---------------|
| 0           | Level_500     |
| 1           | Level_500     |
| 2           | Level_500     |
| 3           | Level_500     |
| 4           | Level_500     |
| ...         | ...           |
*/
CREATE TABLE course (
    course_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    courseLevel TEXT NOT NULL
        -- <values>{'Level_300', 'Level_400', 'Level_500'}</values>
);

/*
Schema: NULLTable: person
Rows: 278
Sample rows:
| p_id   | professor   | student   | hasPosition   | inPhase    | yearsInProgram   |
|--------|-------------|-----------|---------------|------------|------------------|
| 3      | 0           | 1         | 0             | 0          | 0                |
| 4      | 0           | 1         | 0             | 0          | 0                |
| 5      | 1           | 0         | Faculty       | 0          | 0                |
| 6      | 0           | 1         | 0             | Post_Quals | Year_2           |
| 7      | 1           | 0         | Faculty_adj   | 0          | 0                |
| ...    | ...         | ...       | ...           | ...        | ...              |
*/
CREATE TABLE person (
    p_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>3</example>
    professor INTEGER NOT NULL,
        -- <example>0</example>
    student INTEGER NOT NULL,
        -- <example>1</example>
    hasPosition TEXT NOT NULL,
        -- <values>{'0', 'Faculty', 'Faculty_adj', 'Faculty_aff', 'Faculty_eme'}</values>
    inPhase TEXT NOT NULL,
        -- <values>{'0', 'Post_Generals', 'Post_Quals', 'Pre_Quals'}</values>
    yearsInProgram TEXT NOT NULL
        -- <example>'0'</example>
);

/*
Schema: NULLTable: taughtBy
Rows: 189
Sample rows:
| course_id   | p_id   |
|-------------|--------|
| 0           | 40     |
| 1           | 40     |
| 2           | 180    |
| 3           | 279    |
| 4           | 107    |
| ...         | ...    |
*/
CREATE TABLE taughtBy (
    course_id INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> course.course_id</fk>
    p_id INTEGER NOT NULL,
        -- <example>40</example>
        -- <fk> -> person.p_id</fk>
    PRIMARY KEY (course_id, p_id),
    FOREIGN KEY (p_id) REFERENCES person(p_id),
    FOREIGN KEY (course_id) REFERENCES course(course_id)
);
```