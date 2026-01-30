```sql
-- Database: movie_3

-- Table: actor (200 rows)
CREATE TABLE actor (
    actor_id INTEGER PRIMARY KEY,  -- e.g. 1
    first_name TEXT NOT NULL,  -- e.g. 'PENELOPE'
    last_name TEXT NOT NULL,  -- e.g. 'GUINESS'
    last_update DATETIME NOT NULL  -- e.g. '2006-02-15 04:34:33.0'
);

-- Table: address (603 rows)
CREATE TABLE address (
    address_id INTEGER PRIMARY KEY,  -- e.g. 1
    address TEXT NOT NULL,  -- e.g. '47 MySakila Drive'
    address2 TEXT,  -- values: {''}
    district TEXT NOT NULL,  -- e.g. 'Alberta'
    city_id INTEGER NOT NULL,  -- e.g. 300; FK -> city.city_id
    postal_code TEXT,  -- e.g. ''
    phone TEXT NOT NULL,  -- e.g. ''
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 04:45:30.0'
    FOREIGN KEY (city_id) REFERENCES city(city_id)
);

-- Table: category (16 rows)
CREATE TABLE category (
    category_id INTEGER PRIMARY KEY,  -- e.g. 1
    name TEXT NOT NULL,  -- e.g. 'Action'
    last_update DATETIME NOT NULL  -- e.g. '2006-02-15 04:46:27.0'
);

-- Table: city (600 rows)
CREATE TABLE city (
    city_id INTEGER PRIMARY KEY,  -- e.g. 1
    city TEXT NOT NULL,  -- e.g. 'A Corua (La Corua)'
    country_id INTEGER NOT NULL,  -- e.g. 87; FK -> country.country_id
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 04:45:25.0'
    FOREIGN KEY (country_id) REFERENCES country(country_id)
);

-- Table: country (109 rows)
CREATE TABLE country (
    country_id INTEGER PRIMARY KEY,  -- e.g. 1
    country TEXT NOT NULL,  -- e.g. 'Afghanistan'
    last_update DATETIME NOT NULL  -- e.g. '2006-02-15 04:44:00.0'
);

-- Table: customer (599 rows)
CREATE TABLE customer (
    customer_id INTEGER PRIMARY KEY,  -- e.g. 1
    store_id INTEGER NOT NULL,  -- e.g. 1; FK -> store.store_id
    first_name TEXT NOT NULL,  -- e.g. 'MARY'
    last_name TEXT NOT NULL,  -- e.g. 'SMITH'
    email TEXT,  -- e.g. 'MARY.SMITH@sakilacustomer.org'
    address_id INTEGER NOT NULL,  -- e.g. 5; FK -> address.address_id
    active INTEGER NOT NULL,  -- e.g. 1
    create_date DATETIME NOT NULL,  -- e.g. '2006-02-14 22:04:36.0'
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 04:57:20.0'
    FOREIGN KEY (address_id) REFERENCES address(address_id),
    FOREIGN KEY (store_id) REFERENCES store(store_id)
);

-- Table: film (1000 rows)
CREATE TABLE film (
    film_id INTEGER PRIMARY KEY,  -- e.g. 1
    title TEXT NOT NULL,  -- e.g. 'ACADEMY DINOSAUR'
    description TEXT,  -- e.g. 'A Epic Drama of a Feminist And a Mad Scientist who must Battle a Teacher in The Canadian Rockies'
    release_year TEXT,  -- values: {'2006'}
    language_id INTEGER NOT NULL,  -- e.g. 1; FK -> language.language_id
    original_language_id INTEGER,  -- FK -> language.language_id
    rental_duration INTEGER NOT NULL,  -- e.g. 6
    rental_rate REAL NOT NULL,  -- e.g. 0.990
    length INTEGER,  -- e.g. 86
    replacement_cost REAL NOT NULL,  -- e.g. 20.990
    rating TEXT,  -- values: {'G', 'NC-17', 'PG', 'PG-13', 'R'}
    special_features TEXT,  -- e.g. 'Deleted Scenes,Behind the Scenes'
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 05:03:42.0'
    FOREIGN KEY (original_language_id) REFERENCES language(language_id),
    FOREIGN KEY (language_id) REFERENCES language(language_id)
);

-- Table: film_actor (5462 rows)
CREATE TABLE film_actor (
    actor_id INTEGER NOT NULL,  -- e.g. 1; FK -> actor.actor_id
    film_id INTEGER NOT NULL,  -- e.g. 1; FK -> film.film_id
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 05:05:03.0'
    PRIMARY KEY (actor_id, film_id),
    FOREIGN KEY (film_id) REFERENCES film(film_id),
    FOREIGN KEY (actor_id) REFERENCES actor(actor_id)
);

-- Table: film_category (1000 rows)
CREATE TABLE film_category (
    film_id INTEGER NOT NULL,  -- e.g. 1; FK -> film.film_id
    category_id INTEGER NOT NULL,  -- e.g. 6; FK -> category.category_id
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 05:07:09.0'
    PRIMARY KEY (film_id, category_id),
    FOREIGN KEY (category_id) REFERENCES category(category_id),
    FOREIGN KEY (film_id) REFERENCES film(film_id)
);

-- Table: film_text (1000 rows)
CREATE TABLE film_text (
    film_id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    title TEXT NOT NULL,  -- e.g. 'ACADEMY DINOSAUR'
    description TEXT  -- e.g. 'A Epic Drama of a Feminist And a Mad Scientist who must Battle a Teacher in The Canadian Rockies'
);

-- Table: inventory (4581 rows)
CREATE TABLE inventory (
    inventory_id INTEGER PRIMARY KEY,  -- e.g. 1
    film_id INTEGER NOT NULL,  -- e.g. 1; FK -> film.film_id
    store_id INTEGER NOT NULL,  -- e.g. 1; FK -> store.store_id
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 05:09:17.0'
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (film_id) REFERENCES film(film_id)
);

-- Table: language (6 rows)
CREATE TABLE language (
    language_id INTEGER PRIMARY KEY,  -- e.g. 1
    name TEXT NOT NULL,  -- values: {'English', 'French', 'German', 'Italian', 'Japanese', 'Mandarin'}
    last_update DATETIME NOT NULL  -- e.g. '2006-02-15 05:02:19.0'
);

-- Table: payment (16049 rows)
CREATE TABLE payment (
    payment_id INTEGER PRIMARY KEY,  -- e.g. 1
    customer_id INTEGER NOT NULL,  -- e.g. 1; FK -> customer.customer_id
    staff_id INTEGER NOT NULL,  -- e.g. 1; FK -> staff.staff_id
    rental_id INTEGER,  -- e.g. 76; FK -> rental.rental_id
    amount REAL NOT NULL,  -- e.g. 2.990
    payment_date DATETIME NOT NULL,  -- e.g. '2005-05-25 11:30:37.0'
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 22:12:30.0'
    FOREIGN KEY (rental_id) REFERENCES rental(rental_id),
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- Table: rental (16044 rows)
CREATE TABLE rental (
    rental_id INTEGER PRIMARY KEY,  -- e.g. 1
    rental_date DATETIME NOT NULL,  -- e.g. '2005-05-24 22:53:30.0'
    inventory_id INTEGER NOT NULL,  -- e.g. 367; FK -> inventory.inventory_id
    customer_id INTEGER NOT NULL,  -- e.g. 130; FK -> customer.customer_id
    return_date DATETIME,  -- e.g. '2005-05-26 22:04:30.0'
    staff_id INTEGER NOT NULL,  -- e.g. 1; FK -> staff.staff_id
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 21:30:53.0'
    FOREIGN KEY (staff_id) REFERENCES staff(staff_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (inventory_id) REFERENCES inventory(inventory_id)
);

-- Table: staff (2 rows)
CREATE TABLE staff (
    staff_id INTEGER PRIMARY KEY,  -- e.g. 1
    first_name TEXT NOT NULL,  -- values: {'Jon', 'Mike'}
    last_name TEXT NOT NULL,  -- values: {'Hillyer', 'Stephens'}
    address_id INTEGER NOT NULL,  -- e.g. 3; FK -> address.address_id
    picture BLOB,  -- e.g. '0x3F504E470D0A1A0A0000000D494844520000007900000075...3B493FFF0F62B8BC3FC33FA23F0000000049454E44AE42603F'
    email TEXT,  -- values: {'Jon.Stephens@sakilastaff.com', 'Mike.Hillyer@sakilastaff.com'}
    store_id INTEGER NOT NULL,  -- e.g. 1; FK -> store.store_id
    active INTEGER NOT NULL,  -- e.g. 1
    username TEXT NOT NULL,  -- values: {'Jon', 'Mike'}
    password TEXT,  -- values: {'8cb2237d0679ca88db6464eac60da96345513964'}
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 04:57:16.0'
    FOREIGN KEY (store_id) REFERENCES store(store_id),
    FOREIGN KEY (address_id) REFERENCES address(address_id)
);

-- Table: store (2 rows)
CREATE TABLE store (
    store_id INTEGER PRIMARY KEY,  -- e.g. 1
    manager_staff_id INTEGER NOT NULL,  -- e.g. 1; FK -> staff.staff_id
    address_id INTEGER NOT NULL,  -- e.g. 1; FK -> address.address_id
    last_update DATETIME NOT NULL,  -- e.g. '2006-02-15 04:57:12.0'
    FOREIGN KEY (address_id) REFERENCES address(address_id),
    FOREIGN KEY (manager_staff_id) REFERENCES staff(staff_id)
);
```