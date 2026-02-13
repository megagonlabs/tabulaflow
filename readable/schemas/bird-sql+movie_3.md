```sql
-- Database: movie_3

/*
Schema: NULLTable: actor
Rows: 200
Sample rows:
| actor_id   | first_name   | last_name    | last_update           |
|------------|--------------|--------------|-----------------------|
| 1          | PENELOPE     | GUINESS      | 2006-02-15 04:34:33.0 |
| 2          | NICK         | WAHLBERG     | 2006-02-15 04:34:33.0 |
| 3          | ED           | CHASE        | 2006-02-15 04:34:33.0 |
| 4          | JENNIFER     | DAVIS        | 2006-02-15 04:34:33.0 |
| 5          | JOHNNY       | LOLLOBRIGIDA | 2006-02-15 04:34:33.0 |
| ...        | ...          | ...          | ...                   |
*/
CREATE TABLE actor (
    actor_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    first_name TEXT NOT NULL,
        -- <example>'PENELOPE'</example>
    last_name TEXT NOT NULL,
        -- <example>'GUINESS'</example>
    last_update DATETIME NOT NULL
        -- <example>'2006-02-15 04:34:33.0'</example>
);

/*
Schema: NULLTable: address
Rows: 603
Sample rows:
| address_id   | address              | address2   | district   | city_id   | postal_code   | phone       | last_update           |
|--------------|----------------------|------------|------------|-----------|---------------|-------------|-----------------------|
| 1            | 47 MySakila Drive    | [NULL]     | Alberta    | 300       |               |             | 2006-02-15 04:45:30.0 |
| 2            | 28 MySQL Boulevard   | [NULL]     | QLD        | 576       |               |             | 2006-02-15 04:45:30.0 |
| 3            | 23 Workhaven Lane    | [NULL]     | Alberta    | 300       |               | 14033335568 | 2006-02-15 04:45:30.0 |
| 4            | 1411 Lillydale Drive | [NULL]     | QLD        | 576       |               | 6172235589  | 2006-02-15 04:45:30.0 |
| 5            | 1913 Hanoi Way       |            | Nagasaki   | 463       | 35200         | 28303384290 | 2006-02-15 04:45:30.0 |
| ...          | ...                  | ...        | ...        | ...       | ...           | ...         | ...                   |
*/
CREATE TABLE address (
    address_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    address TEXT NOT NULL,
        -- <example>'47 MySakila Drive'</example>
    address2 TEXT NULL,
        -- <values>{''}</values>
    district TEXT NOT NULL,
        -- <example>'Alberta'</example>
    city_id INTEGER NOT NULL,
        -- <example>300</example>
        -- <fk> -> city.city_id</fk>
    postal_code TEXT NOT NULL,
        -- <example>''</example>
    phone TEXT NOT NULL,
        -- <example>''</example>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 04:45:30.0'</example>
    FOREIGN KEY (city_id) REFERENCES city(city_id)
);

/*
Schema: NULLTable: category
Rows: 16
Sample rows:
| category_id   | name      | last_update           |
|---------------|-----------|-----------------------|
| 1             | Action    | 2006-02-15 04:46:27.0 |
| 2             | Animation | 2006-02-15 04:46:27.0 |
| 3             | Children  | 2006-02-15 04:46:27.0 |
| 4             | Classics  | 2006-02-15 04:46:27.0 |
| 5             | Comedy    | 2006-02-15 04:46:27.0 |
| ...           | ...       | ...                   |
*/
CREATE TABLE category (
    category_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NOT NULL,
        -- <example>'Action'</example>
    last_update DATETIME NOT NULL
        -- <example>'2006-02-15 04:46:27.0'</example>
);

/*
Schema: NULLTable: city
Rows: 600
Sample rows:
| city_id   | city               | country_id   | last_update           |
|-----------|--------------------|--------------|-----------------------|
| 1         | A Corua (La Corua) | 87           | 2006-02-15 04:45:25.0 |
| 2         | Abha               | 82           | 2006-02-15 04:45:25.0 |
| 3         | Abu Dhabi          | 101          | 2006-02-15 04:45:25.0 |
| 4         | Acua               | 60           | 2006-02-15 04:45:25.0 |
| 5         | Adana              | 97           | 2006-02-15 04:45:25.0 |
| ...       | ...                | ...          | ...                   |
*/
CREATE TABLE city (
    city_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    city TEXT NOT NULL,
        -- <example>'A Corua (La Corua)'</example>
    country_id INTEGER NOT NULL,
        -- <example>87</example>
        -- <fk> -> country.country_id</fk>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 04:45:25.0'</example>
    FOREIGN KEY (country_id) REFERENCES country(country_id)
);

/*
Schema: NULLTable: country
Rows: 109
Sample rows:
| country_id   | country        | last_update           |
|--------------|----------------|-----------------------|
| 1            | Afghanistan    | 2006-02-15 04:44:00.0 |
| 2            | Algeria        | 2006-02-15 04:44:00.0 |
| 3            | American Samoa | 2006-02-15 04:44:00.0 |
| 4            | Angola         | 2006-02-15 04:44:00.0 |
| 5            | Anguilla       | 2006-02-15 04:44:00.0 |
| ...          | ...            | ...                   |
*/
CREATE TABLE country (
    country_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    country TEXT NOT NULL,
        -- <example>'Afghanistan'</example>
    last_update DATETIME NOT NULL
        -- <example>'2006-02-15 04:44:00.0'</example>
);

/*
Schema: NULLTable: customer
Rows: 599
Sample rows:
| customer_id   | store_id   | first_name   | last_name   | email                               | address_id   | active   | create_date           | last_update           |
|---------------|------------|--------------|-------------|-------------------------------------|--------------|----------|-----------------------|-----------------------|
| 1             | 1          | MARY         | SMITH       | MARY.SMITH@sakilacustomer.org       | 5            | 1        | 2006-02-14 22:04:36.0 | 2006-02-15 04:57:20.0 |
| 2             | 1          | PATRICIA     | JOHNSON     | PATRICIA.JOHNSON@sakilacustomer.org | 6            | 1        | 2006-02-14 22:04:36.0 | 2006-02-15 04:57:20.0 |
| 3             | 1          | LINDA        | WILLIAMS    | LINDA.WILLIAMS@sakilacustomer.org   | 7            | 1        | 2006-02-14 22:04:36.0 | 2006-02-15 04:57:20.0 |
| 4             | 2          | BARBARA      | JONES       | BARBARA.JONES@sakilacustomer.org    | 8            | 1        | 2006-02-14 22:04:36.0 | 2006-02-15 04:57:20.0 |
| 5             | 1          | ELIZABETH    | BROWN       | ELIZABETH.BROWN@sakilacustomer.org  | 9            | 1        | 2006-02-14 22:04:36.0 | 2006-02-15 04:57:20.0 |
| ...           | ...        | ...          | ...         | ...                                 | ...          | ...      | ...                   | ...                   |
*/
CREATE TABLE customer (
    customer_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    store_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> store.store_id</fk>
    first_name TEXT NOT NULL,
        -- <example>'MARY'</example>
    last_name TEXT NOT NULL,
        -- <example>'SMITH'</example>
    email TEXT NOT NULL,
        -- <example>'MARY.SMITH@sakilacustomer.org'</example>
    address_id INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> address.address_id</fk>
    active INTEGER NOT NULL,
        -- <example>1</example>
    create_date DATETIME NOT NULL,
        -- <example>'2006-02-14 22:04:36.0'</example>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 04:57:20.0'</example>
    FOREIGN KEY (address_id) REFERENCES address(address_id),
    FOREIGN KEY (store_id) REFERENCES store(store_id)
);

/*
Schema: NULLTable: film
Rows: 1000
Sample rows:
| film_id   | title            | description                                                                                                           | release_year   | language_id   | original_language_id   | rental_duration   | rental_rate   | length   | replacement_cost   | rating   | special_features                 | last_update           |
|-----------|------------------|-----------------------------------------------------------------------------------------------------------------------|----------------|---------------|------------------------|-------------------|---------------|----------|--------------------|----------|----------------------------------|-----------------------|
| 1         | ACADEMY DINOSAUR | A Epic Drama of a Feminist And a Mad Scientist who must Battle a Teacher in The Canadian Rockies                      | 2006           | 1             | [NULL]                 | 6                 | 0.99          | 86       | 20.99              | PG       | Deleted Scenes,Behind the Scenes | 2006-02-15 05:03:42.0 |
| 2         | ACE GOLDFINGER   | A Astounding Epistle of a Database Administrator And a Explorer who must Find a Car in Ancient China                  | 2006           | 1             | [NULL]                 | 3                 | 4.99          | 48       | 12.99              | G        | Trailers,Deleted Scenes          | 2006-02-15 05:03:42.0 |
| 3         | ADAPTATION HOLES | A Astounding Reflection of a Lumberjack And a Car who must Sink a Lumberjack in A Baloon Factory                      | 2006           | 1             | [NULL]                 | 7                 | 2.99          | 50       | 18.99              | NC-17    | Trailers,Deleted Scenes          | 2006-02-15 05:03:42.0 |
| 4         | AFFAIR PREJUDICE | A Fanciful Documentary of a Frisbee And a Lumberjack who must Chase a Monkey in A Shark Tank                          | 2006           | 1             | [NULL]                 | 5                 | 2.99          | 117      | 26.99              | G        | Commentaries,Behind the Scenes   | 2006-02-15 05:03:42.0 |
| 5         | AFRICAN EGG      | A Fast-Paced Documentary of a Pastry Chef And a Dentist who must Pursue a Forensic Psychologist in The Gulf of Mexico | 2006           | 1             | [NULL]                 | 6                 | 2.99          | 130      | 22.99              | G        | Deleted Scenes                   | 2006-02-15 05:03:42.0 |
| ...       | ...              | ...                                                                                                                   | ...            | ...           | ...                    | ...               | ...           | ...      | ...                | ...      | ...                              | ...                   |
*/
CREATE TABLE film (
    film_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    title TEXT NOT NULL,
        -- <example>'ACADEMY DINOSAUR'</example>
    description TEXT NOT NULL,
        -- <example>'A Epic Drama of a Feminist And a Mad Scientist who must Battle a Teacher in The Canadian Rockies'</example>
    release_year TEXT NOT NULL,
        -- <values>{'2006'}</values>
    language_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> language.language_id</fk>
    original_language_id INTEGER NULL,
        -- <fk> -> language.language_id</fk>
    rental_duration INTEGER NOT NULL,
        -- <example>6</example>
    rental_rate REAL NOT NULL,
        -- <example>0.990</example>
    length INTEGER NOT NULL,
        -- <example>86</example>
    replacement_cost REAL NOT NULL,
        -- <example>20.990</example>
    rating TEXT NOT NULL,
        -- <values>{'G', 'NC-17', 'PG', 'PG-13', 'R'}</values>
    special_features TEXT NOT NULL,
        -- <example>'Deleted Scenes,Behind the Scenes'</example>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 05:03:42.0'</example>
    FOREIGN KEY (original_language_id) REFERENCES language(language_id),
    FOREIGN KEY (language_id) REFERENCES language(language_id)
);

/*
Schema: NULLTable: film_actor
Rows: 5462
Sample rows:
| actor_id   | film_id   | last_update           |
|------------|-----------|-----------------------|
| 1          | 1         | 2006-02-15 05:05:03.0 |
| 1          | 23        | 2006-02-15 05:05:03.0 |
| 1          | 25        | 2006-02-15 05:05:03.0 |
| 1          | 106       | 2006-02-15 05:05:03.0 |
| 1          | 140       | 2006-02-15 05:05:03.0 |
| ...        | ...       | ...                   |
*/
CREATE TABLE film_actor (
    actor_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> actor.actor_id</fk>
    film_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> film.film_id</fk>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 05:05:03.0'</example>
    PRIMARY KEY (actor_id, film_id),
    FOREIGN KEY (film_id) REFERENCES film(film_id),
    FOREIGN KEY (actor_id) REFERENCES actor(actor_id)
);

/*
Schema: NULLTable: film_category
Rows: 1000
Sample rows:
| film_id   | category_id   | last_update           |
|-----------|---------------|-----------------------|
| 1         | 6             | 2006-02-15 05:07:09.0 |
| 2         | 11            | 2006-02-15 05:07:09.0 |
| 3         | 6             | 2006-02-15 05:07:09.0 |
| 4         | 11            | 2006-02-15 05:07:09.0 |
| 5         | 8             | 2006-02-15 05:07:09.0 |
| ...       | ...           | ...                   |
*/
CREATE TABLE film_category (
    film_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> film.film_id</fk>
    category_id INTEGER NOT NULL,
        -- <example>6</example>
        -- <fk> -> category.category_id</fk>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 05:07:09.0'</example>
    PRIMARY KEY (film_id, category_id),
    FOREIGN KEY (category_id) REFERENCES category(category_id),
    FOREIGN KEY (film_id) REFERENCES film(film_id)
);

/*
Schema: NULLTable: film_text
Rows: 1000
Sample rows:
| film_id   | title            | description                                                                                                           |
|-----------|------------------|-----------------------------------------------------------------------------------------------------------------------|
| 1         | ACADEMY DINOSAUR | A Epic Drama of a Feminist And a Mad Scientist who must Battle a Teacher in The Canadian Rockies                      |
| 2         | ACE GOLDFINGER   | A Astounding Epistle of a Database Administrator And a Explorer who must Find a Car in Ancient China                  |
| 3         | ADAPTATION HOLES | A Astounding Reflection of a Lumberjack And a Car who must Sink a Lumberjack in A Baloon Factory                      |
| 4         | AFFAIR PREJUDICE | A Fanciful Documentary of a Frisbee And a Lumberjack who must Chase a Monkey in A Shark Tank                          |
| 5         | AFRICAN EGG      | A Fast-Paced Documentary of a Pastry Chef And a Dentist who must Pursue a Forensic Psychologist in The Gulf of Mexico |
| ...       | ...              | ...                                                                                                                   |
*/
CREATE TABLE film_text (
    film_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    title TEXT NOT NULL,
        -- <example>'ACADEMY DINOSAUR'</example>
    description TEXT NOT NULL
        -- <example>'A Epic Drama of a Feminist And a Mad Scientist who must Battle a Teacher in The Canadian Rockies'</example>
);

/*
Schema: NULLTable: inventory
Rows: 4581
Sample rows:
| inventory_id   | film_id   | store_id   | last_update           |
|----------------|-----------|------------|-----------------------|
| 1              | 1         | 1          | 2006-02-15 05:09:17.0 |
| 2              | 1         | 1          | 2006-02-15 05:09:17.0 |
| 3              | 1         | 1          | 2006-02-15 05:09:17.0 |
| 4              | 1         | 1          | 2006-02-15 05:09:17.0 |
| 5              | 1         | 2          | 2006-02-15 05:09:17.0 |
| ...            | ...       | ...        | ...                   |
*/
CREATE TABLE inventory (
    inventory_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    film_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> film.film_id</fk>
    store_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> store.store_id</fk>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 05:09:17.0'</example>
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (film_id) REFERENCES film(film_id)
);

/*
Schema: NULLTable: language
Rows: 6
All rows:
|   language_id | name     | last_update           |
|---------------|----------|-----------------------|
|             1 | English  | 2006-02-15 05:02:19.0 |
|             2 | Italian  | 2006-02-15 05:02:19.0 |
|             3 | Japanese | 2006-02-15 05:02:19.0 |
|             4 | Mandarin | 2006-02-15 05:02:19.0 |
|             5 | French   | 2006-02-15 05:02:19.0 |
|             6 | German   | 2006-02-15 05:02:19.0 |
*/
CREATE TABLE language (
    language_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NOT NULL,
        -- <values>{'English', 'French', 'German', 'Italian', 'Japanese', 'Mandarin'}</values>
    last_update DATETIME NOT NULL
        -- <example>'2006-02-15 05:02:19.0'</example>
);

/*
Schema: NULLTable: payment
Rows: 16049
Sample rows:
| payment_id   | customer_id   | staff_id   | rental_id   | amount   | payment_date          | last_update           |
|--------------|---------------|------------|-------------|----------|-----------------------|-----------------------|
| 1            | 1             | 1          | 76          | 2.99     | 2005-05-25 11:30:37.0 | 2006-02-15 22:12:30.0 |
| 2            | 1             | 1          | 573         | 0.99     | 2005-05-28 10:35:23.0 | 2006-02-15 22:12:30.0 |
| 3            | 1             | 1          | 1185        | 5.99     | 2005-06-15 00:54:12.0 | 2006-02-15 22:12:30.0 |
| 4            | 1             | 2          | 1422        | 0.99     | 2005-06-15 18:02:53.0 | 2006-02-15 22:12:30.0 |
| 5            | 1             | 2          | 1476        | 9.99     | 2005-06-15 21:08:46.0 | 2006-02-15 22:12:30.0 |
| ...          | ...           | ...        | ...         | ...      | ...                   | ...                   |
*/
CREATE TABLE payment (
    payment_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    customer_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> customer.customer_id</fk>
    staff_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> staff.staff_id</fk>
    rental_id INTEGER NULL,
        -- <example>76</example>
        -- <fk> -> rental.rental_id</fk>
    amount REAL NOT NULL,
        -- <example>2.990</example>
    payment_date DATETIME NOT NULL,
        -- <example>'2005-05-25 11:30:37.0'</example>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 22:12:30.0'</example>
    FOREIGN KEY (rental_id) REFERENCES rental(rental_id),
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

/*
Schema: NULLTable: rental
Rows: 16044
Sample rows:
| rental_id   | rental_date           | inventory_id   | customer_id   | return_date           | staff_id   | last_update           |
|-------------|-----------------------|----------------|---------------|-----------------------|------------|-----------------------|
| 1           | 2005-05-24 22:53:30.0 | 367            | 130           | 2005-05-26 22:04:30.0 | 1          | 2006-02-15 21:30:53.0 |
| 2           | 2005-05-24 22:54:33.0 | 1525           | 459           | 2005-05-28 19:40:33.0 | 1          | 2006-02-15 21:30:53.0 |
| 3           | 2005-05-24 23:03:39.0 | 1711           | 408           | 2005-06-01 22:12:39.0 | 1          | 2006-02-15 21:30:53.0 |
| 4           | 2005-05-24 23:04:41.0 | 2452           | 333           | 2005-06-03 01:43:41.0 | 2          | 2006-02-15 21:30:53.0 |
| 5           | 2005-05-24 23:05:21.0 | 2079           | 222           | 2005-06-02 04:33:21.0 | 1          | 2006-02-15 21:30:53.0 |
| ...         | ...                   | ...            | ...           | ...                   | ...        | ...                   |
*/
CREATE TABLE rental (
    rental_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    rental_date DATETIME NOT NULL,
        -- <example>'2005-05-24 22:53:30.0'</example>
    inventory_id INTEGER NOT NULL,
        -- <example>367</example>
        -- <fk> -> inventory.inventory_id</fk>
    customer_id INTEGER NOT NULL,
        -- <example>130</example>
        -- <fk> -> customer.customer_id</fk>
    return_date DATETIME NULL,
        -- <example>'2005-05-26 22:04:30.0'</example>
    staff_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> staff.staff_id</fk>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 21:30:53.0'</example>
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id)
);

/*
Schema: NULLTable: staff
Rows: 2
All rows:
|   staff_id | first_name   | last_name   |   address_id | picture                                                                                                                                                                                                     | email                        |   store_id |   active | username   | password                                 | last_update           |
|------------|--------------|-------------|--------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------------------------|------------|----------|------------|------------------------------------------|-----------------------|
|          1 | Mike         | Hillyer     |            3 | 0x3F504E470D0A1A0A0000000D4948445200000079000000750802000000E55AD965000000097048597300000EC300000EC3...CC1C426CA5654BEC29C2A7EE40DD3FA23F3F1802EB080855EB3B493FFF0F62B8BC3FC33FA23F0000000049454E44AE42603F | Mike.Hillyer@sakilastaff.com |          1 |        1 | Mike       | 8cb2237d0679ca88db6464eac60da96345513964 | 2006-02-15 04:57:16.0 |
|          2 | Jon          | Stephens    |            4 | [NULL]                                                                                                                                                                                                      | Jon.Stephens@sakilastaff.com |          2 |        1 | Jon        | 8cb2237d0679ca88db6464eac60da96345513964 | 2006-02-15 04:57:16.0 |
*/
CREATE TABLE staff (
    staff_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    first_name TEXT NOT NULL,
        -- <values>{'Jon', 'Mike'}</values>
    last_name TEXT NOT NULL,
        -- <values>{'Hillyer', 'Stephens'}</values>
    address_id INTEGER NOT NULL,
        -- <example>3</example>
        -- <fk> -> address.address_id</fk>
    picture BLOB NULL,
        -- <example>'0x3F504E470D0A1A0A0000000D494844520000007900000075...3B493FFF0F62B8BC3FC33FA23F0000000049454E44AE42603F'</example>
    email TEXT NOT NULL,
        -- <values>{'Jon.Stephens@sakilastaff.com', 'Mike.Hillyer@sakilastaff.com'}</values>
    store_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> store.store_id</fk>
    active INTEGER NOT NULL,
        -- <example>1</example>
    username TEXT NOT NULL,
        -- <values>{'Jon', 'Mike'}</values>
    password TEXT NOT NULL,
        -- <values>{'8cb2237d0679ca88db6464eac60da96345513964'}</values>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 04:57:16.0'</example>
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (address_id) REFERENCES address(address_id)
);

/*
Schema: NULLTable: store
Rows: 2
All rows:
|   store_id |   manager_staff_id |   address_id | last_update           |
|------------|--------------------|--------------|-----------------------|
|          1 |                  1 |            1 | 2006-02-15 04:57:12.0 |
|          2 |                  2 |            2 | 2006-02-15 04:57:12.0 |
*/
CREATE TABLE store (
    store_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    manager_staff_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> staff.staff_id</fk>
    address_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> address.address_id</fk>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 04:57:12.0'</example>
    FOREIGN KEY (address_id) REFERENCES address(address_id),
    FOREIGN KEY (manager_staff_id) REFERENCES staff(staff_id)
);
```