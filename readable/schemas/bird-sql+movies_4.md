```sql
-- Database: movies_4

-- Table: country (88 rows)
CREATE TABLE country (
    country_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 128
    country_iso_code TEXT,  -- e.g. 'AE'
    country_name TEXT  -- e.g. 'United Arab Emirates'
);

-- Table: department (12 rows)
CREATE TABLE department (
    department_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    department_name TEXT  -- e.g. 'Camera'
);

-- Table: gender (3 rows)
CREATE TABLE gender (
    gender_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 0
    gender TEXT  -- values: {'Female', 'Male', 'Unspecified'}
);

-- Table: genre (20 rows)
CREATE TABLE genre (
    genre_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 12
    genre_name TEXT  -- e.g. 'Adventure'
);

-- Table: keyword (9794 rows)
CREATE TABLE keyword (
    keyword_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 30
    keyword_name TEXT  -- e.g. 'individual'
);

-- Table: language (88 rows)
CREATE TABLE language (
    language_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 24574
    language_code TEXT,  -- e.g. 'en'
    language_name TEXT  -- e.g. 'English'
);

-- Table: language_role (2 rows)
CREATE TABLE language_role (
    role_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    language_role TEXT  -- values: {'Original', 'Spoken'}
);

-- Table: movie (4627 rows)
CREATE TABLE movie (
    movie_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 5
    title TEXT,  -- e.g. 'Four Rooms'
    budget INTEGER,  -- e.g. 4000000
    homepage TEXT,  -- e.g. ''
    overview TEXT,  -- e.g. 'It's Ted the Bellhop's first night on the job...an...rving up one unbelievable happening after another.'
    popularity REAL,  -- e.g. 22.876
    release_date DATE,  -- e.g. '1995-12-09'
    revenue INTEGER,  -- e.g. 4300000
    runtime INTEGER,  -- e.g. 98
    movie_status TEXT,  -- values: {'Post Production', 'Released', 'Rumored'}
    tagline TEXT,  -- e.g. 'Twelve outrageous guests. Four scandalous requests...o's in for the wildest New year's Eve of his life.'
    vote_average REAL,  -- e.g. 6.500
    vote_count INTEGER  -- e.g. 530
);

-- Table: movie_cast (59083 rows)
CREATE TABLE movie_cast (
    movie_id INTEGER,  -- e.g. 285; FK -> movie.movie_id
    person_id INTEGER,  -- e.g. 85; FK -> person.person_id
    character_name TEXT,  -- e.g. 'Captain Jack Sparrow'
    gender_id INTEGER,  -- e.g. 2; FK -> gender.gender_id
    cast_order INTEGER,  -- e.g. 0
    FOREIGN KEY (gender_id) REFERENCES gender(gender_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id),
    FOREIGN KEY (person_id) REFERENCES person(person_id)
);

-- Table: movie_company (13677 rows)
CREATE TABLE movie_company (
    movie_id INTEGER,  -- e.g. 5; FK -> movie.movie_id
    company_id INTEGER,  -- e.g. 14; FK -> production_company.company_id
    FOREIGN KEY (company_id) REFERENCES production_company(company_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);

-- Table: movie_crew (129581 rows)
CREATE TABLE movie_crew (
    movie_id INTEGER,  -- e.g. 285; FK -> movie.movie_id
    person_id INTEGER,  -- e.g. 120; FK -> person.person_id
    department_id INTEGER,  -- e.g. 1; FK -> department.department_id
    job TEXT,  -- e.g. 'Director of Photography'
    FOREIGN KEY (department_id) REFERENCES department(department_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id),
    FOREIGN KEY (person_id) REFERENCES person(person_id)
);

-- Table: movie_genres (12160 rows)
CREATE TABLE movie_genres (
    movie_id INTEGER,  -- e.g. 5; FK -> movie.movie_id
    genre_id INTEGER,  -- e.g. 35; FK -> genre.genre_id
    FOREIGN KEY (genre_id) REFERENCES genre(genre_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);

-- Table: movie_keywords (36162 rows)
CREATE TABLE movie_keywords (
    movie_id INTEGER,  -- e.g. 5; FK -> movie.movie_id
    keyword_id INTEGER,  -- e.g. 612; FK -> keyword.keyword_id
    FOREIGN KEY (keyword_id) REFERENCES keyword(keyword_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);

-- Table: movie_languages (11740 rows)
CREATE TABLE movie_languages (
    movie_id INTEGER,  -- e.g. 5; FK -> movie.movie_id
    language_id INTEGER,  -- e.g. 24574; FK -> language.language_id
    language_role_id INTEGER,  -- e.g. 2; FK -> language_role.role_id
    FOREIGN KEY (language_id) REFERENCES language(language_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id),
    FOREIGN KEY (language_role_id) REFERENCES language_role(role_id)
);

-- Table: person (104838 rows)
CREATE TABLE person (
    person_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    person_name TEXT  -- e.g. 'George Lucas'
);

-- Table: production_company (5047 rows)
CREATE TABLE production_company (
    company_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    company_name TEXT  -- e.g. 'Lucasfilm'
);

-- Table: production_country (6436 rows)
CREATE TABLE production_country (
    movie_id INTEGER,  -- e.g. 5; FK -> movie.movie_id
    country_id INTEGER,  -- e.g. 214; FK -> country.country_id
    FOREIGN KEY (country_id) REFERENCES country(country_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);
```