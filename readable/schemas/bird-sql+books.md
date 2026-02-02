```sql
-- Database: books

-- Table: address (1000 rows)
CREATE TABLE address (
    address_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    street_number TEXT NULL,
        -- <example>'57'</example>
    street_name TEXT NULL,
        -- <example>'Glacier Hill Avenue'</example>
    city TEXT NULL,
        -- <example>'Torbat-e Jām'</example>
    country_id INTEGER NULL,
        -- <example>95</example>
        -- <fk> -> country.country_id</fk>
    FOREIGN KEY (country_id) REFERENCES country(country_id)
);

-- Table: address_status (2 rows)
CREATE TABLE address_status (
    status_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    address_status TEXT NULL
        -- <values>{'Active', 'Inactive'}</values>
);

-- Table: author (9235 rows)
CREATE TABLE author (
    author_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    author_name TEXT NULL
        -- <example>'A. Bartlett Giamatti'</example>
);

-- Table: book (11127 rows)
CREATE TABLE book (
    book_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    title TEXT NULL,
        -- <example>'The World's First Love: Mary  Mother of God'</example>
    isbn13 TEXT NULL,
        -- <example>'8987059752'</example>
    language_id INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> book_language.language_id</fk>
    num_pages INTEGER NULL,
        -- <example>276</example>
    publication_date DATE NULL,
        -- <example>'1996-09-01'</example>
    publisher_id INTEGER NULL,
        -- <example>1010</example>
        -- <fk> -> publisher.publisher_id</fk>
    FOREIGN KEY (language_id) REFERENCES book_language(language_id),
    FOREIGN KEY (publisher_id) REFERENCES publisher(publisher_id)
);

-- Table: book_author (17642 rows)
CREATE TABLE book_author (
    book_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> book.book_id</fk>
    author_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> author.author_id</fk>
    PRIMARY KEY (book_id, author_id),
    FOREIGN KEY (author_id) REFERENCES author(author_id),
    FOREIGN KEY (book_id) REFERENCES book(book_id)
);

-- Table: book_language (27 rows)
CREATE TABLE book_language (
    language_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    language_code TEXT NULL,
        -- <example>'eng'</example>
    language_name TEXT NULL
        -- <example>'English'</example>
);

-- Table: country (232 rows)
CREATE TABLE country (
    country_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    country_name TEXT NULL
        -- <example>'Afghanistan'</example>
);

-- Table: cust_order (7550 rows)
CREATE TABLE cust_order (
    order_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    order_date DATETIME NULL,
        -- <example>'2021-07-14 10:47:19'</example>
    customer_id INTEGER NULL,
        -- <example>387</example>
        -- <fk> -> customer.customer_id</fk>
    shipping_method_id INTEGER NULL,
        -- <example>4</example>
        -- <fk> -> shipping_method.method_id</fk>
    dest_address_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> address.address_id</fk>
    FOREIGN KEY (dest_address_id) REFERENCES address(address_id),
    FOREIGN KEY (shipping_method_id) REFERENCES shipping_method(method_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- Table: customer (2000 rows)
CREATE TABLE customer (
    customer_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    first_name TEXT NULL,
        -- <example>'Ursola'</example>
    last_name TEXT NULL,
        -- <example>'Purdy'</example>
    email TEXT NULL
        -- <example>'upurdy0@cdbaby.com'</example>
);

-- Table: customer_address (3350 rows)
CREATE TABLE customer_address (
    customer_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> customer.customer_id</fk>
    address_id INTEGER NULL,
        -- <example>606</example>
        -- <fk> -> address.address_id</fk>
    status_id INTEGER NULL,
        -- <example>1</example>
    PRIMARY KEY (customer_id, address_id),
    FOREIGN KEY (address_id) REFERENCES address(address_id),
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- Table: order_history (22348 rows)
CREATE TABLE order_history (
    history_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    order_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> cust_order.order_id</fk>
    status_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> order_status.status_id</fk>
    status_date DATETIME NULL,
        -- <example>'2021-07-14 17:04:28'</example>
    FOREIGN KEY (status_id) REFERENCES order_status(status_id),
    FOREIGN KEY (order_id) REFERENCES cust_order(order_id)
);

-- Table: order_line (7550 rows)
CREATE TABLE order_line (
    line_id INTEGER NULL PRIMARY KEY,
        -- <example>1024</example>
    order_id INTEGER NULL,
        -- <example>2051</example>
        -- <fk> -> cust_order.order_id</fk>
    book_id INTEGER NULL,
        -- <example>10720</example>
        -- <fk> -> book.book_id</fk>
    price REAL NULL,
        -- <example>3.190</example>
    FOREIGN KEY (book_id) REFERENCES book(book_id),
    FOREIGN KEY (order_id) REFERENCES cust_order(order_id)
);

-- Table: order_status (6 rows)
CREATE TABLE order_status (
    status_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    status_value TEXT NULL
        -- <values>{'Cancelled', 'Delivered', 'Delivery In Progress', 'Order Received', 'Pending Delivery', 'Returned'}</values>
);

-- Table: publisher (2264 rows)
CREATE TABLE publisher (
    publisher_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    publisher_name TEXT NULL
        -- <example>'10/18'</example>
);

-- Table: shipping_method (4 rows)
CREATE TABLE shipping_method (
    method_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    method_name TEXT NULL,
        -- <values>{'Express', 'International', 'Priority', 'Standard'}</values>
    cost REAL NULL
        -- <example>5.900</example>
);
```