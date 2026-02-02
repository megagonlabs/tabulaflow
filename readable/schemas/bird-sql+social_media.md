```sql
-- Database: social_media

-- Table: location (6211 rows)
CREATE TABLE location (
    LocationID INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Country TEXT NULL,
        -- <example>'Albania'</example>
    State TEXT NULL,
        -- <example>'Elbasan'</example>
    StateCode TEXT NULL,
        -- <example>'AL'</example>
    City TEXT NULL
        -- <example>'Elbasan'</example>
);

-- Table: twitter (99901 rows)
CREATE TABLE twitter (
    TweetID TEXT NULL PRIMARY KEY,
        -- <example>'tw-682712873332805633'</example>
    Weekday TEXT NULL,
        -- <values>{'Friday', 'Monday', 'Saturday', 'Sunday', 'Thursday', 'Tuesday', 'Wednesday'}</values>
    Hour INTEGER NULL,
        -- <example>17</example>
    Day INTEGER NULL,
        -- <example>31</example>
    Lang TEXT NULL,
        -- <example>'en'</example>
    IsReshare TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Reach INTEGER NULL,
        -- <example>44</example>
    RetweetCount INTEGER NULL,
        -- <example>0</example>
    Likes INTEGER NULL,
        -- <example>0</example>
    Klout INTEGER NULL,
        -- <example>35</example>
    Sentiment REAL NULL,
        -- <example>0.000</example>
    text TEXT NULL,
        -- <example>'We are hiring: Senior Software Engineer - Proto ht...ud #job #protocol #networking #aws #mediastreaming'</example>
    LocationID INTEGER NULL,
        -- <example>3751</example>
        -- <fk> -> location.LocationID</fk>
    UserID TEXT NULL,
        -- <example>'tw-40932430'</example>
        -- <fk> -> user.UserID</fk>
    FOREIGN KEY (LocationID) REFERENCES location(LocationID),
    FOREIGN KEY (UserID) REFERENCES user(UserID)
);

-- Table: user (99260 rows)
CREATE TABLE user (
    UserID TEXT NULL PRIMARY KEY,
        -- <example>'nknow531394'</example>
    Gender TEXT NULL
        -- <values>{'Female', 'Male', 'Unisex', 'Unknown'}</values>
);
```