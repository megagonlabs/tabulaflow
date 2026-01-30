```sql
-- Database: movielens

-- Table: actors (98690 rows)
CREATE TABLE actors (
    actorid INTEGER NOT NULL PRIMARY KEY,  -- e.g. 4
    a_gender TEXT NOT NULL,  -- values: {'F', 'M'}
    a_quality INTEGER NOT NULL  -- e.g. 4
);

-- Table: directors (2201 rows)
CREATE TABLE directors (
    directorid INTEGER NOT NULL PRIMARY KEY,  -- e.g. 7387
    d_quality INTEGER NOT NULL,  -- e.g. 0
    avg_revenue INTEGER NOT NULL  -- e.g. 0
);

-- Table: movies (3832 rows)
CREATE TABLE movies (
    movieid INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1672052
    year INTEGER NOT NULL,  -- e.g. 3
    isEnglish TEXT NOT NULL,  -- values: {'F', 'T'}
    country TEXT NOT NULL,  -- values: {'France', 'UK', 'USA', 'other'}
    runningtime INTEGER NOT NULL  -- e.g. 2
);

-- Table: movies2actors (138349 rows)
CREATE TABLE movies2actors (
    movieid INTEGER NOT NULL,  -- e.g. 1672052; FK -> movies.movieid
    actorid INTEGER NOT NULL,  -- e.g. 88796; FK -> actors.actorid
    cast_num INTEGER NOT NULL,  -- e.g. 0
    PRIMARY KEY (movieid, actorid),
    FOREIGN KEY (actorid) REFERENCES actors(actorid),
    FOREIGN KEY (movieid) REFERENCES movies(movieid)
);

-- Table: movies2directors (4141 rows)
CREATE TABLE movies2directors (
    movieid INTEGER NOT NULL,  -- e.g. 1672052; FK -> movies.movieid
    directorid INTEGER NOT NULL,  -- e.g. 22397; FK -> directors.directorid
    genre TEXT NOT NULL,  -- values: {'Action', 'Adventure', 'Animation', 'Comedy', 'Crime', 'Documentary', 'Drama', 'Horror', 'Other'}
    PRIMARY KEY (movieid, directorid),
    FOREIGN KEY (directorid) REFERENCES directors(directorid),
    FOREIGN KEY (movieid) REFERENCES movies(movieid)
);

-- Table: u2base (996159 rows)
CREATE TABLE u2base (
    userid INTEGER NOT NULL,  -- e.g. 1; FK -> users.userid
    movieid INTEGER NOT NULL,  -- e.g. 1684486; FK -> movies.movieid
    rating TEXT NOT NULL,  -- values: {'1', '2', '3', '4', '5'}
    PRIMARY KEY (userid, movieid),
    FOREIGN KEY (movieid) REFERENCES movies(movieid),
    FOREIGN KEY (userid) REFERENCES users(userid)
);

-- Table: users (6039 rows)
CREATE TABLE users (
    userid INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    age TEXT NOT NULL,  -- values: {'1', '18', '25', '35', '45', '50', '56'}
    u_gender TEXT NOT NULL,  -- values: {'F', 'M'}
    occupation TEXT NOT NULL  -- values: {'1', '2', '3', '4', '5'}
);
```