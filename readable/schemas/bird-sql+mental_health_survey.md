```sql
-- Database: mental_health_survey

-- Table: Answer (234640 rows)
CREATE TABLE Answer (
    AnswerText TEXT NULL,
        -- <example>'37'</example>
    SurveyID INTEGER NULL,
        -- <example>2014</example>
        -- <fk> -> Survey.SurveyID</fk>
    UserID INTEGER NULL,
        -- <example>1</example>
    QuestionID INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Question.questionid</fk>
    PRIMARY KEY (UserID, QuestionID),
    FOREIGN KEY (QuestionID) REFERENCES Question(questionid),
    FOREIGN KEY (SurveyID) REFERENCES Survey(SurveyID)
);

-- Table: Question (105 rows)
CREATE TABLE Question (
    questiontext TEXT NULL,
        -- <example>'What is your age?'</example>
    questionid INTEGER NULL PRIMARY KEY
        -- <example>1</example>
);

-- Table: Survey (5 rows)
CREATE TABLE Survey (
    SurveyID INTEGER NULL PRIMARY KEY,
        -- <example>2014</example>
    Description TEXT NULL
        -- <values>{'mental health survey for 2014', 'mental health survey for 2016', 'mental health survey for 2017', 'mental health survey for 2018', 'mental health survey for 2019'}</values>
);
```