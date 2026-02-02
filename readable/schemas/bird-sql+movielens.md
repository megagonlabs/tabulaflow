```sql
-- Database: movielens

-- Table: actors (98690 rows)
CREATE TABLE actors (
    actorid INTEGER NOT NULL PRIMARY KEY,
        -- <example>4</example>
    a_gender TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    a_quality INTEGER NOT NULL
        -- <example>4</example>
);

-- Table: directors (2201 rows)
CREATE TABLE directors (
    directorid INTEGER NOT NULL PRIMARY KEY,
        -- <example>7387</example>
    d_quality INTEGER NOT NULL,
        -- <example>0</example>
    avg_revenue INTEGER NOT NULL
        -- <example>0</example>
);

-- Table: movies (3832 rows)
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

-- Table: movies2actors (138349 rows)
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

-- Table: movies2directors (4141 rows)
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

-- Table: u2base (996159 rows)
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

-- Table: users (6039 rows)
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