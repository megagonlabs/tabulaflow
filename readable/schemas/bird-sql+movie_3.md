```sql
-- Database: movie_3

-- Table: actor (200 rows)
CREATE TABLE actor (
    actor_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    first_name TEXT NOT NULL,
        -- <example>'PENELOPE'</example>
    last_name TEXT NOT NULL,
        -- <example>'GUINESS'</example>
    last_update DATETIME NOT NULL
        -- <example>'2006-02-15 04:34:33.0'</example>
);

-- Table: address (603 rows)
CREATE TABLE address (
    address_id INTEGER NULL PRIMARY KEY,
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
    postal_code TEXT NULL,
        -- <example>''</example>
    phone TEXT NOT NULL,
        -- <example>''</example>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 04:45:30.0'</example>
    FOREIGN KEY (city_id) REFERENCES city(city_id)
);

-- Table: category (16 rows)
CREATE TABLE category (
    category_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NOT NULL,
        -- <example>'Action'</example>
    last_update DATETIME NOT NULL
        -- <example>'2006-02-15 04:46:27.0'</example>
);

-- Table: city (600 rows)
CREATE TABLE city (
    city_id INTEGER NULL PRIMARY KEY,
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

-- Table: country (109 rows)
CREATE TABLE country (
    country_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    country TEXT NOT NULL,
        -- <example>'Afghanistan'</example>
    last_update DATETIME NOT NULL
        -- <example>'2006-02-15 04:44:00.0'</example>
);

-- Table: customer (599 rows)
CREATE TABLE customer (
    customer_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    store_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> store.store_id</fk>
    first_name TEXT NOT NULL,
        -- <example>'MARY'</example>
    last_name TEXT NOT NULL,
        -- <example>'SMITH'</example>
    email TEXT NULL,
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

-- Table: film (1000 rows)
CREATE TABLE film (
    film_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    title TEXT NOT NULL,
        -- <example>'ACADEMY DINOSAUR'</example>
    description TEXT NULL,
        -- <example>'A Epic Drama of a Feminist And a Mad Scientist who must Battle a Teacher in The Canadian Rockies'</example>
    release_year TEXT NULL,
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
    length INTEGER NULL,
        -- <example>86</example>
    replacement_cost REAL NOT NULL,
        -- <example>20.990</example>
    rating TEXT NULL,
        -- <values>{'G', 'NC-17', 'PG', 'PG-13', 'R'}</values>
    special_features TEXT NULL,
        -- <example>'Deleted Scenes,Behind the Scenes'</example>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 05:03:42.0'</example>
    FOREIGN KEY (original_language_id) REFERENCES language(language_id),
    FOREIGN KEY (language_id) REFERENCES language(language_id)
);

-- Table: film_actor (5462 rows)
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

-- Table: film_category (1000 rows)
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

-- Table: film_text (1000 rows)
CREATE TABLE film_text (
    film_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    title TEXT NOT NULL,
        -- <example>'ACADEMY DINOSAUR'</example>
    description TEXT NULL
        -- <example>'A Epic Drama of a Feminist And a Mad Scientist who must Battle a Teacher in The Canadian Rockies'</example>
);

-- Table: inventory (4581 rows)
CREATE TABLE inventory (
    inventory_id INTEGER NULL PRIMARY KEY,
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

-- Table: language (6 rows)
CREATE TABLE language (
    language_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NOT NULL,
        -- <values>{'English', 'French', 'German', 'Italian', 'Japanese', 'Mandarin'}</values>
    last_update DATETIME NOT NULL
        -- <example>'2006-02-15 05:02:19.0'</example>
);

-- Table: payment (16049 rows)
CREATE TABLE payment (
    payment_id INTEGER NULL PRIMARY KEY,
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

-- Table: rental (16044 rows)
CREATE TABLE rental (
    rental_id INTEGER NULL PRIMARY KEY,
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

-- Table: staff (2 rows)
CREATE TABLE staff (
    staff_id INTEGER NULL PRIMARY KEY,
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
    email TEXT NULL,
        -- <values>{'Jon.Stephens@sakilastaff.com', 'Mike.Hillyer@sakilastaff.com'}</values>
    store_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> store.store_id</fk>
    active INTEGER NOT NULL,
        -- <example>1</example>
    username TEXT NOT NULL,
        -- <values>{'Jon', 'Mike'}</values>
    password TEXT NULL,
        -- <values>{'8cb2237d0679ca88db6464eac60da96345513964'}</values>
    last_update DATETIME NOT NULL,
        -- <example>'2006-02-15 04:57:16.0'</example>
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (address_id) REFERENCES address(address_id)
);

-- Table: store (2 rows)
CREATE TABLE store (
    store_id INTEGER NULL PRIMARY KEY,
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