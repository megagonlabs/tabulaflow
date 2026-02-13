```sql
-- Database: beer_factory

/*
Table: customers
Rows: 554
Sample rows:
| CustomerID   | First     | Last    | StreetAddress        | City       | State   | ZipCode   | Email                   | PhoneNumber    | FirstPurchaseDate   | SubscribedToEmailList   | Gender   |
|--------------|-----------|---------|----------------------|------------|---------|-----------|-------------------------|----------------|---------------------|-------------------------|----------|
| 101811       | Kenneth   | Walton  | 6715 Commonwealth Dr | Sacramento | CA      | 94256     | walton.k76@fastmail.com | (916) 918-1561 | 2013-05-30          | FALSE                   | M        |
| 103508       | Madeleine | Jones   | 3603 Leola Way       | Sacramento | CA      | 94258     | j_madeleine@gmail.com   | (916) 186-9423 | 2013-02-06          | FALSE                   | F        |
| 104939       | Damen     | Wheeler | 6740 Branwood Way    | Orangevale | CA      | 95662     | dwheeler@outlook.com    | (916) 164-1156 | 2013-04-11          | FALSE                   | M        |
| 105549       | Kevin     | Gilbert | 3198 Livingston Way  | Folsom     | CA      | 95671     | kgilbert@fastmail.com   | (916) 304-9859 | 2013-02-28          | TRUE                    | M        |
| 105771       | John      | Young   | 663 Westward Way     | Sacramento | CA      | 95899     | john.y90@mail.com       | (916) 730-6109 | 2013-09-05          | TRUE                    | M        |
| ...          | ...       | ...     | ...                  | ...        | ...     | ...       | ...                     | ...            | ...                 | ...                     | ...      |
*/
CREATE TABLE customers (
    CustomerID INTEGER NOT NULL PRIMARY KEY,
        -- <example>101811</example>
    First TEXT NOT NULL,
        -- <example>'Kenneth'</example>
    Last TEXT NOT NULL,
        -- <example>'Walton'</example>
    StreetAddress TEXT NOT NULL,
        -- <example>'6715 Commonwealth Dr'</example>
    City TEXT NOT NULL,
        -- <example>'Sacramento'</example>
    State TEXT NOT NULL,
        -- <values>{'CA'}</values>
    ZipCode INTEGER NOT NULL,
        -- <example>94256</example>
    Email TEXT NOT NULL,
        -- <example>'walton.k76@fastmail.com'</example>
    PhoneNumber TEXT NOT NULL,
        -- <example>'(916) 918-1561'</example>
    FirstPurchaseDate DATE NOT NULL,
        -- <example>'2013-05-30'</example>
    SubscribedToEmailList TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Gender TEXT NOT NULL
        -- <values>{'F', 'M'}</values>
);

/*
Table: geolocation
Rows: 3
All rows:
|   LocationID |   Latitude |   Longitude |
|--------------|------------|-------------|
|            0 |   0        |     0       |
|            1 |  38.566129 |  -121.42643 |
|            2 |  38.559615 |  -121.42243 |
*/
CREATE TABLE geolocation (
    LocationID INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
        -- <fk> -> location.LocationID</fk>
    Latitude REAL NOT NULL,
        -- <example>0.000</example>
    Longitude REAL NOT NULL,
        -- <example>0.000</example>
    FOREIGN KEY (LocationID) REFERENCES location(LocationID)
);

/*
Table: location
Rows: 3
All rows:
|   LocationID | LocationName                       | StreetAddress   | City       | State   | ZipCode   |
|--------------|------------------------------------|-----------------|------------|---------|-----------|
|            0 | LOST                               | [NULL]          | [NULL]     | [NULL]  | [NULL]    |
|            1 | Sac State American River Courtyard | 6000 J St       | Sacramento | CA      | 95819.0   |
|            2 | Sac State Union                    | 6000 J St       | Sacramento | CA      | 95819.0   |
*/
CREATE TABLE location (
    LocationID INTEGER NOT NULL PRIMARY KEY,
        -- <example>0</example>
        -- <fk> -> geolocation.LocationID</fk>
    LocationName TEXT NOT NULL,
        -- <values>{'LOST', 'Sac State American River Courtyard', 'Sac State Union'}</values>
    StreetAddress TEXT NULL,
        -- <values>{'6000 J St'}</values>
    City TEXT NULL,
        -- <values>{'Sacramento'}</values>
    State TEXT NULL,
        -- <values>{'CA'}</values>
    ZipCode INTEGER NULL,
        -- <example>95819</example>
    FOREIGN KEY (LocationID) REFERENCES geolocation(LocationID)
);

/*
Table: rootbeer
Rows: 6430
Sample rows:
| RootBeerID   | BrandID   | ContainerType   | LocationID   | PurchaseDate   |
|--------------|-----------|-----------------|--------------|----------------|
| 100000       | 10001     | Bottle          | 1            | 2015-07-03     |
| 100001       | 10001     | Bottle          | 1            | 2016-05-09     |
| 100002       | 10001     | Can             | 2            | 2015-05-24     |
| 100003       | 10001     | Can             | 2            | 2015-08-15     |
| 100004       | 10001     | Can             | 1            | 2015-03-10     |
| ...          | ...       | ...             | ...          | ...            |
*/
CREATE TABLE rootbeer (
    RootBeerID INTEGER NOT NULL PRIMARY KEY,
        -- <example>100000</example>
    BrandID INTEGER NOT NULL,
        -- <example>10001</example>
        -- <fk> -> rootbeerbrand.BrandID</fk>
    ContainerType TEXT NOT NULL,
        -- <values>{'Bottle', 'Can'}</values>
    LocationID INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> geolocation.LocationID</fk>
        -- <fk> -> location.LocationID</fk>
    PurchaseDate DATE NOT NULL,
        -- <example>'2015-07-03'</example>
    FOREIGN KEY (LocationID) REFERENCES geolocation(LocationID),
    FOREIGN KEY (LocationID) REFERENCES location(LocationID),
    FOREIGN KEY (BrandID) REFERENCES rootbeerbrand(BrandID)
);

/*
Table: rootbeerbrand
Rows: 24
Sample rows:
| BrandID   | BrandName     | FirstBrewedYear   | BreweryName             | City         | State   | Country       | Description                                                                                                                                                                                                 | CaneSugar   | CornSyrup   | Honey   | ArtificialSweetener   | Caffeinated   | Alcoholic   | AvailableInCans   | AvailableInBottles   | AvailableInKegs   | Website                                           | FacebookPage   | Twitter   | WholesaleCost   | CurrentRetailPrice   |
|-----------|---------------|-------------------|-------------------------|--------------|---------|---------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|-------------|---------|-----------------------|---------------|-------------|-------------------|----------------------|-------------------|---------------------------------------------------|----------------|-----------|-----------------|----------------------|
| 10001     | A&W           | 1919              | Dr Pepper Snapple Group | Lodi         | CA      | United States | After setting up the first A&W Root Beer stand in California in 1919, Roy Allen partnered with Frank...erage A&W. The two partners then set out to open more root beer stands all across the United States. | FALSE       | TRUE        | FALSE   | FALSE                 | FALSE         | FALSE       | TRUE              | FALSE                | FALSE             | http://www.rootbeer.com/                          | [NULL]         | [NULL]    | 0.42            | 1.0                  |
| 10002     | A.J. Stephans | 1926              | AJ Stephans Beverages   | Fall River   | MA      | United States | AJ Stephans Company makes 
the finest elixirs and mixers in New England                                                                                                                                                                                                             | TRUE        | FALSE       | FALSE   | FALSE                 | FALSE         | FALSE       | FALSE             | TRUE                 | FALSE             | http://www.ajstephans.com/                        | [NULL]         | [NULL]    | 0.98            | 3.0                  |
| 10003     | Abita         | 1986              | Abita Brewery           | Covington    | LA      | United States | Abita Root Beer is made with a hot mix process using spring water, herbs, vanilla and yucca (which c...ta sweetens its root beer with pure Louisiana cane sugar. The resulting taste is reminiscent of soft | TRUE        | FALSE       | FALSE   | FALSE                 | FALSE         | FALSE       | FALSE             | TRUE                 | FALSE             | https://abita.com/brews/our_brews/abita-root-beer | [NULL]         | [NULL]    | 1.13            | 3.0                  |
| 10004     | Barq's        | 1898              | Coca-Cola               | New Orleans  | LA      | United States | Since 1898 Barq's root beer has had a simple slogan - DRINK BARQ'S. IT'S GOOD. After more than a century, it's (still) good.                                                                                | FALSE       | TRUE        | FALSE   | FALSE                 | TRUE          | FALSE       | TRUE              | FALSE                | FALSE             | http://www.barqs.com/                             | [NULL]         | [NULL]    | 0.4             | 1.0                  |
| 10005     | Bedfords      | 1984              | Northwest Soda Works    | Port Angeles | WA      | United States | Always ice cold, “never with ice”.                                                                                                                                                                          | TRUE        | FALSE       | FALSE   | FALSE                 | FALSE         | FALSE       | FALSE             | TRUE                 | FALSE             | http://bedfordssodas.com/products.html            | [NULL]         | [NULL]    | 1.1             | 3.0                  |
| ...       | ...           | ...               | ...                     | ...          | ...     | ...           | ...                                                                                                                                                                                                         | ...         | ...         | ...     | ...                   | ...           | ...         | ...               | ...                  | ...               | ...                                               | ...            | ...       | ...             | ...                  |
*/
CREATE TABLE rootbeerbrand (
    BrandID INTEGER NOT NULL PRIMARY KEY,
        -- <example>10001</example>
    BrandName TEXT NOT NULL,
        -- <example>'A&W'</example>
    FirstBrewedYear INTEGER NOT NULL,
        -- <example>1919</example>
    BreweryName TEXT NOT NULL,
        -- <example>'Dr Pepper Snapple Group'</example>
    City TEXT NULL,
        -- <example>'Lodi'</example>
    State TEXT NULL,
        -- <example>'CA'</example>
    Country TEXT NOT NULL,
        -- <values>{'Australia', 'United States'}</values>
    Description TEXT NOT NULL,
        -- <example>'After setting up the first A&W Root Beer stand in ...ore root beer stands all across the United States.'</example>
    CaneSugar TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    CornSyrup TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Honey TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    ArtificialSweetener TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Caffeinated TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Alcoholic TEXT NOT NULL,
        -- <values>{'FALSE'}</values>
    AvailableInCans TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    AvailableInBottles TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    AvailableInKegs TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Website TEXT NULL,
        -- <example>'http://www.rootbeer.com/'</example>
    FacebookPage TEXT NULL,
        -- <values>{'https://www.facebook.com/1919rootbeer', 'https://www.facebook.com/Dads-Old-Fashioned-Root-Beer-and-Cream-Soda-117159998301204/', 'https://www.facebook.com/Dog-N-Suds-Bottled-Root-Beer-117372294947833/', 'https://www.facebook.com/Gales-Root-Beer-207365072632626/', 'https://www.facebook.com/MugRootBeer/', 'https://www.facebook.com/fitzsrootbeer'}</values>
    Twitter TEXT NULL,
        -- <values>{'https://twitter.com/1919rootbeer', 'https://twitter.com/ilovedads'}</values>
    WholesaleCost REAL NOT NULL,
        -- <example>0.420</example>
    CurrentRetailPrice REAL NOT NULL
        -- <example>1.000</example>
);

/*
Table: rootbeerreview
Rows: 713
Sample rows:
| CustomerID   | BrandID   | StarRating   | ReviewDate   | Review   |
|--------------|-----------|--------------|--------------|----------|
| 101811       | 10012     | 5            | 2013-07-15   | [NULL]   |
| 101811       | 10014     | 1            | 2013-07-08   | [NULL]   |
| 101811       | 10015     | 3            | 2013-07-25   | [NULL]   |
| 101811       | 10021     | 2            | 2013-11-15   | [NULL]   |
| 105549       | 10015     | 2            | 2013-08-11   | [NULL]   |
| ...          | ...       | ...          | ...          | ...      |
*/
CREATE TABLE rootbeerreview (
    CustomerID INTEGER NOT NULL,
        -- <example>101811</example>
        -- <fk> -> customers.CustomerID</fk>
    BrandID INTEGER NOT NULL,
        -- <example>10012</example>
        -- <fk> -> rootbeerbrand.BrandID</fk>
    StarRating INTEGER NOT NULL,
        -- <example>5</example>
    ReviewDate DATE NOT NULL,
        -- <example>'2013-07-15'</example>
    Review TEXT NULL,
        -- <example>'You could have done better Sactown.'</example>
    PRIMARY KEY (CustomerID, BrandID),
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID),
    FOREIGN KEY (BrandID) REFERENCES rootbeerbrand(BrandID)
);

/*
Table: transaction
Rows: 6312
Sample rows:
| TransactionID   | CreditCardNumber   | CustomerID   | TransactionDate   | CreditCardType   | LocationID   | RootBeerID   | PurchasePrice   |
|-----------------|--------------------|--------------|-------------------|------------------|--------------|--------------|-----------------|
| 100000          | 6011583832864739   | 864896       | 2014-07-07        | Discover         | 2            | 105661       | 3.0             |
| 100001          | 6011583832864739   | 864896       | 2014-07-07        | Discover         | 2            | 105798       | 3.0             |
| 100002          | 6011583832864739   | 864896       | 2014-07-07        | Discover         | 2            | 102514       | 3.0             |
| 100003          | 6011583832864739   | 864896       | 2014-07-07        | Discover         | 2            | 105623       | 3.0             |
| 100004          | 4716634257568793   | 610766       | 2014-07-13        | Visa             | 1            | 103940       | 3.0             |
| ...             | ...                | ...          | ...               | ...              | ...          | ...          | ...             |
*/
CREATE TABLE transaction (
    TransactionID INTEGER NOT NULL PRIMARY KEY,
        -- <example>100000</example>
    CreditCardNumber INTEGER NOT NULL,
        -- <example>6011583832864739</example>
    CustomerID INTEGER NOT NULL,
        -- <example>864896</example>
        -- <fk> -> customers.CustomerID</fk>
    TransactionDate DATE NOT NULL,
        -- <example>'2014-07-07'</example>
    CreditCardType TEXT NOT NULL,
        -- <values>{'American Express', 'Discover', 'MasterCard', 'Visa'}</values>
    LocationID INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> location.LocationID</fk>
    RootBeerID INTEGER NOT NULL,
        -- <example>105661</example>
        -- <fk> -> rootbeer.RootBeerID</fk>
    PurchasePrice REAL NOT NULL,
        -- <example>3.000</example>
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID),
    FOREIGN KEY (LocationID) REFERENCES location(LocationID),
    FOREIGN KEY (RootBeerID) REFERENCES rootbeer(RootBeerID)
);
```