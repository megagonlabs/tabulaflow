```sql
-- Database: book_publishing_company

-- Table: authors (23 rows)
CREATE TABLE authors (
    au_id TEXT PRIMARY KEY,  -- e.g. '172-32-1176'
    au_lname TEXT NOT NULL,  -- e.g. 'White'
    au_fname TEXT NOT NULL,  -- e.g. 'Johnson'
    phone TEXT NOT NULL,  -- e.g. '408 496-7223'
    address TEXT,  -- e.g. '10932 Bigge Rd.'
    city TEXT,  -- e.g. 'Menlo Park'
    state TEXT,  -- values: {'CA', 'IN', 'KS', 'MD', 'MI', 'OR', 'TN', 'UT'}
    zip TEXT,  -- e.g. '94025'
    contract TEXT NOT NULL  -- values: {'0'}
);

-- Table: discounts (3 rows)
CREATE TABLE discounts (
    discounttype TEXT NOT NULL,  -- values: {'Customer Discount', 'Initial Customer', 'Volume Discount'}
    stor_id TEXT,  -- values: {'8042'}; FK -> stores.stor_id
    lowqty INTEGER,  -- e.g. 100
    highqty INTEGER,  -- e.g. 1000
    discount REAL NOT NULL,  -- e.g. 10.500
    FOREIGN KEY (stor_id) REFERENCES stores(stor_id)
);

-- Table: employee (43 rows)
CREATE TABLE employee (
    emp_id TEXT PRIMARY KEY,  -- e.g. 'A-C71970F'
    fname TEXT NOT NULL,  -- e.g. 'Aria'
    minit TEXT,  -- e.g. ''
    lname TEXT NOT NULL,  -- e.g. 'Cruz'
    job_id INTEGER NOT NULL,  -- e.g. 10; FK -> jobs.job_id
    job_lvl INTEGER,  -- e.g. 87
    pub_id TEXT NOT NULL,  -- values: {'0736', '0877', '1389', '1622', '1756', '9901', '9952', '9999'}; FK -> publishers.pub_id
    hire_date DATETIME NOT NULL,  -- e.g. '1991-10-26 00:00:00.0'
    FOREIGN KEY (job_id) REFERENCES jobs(job_id),
    FOREIGN KEY (pub_id) REFERENCES publishers(pub_id)
);

-- Table: jobs (14 rows)
CREATE TABLE jobs (
    job_id INTEGER PRIMARY KEY,  -- e.g. 1
    job_desc TEXT NOT NULL,  -- e.g. 'New Hire - Job not specified'
    min_lvl INTEGER NOT NULL,  -- e.g. 10
    max_lvl INTEGER NOT NULL  -- e.g. 10
);

-- Table: pub_info (7 rows)
CREATE TABLE pub_info (
    pub_id TEXT PRIMARY KEY,  -- values: {'0877', '1389', '1622', '1756', '9901', '9952', '9999'}; FK -> publishers.pub_id
    logo BLOB,  -- e.g. '0x4749463839618B002F00B30F000000008000000080008080...294917DC473035E0B9E3183F9A3BB6F7ABDE608B018800003B'
    pr_info TEXT,  -- values: {'This is sample text data for Algodata Infosystems,...ta Infosystems is located in Berkeley, California.', 'This is sample text data for Binnet & Hardley, pub...e. Binnet & Hardley is located in Washington, D.C.', 'This is sample text data for Five Lakes Publishing... Lakes Publishing is located in Chicago, Illinois.', 'This is sample text data for GGG&G, publisher 9901...bs database. GGG&G is located in München, Germany.', 'This is sample text data for Lucerne Publishing, p...e. Lucerne publishing is located in Paris, France.', 'This is sample text data for Ramona Publishers, pu...se. Ramona Publishers is located in Dallas, Texas.', 'This is sample text data for Scootney Books, publi...otney Books is located in New York City, New York.'}
    FOREIGN KEY (pub_id) REFERENCES publishers(pub_id)
);

-- Table: publishers (8 rows)
CREATE TABLE publishers (
    pub_id TEXT PRIMARY KEY,  -- values: {'0736', '0877', '1389', '1622', '1756', '9901', '9952', '9999'}
    pub_name TEXT,  -- values: {'Algodata Infosystems', 'Binnet & Hardley', 'Five Lakes Publishing', 'GGG&G', 'Lucerne Publishing', 'New Moon Books', 'Ramona Publishers', 'Scootney Books'}
    city TEXT,  -- values: {'Berkeley', 'Boston', 'Chicago', 'Dallas', 'Mnchen', 'New York', 'Paris', 'Washington'}
    state TEXT,  -- values: {'CA', 'DC', 'IL', 'MA', 'NY', 'TX'}
    country TEXT  -- values: {'France', 'Germany', 'USA'}
);

-- Table: roysched (86 rows)
CREATE TABLE roysched (
    title_id TEXT NOT NULL,  -- e.g. 'BU1032'; FK -> titles.title_id
    lorange INTEGER,  -- e.g. 0
    hirange INTEGER,  -- e.g. 5000
    royalty INTEGER,  -- e.g. 10
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

-- Table: sales (21 rows)
CREATE TABLE sales (
    stor_id TEXT NOT NULL,  -- values: {'6380', '7066', '7067', '7131', '7896', '8042'}; FK -> stores.stor_id
    ord_num TEXT NOT NULL,  -- e.g. '6871'
    ord_date DATETIME NOT NULL,  -- e.g. '1994-09-14 00:00:00.0'
    qty INTEGER NOT NULL,  -- e.g. 5
    payterms TEXT NOT NULL,  -- values: {'Net 30', 'Net 60', 'ON invoice'}
    title_id TEXT NOT NULL,  -- e.g. 'BU1032'; FK -> titles.title_id
    PRIMARY KEY (stor_id, ord_num, title_id),
    FOREIGN KEY (stor_id) REFERENCES stores(stor_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

-- Table: stores (6 rows)
CREATE TABLE stores (
    stor_id TEXT PRIMARY KEY,  -- values: {'6380', '7066', '7067', '7131', '7896', '8042'}
    stor_name TEXT,  -- values: {'Barnum's', 'Bookbeat', 'Doc-U-Mat: Quality Laundry and Books', 'Eric the Read Books', 'Fricative Bookshop', 'News & Brews'}
    stor_address TEXT,  -- values: {'24-A Avogadro Way', '567 Pasadena Ave.', '577 First St.', '679 Carson St.', '788 Catamaugus Ave.', '89 Madison St.'}
    city TEXT,  -- values: {'Fremont', 'Los Gatos', 'Portland', 'Remulade', 'Seattle', 'Tustin'}
    state TEXT,  -- values: {'CA', 'OR', 'WA'}
    zip TEXT  -- values: {'89076', '90019', '92789', '96745', '98014', '98056'}
);

-- Table: titleauthor (25 rows)
CREATE TABLE titleauthor (
    au_id TEXT NOT NULL,  -- e.g. '172-32-1176'; FK -> authors.au_id
    title_id TEXT NOT NULL,  -- e.g. 'PS3333'; FK -> titles.title_id
    au_ord INTEGER,  -- e.g. 1
    royaltyper INTEGER,  -- e.g. 100
    PRIMARY KEY (au_id, title_id),
    FOREIGN KEY (au_id) REFERENCES authors(au_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

-- Table: titles (18 rows)
CREATE TABLE titles (
    title_id TEXT PRIMARY KEY,  -- e.g. 'BU1032'
    title TEXT NOT NULL,  -- e.g. 'The Busy Executive's Database Guide'
    type TEXT NOT NULL,  -- values: {'UNDECIDED', 'business', 'mod_cook', 'popular_comp', 'psychology', 'trad_cook'}
    pub_id TEXT,  -- values: {'0736', '0877', '1389'}; FK -> publishers.pub_id
    price REAL,  -- e.g. 19.990
    advance REAL,  -- e.g. 5000.000
    royalty INTEGER,  -- e.g. 10
    ytd_sales INTEGER,  -- e.g. 4095
    notes TEXT,  -- e.g. 'An overview of available database systems with emp...asis on common business applications. Illustrated.'
    pubdate DATETIME NOT NULL,  -- e.g. '1991-06-12 00:00:00.0'
    FOREIGN KEY (pub_id) REFERENCES publishers(pub_id)
);
```