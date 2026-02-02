```sql
-- Database: beer_factory

-- Table: customers (554 rows)
CREATE TABLE customers (
    CustomerID INTEGER NULL PRIMARY KEY,
        -- <example>101811</example>
    First TEXT NULL,
        -- <example>'Kenneth'</example>
    Last TEXT NULL,
        -- <example>'Walton'</example>
    StreetAddress TEXT NULL,
        -- <example>'6715 Commonwealth Dr'</example>
    City TEXT NULL,
        -- <example>'Sacramento'</example>
    State TEXT NULL,
        -- <values>{'CA'}</values>
    ZipCode INTEGER NULL,
        -- <example>94256</example>
    Email TEXT NULL,
        -- <example>'walton.k76@fastmail.com'</example>
    PhoneNumber TEXT NULL,
        -- <example>'(916) 918-1561'</example>
    FirstPurchaseDate DATE NULL,
        -- <example>'2013-05-30'</example>
    SubscribedToEmailList TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Gender TEXT NULL
        -- <values>{'F', 'M'}</values>
);

-- Table: geolocation (3 rows)
CREATE TABLE geolocation (
    LocationID INTEGER NULL PRIMARY KEY,
        -- <example>0</example>
        -- <fk> -> location.LocationID</fk>
    Latitude REAL NULL,
        -- <example>0.000</example>
    Longitude REAL NULL,
        -- <example>0.000</example>
    FOREIGN KEY (LocationID) REFERENCES location(LocationID)
);

-- Table: location (3 rows)
CREATE TABLE location (
    LocationID INTEGER NULL PRIMARY KEY,
        -- <example>0</example>
        -- <fk> -> geolocation.LocationID</fk>
    LocationName TEXT NULL,
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

-- Table: rootbeer (6430 rows)
CREATE TABLE rootbeer (
    RootBeerID INTEGER NULL PRIMARY KEY,
        -- <example>100000</example>
    BrandID INTEGER NULL,
        -- <example>10001</example>
        -- <fk> -> rootbeerbrand.BrandID</fk>
    ContainerType TEXT NULL,
        -- <values>{'Bottle', 'Can'}</values>
    LocationID INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> geolocation.LocationID</fk>
        -- <fk> -> location.LocationID</fk>
    PurchaseDate DATE NULL,
        -- <example>'2015-07-03'</example>
    FOREIGN KEY (LocationID) REFERENCES geolocation(LocationID),
    FOREIGN KEY (LocationID) REFERENCES location(LocationID),
    FOREIGN KEY (BrandID) REFERENCES rootbeerbrand(BrandID)
);

-- Table: rootbeerbrand (24 rows)
CREATE TABLE rootbeerbrand (
    BrandID INTEGER NULL PRIMARY KEY,
        -- <example>10001</example>
    BrandName TEXT NULL,
        -- <example>'A&W'</example>
    FirstBrewedYear INTEGER NULL,
        -- <example>1919</example>
    BreweryName TEXT NULL,
        -- <example>'Dr Pepper Snapple Group'</example>
    City TEXT NULL,
        -- <example>'Lodi'</example>
    State TEXT NULL,
        -- <example>'CA'</example>
    Country TEXT NULL,
        -- <values>{'Australia', 'United States'}</values>
    Description TEXT NULL,
        -- <example>'After setting up the first A&W Root Beer stand in ...ore root beer stands all across the United States.'</example>
    CaneSugar TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    CornSyrup TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Honey TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    ArtificialSweetener TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Caffeinated TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Alcoholic TEXT NULL,
        -- <values>{'FALSE'}</values>
    AvailableInCans TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    AvailableInBottles TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    AvailableInKegs TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    Website TEXT NULL,
        -- <example>'http://www.rootbeer.com/'</example>
    FacebookPage TEXT NULL,
        -- <values>{'https://www.facebook.com/1919rootbeer', 'https://www.facebook.com/Dads-Old-Fashioned-Root-Beer-and-Cream-Soda-117159998301204/', 'https://www.facebook.com/Dog-N-Suds-Bottled-Root-Beer-117372294947833/', 'https://www.facebook.com/Gales-Root-Beer-207365072632626/', 'https://www.facebook.com/MugRootBeer/', 'https://www.facebook.com/fitzsrootbeer'}</values>
    Twitter TEXT NULL,
        -- <values>{'https://twitter.com/1919rootbeer', 'https://twitter.com/ilovedads'}</values>
    WholesaleCost REAL NULL,
        -- <example>0.420</example>
    CurrentRetailPrice REAL NULL
        -- <example>1.000</example>
);

-- Table: rootbeerreview (713 rows)
CREATE TABLE rootbeerreview (
    CustomerID INTEGER NULL,
        -- <example>101811</example>
        -- <fk> -> customers.CustomerID</fk>
    BrandID INTEGER NULL,
        -- <example>10012</example>
        -- <fk> -> rootbeerbrand.BrandID</fk>
    StarRating INTEGER NULL,
        -- <example>5</example>
    ReviewDate DATE NULL,
        -- <example>'2013-07-15'</example>
    Review TEXT NULL,
        -- <example>'You could have done better Sactown.'</example>
    PRIMARY KEY (CustomerID, BrandID),
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID),
    FOREIGN KEY (BrandID) REFERENCES rootbeerbrand(BrandID)
);

-- Table: transaction (6312 rows)
CREATE TABLE transaction (
    TransactionID INTEGER NULL PRIMARY KEY,
        -- <example>100000</example>
    CreditCardNumber INTEGER NULL,
        -- <example>6011583832864739</example>
    CustomerID INTEGER NULL,
        -- <example>864896</example>
        -- <fk> -> customers.CustomerID</fk>
    TransactionDate DATE NULL,
        -- <example>'2014-07-07'</example>
    CreditCardType TEXT NULL,
        -- <values>{'American Express', 'Discover', 'MasterCard', 'Visa'}</values>
    LocationID INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> location.LocationID</fk>
    RootBeerID INTEGER NULL,
        -- <example>105661</example>
        -- <fk> -> rootbeer.RootBeerID</fk>
    PurchasePrice REAL NULL,
        -- <example>3.000</example>
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID),
    FOREIGN KEY (LocationID) REFERENCES location(LocationID),
    FOREIGN KEY (RootBeerID) REFERENCES rootbeer(RootBeerID)
);
```