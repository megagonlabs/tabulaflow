```sql
-- Database: movielens

/*
Table: actors
Rows: 98690
Sample rows:
| actorid   | a_gender   | a_quality   |
|-----------|------------|-------------|
| 4         | M          | 4           |
| 16        | M          | 0           |
| 28        | M          | 4           |
| 566       | M          | 4           |
| 580       | M          | 4           |
| ...       | ...        | ...         |
*/
CREATE TABLE actors (
    actorid INTEGER NOT NULL PRIMARY KEY,
        -- <example>4</example>
    a_gender TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    a_quality INTEGER NOT NULL
        -- <example>4</example>
);

/*
Table: directors
Rows: 2201
Sample rows:
| directorid   | d_quality   | avg_revenue   |
|--------------|-------------|---------------|
| 67           | 4           | 1             |
| 92           | 2           | 3             |
| 284          | 4           | 0             |
| 708          | 4           | 1             |
| 746          | 4           | 4             |
| ...          | ...         | ...           |
*/
CREATE TABLE directors (
    directorid INTEGER NOT NULL PRIMARY KEY,
        -- <example>7387</example>
    d_quality INTEGER NOT NULL,
        -- <example>0</example>
    avg_revenue INTEGER NOT NULL
        -- <example>0</example>
);

/*
Table: movies
Rows: 3832
Sample rows:
| movieid   | year   | isEnglish   | country   | runningtime   |
|-----------|--------|-------------|-----------|---------------|
| 1672052   | 3      | T           | other     | 2             |
| 1672111   | 4      | T           | other     | 2             |
| 1672580   | 4      | T           | USA       | 3             |
| 1672716   | 4      | T           | USA       | 2             |
| 1672946   | 4      | T           | USA       | 0             |
| ...       | ...    | ...         | ...       | ...           |
*/
CREATE TABLE movies (
    movieid INTEGER NOT NULL PRIMARY KEY,
        -- <example>1672052</example>
    year INTEGER NOT NULL,
        -- <example>3</example>
    isEnglish TEXT NOT NULL,
        -- <values>{'F', 'T'}</values>
    country TEXT NOT NULL,
        -- <values>{'France', 'UK', 'USA', 'other'}</values>
    runningtime INTEGER NOT NULL
        -- <example>2</example>
);

/*
Table: movies2actors
Rows: 138349
Sample rows:
| movieid   | actorid   | cast_num   |
|-----------|-----------|------------|
| 1672580   | 981535    | 0          |
| 1672946   | 1094968   | 0          |
| 1673647   | 149985    | 0          |
| 1673647   | 261595    | 0          |
| 1673647   | 781357    | 0          |
| ...       | ...       | ...        |
*/
CREATE TABLE movies2actors (
    movieid INTEGER NOT NULL,
        -- <example>1672052</example>
        -- <fk> -> movies.movieid</fk>
    actorid INTEGER NOT NULL,
        -- <example>88796</example>
        -- <fk> -> actors.actorid</fk>
    cast_num INTEGER NOT NULL,
        -- <example>0</example>
    PRIMARY KEY (movieid, actorid),
    FOREIGN KEY (actorid) REFERENCES actors(actorid),
    FOREIGN KEY (movieid) REFERENCES movies(movieid)
);

/*
Table: movies2directors
Rows: 4141
Sample rows:
| movieid   | directorid   | genre   |
|-----------|--------------|---------|
| 1672111   | 54934        | Action  |
| 1672946   | 188940       | Action  |
| 1679461   | 179783       | Action  |
| 1691387   | 291700       | Action  |
| 1693305   | 14663        | Action  |
| ...       | ...          | ...     |
*/
CREATE TABLE movies2directors (
    movieid INTEGER NOT NULL,
        -- <example>1672052</example>
        -- <fk> -> movies.movieid</fk>
    directorid INTEGER NOT NULL,
        -- <example>22397</example>
        -- <fk> -> directors.directorid</fk>
    genre TEXT NOT NULL,
        -- <values>{'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Horror', 'Other'}</values>
    PRIMARY KEY (movieid, directorid),
    FOREIGN KEY (directorid) REFERENCES directors(directorid),
    FOREIGN KEY (movieid) REFERENCES movies(movieid)
);

/*
Table: u2base
Rows: 996159
Sample rows:
| userid   | movieid   | rating   |
|----------|-----------|----------|
| 2        | 1964242   | 1        |
| 2        | 2219779   | 1        |
| 3        | 1856939   | 1        |
| 4        | 2273044   | 1        |
| 5        | 1681655   | 1        |
| ...      | ...       | ...      |
*/
CREATE TABLE u2base (
    userid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> users.userid</fk>
    movieid INTEGER NOT NULL,
        -- <example>1684486</example>
        -- <fk> -> movies.movieid</fk>
    rating TEXT NOT NULL,
        -- <values>{'1', '2', '3', '4', '5'}</values>
    PRIMARY KEY (userid, movieid),
    FOREIGN KEY (movieid) REFERENCES movies(movieid),
    FOREIGN KEY (userid) REFERENCES users(userid)
);

/*
Table: users
Rows: 6039
Sample rows:
| userid   | age   | u_gender   | occupation   |
|----------|-------|------------|--------------|
| 1        | 1     | F          | 2            |
| 2        | 56    | M          | 3            |
| 3        | 25    | M          | 2            |
| 4        | 45    | M          | 4            |
| 5        | 25    | M          | 3            |
| ...      | ...   | ...        | ...          |
*/
CREATE TABLE users (
    userid INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    age TEXT NOT NULL,
        -- <values>{'1', '18', '25', '35', '45', '50', '56'}</values>
    u_gender TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    occupation TEXT NOT NULL
        -- <values>{'1', '2', '3', '4', '5'}</values>
);
```