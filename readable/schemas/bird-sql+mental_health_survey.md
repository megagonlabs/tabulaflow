```sql
-- Database: mental_health_survey

-- Table: Answer (234640 rows)
CREATE TABLE Answer (
    AnswerText TEXT,  -- e.g. '37'
    SurveyID INTEGER,  -- e.g. 2014; FK -> Survey.SurveyID
    UserID INTEGER,  -- e.g. 1
    QuestionID INTEGER,  -- e.g. 1; FK -> Question.questionid
    PRIMARY KEY (UserID, QuestionID),
    FOREIGN KEY (QuestionID) REFERENCES Question(questionid),
    FOREIGN KEY (SurveyID) REFERENCES Survey(SurveyID)
);

-- Table: Question (105 rows)
CREATE TABLE Question (
    questiontext TEXT,  -- e.g. 'What is your age?'
    questionid INTEGER PRIMARY KEY  -- e.g. 1
);

-- Table: Survey (5 rows)
CREATE TABLE Survey (
    SurveyID INTEGER PRIMARY KEY,  -- e.g. 2014
    Description TEXT  -- values: {'mental health survey for 2014', 'mental health survey for 2016', 'mental health survey for 2017', 'mental health survey for 2018', 'mental health survey for 2019'}
);
```