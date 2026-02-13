```sql
-- Database: public_review_platform

/*
Table: Attributes
Rows: 80
Sample rows:
| attribute_id   | attribute_name   |
|----------------|------------------|
| 1              | Alcohol          |
| 2              | Waiter Service   |
| 3              | Delivery         |
| 4              | Attire           |
| 5              | Good for Kids    |
| ...            | ...              |
*/
CREATE TABLE Attributes (
    attribute_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    attribute_name TEXT NOT NULL
        -- <example>'Alcohol'</example>
);

/*
Table: Business
Rows: 15585
Sample rows:
| business_id   | active   | city       | state   | stars   | review_count   |
|---------------|----------|------------|---------|---------|----------------|
| 1             | true     | Phoenix    | AZ      | 3.0     | Low            |
| 2             | true     | Scottsdale | AZ      | 4.5     | Medium         |
| 3             | true     | Scottsdale | AZ      | 4.0     | Medium         |
| 4             | true     | Glendale   | AZ      | 4.0     | Low            |
| 5             | true     | Scottsdale | AZ      | 5.0     | Low            |
| ...           | ...      | ...        | ...     | ...     | ...            |
*/
CREATE TABLE Business (
    business_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    active TEXT NOT NULL,
        -- <values>{'false', 'true'}</values>
    city TEXT NOT NULL,
        -- <example>'Phoenix'</example>
    state TEXT NOT NULL,
        -- <values>{'AZ', 'CA', 'SC'}</values>
    stars REAL NOT NULL,
        -- <example>3.000</example>
    review_count TEXT NOT NULL
        -- <values>{'High', 'Low', 'Medium', 'Uber'}</values>
);

/*
Table: Business_Attributes
Rows: 206934
Sample rows:
| attribute_id   | business_id   | attribute_value   |
|----------------|---------------|-------------------|
| 1              | 2             | none              |
| 1              | 3             | none              |
| 1              | 13            | none              |
| 1              | 17            | full_bar          |
| 1              | 22            | full_bar          |
| ...            | ...           | ...               |
*/
CREATE TABLE Business_Attributes (
    attribute_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Attributes.attribute_id</fk>
    business_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> Business.business_id</fk>
    attribute_value TEXT NOT NULL,
        -- <example>'none'</example>
    PRIMARY KEY (attribute_id, business_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id),
    FOREIGN KEY (attribute_id) REFERENCES Attributes(attribute_id)
);

/*
Table: Business_Categories
Rows: 43703
Sample rows:
| business_id   | category_id   |
|---------------|---------------|
| 1             | 8             |
| 1             | 143           |
| 2             | 18            |
| 2             | 170           |
| 3             | 18            |
| ...           | ...           |
*/
CREATE TABLE Business_Categories (
    business_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Business.business_id</fk>
    category_id INTEGER NOT NULL,
        -- <example>8</example>
        -- <fk> -> Categories.category_id</fk>
    PRIMARY KEY (business_id, category_id),
    FOREIGN KEY (category_id) REFERENCES Categories(category_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

/*
Table: Business_Hours
Rows: 47831
Sample rows:
| business_id   | day_id   | opening_time   | closing_time   |
|---------------|----------|----------------|----------------|
| 2             | 2        | 11AM           | 8PM            |
| 2             | 3        | 11AM           | 8PM            |
| 2             | 4        | 11AM           | 8PM            |
| 2             | 5        | 11AM           | 8PM            |
| 2             | 6        | 11AM           | 8PM            |
| ...           | ...      | ...            | ...            |
*/
CREATE TABLE Business_Hours (
    business_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> Business.business_id</fk>
    day_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> Days.day_id</fk>
    opening_time TEXT NOT NULL,
        -- <example>'11AM'</example>
    closing_time TEXT NOT NULL,
        -- <example>'8PM'</example>
    PRIMARY KEY (business_id, day_id),
    FOREIGN KEY (day_id) REFERENCES Days(day_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

/*
Table: Categories
Rows: 591
Sample rows:
| category_id   | category_name        |
|---------------|----------------------|
| 1             | Active Life          |
| 2             | Arts & Entertainment |
| 3             | Stadiums & Arenas    |
| 4             | Horse Racing         |
| 5             | Tires                |
| ...           | ...                  |
*/
CREATE TABLE Categories (
    category_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    category_name TEXT NOT NULL
        -- <example>'Active Life'</example>
);

/*
Table: Checkins
Rows: 80038
Sample rows:
| business_id   | day_id   | label_time_0   | label_time_1   | label_time_2   | label_time_3   | label_time_4   | label_time_5   | label_time_6   | label_time_7   | label_time_8   | label_time_9   | label_time_10   | label_time_11   | label_time_12   | label_time_13   | label_time_14   | label_time_15   | label_time_16   | label_time_17   | label_time_18   | label_time_19   | label_time_20   | label_time_21   | label_time_22   | label_time_23   |
|---------------|----------|----------------|----------------|----------------|----------------|----------------|----------------|----------------|----------------|----------------|----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|
| 1             | 1        | None           | None           | None           | None           | None           | None           | None           | None           | None           | Low            | None            | Low             | None            | None            | None            | None            | None            | Low             | None            | None            | None            | None            | None            | None            |
| 1             | 2        | None           | None           | None           | None           | None           | None           | None           | None           | None           | None           | None            | None            | None            | None            | None            | Low             | None            | None            | None            | Low             | None            | None            | None            | None            |
| 1             | 3        | None           | None           | None           | None           | None           | None           | None           | None           | None           | None           | None            | Low             | None            | Low             | Low             | Low             | None            | Low             | None            | None            | None            | None            | None            | None            |
| 1             | 4        | None           | None           | None           | None           | None           | None           | None           | None           | None           | None           | None            | None            | Low             | None            | None            | None            | None            | None            | None            | None            | Low             | None            | None            | None            |
| 1             | 5        | None           | None           | None           | None           | None           | None           | None           | None           | None           | None           | None            | None            | None            | None            | None            | None            | None            | None            | None            | None            | None            | None            | None            | None            |
| ...           | ...      | ...            | ...            | ...            | ...            | ...            | ...            | ...            | ...            | ...            | ...            | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             |
*/
CREATE TABLE Checkins (
    business_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Business.business_id</fk>
    day_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Days.day_id</fk>
    label_time_0 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None'}</values>
    label_time_1 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None'}</values>
    label_time_2 TEXT NOT NULL,
        -- <values>{'Low', 'Medium', 'None'}</values>
    label_time_3 TEXT NOT NULL,
        -- <values>{'Low', 'Medium', 'None'}</values>
    label_time_4 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None'}</values>
    label_time_5 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_6 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_7 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_8 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_9 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_10 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_11 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_12 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_13 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_14 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_15 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_16 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_17 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_18 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_19 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_20 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_21 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_22 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    label_time_23 TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None'}</values>
    PRIMARY KEY (business_id, day_id),
    FOREIGN KEY (day_id) REFERENCES Days(day_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

/*
Table: Compliments
Rows: 11
Sample rows:
| compliment_id   | compliment_type   |
|-----------------|-------------------|
| 1               | photos            |
| 2               | cool              |
| 3               | hot               |
| 4               | note              |
| 5               | more              |
| ...             | ...               |
*/
CREATE TABLE Compliments (
    compliment_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    compliment_type TEXT NOT NULL
        -- <example>'photos'</example>
);

/*
Table: Days
Rows: 7
All rows:
|   day_id | day_of_week   |
|----------|---------------|
|        1 | Sunday        |
|        2 | Monday        |
|        3 | Tuesday       |
|        4 | Wednesday     |
|        5 | Thursday      |
|        6 | Friday        |
|        7 | Saturday      |
*/
CREATE TABLE Days (
    day_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    day_of_week TEXT NOT NULL
        -- <values>{'Friday', 'Monday', 'Saturday', 'Sunday', 'Thursday', 'Tuesday', 'Wednesday'}</values>
);

/*
Table: Elite
Rows: 16366
Sample rows:
| user_id   | year_id   |
|-----------|-----------|
| 3         | 2010      |
| 3         | 2011      |
| 3         | 2012      |
| 3         | 2013      |
| 3         | 2014      |
| ...       | ...       |
*/
CREATE TABLE Elite (
    user_id INTEGER NOT NULL,
        -- <example>3</example>
        -- <fk> -> Users.user_id</fk>
    year_id INTEGER NOT NULL,
        -- <example>2010</example>
        -- <fk> -> Years.year_id</fk>
    PRIMARY KEY (user_id, year_id),
    FOREIGN KEY (year_id) REFERENCES Years(year_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id)
);

/*
Table: Reviews
Rows: 322906
Sample rows:
| business_id   | user_id   | review_stars   | review_votes_funny   | review_votes_useful   | review_votes_cool   | review_length   |
|---------------|-----------|----------------|----------------------|-----------------------|---------------------|-----------------|
| 1             | 36129     | 2              | None                 | None                  | None                | Medium          |
| 1             | 40299     | 1              | None                 | None                  | None                | Short           |
| 1             | 59125     | 5              | None                 | None                  | None                | Short           |
| 1             | 60776     | 1              | Low                  | Low                   | None                | Long            |
| 1             | 62013     | 5              | None                 | None                  | Low                 | Medium          |
| ...           | ...       | ...            | ...                  | ...                   | ...                 | ...             |
*/
CREATE TABLE Reviews (
    business_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Business.business_id</fk>
    user_id INTEGER NOT NULL,
        -- <example>36129</example>
        -- <fk> -> Users.user_id</fk>
    review_stars INTEGER NOT NULL,
        -- <example>2</example>
    review_votes_funny TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    review_votes_useful TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    review_votes_cool TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    review_length TEXT NOT NULL,
        -- <values>{'Long', 'Medium', 'Short'}</values>
    PRIMARY KEY (business_id, user_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

/*
Table: Tips
Rows: 87157
Sample rows:
| business_id   | user_id   | likes   | tip_length   |
|---------------|-----------|---------|--------------|
| 2             | 12490     | 0       | Medium       |
| 2             | 16328     | 0       | Medium       |
| 2             | 19191     | 0       | Short        |
| 2             | 25891     | 0       | Medium       |
| 2             | 34759     | 0       | Medium       |
| ...           | ...       | ...     | ...          |
*/
CREATE TABLE Tips (
    business_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> Business.business_id</fk>
    user_id INTEGER NOT NULL,
        -- <example>12490</example>
        -- <fk> -> Users.user_id</fk>
    likes INTEGER NOT NULL,
        -- <example>0</example>
    tip_length TEXT NOT NULL,
        -- <values>{'Long', 'Medium', 'Short'}</values>
    PRIMARY KEY (business_id, user_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (business_id) REFERENCES Business(business_id)
);

/*
Table: Users
Rows: 70817
Sample rows:
| user_id   | user_yelping_since_year   | user_average_stars   | user_votes_funny   | user_votes_useful   | user_votes_cool   | user_review_count   | user_fans   |
|-----------|---------------------------|----------------------|--------------------|---------------------|-------------------|---------------------|-------------|
| 1         | 2012                      | 4.0                  | Low                | Low                 | Low               | Medium              | Low         |
| 2         | 2010                      | 2.5                  | None               | Medium              | Low               | Medium              | None        |
| 3         | 2009                      | 4.0                  | Uber               | Uber                | Uber              | High                | Medium      |
| 4         | 2008                      | 4.5                  | None               | Medium              | Low               | Medium              | None        |
| 5         | 2010                      | 5.0                  | None               | Low                 | Low               | Low                 | None        |
| ...       | ...                       | ...                  | ...                | ...                 | ...               | ...                 | ...         |
*/
CREATE TABLE Users (
    user_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    user_yelping_since_year INTEGER NOT NULL,
        -- <example>2012</example>
    user_average_stars TEXT NOT NULL,
        -- <values>{'0.0', '1.0', '1.5', '2.0', '2.5', '3.0', '3.5', '4.0', '4.5', '5.0'}</values>
    user_votes_funny TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    user_votes_useful TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    user_votes_cool TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
    user_review_count TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'Uber'}</values>
    user_fans TEXT NOT NULL
        -- <values>{'High', 'Low', 'Medium', 'None', 'Uber'}</values>
);

/*
Table: Users_Compliments
Rows: 98810
Sample rows:
| compliment_id   | user_id   | number_of_compliments   |
|-----------------|-----------|-------------------------|
| 1               | 3         | Medium                  |
| 1               | 19        | Low                     |
| 1               | 45        | Low                     |
| 1               | 53        | Low                     |
| 1               | 102       | Low                     |
| ...             | ...       | ...                     |
*/
CREATE TABLE Users_Compliments (
    compliment_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Compliments.compliment_id</fk>
    user_id INTEGER NOT NULL,
        -- <example>3</example>
        -- <fk> -> Users.user_id</fk>
    number_of_compliments TEXT NOT NULL,
        -- <values>{'High', 'Low', 'Medium', 'Uber'}</values>
    PRIMARY KEY (compliment_id, user_id),
    FOREIGN KEY (user_id) REFERENCES Users(user_id),
    FOREIGN KEY (compliment_id) REFERENCES Compliments(compliment_id)
);

/*
Table: Years
Rows: 10
All rows:
|   year_id |   actual_year |
|-----------|---------------|
|      2005 |          2005 |
|      2006 |          2006 |
|      2007 |          2007 |
|      2008 |          2008 |
|      2009 |          2009 |
|      2010 |          2010 |
|      2011 |          2011 |
|      2012 |          2012 |
|      2013 |          2013 |
|      2014 |          2014 |
*/
CREATE TABLE Years (
    year_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>2005</example>
    actual_year INTEGER NOT NULL
        -- <example>2005</example>
);
```