```sql
-- Database: book_publishing_company

-- Table: authors (23 rows)
CREATE TABLE authors (
    au_id TEXT NULL PRIMARY KEY,
        -- <example>'172-32-1176'</example>
    au_lname TEXT NOT NULL,
        -- <example>'White'</example>
    au_fname TEXT NOT NULL,
        -- <example>'Johnson'</example>
    phone TEXT NOT NULL,
        -- <example>'408 496-7223'</example>
    address TEXT NULL,
        -- <example>'10932 Bigge Rd.'</example>
    city TEXT NULL,
        -- <example>'Menlo Park'</example>
    state TEXT NULL,
        -- <values>{'CA', 'IN', 'KS', 'MD', 'MI', 'OR', 'TN', 'UT'}</values>
    zip TEXT NULL,
        -- <example>'94025'</example>
    contract TEXT NOT NULL
        -- <values>{'0'}</values>
);

-- Table: discounts (3 rows)
CREATE TABLE discounts (
    discounttype TEXT NOT NULL,
        -- <values>{'Customer Discount', 'Initial Customer', 'Volume Discount'}</values>
    stor_id TEXT NULL,
        -- <values>{'8042'}</values>
        -- <fk> -> stores.stor_id</fk>
    lowqty INTEGER NULL,
        -- <example>100</example>
    highqty INTEGER NULL,
        -- <example>1000</example>
    discount REAL NOT NULL,
        -- <example>10.500</example>
    FOREIGN KEY (stor_id) REFERENCES stores(stor_id)
);

-- Table: employee (43 rows)
CREATE TABLE employee (
    emp_id TEXT NULL PRIMARY KEY,
        -- <example>'A-C71970F'</example>
    fname TEXT NOT NULL,
        -- <example>'Aria'</example>
    minit TEXT NULL,
        -- <example>''</example>
    lname TEXT NOT NULL,
        -- <example>'Cruz'</example>
    job_id INTEGER NOT NULL,
        -- <example>10</example>
        -- <fk> -> jobs.job_id</fk>
    job_lvl INTEGER NULL,
        -- <example>87</example>
    pub_id TEXT NOT NULL,
        -- <values>{'0736', '0877', '1389', '1622', '1756', '9901', '9952', '9999'}</values>
        -- <fk> -> publishers.pub_id</fk>
    hire_date DATETIME NOT NULL,
        -- <example>'1991-10-26 00:00:00.0'</example>
    FOREIGN KEY (job_id) REFERENCES jobs(job_id),
    FOREIGN KEY (pub_id) REFERENCES publishers(pub_id)
);

-- Table: jobs (14 rows)
CREATE TABLE jobs (
    job_id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    job_desc TEXT NOT NULL,
        -- <example>'New Hire - Job not specified'</example>
    min_lvl INTEGER NOT NULL,
        -- <example>10</example>
    max_lvl INTEGER NOT NULL
        -- <example>10</example>
);

-- Table: pub_info (7 rows)
CREATE TABLE pub_info (
    pub_id TEXT NULL PRIMARY KEY,
        -- <values>{'0877', '1389', '1622', '1756', '9901', '9952', '9999'}</values>
        -- <fk> -> publishers.pub_id</fk>
    logo BLOB NULL,
        -- <example>'0x4749463839618B002F00B30F000000008000000080008080...294917DC473035E0B9E3183F9A3BB6F7ABDE608B018800003B'</example>
    pr_info TEXT NULL,
        -- <values>{'This is sample text data for Algodata Infosystems,...ta Infosystems is located in Berkeley, California.', 'This is sample text data for Binnet & Hardley, pub...e. Binnet & Hardley is located in Washington, D.C.', 'This is sample text data for Five Lakes Publishing... Lakes Publishing is located in Chicago, Illinois.', 'This is sample text data for GGG&G, publisher 9901...bs database. GGG&G is located in München, Germany.', 'This is sample text data for Lucerne Publishing, p...e. Lucerne publishing is located in Paris, France.', 'This is sample text data for Ramona Publishers, pu...se. Ramona Publishers is located in Dallas, Texas.', 'This is sample text data for Scootney Books, publi...otney Books is located in New York City, New York.'}</values>
    FOREIGN KEY (pub_id) REFERENCES publishers(pub_id)
);

-- Table: publishers (8 rows)
CREATE TABLE publishers (
    pub_id TEXT NULL PRIMARY KEY,
        -- <values>{'0736', '0877', '1389', '1622', '1756', '9901', '9952', '9999'}</values>
    pub_name TEXT NULL,
        -- <values>{'Algodata Infosystems', 'Binnet & Hardley', 'Five Lakes Publishing', 'GGG&G', 'Lucerne Publishing', 'New Moon Books', 'Ramona Publishers', 'Scootney Books'}</values>
    city TEXT NULL,
        -- <values>{'Berkeley', 'Boston', 'Chicago', 'Dallas', 'Mnchen', 'New York', 'Paris', 'Washington'}</values>
    state TEXT NULL,
        -- <values>{'CA', 'DC', 'IL', 'MA', 'NY', 'TX'}</values>
    country TEXT NULL
        -- <values>{'France', 'Germany', 'USA'}</values>
);

-- Table: roysched (86 rows)
CREATE TABLE roysched (
    title_id TEXT NOT NULL,
        -- <example>'BU1032'</example>
        -- <fk> -> titles.title_id</fk>
    lorange INTEGER NULL,
        -- <example>0</example>
    hirange INTEGER NULL,
        -- <example>5000</example>
    royalty INTEGER NULL,
        -- <example>10</example>
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

-- Table: sales (21 rows)
CREATE TABLE sales (
    stor_id TEXT NOT NULL,
        -- <values>{'6380', '7066', '7067', '7131', '7896', '8042'}</values>
        -- <fk> -> stores.stor_id</fk>
    ord_num TEXT NOT NULL,
        -- <example>'6871'</example>
    ord_date DATETIME NOT NULL,
        -- <example>'1994-09-14 00:00:00.0'</example>
    qty INTEGER NOT NULL,
        -- <example>5</example>
    payterms TEXT NOT NULL,
        -- <values>{'Net 30', 'Net 60', 'ON invoice'}</values>
    title_id TEXT NOT NULL,
        -- <example>'BU1032'</example>
        -- <fk> -> titles.title_id</fk>
    PRIMARY KEY (stor_id, ord_num, title_id),
    FOREIGN KEY (stor_id) REFERENCES stores(stor_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

-- Table: stores (6 rows)
CREATE TABLE stores (
    stor_id TEXT NULL PRIMARY KEY,
        -- <values>{'6380', '7066', '7067', '7131', '7896', '8042'}</values>
    stor_name TEXT NULL,
        -- <values>{'Barnum's', 'Bookbeat', 'Doc-U-Mat: Quality Laundry and Books', 'Eric the Read Books', 'Fricative Bookshop', 'News & Brews'}</values>
    stor_address TEXT NULL,
        -- <values>{'24-A Avogadro Way', '567 Pasadena Ave.', '577 First St.', '679 Carson St.', '788 Catamaugus Ave.', '89 Madison St.'}</values>
    city TEXT NULL,
        -- <values>{'Fremont', 'Los Gatos', 'Portland', 'Remulade', 'Seattle', 'Tustin'}</values>
    state TEXT NULL,
        -- <values>{'CA', 'OR', 'WA'}</values>
    zip TEXT NULL
        -- <values>{'89076', '90019', '92789', '96745', '98014', '98056'}</values>
);

-- Table: titleauthor (25 rows)
CREATE TABLE titleauthor (
    au_id TEXT NOT NULL,
        -- <example>'172-32-1176'</example>
        -- <fk> -> authors.au_id</fk>
    title_id TEXT NOT NULL,
        -- <example>'PS3333'</example>
        -- <fk> -> titles.title_id</fk>
    au_ord INTEGER NULL,
        -- <example>1</example>
    royaltyper INTEGER NULL,
        -- <example>100</example>
    PRIMARY KEY (au_id, title_id),
    FOREIGN KEY (au_id) REFERENCES authors(au_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

-- Table: titles (18 rows)
CREATE TABLE titles (
    title_id TEXT NULL PRIMARY KEY,
        -- <example>'BU1032'</example>
    title TEXT NOT NULL,
        -- <example>'The Busy Executive's Database Guide'</example>
    type TEXT NOT NULL,
        -- <values>{'UNDECIDED', 'business', 'mod_cook', 'popular_comp', 'psychology', 'trad_cook'}</values>
    pub_id TEXT NULL,
        -- <values>{'0736', '0877', '1389'}</values>
        -- <fk> -> publishers.pub_id</fk>
    price REAL NULL,
        -- <example>19.990</example>
    advance REAL NULL,
        -- <example>5000.000</example>
    royalty INTEGER NULL,
        -- <example>10</example>
    ytd_sales INTEGER NULL,
        -- <example>4095</example>
    notes TEXT NULL,
        -- <example>'An overview of available database systems with emp...asis on common business applications. Illustrated.'</example>
    pubdate DATETIME NOT NULL,
        -- <example>'1991-06-12 00:00:00.0'</example>
    FOREIGN KEY (pub_id) REFERENCES publishers(pub_id)
);
```