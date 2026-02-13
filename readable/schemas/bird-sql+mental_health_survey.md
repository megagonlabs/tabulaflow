```sql
-- Database: mental_health_survey

/*
Table: Answer
Rows: 234640
Sample rows:
| AnswerText   | SurveyID   | UserID   | QuestionID   |
|--------------|------------|----------|--------------|
| 37           | 2014       | 1        | 1            |
| 44           | 2014       | 2        | 1            |
| 32           | 2014       | 3        | 1            |
| 31           | 2014       | 4        | 1            |
| 31           | 2014       | 5        | 1            |
| ...          | ...        | ...      | ...          |
*/
CREATE TABLE Answer (
    AnswerText TEXT NOT NULL,
        -- <example>'37'</example>
    SurveyID INTEGER NOT NULL,
        -- <example>2014</example>
        -- <fk> -> Survey.SurveyID</fk>
    UserID INTEGER NOT NULL,
        -- <example>1</example>
    QuestionID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Question.questionid</fk>
    PRIMARY KEY (UserID, QuestionID),
    FOREIGN KEY (QuestionID) REFERENCES Question(questionid),
    FOREIGN KEY (SurveyID) REFERENCES Survey(SurveyID)
);

/*
Table: Question
Rows: 105
Sample rows:
| questiontext                                                               | questionid   |
|----------------------------------------------------------------------------|--------------|
| What is your age?                                                          | 1            |
| What is your gender?                                                       | 2            |
| What country do you live in?                                               | 3            |
| If you live in the United States, which state or territory do you live in? | 4            |
| Are you self-employed?                                                     | 5            |
| ...                                                                        | ...          |
*/
CREATE TABLE Question (
    questiontext TEXT NOT NULL,
        -- <example>'What is your age?'</example>
    questionid INTEGER NOT NULL PRIMARY KEY
        -- <example>1</example>
);

/*
Table: Survey
Rows: 5
All rows:
|   SurveyID | Description                   |
|------------|-------------------------------|
|       2014 | mental health survey for 2014 |
|       2016 | mental health survey for 2016 |
|       2017 | mental health survey for 2017 |
|       2018 | mental health survey for 2018 |
|       2019 | mental health survey for 2019 |
*/
CREATE TABLE Survey (
    SurveyID INTEGER NOT NULL PRIMARY KEY,
        -- <example>2014</example>
    Description TEXT NOT NULL
        -- <values>{'mental health survey for 2014', 'mental health survey for 2016', 'mental health survey for 2017', 'mental health survey for 2018', 'mental health survey for 2019'}</values>
);
```