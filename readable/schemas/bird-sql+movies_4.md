```sql
-- Database: movies_4

/*
Schema: NULLTable: country
Rows: 88
Sample rows:
| country_id   | country_iso_code   | country_name         |
|--------------|--------------------|----------------------|
| 128          | AE                 | United Arab Emirates |
| 129          | AF                 | Afghanistan          |
| 130          | AO                 | Angola               |
| 131          | AR                 | Argentina            |
| 132          | AT                 | Austria              |
| ...          | ...                | ...                  |
*/
CREATE TABLE country (
    country_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>128</example>
    country_iso_code TEXT NOT NULL,
        -- <example>'AE'</example>
    country_name TEXT NOT NULL
        -- <example>'United Arab Emirates'</example>
);

/*
Schema: NULLTable: department
Rows: 12
Sample rows:
| department_id   | department_name   |
|-----------------|-------------------|
| 1               | Camera            |
| 2               | Directing         |
| 3               | Production        |
| 4               | Writing           |
| 5               | Editing           |
| ...             | ...               |
*/
CREATE TABLE department (
    department_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    department_name TEXT NOT NULL
        -- <example>'Camera'</example>
);

/*
Schema: NULLTable: gender
Rows: 3
All rows:
|   gender_id | gender      |
|-------------|-------------|
|           0 | Unspecified |
|           1 | Female      |
|           2 | Male        |
*/
CREATE TABLE gender (
    gender_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
    gender TEXT NOT NULL
        -- <values>{'Female', 'Male', 'Unspecified'}</values>
);

/*
Schema: NULLTable: genre
Rows: 20
Sample rows:
| genre_id   | genre_name   |
|------------|--------------|
| 12         | Adventure    |
| 14         | Fantasy      |
| 16         | Animation    |
| 18         | Drama        |
| 27         | Horror       |
| ...        | ...          |
*/
CREATE TABLE genre (
    genre_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>12</example>
    genre_name TEXT NOT NULL
        -- <example>'Adventure'</example>
);

/*
Schema: NULLTable: keyword
Rows: 9794
Sample rows:
| keyword_id   | keyword_name     |
|--------------|------------------|
| 30           | individual       |
| 65           | holiday          |
| 74           | germany          |
| 75           | gunslinger       |
| 83           | saving the world |
| ...          | ...              |
*/
CREATE TABLE keyword (
    keyword_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>30</example>
    keyword_name TEXT NOT NULL
        -- <example>'individual'</example>
);

/*
Schema: NULLTable: language
Rows: 88
Sample rows:
| language_id   | language_code   | language_name   |
|---------------|-----------------|-----------------|
| 24574         | en              | English         |
| 24575         | sv              | svenska         |
| 24576         | de              | Deutsch         |
| 24577         | xx              | No Language     |
| 24578         | ja              | u65e5u672cu8a9e |
| ...           | ...             | ...             |
*/
CREATE TABLE language (
    language_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>24574</example>
    language_code TEXT NOT NULL,
        -- <example>'en'</example>
    language_name TEXT NOT NULL
        -- <example>'English'</example>
);

/*
Schema: NULLTable: language_role
Rows: 2
All rows:
|   role_id | language_role   |
|-----------|-----------------|
|         1 | Original        |
|         2 | Spoken          |
*/
CREATE TABLE language_role (
    role_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    language_role TEXT NOT NULL
        -- <values>{'Original', 'Spoken'}</values>
);

/*
Schema: NULLTable: movie
Rows: 4627
Sample rows:
| movie_id   | title           | budget   | homepage                                                      | overview                                                                                                                                                                                                    | popularity   | release_date   | revenue   | runtime   | movie_status   | tagline                                                                                                                                                     | vote_average   | vote_count   |
|------------|-----------------|----------|---------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|----------------|-----------|-----------|----------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------|--------------|
| 5          | Four Rooms      | 4000000  |                                                               | It's Ted the Bellhop's first night on the job...and the hotel's very unusual guests are about to pla...s. It seems that this evening's room service is serving up one unbelievable happening after another. | 22.87623     | 1995-12-09     | 4300000   | 98        | Released       | Twelve outrageous guests. Four scandalous requests. And one lone bellhop, in his first day on the job, who's in for the wildest New year's Eve of his life. | 6.5            | 530          |
| 11         | Star Wars       | 11000000 | http://www.starwars.com/films/star-wars-episode-iv-a-new-hope | Princess Leia is captured and held hostage by the evil Imperial forces in their effort to take over ...hing captain Han Solo team together with the loveable robot duo R2-D2 and C-3PO to rescue the beauti | 126.393695   | 1977-05-25     | 775398007 | 121       | Released       | A long time ago in a galaxy far, far away...                                                                                                                | 8.1            | 6624         |
| 12         | Finding Nemo    | 94000000 | http://movies.disney.com/finding-nemo                         | Nemo, an adventurous young clownfish, is unexpectedly taken from his Great Barrier Reef home to a de...r Marlin and a friendly but forgetful fish Dory to bring Nemo home -- meeting vegetarian sharks, sur | 85.688789    | 2003-05-30     | 940335536 | 100       | Released       | There are 3.7 trillion fish in the ocean, they're looking for one.                                                                                          | 7.6            | 6122         |
| 13         | Forrest Gump    | 55000000 |                                                               | A man with a low IQ has accomplished great things in his life and been present during significant hi... imagined he could do. Yet, despite all the things he has attained, his one true love eludes him. 'F | 138.133331   | 1994-07-06     | 677945399 | 142       | Released       | The world will never be the same, once you've seen it through the eyes of Forrest Gump.                                                                     | 8.2            | 7927         |
| 14         | American Beauty | 15000000 | http://www.dreamworks.com/ab/                                 | Lester Burnham, a depressed suburban father in a mid-life crisis, decides to turn his hectic life around after developing an infatuation with his daughter's attractive friend.                             | 80.878605    | 1999-09-15     | 356296601 | 122       | Released       | Look closer.                                                                                                                                                | 7.9            | 3313         |
| ...        | ...             | ...      | ...                                                           | ...                                                                                                                                                                                                         | ...          | ...            | ...       | ...       | ...            | ...                                                                                                                                                         | ...            | ...          |
*/
CREATE TABLE movie (
    movie_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>5</example>
    title TEXT NOT NULL,
        -- <example>'Four Rooms'</example>
    budget INTEGER NOT NULL,
        -- <example>4000000</example>
    homepage TEXT NOT NULL,
        -- <example>''</example>
    overview TEXT NOT NULL,
        -- <example>'It's Ted the Bellhop's first night on the job...an...rving up one unbelievable happening after another.'</example>
    popularity REAL NOT NULL,
        -- <example>22.876</example>
    release_date DATE NOT NULL,
        -- <example>'1995-12-09'</example>
    revenue INTEGER NOT NULL,
        -- <example>4300000</example>
    runtime INTEGER NOT NULL,
        -- <example>98</example>
    movie_status TEXT NOT NULL,
        -- <values>{'Post Production', 'Released', 'Rumored'}</values>
    tagline TEXT NOT NULL,
        -- <example>'Twelve outrageous guests. Four scandalous requests...o's in for the wildest New year's Eve of his life.'</example>
    vote_average REAL NOT NULL,
        -- <example>6.500</example>
    vote_count INTEGER NOT NULL
        -- <example>530</example>
);

/*
Schema: NULLTable: movie_cast
Rows: 59083
Sample rows:
| movie_id   | person_id   | character_name                | gender_id   | cast_order   |
|------------|-------------|-------------------------------|-------------|--------------|
| 285        | 85          | Captain Jack Sparrow          | 2           | 0            |
| 285        | 114         | Will Turner                   | 2           | 1            |
| 285        | 116         | Elizabeth Swann               | 1           | 2            |
| 285        | 1640        | William Bootstrap Bill Turner | 2           | 3            |
| 285        | 1619        | Captain Sao Feng              | 2           | 4            |
| ...        | ...         | ...                           | ...         | ...          |
*/
CREATE TABLE movie_cast (
    movie_id INTEGER NOT NULL,
        -- <example>285</example>
        -- <fk> -> movie.movie_id</fk>
    person_id INTEGER NOT NULL,
        -- <example>85</example>
        -- <fk> -> person.person_id</fk>
    character_name TEXT NOT NULL,
        -- <example>'Captain Jack Sparrow'</example>
    gender_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> gender.gender_id</fk>
    cast_order INTEGER NOT NULL,
        -- <example>0</example>
    FOREIGN KEY (gender_id) REFERENCES gender(gender_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id),
    FOREIGN KEY (person_id) REFERENCES person(person_id)
);

/*
Schema: NULLTable: movie_company
Rows: 13677
Sample rows:
| movie_id   | company_id   |
|------------|--------------|
| 5          | 14           |
| 5          | 59           |
| 11         | 1            |
| 11         | 306          |
| 12         | 3            |
| ...        | ...          |
*/
CREATE TABLE movie_company (
    movie_id INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    company_id INTEGER NOT NULL,
        -- <example>14</example>
        -- <fk> -> production_company.company_id</fk>
    FOREIGN KEY (company_id) REFERENCES production_company(company_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);

/*
Schema: NULLTable: movie_crew
Rows: 129581
Sample rows:
| movie_id   | person_id   | department_id   | job                     |
|------------|-------------|-----------------|-------------------------|
| 285        | 120         | 1               | Director of Photography |
| 285        | 1704        | 2               | Director                |
| 285        | 770         | 3               | Producer                |
| 285        | 1705        | 4               | Screenplay              |
| 285        | 1706        | 4               | Screenplay              |
| ...        | ...         | ...             | ...                     |
*/
CREATE TABLE movie_crew (
    movie_id INTEGER NOT NULL,
        -- <example>285</example>
        -- <fk> -> movie.movie_id</fk>
    person_id INTEGER NOT NULL,
        -- <example>120</example>
        -- <fk> -> person.person_id</fk>
    department_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> department.department_id</fk>
    job TEXT NOT NULL,
        -- <example>'Director of Photography'</example>
    FOREIGN KEY (department_id) REFERENCES department(department_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id),
    FOREIGN KEY (person_id) REFERENCES person(person_id)
);

/*
Schema: NULLTable: movie_genres
Rows: 12160
Sample rows:
| movie_id   | genre_id   |
|------------|------------|
| 5          | 35         |
| 5          | 80         |
| 11         | 12         |
| 11         | 28         |
| 11         | 878        |
| ...        | ...        |
*/
CREATE TABLE movie_genres (
    movie_id INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    genre_id INTEGER NOT NULL,
        -- <example>35</example>
        -- <fk> -> genre.genre_id</fk>
    FOREIGN KEY (genre_id) REFERENCES genre(genre_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);

/*
Schema: NULLTable: movie_keywords
Rows: 36162
Sample rows:
| movie_id   | keyword_id   |
|------------|--------------|
| 5          | 612          |
| 5          | 613          |
| 5          | 616          |
| 5          | 622          |
| 5          | 922          |
| ...        | ...          |
*/
CREATE TABLE movie_keywords (
    movie_id INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    keyword_id INTEGER NOT NULL,
        -- <example>612</example>
        -- <fk> -> keyword.keyword_id</fk>
    FOREIGN KEY (keyword_id) REFERENCES keyword(keyword_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);

/*
Schema: NULLTable: movie_languages
Rows: 11740
Sample rows:
| movie_id   | language_id   | language_role_id   |
|------------|---------------|--------------------|
| 5          | 24574         | 2                  |
| 11         | 24574         | 2                  |
| 12         | 24574         | 2                  |
| 13         | 24574         | 2                  |
| 14         | 24574         | 2                  |
| ...        | ...           | ...                |
*/
CREATE TABLE movie_languages (
    movie_id INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    language_id INTEGER NOT NULL,
        -- <example>24574</example>
        -- <fk> -> language.language_id</fk>
    language_role_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> language_role.role_id</fk>
    FOREIGN KEY (language_id) REFERENCES language(language_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id),
    FOREIGN KEY (language_role_id) REFERENCES language_role(role_id)
);

/*
Schema: NULLTable: person
Rows: 104838
Sample rows:
| person_id   | person_name   |
|-------------|---------------|
| 1           | George Lucas  |
| 2           | Mark Hamill   |
| 3           | Harrison Ford |
| 4           | Carrie Fisher |
| 5           | Peter Cushing |
| ...         | ...           |
*/
CREATE TABLE person (
    person_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    person_name TEXT NOT NULL
        -- <example>'George Lucas'</example>
);

/*
Schema: NULLTable: production_company
Rows: 5047
Sample rows:
| company_id   | company_name            |
|--------------|-------------------------|
| 1            | Lucasfilm               |
| 2            | Walt Disney Pictures    |
| 3            | Pixar Animation Studios |
| 4            | Paramount Pictures      |
| 5            | Columbia Pictures       |
| ...          | ...                     |
*/
CREATE TABLE production_company (
    company_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    company_name TEXT NOT NULL
        -- <example>'Lucasfilm'</example>
);

/*
Schema: NULLTable: production_country
Rows: 6436
Sample rows:
| movie_id   | country_id   |
|------------|--------------|
| 5          | 214          |
| 11         | 214          |
| 12         | 214          |
| 13         | 214          |
| 14         | 214          |
| ...        | ...          |
*/
CREATE TABLE production_country (
    movie_id INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> movie.movie_id</fk>
    country_id INTEGER NOT NULL,
        -- <example>214</example>
        -- <fk> -> country.country_id</fk>
    FOREIGN KEY (country_id) REFERENCES country(country_id),
    FOREIGN KEY (movie_id) REFERENCES movie(movie_id)
);
```