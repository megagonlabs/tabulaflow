```sql
-- Database: book_publishing_company

/*
Schema: NULLTable: authors
Rows: 23
Sample rows:
| au_id       | au_lname   | au_fname   | phone        | address              | city       | state   | zip   | contract   |
|-------------|------------|------------|--------------|----------------------|------------|---------|-------|------------|
| 172-32-1176 | White      | Johnson    | 408 496-7223 | 10932 Bigge Rd.      | Menlo Park | CA      | 94025 | 0          |
| 213-46-8915 | Green      | Marjorie   | 415 986-7020 | 309 63rd St. #411    | Oakland    | CA      | 94618 | 0          |
| 238-95-7766 | Carson     | Cheryl     | 415 548-7723 | 589 Darwin Ln.       | Berkeley   | CA      | 94705 | 0          |
| 267-41-2394 | O'Leary    | Michael    | 408 286-2428 | 22 Cleveland Av. #14 | San Jose   | CA      | 95128 | 0          |
| 274-80-9391 | Straight   | Dean       | 415 834-2919 | 5420 College Av.     | Oakland    | CA      | 94609 | 0          |
| ...         | ...        | ...        | ...          | ...                  | ...        | ...     | ...   | ...        |
*/
CREATE TABLE authors (
    au_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'172-32-1176'</example>
    au_lname TEXT NOT NULL,
        -- <example>'White'</example>
    au_fname TEXT NOT NULL,
        -- <example>'Johnson'</example>
    phone TEXT NOT NULL,
        -- <example>'408 496-7223'</example>
    address TEXT NOT NULL,
        -- <example>'10932 Bigge Rd.'</example>
    city TEXT NOT NULL,
        -- <example>'Menlo Park'</example>
    state TEXT NOT NULL,
        -- <values>{'CA', 'IN', 'KS', 'MD', 'MI', 'OR', 'TN', 'UT'}</values>
    zip TEXT NOT NULL,
        -- <example>'94025'</example>
    contract TEXT NOT NULL
        -- <values>{'0'}</values>
);

/*
Schema: NULLTable: discounts
Rows: 3
All rows:
| discounttype      | stor_id   | lowqty   | highqty   |   discount |
|-------------------|-----------|----------|-----------|------------|
| Initial Customer  | [NULL]    | [NULL]   | [NULL]    |       10.5 |
| Volume Discount   | [NULL]    | 100.0    | 1000.0    |        6.7 |
| Customer Discount | 8042      | [NULL]   | [NULL]    |        5   |
*/
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

/*
Schema: NULLTable: employee
Rows: 43
Sample rows:
| emp_id    | fname   | minit   | lname     | job_id   | job_lvl   | pub_id   | hire_date             |
|-----------|---------|---------|-----------|----------|-----------|----------|-----------------------|
| A-C71970F | Aria    |         | Cruz      | 10       | 87        | 1389     | 1991-10-26 00:00:00.0 |
| A-R89858F | Annette |         | Roulet    | 6        | 152       | 9999     | 1990-02-21 00:00:00.0 |
| AMD15433F | Ann     | M       | Devon     | 3        | 200       | 9952     | 1991-07-16 00:00:00.0 |
| ARD36773F | Anabela | R       | Domingues | 8        | 100       | 0877     | 1993-01-27 00:00:00.0 |
| CFH28514M | Carlos  | F       | Hernadez  | 5        | 211       | 9999     | 1989-04-21 00:00:00.0 |
| ...       | ...     | ...     | ...       | ...      | ...       | ...      | ...                   |
*/
CREATE TABLE employee (
    emp_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'A-C71970F'</example>
    fname TEXT NOT NULL,
        -- <example>'Aria'</example>
    minit TEXT NOT NULL,
        -- <example>''</example>
    lname TEXT NOT NULL,
        -- <example>'Cruz'</example>
    job_id INTEGER NOT NULL,
        -- <example>10</example>
        -- <fk> -> jobs.job_id</fk>
    job_lvl INTEGER NOT NULL,
        -- <example>87</example>
    pub_id TEXT NOT NULL,
        -- <values>{'0736', '0877', '1389', '1622', '1756', '9901', '9952', '9999'}</values>
        -- <fk> -> publishers.pub_id</fk>
    hire_date DATETIME NOT NULL,
        -- <example>'1991-10-26 00:00:00.0'</example>
    FOREIGN KEY (job_id) REFERENCES jobs(job_id),
    FOREIGN KEY (pub_id) REFERENCES publishers(pub_id)
);

/*
Schema: NULLTable: jobs
Rows: 14
Sample rows:
| job_id   | job_desc                     | min_lvl   | max_lvl   |
|----------|------------------------------|-----------|-----------|
| 1        | New Hire - Job not specified | 10        | 10        |
| 2        | Chief Executive Officer      | 200       | 250       |
| 3        | Business Operations Manager  | 175       | 225       |
| 4        | Chief Financial Officier     | 175       | 250       |
| 5        | Publisher                    | 150       | 250       |
| ...      | ...                          | ...       | ...       |
*/
CREATE TABLE jobs (
    job_id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    job_desc TEXT NOT NULL,
        -- <example>'New Hire - Job not specified'</example>
    min_lvl INTEGER NOT NULL,
        -- <example>10</example>
    max_lvl INTEGER NOT NULL
        -- <example>10</example>
);

/*
Schema: NULLTable: pub_info
Rows: 7
All rows:
|   pub_id | logo                                                                                                                                                                                                        | pr_info                                                                                                                                                                                                     |
|----------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
|     0877 | 0x4749463839618B002F00B30F00000000800000008000808000000080800080008080808080C0C0C0FF000000FF00FFFF00...63DD0BE66D2ACD8B2BCB9283CEDEE3C6A53EE39BA7579A62C1294917DC473035E0B9E3183F9A3BB6F7ABDE608B018800003B | This is sample text data for Binnet & Hardley, publisher 0877 in the pubs database. Binnet & Hardley...nnet & Hardley, publisher 0877 in the pubs database. Binnet & Hardley is located in Washington, D.C. |
|     1389 | 0x474946383961C2001D00B30F00000000800000008000808000000080800080008080808080C0C0C0FF000000FF00FFFF00...0E5CD11D1D478C1C59714053AA4C4955AB4B9956879AB497F62E1CBA2373DA25B752239F8787119390AB5806C74E1100003B | This is sample text data for Algodata Infosystems, publisher 1389 in the pubs database. Algodata Inf...stems, publisher 1389 in the pubs database. Algodata Infosystems is located in Berkeley, California. |
|     1622 | 0x474946383961F5003400B30F00000000800000008000808000000080800080008080808080C0C0C0FF000000FF00FFFF00...69DCCE684725FC0546C3B40875D79E70A5867A8274E69E8BAEAC1FEEC02E92EE3AA7ADA015365BEFBE83F2EB6F351100003B | This is sample text data for Five Lakes Publishing, publisher 1622 in the pubs database. Five Lakes ...lishing, publisher 1622 in the pubs database. Five Lakes Publishing is located in Chicago, Illinois. |
|     1756 | 0x474946383961E3002500B30F00000000800000008000808000000080800080008080808080C0C0C0FF000000FF00FFFF00...B2EB9972EB6EDB66D26D71768D5B2B1FEFC65B11AFA5FA96C93AF50AA6AFBEFE263C1DC0FCA2AB8AC210472C310A1100003B | This is sample text data for Ramona Publishers, publisher 1756 in the pubs database. Ramona Publishers is located in Dallas, Texas.                                                                         |
|     9901 | 0x4749463839615D002200B30F00000000800000008000808000000080800080008080808080C0C0C0FF000000FF00FFFF00...A2D4D3082E583C89BD2C2D720753E1C8922697D44CF6AE53BF6D4041750B4AD467C54548932A1D7374A9D3A789004400003B | This is sample text data for GGG&G, publisher 9901 in the pubs database. GGG&G is located in München, Germany.                                                                                              |
|     9952 | 0x47494638396107012800B30F00000000800000008000808000000080800080008080808080C0C0C0FF000000FF00FFFF00...CA67297129D88F9E881A3AA83E8AB623E85E8B0EDAE89C892216E9A584B80318A69C7E3269A7A046FA69A8A4B6094004003B | This is sample text data for Scootney Books, publisher 9952 in the pubs database. Scootney Books is located in New York City, New York.                                                                     |
|     9999 | 0x474946383961A9002400B30F00000000800000008000808000000080800080008080808080C0C0C0FF000000FF00FFFF00...B5588BE5CCA5B1BDA377B99E3CBE9EDA31944A951ADF7DB15263A1429B37BB7E429D8EC4D754B87164078F2B87012002003B | This is sample text data for Lucerne Publishing, publisher 9999 in the pubs database. Lucerne publis...rne Publishing, publisher 9999 in the pubs database. Lucerne publishing is located in Paris, France. |
*/
CREATE TABLE pub_info (
    pub_id TEXT NOT NULL PRIMARY KEY,
        -- <values>{'0877', '1389', '1622', '1756', '9901', '9952', '9999'}</values>
        -- <fk> -> publishers.pub_id</fk>
    logo BLOB NOT NULL,
        -- <example>'0x4749463839618B002F00B30F000000008000000080008080...294917DC473035E0B9E3183F9A3BB6F7ABDE608B018800003B'</example>
    pr_info TEXT NOT NULL,
        -- <values>{'This is sample text data for Algodata Infosystems,...ta Infosystems is located in Berkeley, California.', 'This is sample text data for Binnet & Hardley, pub...e. Binnet & Hardley is located in Washington, D.C.', 'This is sample text data for Five Lakes Publishing... Lakes Publishing is located in Chicago, Illinois.', 'This is sample text data for GGG&G, publisher 9901...bs database. GGG&G is located in München, Germany.', 'This is sample text data for Lucerne Publishing, p...e. Lucerne publishing is located in Paris, France.', 'This is sample text data for Ramona Publishers, pu...se. Ramona Publishers is located in Dallas, Texas.', 'This is sample text data for Scootney Books, publi...otney Books is located in New York City, New York.'}</values>
    FOREIGN KEY (pub_id) REFERENCES publishers(pub_id)
);

/*
Schema: NULLTable: publishers
Rows: 8
All rows:
|   pub_id | pub_name              | city       | state   | country   |
|----------|-----------------------|------------|---------|-----------|
|     0736 | New Moon Books        | Boston     | MA      | USA       |
|     0877 | Binnet & Hardley      | Washington | DC      | USA       |
|     1389 | Algodata Infosystems  | Berkeley   | CA      | USA       |
|     1622 | Five Lakes Publishing | Chicago    | IL      | USA       |
|     1756 | Ramona Publishers     | Dallas     | TX      | USA       |
|     9901 | GGG&G                 | Mnchen            | [NULL]  | Germany   |
|     9952 | Scootney Books        | New York   | NY      | USA       |
|     9999 | Lucerne Publishing    | Paris      | [NULL]  | France    |
*/
CREATE TABLE publishers (
    pub_id TEXT NOT NULL PRIMARY KEY,
        -- <values>{'0736', '0877', '1389', '1622', '1756', '9901', '9952', '9999'}</values>
    pub_name TEXT NOT NULL,
        -- <values>{'Algodata Infosystems', 'Binnet & Hardley', 'Five Lakes Publishing', 'GGG&G', 'Lucerne Publishing', 'New Moon Books', 'Ramona Publishers', 'Scootney Books'}</values>
    city TEXT NOT NULL,
        -- <values>{'Berkeley', 'Boston', 'Chicago', 'Dallas', 'Mnchen', 'New York', 'Paris', 'Washington'}</values>
    state TEXT NULL,
        -- <values>{'CA', 'DC', 'IL', 'MA', 'NY', 'TX'}</values>
    country TEXT NOT NULL
        -- <values>{'France', 'Germany', 'USA'}</values>
);

/*
Schema: NULLTable: roysched
Rows: 86
Sample rows:
| title_id   | lorange   | hirange   | royalty   |
|------------|-----------|-----------|-----------|
| BU1032     | 0         | 5000      | 10        |
| BU1032     | 5001      | 50000     | 12        |
| PC1035     | 0         | 2000      | 10        |
| PC1035     | 2001      | 3000      | 12        |
| PC1035     | 3001      | 4000      | 14        |
| ...        | ...       | ...       | ...       |
*/
CREATE TABLE roysched (
    title_id TEXT NOT NULL,
        -- <example>'BU1032'</example>
        -- <fk> -> titles.title_id</fk>
    lorange INTEGER NOT NULL,
        -- <example>0</example>
    hirange INTEGER NOT NULL,
        -- <example>5000</example>
    royalty INTEGER NOT NULL,
        -- <example>10</example>
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

/*
Schema: NULLTable: sales
Rows: 21
Sample rows:
| stor_id   | ord_num   | ord_date              | qty   | payterms   | title_id   |
|-----------|-----------|-----------------------|-------|------------|------------|
| 6380      | 6871      | 1994-09-14 00:00:00.0 | 5     | Net 60     | BU1032     |
| 6380      | 722a      | 1994-09-13 00:00:00.0 | 3     | Net 60     | PS2091     |
| 7066      | A2976     | 1993-05-24 00:00:00.0 | 50    | Net 30     | PC8888     |
| 7066      | QA7442.3  | 1994-09-13 00:00:00.0 | 75    | ON invoice | PS2091     |
| 7067      | D4482     | 1994-09-14 00:00:00.0 | 10    | Net 60     | PS2091     |
| ...       | ...       | ...                   | ...   | ...        | ...        |
*/
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

/*
Schema: NULLTable: stores
Rows: 6
All rows:
|   stor_id | stor_name                            | stor_address        | city      | state   |   zip |
|-----------|--------------------------------------|---------------------|-----------|---------|-------|
|      6380 | Eric the Read Books                  | 788 Catamaugus Ave. | Seattle   | WA      | 98056 |
|      7066 | Barnum's                             | 567 Pasadena Ave.   | Tustin    | CA      | 92789 |
|      7067 | News & Brews                         | 577 First St.       | Los Gatos | CA      | 96745 |
|      7131 | Doc-U-Mat: Quality Laundry and Books | 24-A Avogadro Way   | Remulade  | WA      | 98014 |
|      7896 | Fricative Bookshop                   | 89 Madison St.      | Fremont   | CA      | 90019 |
|      8042 | Bookbeat                             | 679 Carson St.      | Portland  | OR      | 89076 |
*/
CREATE TABLE stores (
    stor_id TEXT NOT NULL PRIMARY KEY,
        -- <values>{'6380', '7066', '7067', '7131', '7896', '8042'}</values>
    stor_name TEXT NOT NULL,
        -- <values>{'Barnum's', 'Bookbeat', 'Doc-U-Mat: Quality Laundry and Books', 'Eric the Read Books', 'Fricative Bookshop', 'News & Brews'}</values>
    stor_address TEXT NOT NULL,
        -- <values>{'24-A Avogadro Way', '567 Pasadena Ave.', '577 First St.', '679 Carson St.', '788 Catamaugus Ave.', '89 Madison St.'}</values>
    city TEXT NOT NULL,
        -- <values>{'Fremont', 'Los Gatos', 'Portland', 'Remulade', 'Seattle', 'Tustin'}</values>
    state TEXT NOT NULL,
        -- <values>{'CA', 'OR', 'WA'}</values>
    zip TEXT NOT NULL
        -- <values>{'89076', '90019', '92789', '96745', '98014', '98056'}</values>
);

/*
Schema: NULLTable: titleauthor
Rows: 25
Sample rows:
| au_id       | title_id   | au_ord   | royaltyper   |
|-------------|------------|----------|--------------|
| 172-32-1176 | PS3333     | 1        | 100          |
| 213-46-8915 | BU1032     | 2        | 40           |
| 213-46-8915 | BU2075     | 1        | 100          |
| 238-95-7766 | PC1035     | 1        | 100          |
| 267-41-2394 | BU1111     | 2        | 40           |
| ...         | ...        | ...      | ...          |
*/
CREATE TABLE titleauthor (
    au_id TEXT NOT NULL,
        -- <example>'172-32-1176'</example>
        -- <fk> -> authors.au_id</fk>
    title_id TEXT NOT NULL,
        -- <example>'PS3333'</example>
        -- <fk> -> titles.title_id</fk>
    au_ord INTEGER NOT NULL,
        -- <example>1</example>
    royaltyper INTEGER NOT NULL,
        -- <example>100</example>
    PRIMARY KEY (au_id, title_id),
    FOREIGN KEY (au_id) REFERENCES authors(au_id),
    FOREIGN KEY (title_id) REFERENCES titles(title_id)
);

/*
Schema: NULLTable: titles
Rows: 18
Sample rows:
| title_id   | title                                                | type     | pub_id   | price   | advance   | royalty   | ytd_sales   | notes                                                                                                                   | pubdate               |
|------------|------------------------------------------------------|----------|----------|---------|-----------|-----------|-------------|-------------------------------------------------------------------------------------------------------------------------|-----------------------|
| BU1032     | The Busy Executive's Database Guide                  | business | 1389     | 19.99   | 5000.0    | 10.0      | 4095.0      | An overview of available database systems with emphasis on common business applications. Illustrated.                   | 1991-06-12 00:00:00.0 |
| BU1111     | Cooking with Computers: Surreptitious Balance Sheets | business | 1389     | 11.95   | 5000.0    | 10.0      | 3876.0      | Helpful hints on how to use your electronic resources to the best advantage.                                            | 1991-06-09 00:00:00.0 |
| BU2075     | You Can Combat Computer Stress!                      | business | 0736     | 2.99    | 10125.0   | 24.0      | 18722.0     | The latest medical and psychological techniques for living with the electronic office. Easy-to-understand explanations. | 1991-06-30 00:00:00.0 |
| BU7832     | Straight Talk About Computers                        | business | 1389     | 19.99   | 5000.0    | 10.0      | 4095.0      | Annotated analysis of what computers can do for you: a no-hype guide for the critical user.                             | 1991-06-22 00:00:00.0 |
| MC2222     | Silicon Valley Gastronomic Treats                    | mod_cook | 0877     | 19.99   | 0.0       | 12.0      | 2032.0      | Favorite recipes for quick, easy, and elegant meals.                                                                    | 1991-06-09 00:00:00.0 |
| ...        | ...                                                  | ...      | ...      | ...     | ...       | ...       | ...         | ...                                                                                                                     | ...                   |
*/
CREATE TABLE titles (
    title_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'BU1032'</example>
    title TEXT NOT NULL,
        -- <example>'The Busy Executive's Database Guide'</example>
    type TEXT NOT NULL,
        -- <values>{'UNDECIDED', 'business', 'mod_cook', 'popular_comp', 'psychology', 'trad_cook'}</values>
    pub_id TEXT NOT NULL,
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