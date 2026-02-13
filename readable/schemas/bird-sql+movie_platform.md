```sql
-- Database: movie_platform

/*
Schema: NULLTable: lists
Rows: 79565
Sample rows:
| user_id   | list_id   | list_title                          | list_movie_number   | list_update_timestamp_utc   | list_creation_timestamp_utc   | list_followers   | list_url                                                  | list_comments   | list_description                                                                                          | list_cover_image_url                                                   | list_first_image_url                                                  | list_second_image_url                                                 | list_third_image_url                                                  |
|-----------|-----------|-------------------------------------|---------------------|-----------------------------|-------------------------------|------------------|-----------------------------------------------------------|-----------------|-----------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------|-----------------------------------------------------------------------|-----------------------------------------------------------------------|-----------------------------------------------------------------------|
| 88260493  | 1         | Films that made your kid sister cry | 5                   | 2019-01-24 19:16:18         | 2009-11-11 00:02:21           | 5                | http://mubi.com/lists/films-that-made-your-kid-sister-cry | 3               | <p>Don’t be such a baby!!</p>
<p><strong>bold</strong></p>                                                                                                           | https://assets.mubicdn.net/images/film/3822/image-w1280.jpg?1445914994 | https://assets.mubicdn.net/images/film/3822/image-w320.jpg?1445914994 | https://assets.mubicdn.net/images/film/506/image-w320.jpg?1543838422  | https://assets.mubicdn.net/images/film/485/image-w320.jpg?1575331204  |
| 45204418  | 2         | Headscratchers                      | 3                   | 2018-12-03 15:12:20         | 2009-11-11 00:05:11           | 1                | http://mubi.com/lists/headscratchers                      | 2               | <p>Films that need at least two viewings to really make sense.</p>
<p>Or at least… they did for <em>me</em>.</p>                                                                                                           | https://assets.mubicdn.net/images/film/4343/image-w1280.jpg?1583331932 | https://assets.mubicdn.net/images/film/4343/image-w320.jpg?1583331932 | https://assets.mubicdn.net/images/film/159/image-w320.jpg?1548864573  | https://assets.mubicdn.net/images/film/142/image-w320.jpg?1544094102  |
| 48905025  | 3         | Sexy Time Movies                    | 7                   | 2019-05-30 03:00:07         | 2009-11-11 00:20:00           | 6                | http://mubi.com/lists/sexy-time-movies                    | 5               | <p>Films that get you in the mood…for love. In development.</p>
<p>Remarks</p>
<p><strong>Enter the ...eauteurs.com/films/2377" rel="nofollow">Enter the Void</a> then you’ll know why that’s on this list.                                                                                                           | https://assets.mubicdn.net/images/film/3491/image-w1280.jpg?1564112978 | https://assets.mubicdn.net/images/film/3491/image-w320.jpg?1564112978 | https://assets.mubicdn.net/images/film/2377/image-w320.jpg?1564675204 | https://assets.mubicdn.net/images/film/2874/image-w320.jpg?1546574412 |
| 12074910  | 7         | This is America                     | 11                  | 2019-01-24 19:16:18         | 2009-11-11 00:32:52           | 9                | http://mubi.com/lists/this-is-america                     | 3               | <p>Stories of the people, place and things.</p>                                                           | https://assets.mubicdn.net/images/film/4058/image-w1280.jpg?1546815657 | https://assets.mubicdn.net/images/film/4058/image-w320.jpg?1546815657 | https://assets.mubicdn.net/images/film/1033/image-w320.jpg?1553538051 | https://assets.mubicdn.net/images/film/407/image-w320.jpg?1490057681  |
| 67171533  | 8         | Best Documentaries                  | 41                  | 2020-04-25 05:55:07         | 2009-11-11 00:41:10           | 90               | http://mubi.com/lists/best-documentaries                  | 4               | <p>See also: <a href="http://www.theauteurs.com/lists/31" rel="nofollow">Best Music Documentaries</a></p> | https://assets.mubicdn.net/images/film/470/image-w1280.jpg?1546480829  | https://assets.mubicdn.net/images/film/470/image-w320.jpg?1546480829  | https://assets.mubicdn.net/images/film/2115/image-w320.jpg?1563782406 | https://assets.mubicdn.net/images/film/1688/image-w320.jpg?1575033549 |
| ...       | ...       | ...                                 | ...                 | ...                         | ...                           | ...              | ...                                                       | ...             | ...                                                                                                       | ...                                                                    | ...                                                                   | ...                                                                   | ...                                                                   |
*/
CREATE TABLE lists (
    user_id INTEGER NOT NULL,
        -- <example>88260493</example>
        -- <fk> -> lists_users.user_id</fk>
    list_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    list_title TEXT NOT NULL,
        -- <example>'Films that made your kid sister cry'</example>
    list_movie_number INTEGER NOT NULL,
        -- <example>5</example>
    list_update_timestamp_utc TEXT NOT NULL,
        -- <example>'2019-01-24 19:16:18'</example>
    list_creation_timestamp_utc TEXT NOT NULL,
        -- <example>'2009-11-11 00:02:21'</example>
    list_followers INTEGER NOT NULL,
        -- <example>5</example>
    list_url TEXT NOT NULL,
        -- <example>'http://mubi.com/lists/films-that-made-your-kid-sister-cry'</example>
    list_comments INTEGER NOT NULL,
        -- <example>3</example>
    list_description TEXT NULL,
        -- <example>'<p>Don’t be such a baby!!</p>
<p><strong>bold</strong></p>'</example>
    list_cover_image_url TEXT NULL,
        -- <example>'https://assets.mubicdn.net/images/film/3822/image-w1280.jpg?1445914994'</example>
    list_first_image_url TEXT NULL,
        -- <example>'https://assets.mubicdn.net/images/film/3822/image-w320.jpg?1445914994'</example>
    list_second_image_url TEXT NULL,
        -- <example>'https://assets.mubicdn.net/images/film/506/image-w320.jpg?1543838422'</example>
    list_third_image_url TEXT NULL,
        -- <example>'https://assets.mubicdn.net/images/film/485/image-w320.jpg?1575331204'</example>
    FOREIGN KEY (user_id) REFERENCES lists_users(user_id)
);

/*
Schema: NULLTable: lists_users
Rows: 80311
Sample rows:
| user_id   | list_id   | list_update_date_utc   | list_creation_date_utc   | user_trialist   | user_subscriber   | user_avatar_image_url                                                      | user_cover_image_url   | user_eligible_for_trial   | user_has_payment_method   |
|-----------|-----------|------------------------|--------------------------|-----------------|-------------------|----------------------------------------------------------------------------|------------------------|---------------------------|---------------------------|
| 85981819  | 1969      | 2019-11-26             | 2009-12-18               | 1               | 1                 | https://assets.mubicdn.net/images/avatars/74983/images-w150.jpg?1523895214 | [NULL]                 | 0                         | 1                         |
| 85981819  | 3946      | 2020-05-01             | 2010-01-30               | 1               | 1                 | https://assets.mubicdn.net/images/avatars/74983/images-w150.jpg?1523895214 | [NULL]                 | 0                         | 1                         |
| 85981819  | 6683      | 2020-04-12             | 2010-03-31               | 1               | 1                 | https://assets.mubicdn.net/images/avatars/74983/images-w150.jpg?1523895214 | [NULL]                 | 0                         | 1                         |
| 85981819  | 8865      | 2018-12-14             | 2010-05-10               | 1               | 1                 | https://assets.mubicdn.net/images/avatars/74983/images-w150.jpg?1523895214 | [NULL]                 | 0                         | 1                         |
| 85981819  | 13796     | 2019-11-26             | 2010-08-25               | 1               | 1                 | https://assets.mubicdn.net/images/avatars/74983/images-w150.jpg?1523895214 | [NULL]                 | 0                         | 1                         |
| ...       | ...       | ...                    | ...                      | ...             | ...               | ...                                                                        | ...                    | ...                       | ...                       |
*/
CREATE TABLE lists_users (
    user_id INTEGER NOT NULL,
        -- <example>2385</example>
        -- <fk> -> lists.user_id</fk>
    list_id INTEGER NOT NULL,
        -- <example>192287</example>
        -- <fk> -> lists.list_id</fk>
    list_update_date_utc TEXT NOT NULL,
        -- <example>'2019-11-26'</example>
    list_creation_date_utc TEXT NOT NULL,
        -- <example>'2009-12-18'</example>
    user_trialist INTEGER NOT NULL,
        -- <example>1</example>
    user_subscriber INTEGER NOT NULL,
        -- <example>1</example>
    user_avatar_image_url TEXT NOT NULL,
        -- <example>'https://assets.mubicdn.net/images/avatars/74983/images-w150.jpg?1523895214'</example>
    user_cover_image_url TEXT NULL,
        -- <example>'https://assets.mubicdn.net/images/cover_images/12788/images-small.jpg?1406887796'</example>
    user_eligible_for_trial TEXT NOT NULL,
        -- <values>{'0', '1'}</values>
    user_has_payment_method TEXT NOT NULL,
        -- <values>{'0', '1'}</values>
    PRIMARY KEY (user_id, list_id),
    FOREIGN KEY (list_id) REFERENCES lists(list_id),
    FOREIGN KEY (user_id) REFERENCES lists(user_id)
);

/*
Schema: NULLTable: movies
Rows: 226087
Sample rows:
| movie_id   | movie_title                 | movie_release_year   | movie_url                                         | movie_title_language   | movie_popularity   | movie_image_url                                                                  | director_id   | director_name                  | director_url                                                             |
|------------|-----------------------------|----------------------|---------------------------------------------------|------------------------|--------------------|----------------------------------------------------------------------------------|---------------|--------------------------------|--------------------------------------------------------------------------|
| 1          | La Antena                   | 2007                 | http://mubi.com/films/la-antena                   | en                     | 105                | https://images.mubicdn.net/images/film/1/cache-7927-1581389497/image-w1280.jpg   | 131           | Esteban Sapir                  | http://mubi.com/cast/esteban-sapir                                       |
| 2          | Elementary Particles        | 2006                 | http://mubi.com/films/elementary-particles        | en                     | 23                 | https://images.mubicdn.net/images/film/2/cache-512179-1581389841/image-w1280.jpg | 73            | Oskar Roehler                  | http://mubi.com/cast/oskar-roehler                                       |
| 3          | It's Winter                 | 2006                 | http://mubi.com/films/its-winter                  | en                     | 21                 | https://images.mubicdn.net/images/film/3/cache-7929-1481539519/image-w1280.jpg   | 82            | Rafi Pitts                     | http://mubi.com/cast/rafi-pitts                                          |
| 4          | Kirikou and the Wild Beasts | 2005                 | http://mubi.com/films/kirikou-and-the-wild-beasts | en                     | 46                 | https://images.mubicdn.net/images/film/4/cache-7930-1568880017/image-w1280.jpg   | 89, 90        | Michel Ocelot, Bénédicte Galup | http://mubi.com/cast/michel-ocelot, http://mubi.com/cast/benedicte-galup |
| 5          | Padre Nuestro               | 2007                 | http://mubi.com/films/padre-nuestro               | en                     | 7                  | https://images.mubicdn.net/images/film/5/cache-7931-1581390636/image-w1280.jpg   | 92            | Christopher Zalla              | http://mubi.com/cast/christopher-zalla                                   |
| ...        | ...                         | ...                  | ...                                               | ...                    | ...                | ...                                                                              | ...           | ...                            | ...                                                                      |
*/
CREATE TABLE movies (
    movie_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    movie_title TEXT NOT NULL,
        -- <example>'La Antena'</example>
    movie_release_year INTEGER NULL,
        -- <example>2007</example>
    movie_url TEXT NOT NULL,
        -- <example>'http://mubi.com/films/la-antena'</example>
    movie_title_language TEXT NOT NULL,
        -- <values>{'en'}</values>
    movie_popularity INTEGER NOT NULL,
        -- <example>105</example>
    movie_image_url TEXT NULL,
        -- <example>'https://images.mubicdn.net/images/film/1/cache-7927-1581389497/image-w1280.jpg'</example>
    director_id TEXT NOT NULL,
        -- <example>'131'</example>
    director_name TEXT NULL,
        -- <example>'Esteban Sapir'</example>
    director_url TEXT NOT NULL
        -- <example>'http://mubi.com/cast/esteban-sapir'</example>
);

/*
Schema: NULLTable: ratings
Rows: 15517252
Sample rows:
| movie_id   | rating_id   | rating_url                                                              | rating_score   | rating_timestamp_utc   | critic                                                                                                                                                                                                      | critic_likes   | critic_comments   | user_id   | user_trialist   | user_subscriber   | user_eligible_for_trial   | user_has_payment_method   |
|------------|-------------|-------------------------------------------------------------------------|----------------|------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------|-------------------|-----------|-----------------|-------------------|---------------------------|---------------------------|
| 1066       | 15610495    | http://mubi.com/films/pavee-lackeen-the-traveller-girl/ratings/15610495 | 3              | 2017-06-10 12:38:33    | [NULL]                                                                                                                                                                                                      | 0              | 0                 | 41579158  | 0               | 0                 | 1                         | 0                         |
| 1066       | 10704606    | http://mubi.com/films/pavee-lackeen-the-traveller-girl/ratings/10704606 | 2              | 2014-08-15 23:42:31    | [NULL]                                                                                                                                                                                                      | 0              | 0                 | 85981819  | 1               | 1                 | 0                         | 1                         |
| 1066       | 10177114    | http://mubi.com/films/pavee-lackeen-the-traveller-girl/ratings/10177114 | 2              | 2014-01-30 13:21:57    | [NULL]                                                                                                                                                                                                      | 0              | 0                 | 4208563   | 0               | 0                 | 1                         | 1                         |
| 1066       | 10130280    | http://mubi.com/films/pavee-lackeen-the-traveller-girl/ratings/10130280 | 3              | 2014-01-19 01:04:23    | I am a bit disappointed by this documentary film I've been wanting to watch for years as it is way l... imagined and rather cheaply made technically speaking. Otherwise it is O.K. and rather interesting. | 0              | 0                 | 9820140   | 0               | 0                 | 1                         | 0                         |
| 1066       | 8357049     | http://mubi.com/films/pavee-lackeen-the-traveller-girl/ratings/8357049  | 4              | 2012-10-02 18:28:47    | [NULL]                                                                                                                                                                                                      | 0              | 0                 | 68654088  | 0               | 0                 | 1                         | 1                         |
| ...        | ...         | ...                                                                     | ...            | ...                    | ...                                                                                                                                                                                                         | ...            | ...               | ...       | ...             | ...               | ...                       | ...                       |
*/
CREATE TABLE ratings (
    movie_id INTEGER NOT NULL,
        -- <example>1066</example>
        -- <fk> -> movies.movie_id</fk>
    rating_id INTEGER NOT NULL,
        -- <example>15610495</example>
        -- <fk> -> ratings.rating_id</fk>
    rating_url TEXT NOT NULL,
        -- <example>'http://mubi.com/films/pavee-lackeen-the-traveller-girl/ratings/15610495'</example>
    rating_score INTEGER NULL,
        -- <example>3</example>
    rating_timestamp_utc TEXT NOT NULL,
        -- <example>'2017-06-10 12:38:33'</example>
    critic TEXT NULL,
        -- <example>'I am a bit disappointed by this documentary film I...king. Otherwise it is O.K. and rather interesting.'</example>
    critic_likes INTEGER NOT NULL,
        -- <example>0</example>
    critic_comments INTEGER NOT NULL,
        -- <example>0</example>
    user_id INTEGER NOT NULL,
        -- <example>41579158</example>
        -- <fk> -> lists_users.user_id</fk>
        -- <fk> -> ratings_users.user_id</fk>
    user_trialist INTEGER NULL,
        -- <example>0</example>
    user_subscriber INTEGER NULL,
        -- <example>0</example>
    user_eligible_for_trial INTEGER NULL,
        -- <example>1</example>
    user_has_payment_method INTEGER NULL,
        -- <example>0</example>
    FOREIGN KEY (movie_id) REFERENCES movies(movie_id),
    FOREIGN KEY (user_id) REFERENCES lists_users(user_id),
    FOREIGN KEY (rating_id) REFERENCES ratings(rating_id),
    FOREIGN KEY (user_id) REFERENCES ratings_users(user_id)
);

/*
Schema: NULLTable: ratings_users
Rows: 4297641
Sample rows:
| user_id   | rating_date_utc   | user_trialist   | user_subscriber   | user_avatar_image_url                                                                                      | user_cover_image_url   | user_eligible_for_trial   | user_has_payment_method   |
|-----------|-------------------|-----------------|-------------------|------------------------------------------------------------------------------------------------------------|------------------------|---------------------------|---------------------------|
| 41579158  | 2017-06-10        | 0               | 0                 | https://assets.mubicdn.net/images/avatars/74283/images-w150.jpg?1523895155                                 | [NULL]                 | 1                         | 0                         |
| 68654088  | 2012-10-02        | 0               | 0                 | https://assets.mubicdn.net/images/avatars/27714/images-w150.jpg?1523889463                                 | [NULL]                 | 1                         | 1                         |
| 84114365  | 2010-12-25        | 0               | 0                 | https://assets.mubicdn.net/images/avatars/1808/images-w150.jpg?1523883471                                  | [NULL]                 | 1                         | 0                         |
| 29755671  | 2010-11-15        | 0               | 0                 | //mubi.com/assets/placeholders/avatar-c68833eec06a12b110c74dd2fa1709ae983ead021e695f886dcfafda0da3c6ed.png | [NULL]                 | 1                         | 0                         |
| 93302487  | 2010-01-05        | 0               | 0                 | https://assets.mubicdn.net/images/avatars/12246/images-w150.jpg?1523885889                                 | [NULL]                 | 1                         | 0                         |
| ...       | ...               | ...             | ...               | ...                                                                                                        | ...                    | ...                       | ...                       |
*/
CREATE TABLE ratings_users (
    user_id INTEGER NOT NULL,
        -- <example>41579158</example>
        -- <fk> -> lists_users.user_id</fk>
    rating_date_utc TEXT NOT NULL,
        -- <example>'2017-06-10'</example>
    user_trialist INTEGER NULL,
        -- <example>0</example>
    user_subscriber INTEGER NULL,
        -- <example>0</example>
    user_avatar_image_url TEXT NULL,
        -- <example>'https://assets.mubicdn.net/images/avatars/74283/images-w150.jpg?1523895155'</example>
    user_cover_image_url TEXT NULL,
        -- <example>'https://assets.mubicdn.net/images/cover_images/37844/images-small.png?1444549039'</example>
    user_eligible_for_trial INTEGER NULL,
        -- <example>1</example>
    user_has_payment_method INTEGER NULL,
        -- <example>0</example>
    FOREIGN KEY (user_id) REFERENCES lists_users(user_id)
);
```