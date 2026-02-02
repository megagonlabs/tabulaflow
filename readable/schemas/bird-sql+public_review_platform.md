```sql
-- Database: public_review_platform

-- Table: Attributes (80 rows)
CREATE TABLE Attributes (
    attribute_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    attribute_name TEXT NULL
        -- <example>'Alcohol'</example>
);

-- Table: Business (15585 rows)
CREATE TABLE Business (
    business_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    active TEXT NULL,
        -- <values>{'false', 'true'}</values>
    city TEXT NULL,
        -- <example>'Phoenix'</example>
    state TEXT NULL,
        -- <values>{'AZ', 'CA', 'SC'}</values>
    stars REAL NULL,
        -- <example>3.000</example>
    review_count TEXT NULL
        -- <values>{'High', 'Low', 'Medium', 'Uber'}</values>
);

-- Table: Business_Attributes (206934 rows)
CREATE TABLE Business_Attributes (
    attribute_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Attributes.attribute_id</fk>
    business_id INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> Business.business_id</fk>
    attribute_value TEXT NULL,
        -- <example>'none'</example>
    PRIMARY KEY (attribute_id, business_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id),
    FOREIGN KEY (attribute_id) REFERENCES Attributes(attribute_id)
);

-- Table: Business_Categories (43703 rows)
CREATE TABLE Business_Categories (
    business_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Business.business_id</fk>
    category_id INTEGER NULL,
        -- <example>8</example>
        -- <fk> -> Categories.category_id</fk>
    PRIMARY KEY (business_id, category_id),
    FOREIGN KEY (category_id) REFERENCES Categories(category_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

-- Table: Business_Hours (47831 rows)
CREATE TABLE Business_Hours (
    business_id INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> Business.business_id</fk>
    day_id INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> Days.day_id</fk>
    opening_time TEXT NULL,
        -- <example>'11AM'</example>
    closing_time TEXT NULL,
        -- <example>'8PM'</example>
    PRIMARY KEY (business_id, day_id),
    FOREIGN KEY (day_id) REFERENCES Days(day_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

-- Table: Categories (591 rows)
CREATE TABLE Categories (
    category_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    category_name TEXT NULL
        -- <example>'Active Life'</example>
);

-- Table: Checkins (80038 rows)
CREATE TABLE Checkins (
    business_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Business.business_id</fk>
    day_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Days.day_id</fk>
    label_time_0 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None'}</values>
    label_time_1 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None'}</values>
    label_time_2 TEXT NULL,
        -- <values>{'Low', 'Medium', 'None'}</values>
    label_time_3 TEXT NULL,
        -- <values>{'Low', 'Medium', 'None'}</values>
    label_time_4 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None'}</values>
    label_time_5 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_6 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_7 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_8 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_9 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_10 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_11 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_12 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_13 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_14 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_15 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_16 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_17 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_18 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_19 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_20 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_21 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_22 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_23 TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None'}</values>
    PRIMARY KEY (business_id, day_id),
    FOREIGN KEY (day_id) REFERENCES Days(day_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

-- Table: Compliments (11 rows)
CREATE TABLE Compliments (
    compliment_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    compliment_type TEXT NULL
        -- <example>'photos'</example>
);

-- Table: Days (7 rows)
CREATE TABLE Days (
    day_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    day_of_week TEXT NULL
        -- <values>{'Friday', 'Monday', 'Saturday', 'Sunday', 'Thursday', 'Tuesday', 'Wednesday'}</values>
);

-- Table: Elite (16366 rows)
CREATE TABLE Elite (
    user_id INTEGER NULL,
        -- <example>3</example>
        -- <fk> -> Users.user_id</fk>
    year_id INTEGER NULL,
        -- <example>2010</example>
        -- <fk> -> Years.year_id</fk>
    PRIMARY KEY (user_id, year_id),
    FOREIGN KEY (year_id) REFERENCES Years(year_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

-- Table: Reviews (322906 rows)
CREATE TABLE Reviews (
    business_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Business.business_id</fk>
    user_id INTEGER NULL,
        -- <example>36129</example>
        -- <fk> -> Users.user_id</fk>
    review_stars INTEGER NULL,
        -- <example>2</example>
    review_votes_funny TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    review_votes_useful TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    review_votes_cool TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    review_length TEXT NULL,
        -- <values>{'Long', 'Medium', 'Short'}</values>
    PRIMARY KEY (business_id, user_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

-- Table: Tips (87157 rows)
CREATE TABLE Tips (
    business_id INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> Business.business_id</fk>
    user_id INTEGER NULL,
        -- <example>12490</example>
        -- <fk> -> Users.user_id</fk>
    likes INTEGER NULL,
        -- <example>0</example>
    tip_length TEXT NULL,
        -- <values>{'Long', 'Medium', 'Short'}</values>
    PRIMARY KEY (business_id, user_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

-- Table: Users (70817 rows)
CREATE TABLE Users (
    user_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    user_yelping_since_year INTEGER NULL,
        -- <example>2012</example>
    user_average_stars TEXT NULL,
        -- <values>{'0.0', '1.0', '1.5', '2.0', '2.5', '3.0', '3.5', '4.0', '4.5', '5.0'}</values>
    user_votes_funny TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    user_votes_useful TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    user_votes_cool TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    user_review_count TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'Uber'}</values>
    user_fans TEXT NULL
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
);

-- Table: Users_Compliments (98810 rows)
CREATE TABLE Users_Compliments (
    compliment_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Compliments.compliment_id</fk>
    user_id INTEGER NULL,
        -- <example>3</example>
        -- <fk> -> Users.user_id</fk>
    number_of_compliments TEXT NULL,
        -- <values>{'High', 'Low', 'Medium', 'Uber'}</values>
    PRIMARY KEY (compliment_id, user_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (compliment_id) REFERENCES Compliments(compliment_id)
);

-- Table: Years (10 rows)
CREATE TABLE Years (
    year_id INTEGER NULL PRIMARY KEY,
        -- <example>2005</example>
    actual_year INTEGER NULL
        -- <example>2005</example>
);
```