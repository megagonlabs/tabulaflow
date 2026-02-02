```sql
-- Database: movie_platform

-- Table: lists (79565 rows)
CREATE TABLE lists (
    user_id INTEGER NULL,
        -- <example>88260493</example>
        -- <fk> -> lists_users.user_id</fk>
    list_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    list_title TEXT NULL,
        -- <example>'Films that made your kid sister cry'</example>
    list_movie_number INTEGER NULL,
        -- <example>5</example>
    list_update_timestamp_utc TEXT NULL,
        -- <example>'2019-01-24 19:16:18'</example>
    list_creation_timestamp_utc TEXT NULL,
        -- <example>'2009-11-11 00:02:21'</example>
    list_followers INTEGER NULL,
        -- <example>5</example>
    list_url TEXT NULL,
        -- <example>'http://mubi.com/lists/films-that-made-your-kid-sister-cry'</example>
    list_comments INTEGER NULL,
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

-- Table: lists_users (80311 rows)
CREATE TABLE lists_users (
    user_id INTEGER NOT NULL,
        -- <example>2385</example>
        -- <fk> -> lists.user_id</fk>
    list_id INTEGER NOT NULL,
        -- <example>192287</example>
        -- <fk> -> lists.list_id</fk>
    list_update_date_utc TEXT NULL,
        -- <example>'2019-11-26'</example>
    list_creation_date_utc TEXT NULL,
        -- <example>'2009-12-18'</example>
    user_trialist INTEGER NULL,
        -- <example>1</example>
    user_subscriber INTEGER NULL,
        -- <example>1</example>
    user_avatar_image_url TEXT NULL,
        -- <example>'https://assets.mubicdn.net/images/avatars/74983/images-w150.jpg?1523895214'</example>
    user_cover_image_url TEXT NULL,
        -- <example>'https://assets.mubicdn.net/images/cover_images/12788/images-small.jpg?1406887796'</example>
    user_eligible_for_trial TEXT NULL,
        -- <values>{'0', '1'}</values>
    user_has_payment_method TEXT NULL,
        -- <values>{'0', '1'}</values>
    PRIMARY KEY (user_id, list_id),
    FOREIGN KEY (list_id) REFERENCES lists(list_id),
    FOREIGN KEY (user_id) REFERENCES lists(user_id)
);

-- Table: movies (226087 rows)
CREATE TABLE movies (
    movie_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    movie_title TEXT NULL,
        -- <example>'La Antena'</example>
    movie_release_year INTEGER NULL,
        -- <example>2007</example>
    movie_url TEXT NULL,
        -- <example>'http://mubi.com/films/la-antena'</example>
    movie_title_language TEXT NULL,
        -- <values>{'en'}</values>
    movie_popularity INTEGER NULL,
        -- <example>105</example>
    movie_image_url TEXT NULL,
        -- <example>'https://images.mubicdn.net/images/film/1/cache-7927-1581389497/image-w1280.jpg'</example>
    director_id TEXT NULL,
        -- <example>'131'</example>
    director_name TEXT NULL,
        -- <example>'Esteban Sapir'</example>
    director_url TEXT NULL
        -- <example>'http://mubi.com/cast/esteban-sapir'</example>
);

-- Table: ratings (15517252 rows)
CREATE TABLE ratings (
    movie_id INTEGER NULL,
        -- <example>1066</example>
        -- <fk> -> movies.movie_id</fk>
    rating_id INTEGER NULL,
        -- <example>15610495</example>
        -- <fk> -> ratings.rating_id</fk>
    rating_url TEXT NULL,
        -- <example>'http://mubi.com/films/pavee-lackeen-the-traveller-girl/ratings/15610495'</example>
    rating_score INTEGER NULL,
        -- <example>3</example>
    rating_timestamp_utc TEXT NULL,
        -- <example>'2017-06-10 12:38:33'</example>
    critic TEXT NULL,
        -- <example>'I am a bit disappointed by this documentary film I...king. Otherwise it is O.K. and rather interesting.'</example>
    critic_likes INTEGER NULL,
        -- <example>0</example>
    critic_comments INTEGER NULL,
        -- <example>0</example>
    user_id INTEGER NULL,
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

-- Table: ratings_users (4297641 rows)
CREATE TABLE ratings_users (
    user_id INTEGER NULL,
        -- <example>41579158</example>
        -- <fk> -> lists_users.user_id</fk>
    rating_date_utc TEXT NULL,
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