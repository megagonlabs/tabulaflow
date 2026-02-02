```sql
-- Database: movies_4

-- Table: country (88 rows)
CREATE TABLE country (
    country_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>128</example>
    country_iso_code TEXT NULL,
        -- <example>'AE'</example>
    country_name TEXT NULL
        -- <example>'United Arab Emirates'</example>
);

-- Table: department (12 rows)
CREATE TABLE department (
    department_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    department_name TEXT NULL
        -- <example>'Camera'</example>
);

-- Table: gender (3 rows)
CREATE TABLE gender (
    gender_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    gender TEXT NULL
        -- <values>{'Female', 'Male', 'Unspecified'}</values>
);

-- Table: genre (20 rows)
CREATE TABLE genre (
    genre_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>12</example>
    genre_name TEXT NULL
        -- <example>'Adventure'</example>
);

-- Table: keyword (9794 rows)
CREATE TABLE keyword (
    keyword_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>30</example>
    keyword_name TEXT NULL
        -- <example>'individual'</example>
);

-- Table: language (88 rows)
CREATE TABLE language (
    language_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>24574</example>
    language_code TEXT NULL,
        -- <example>'en'</example>
    language_name TEXT NULL
        -- <example>'English'</example>
);

-- Table: language_role (2 rows)
CREATE TABLE language_role (
    role_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    language_role TEXT NULL
        -- <values>{'Original', 'Spoken'}</values>
);

-- Table: movie (4627 rows)
CREATE TABLE movie (
    movie_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>5</example>
    title TEXT NULL,
        -- <example>'Four Rooms'</example>
    budget INTEGER NULL,
        -- <example>4000000</example>
    homepage TEXT NULL,
        -- <example>''</example>
    overview TEXT NULL,
        -- <example>'It's Ted the Bellhop's first night on the job...an...rving up one unbelievable happening after another.'</example>
    popularity REAL NULL,
        -- <example>22.876</example>
    release_date DATE NULL,
        -- <example>'1995-12-09'</example>
    revenue INTEGER NULL,
        -- <example>4300000</example>
    runtime INTEGER NULL,
        -- <example>98</example>
    movie_status TEXT NULL,
        -- <values>{'Post Production', 'Released', 'Rumored'}</values>
    tagline TEXT NULL,
        -- <example>'Twelve outrageous guests. Four scandalous requests...o's in for the wildest New year's Eve of his life.'</example>
    vote_average REAL NULL,
        -- <example>6.500</example>
    vote_count INTEGER NULL
        -- <example>530</example>
);

-- Table: movie_cast (59083 rows)
CREATE TABLE movie_cast (
    movie_id INTEGER NULL,
        -- <example>285</example>
        -- <fk> -> movie.movie_id</fk>
    person_id INTEGER NULL,
        -- <example>85</example>
        -- <fk> -> person.person_id</fk>
    character_name TEXT NULL,
        -- <example>'Captain Jack Sparrow'</example>
    gender_id INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> gender.gender_id</fk>
    cast_order INTEGER NULL,
        -- <example>0</example>
    FOREIGN KEY (gender_id) REFERENCES gender(gender_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id),
    FOREIGN KEY (person_id) REFERENCES person(person_id)
);

-- Table: movie_company (13677 rows)
CREATE TABLE movie_company (
    movie_id INTEGER NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    company_id INTEGER NULL,
        -- <example>14</example>
        -- <fk> -> production_company.company_id</fk>
    FOREIGN KEY (company_id) REFERENCES production_company(company_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);

-- Table: movie_crew (129581 rows)
CREATE TABLE movie_crew (
    movie_id INTEGER NULL,
        -- <example>285</example>
        -- <fk> -> movie.movie_id</fk>
    person_id INTEGER NULL,
        -- <example>120</example>
        -- <fk> -> person.person_id</fk>
    department_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> department.department_id</fk>
    job TEXT NULL,
        -- <example>'Director of Photography'</example>
    FOREIGN KEY (department_id) REFERENCES department(department_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id),
    FOREIGN KEY (person_id) REFERENCES person(person_id)
);

-- Table: movie_genres (12160 rows)
CREATE TABLE movie_genres (
    movie_id INTEGER NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    genre_id INTEGER NULL,
        -- <example>35</example>
        -- <fk> -> genre.genre_id</fk>
    FOREIGN KEY (genre_id) REFERENCES genre(genre_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);

-- Table: movie_keywords (36162 rows)
CREATE TABLE movie_keywords (
    movie_id INTEGER NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    keyword_id INTEGER NULL,
        -- <example>612</example>
        -- <fk> -> keyword.keyword_id</fk>
    FOREIGN KEY (keyword_id) REFERENCES keyword(keyword_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);

-- Table: movie_languages (11740 rows)
CREATE TABLE movie_languages (
    movie_id INTEGER NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    language_id INTEGER NULL,
        -- <example>24574</example>
        -- <fk> -> language.language_id</fk>
    language_role_id INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> language_role.role_id</fk>
    FOREIGN KEY (language_id) REFERENCES language(language_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id),
    FOREIGN KEY (language_role_id) REFERENCES language_role(role_id)
);

-- Table: person (104838 rows)
CREATE TABLE person (
    person_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    person_name TEXT NULL
        -- <example>'George Lucas'</example>
);

-- Table: production_company (5047 rows)
CREATE TABLE production_company (
    company_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    company_name TEXT NULL
        -- <example>'Lucasfilm'</example>
);

-- Table: production_country (6436 rows)
CREATE TABLE production_country (
    movie_id INTEGER NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    country_id INTEGER NULL,
        -- <example>214</example>
        -- <fk> -> country.country_id</fk>
    FOREIGN KEY (country_id) REFERENCES country(country_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);
```