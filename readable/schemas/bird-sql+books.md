```sql
-- Database: books

/*
Table: address
Rows: 1000
Sample rows:
| address_id   | street_number   | street_name         | city         | country_id   |
|--------------|-----------------|---------------------|--------------|--------------|
| 1            | 57              | Glacier Hill Avenue | Torbat-e Jām | 95           |
| 2            | 86              | Dottie Junction     | Beaumont     | 37           |
| 3            | 292             | Ramsey Avenue       | Cayambe      | 60           |
| 4            | 5618            | Thackeray Junction  | Caldas       | 47           |
| 5            | 4               | 2nd Park            | Ngunguru     | 153          |
| ...          | ...             | ...                 | ...          | ...          |
*/
CREATE TABLE address (
    address_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    street_number TEXT NOT NULL,
        -- <example>'57'</example>
    street_name TEXT NOT NULL,
        -- <example>'Glacier Hill Avenue'</example>
    city TEXT NOT NULL,
        -- <example>'Torbat-e Jām'</example>
    country_id INTEGER NOT NULL,
        -- <example>95</example>
        -- <fk> -> country.country_id</fk>
    FOREIGN KEY (country_id) REFERENCES country(country_id)
);

/*
Table: address_status
Rows: 2
All rows:
|   status_id | address_status   |
|-------------|------------------|
|           1 | Active           |
|           2 | Inactive         |
*/
CREATE TABLE address_status (
    status_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    address_status TEXT NOT NULL
        -- <values>{'Active', 'Inactive'}</values>
);

/*
Table: author
Rows: 9235
Sample rows:
| author_id   | author_name          |
|-------------|----------------------|
| 1           | A. Bartlett Giamatti |
| 2           | A. Elizabeth Delany  |
| 3           | A. Merritt           |
| 4           | A. Roger Merrill     |
| 5           | A. Walton Litz       |
| ...         | ...                  |
*/
CREATE TABLE author (
    author_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    author_name TEXT NOT NULL
        -- <example>'A. Bartlett Giamatti'</example>
);

/*
Table: book
Rows: 11127
Sample rows:
| book_id   | title                                                                      | isbn13      | language_id   | num_pages   | publication_date   | publisher_id   |
|-----------|----------------------------------------------------------------------------|-------------|---------------|-------------|--------------------|----------------|
| 1         | The World's First Love: Mary  Mother of God                                | 8987059752  | 2             | 276         | 1996-09-01         | 1010           |
| 2         | The Illuminati                                                             | 20049130001 | 1             | 352         | 2004-10-04         | 1967           |
| 3         | The Servant Leader                                                         | 23755004321 | 1             | 128         | 2003-03-11         | 1967           |
| 4         | What Life Was Like in the Jewel in the Crown: British India  AD 1600-1905  | 34406054602 | 1             | 168         | 1999-09-01         | 1978           |
| 5         | Cliffs Notes on Aristophanes' Lysistrata  The Birds  The Clouds  The Frogs | 49086007763 | 1             | 80          | 1983-12-29         | 416            |
| ...       | ...                                                                        | ...         | ...           | ...         | ...                | ...            |
*/
CREATE TABLE book (
    book_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    title TEXT NOT NULL,
        -- <example>'The World's First Love: Mary  Mother of God'</example>
    isbn13 TEXT NOT NULL,
        -- <example>'8987059752'</example>
    language_id INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> book_language.language_id</fk>
    num_pages INTEGER NOT NULL,
        -- <example>276</example>
    publication_date DATE NOT NULL,
        -- <example>'1996-09-01'</example>
    publisher_id INTEGER NOT NULL,
        -- <example>1010</example>
        -- <fk> -> publisher.publisher_id</fk>
    FOREIGN KEY (language_id) REFERENCES book_language(language_id),
    FOREIGN KEY (publisher_id) REFERENCES publisher(publisher_id)
);

/*
Table: book_author
Rows: 17642
Sample rows:
| book_id   | author_id   |
|-----------|-------------|
| 10539     | 1           |
| 8109      | 2           |
| 2792      | 3           |
| 6228      | 4           |
| 1058      | 5           |
| ...       | ...         |
*/
CREATE TABLE book_author (
    book_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> book.book_id</fk>
    author_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> author.author_id</fk>
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (author_id) REFERENCES author(author_id),
    FOREIGN KEY (book_id) REFERENCES book(book_id)
);

/*
Table: book_language
Rows: 27
Sample rows:
| language_id   | language_code   | language_name         |
|---------------|-----------------|-----------------------|
| 1             | eng             | English               |
| 2             | en-US           | United States English |
| 3             | fre             | French                |
| 4             | spa             | Spanish               |
| 5             | en-GB           | British English       |
| ...           | ...             | ...                   |
*/
CREATE TABLE book_language (
    language_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    language_code TEXT NOT NULL,
        -- <example>'eng'</example>
    language_name TEXT NOT NULL
        -- <example>'English'</example>
);

/*
Table: country
Rows: 232
Sample rows:
| country_id   | country_name         |
|--------------|----------------------|
| 1            | Afghanistan          |
| 2            | Netherlands Antilles |
| 3            | Albania              |
| 4            | Algeria              |
| 5            | Andorra              |
| ...          | ...                  |
*/
CREATE TABLE country (
    country_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    country_name TEXT NOT NULL
        -- <example>'Afghanistan'</example>
);

/*
Table: cust_order
Rows: 7550
Sample rows:
| order_id   | order_date          | customer_id   | shipping_method_id   | dest_address_id   |
|------------|---------------------|---------------|----------------------|-------------------|
| 1          | 2021-07-14 10:47:19 | 387           | 4                    | 1                 |
| 2          | 2020-08-16 17:26:41 | 1256          | 2                    | 1                 |
| 3          | 2021-08-19 21:43:07 | 1335          | 1                    | 1                 |
| 4          | 2021-12-23 19:01:08 | 1480          | 1                    | 1                 |
| 5          | 2022-06-15 01:15:35 | 400           | 1                    | 2                 |
| ...        | ...                 | ...           | ...                  | ...               |
*/
CREATE TABLE cust_order (
    order_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    order_date DATETIME NOT NULL,
        -- <example>'2021-07-14 10:47:19'</example>
    customer_id INTEGER NOT NULL,
        -- <example>387</example>
        -- <fk> -> customer.customer_id</fk>
    shipping_method_id INTEGER NOT NULL,
        -- <example>4</example>
        -- <fk> -> shipping_method.method_id</fk>
    dest_address_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> address.address_id</fk>
    FOREIGN KEY (dest_address_id) REFERENCES address(address_id),
    FOREIGN KEY (shipping_method_id) REFERENCES shipping_method(method_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

/*
Table: customer
Rows: 2000
Sample rows:
| customer_id   | first_name   | last_name   | email                  |
|---------------|--------------|-------------|------------------------|
| 1             | Ursola       | Purdy       | upurdy0@cdbaby.com     |
| 2             | Ruthanne     | Vatini      | rvatini1@fema.gov      |
| 3             | Reidar       | Turbitt     | rturbitt2@geocities.jp |
| 4             | Rich         | Kirsz       | rkirsz3@jalbum.net     |
| 5             | Carline      | Kupis       | ckupis4@tamu.edu       |
| ...           | ...          | ...         | ...                    |
*/
CREATE TABLE customer (
    customer_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    first_name TEXT NOT NULL,
        -- <example>'Ursola'</example>
    last_name TEXT NOT NULL,
        -- <example>'Purdy'</example>
    email TEXT NOT NULL
        -- <example>'upurdy0@cdbaby.com'</example>
);

/*
Table: customer_address
Rows: 3350
Sample rows:
| customer_id   | address_id   | status_id   |
|---------------|--------------|-------------|
| 1             | 606          | 1           |
| 2             | 266          | 1           |
| 3             | 376          | 1           |
| 4             | 655          | 1           |
| 5             | 273          | 1           |
| ...           | ...          | ...         |
*/
CREATE TABLE customer_address (
    customer_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> customer.customer_id</fk>
    address_id INTEGER NOT NULL,
        -- <example>606</example>
        -- <fk> -> address.address_id</fk>
    status_id INTEGER NOT NULL,
        -- <example>1</example>
    PRIMARY KEY (customer_id, address_id),
    FOREIGN KEY (address_id) REFERENCES address(address_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

/*
Table: order_history
Rows: 22348
Sample rows:
| history_id   | order_id   | status_id   | status_date         |
|--------------|------------|-------------|---------------------|
| 1            | 1          | 1           | 2021-07-14 17:04:28 |
| 2            | 2          | 1           | 2020-08-16 20:23:19 |
| 3            | 3          | 1           | 2021-08-20 05:34:51 |
| 4            | 4          | 1           | 2021-12-24 01:29:55 |
| 5            | 5          | 1           | 2022-06-15 10:04:20 |
| ...          | ...        | ...         | ...                 |
*/
CREATE TABLE order_history (
    history_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    order_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> cust_order.order_id</fk>
    status_id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> order_status.status_id</fk>
    status_date DATETIME NOT NULL,
        -- <example>'2021-07-14 17:04:28'</example>
    FOREIGN KEY (status_id) REFERENCES order_status(status_id),
    FOREIGN KEY (order_id) REFERENCES cust_order(order_id)
);

/*
Table: order_line
Rows: 7550
Sample rows:
| line_id   | order_id   | book_id   | price   |
|-----------|------------|-----------|---------|
| 1024      | 2051       | 10720     | 3.19    |
| 1025      | 899        | 10105     | 1.24    |
| 1026      | 4994       | 6503      | 14.74   |
| 1027      | 7041       | 10354     | 8.85    |
| 1028      | 9088       | 4684      | 15.55   |
| ...       | ...        | ...       | ...     |
*/
CREATE TABLE order_line (
    line_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1024</example>
    order_id INTEGER NOT NULL,
        -- <example>2051</example>
        -- <fk> -> cust_order.order_id</fk>
    book_id INTEGER NOT NULL,
        -- <example>10720</example>
        -- <fk> -> book.book_id</fk>
    price REAL NOT NULL,
        -- <example>3.190</example>
    FOREIGN KEY (book_id) REFERENCES book(book_id),
    FOREIGN KEY (order_id) REFERENCES cust_order(order_id)
);

/*
Table: order_status
Rows: 6
All rows:
|   status_id | status_value         |
|-------------|----------------------|
|           1 | Order Received       |
|           2 | Pending Delivery     |
|           3 | Delivery In Progress |
|           4 | Delivered            |
|           5 | Cancelled            |
|           6 | Returned             |
*/
CREATE TABLE order_status (
    status_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    status_value TEXT NOT NULL
        -- <values>{'Cancelled', 'Delivered', 'Delivery In Progress', 'Order Received', 'Pending Delivery', 'Returned'}</values>
);

/*
Table: publisher
Rows: 2264
Sample rows:
| publisher_id   | publisher_name                |
|----------------|-------------------------------|
| 1              | 10/18                         |
| 2              | 1st Book Library              |
| 3              | 1st World Library             |
| 4              | A & C Black (Childrens books) |
| 5              | A Harvest Book/Harcourt Inc.  |
| ...            | ...                           |
*/
CREATE TABLE publisher (
    publisher_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    publisher_name TEXT NOT NULL
        -- <example>'10/18'</example>
);

/*
Table: shipping_method
Rows: 4
All rows:
|   method_id | method_name   |   cost |
|-------------|---------------|--------|
|           1 | Standard      |    5.9 |
|           2 | Priority      |    8.9 |
|           3 | Express       |   11.9 |
|           4 | International |   24.5 |
*/
CREATE TABLE shipping_method (
    method_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    method_name TEXT NOT NULL,
        -- <values>{'Express', 'International', 'Priority', 'Standard'}</values>
    cost REAL NOT NULL
        -- <example>5.900</example>
);
```