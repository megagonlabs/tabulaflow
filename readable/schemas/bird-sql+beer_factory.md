```sql
-- Database: beer_factory

-- Table: customers (554 rows)
CREATE TABLE customers (
    CustomerID INTEGER PRIMARY KEY,  -- e.g. 101811
    First TEXT,  -- e.g. 'Kenneth'
    Last TEXT,  -- e.g. 'Walton'
    StreetAddress TEXT,  -- e.g. '6715 Commonwealth Dr'
    City TEXT,  -- e.g. 'Sacramento'
    State TEXT,  -- values: {'CA'}
    ZipCode INTEGER,  -- e.g. 94256
    Email TEXT,  -- e.g. 'walton.k76@fastmail.com'
    PhoneNumber TEXT,  -- e.g. '(916) 918-1561'
    FirstPurchaseDate DATE,  -- e.g. '2013-05-30'
    SubscribedToEmailList TEXT,  -- values: {'FALSE', 'TRUE'}
    Gender TEXT  -- values: {'F', 'M'}
);

-- Table: geolocation (3 rows)
CREATE TABLE geolocation (
    LocationID INTEGER PRIMARY KEY,  -- e.g. 0; FK -> location.LocationID
    Latitude REAL,  -- e.g. 0.000
    Longitude REAL,  -- e.g. 0.000
    FOREIGN KEY (LocationID) REFERENCES location(LocationID)
);

-- Table: location (3 rows)
CREATE TABLE location (
    LocationID INTEGER PRIMARY KEY,  -- e.g. 0; FK -> geolocation.LocationID
    LocationName TEXT,  -- values: {'LOST', 'Sac State American River Courtyard', 'Sac State Union'}
    StreetAddress TEXT,  -- values: {'6000 J St'}
    City TEXT,  -- values: {'Sacramento'}
    State TEXT,  -- values: {'CA'}
    ZipCode INTEGER,  -- e.g. 95819
    FOREIGN KEY (LocationID) REFERENCES geolocation(LocationID)
);

-- Table: rootbeer (6430 rows)
CREATE TABLE rootbeer (
    RootBeerID INTEGER PRIMARY KEY,  -- e.g. 100000
    BrandID INTEGER,  -- e.g. 10001; FK -> rootbeerbrand.BrandID
    ContainerType TEXT,  -- values: {'Bottle', 'Can'}
    LocationID INTEGER,  -- e.g. 1; FK -> geolocation.LocationID; FK -> location.LocationID
    PurchaseDate DATE,  -- e.g. '2015-07-03'
    FOREIGN KEY (LocationID) REFERENCES geolocation(LocationID),
    FOREIGN KEY (LocationID) REFERENCES location(LocationID),
    FOREIGN KEY (BrandID) REFERENCES rootbeerbrand(BrandID)
);

-- Table: rootbeerbrand (24 rows)
CREATE TABLE rootbeerbrand (
    BrandID INTEGER PRIMARY KEY,  -- e.g. 10001
    BrandName TEXT,  -- e.g. 'A&W'
    FirstBrewedYear INTEGER,  -- e.g. 1919
    BreweryName TEXT,  -- e.g. 'Dr Pepper Snapple Group'
    City TEXT,  -- e.g. 'Lodi'
    State TEXT,  -- e.g. 'CA'
    Country TEXT,  -- values: {'Australia', 'United States'}
    Description TEXT,  -- e.g. 'After setting up the first A&W Root Beer stand in ...ore root beer stands all across the United States.'
    CaneSugar TEXT,  -- values: {'FALSE', 'TRUE'}
    CornSyrup TEXT,  -- values: {'FALSE', 'TRUE'}
    Honey TEXT,  -- values: {'FALSE', 'TRUE'}
    ArtificialSweetener TEXT,  -- values: {'FALSE', 'TRUE'}
    Caffeinated TEXT,  -- values: {'FALSE', 'TRUE'}
    Alcoholic TEXT,  -- values: {'FALSE'}
    AvailableInCans TEXT,  -- values: {'FALSE', 'TRUE'}
    AvailableInBottles TEXT,  -- values: {'FALSE', 'TRUE'}
    AvailableInKegs TEXT,  -- values: {'FALSE', 'TRUE'}
    Website TEXT,  -- e.g. 'http://www.rootbeer.com/'
    FacebookPage TEXT,  -- values: {'https://www.facebook.com/1919rootbeer', 'https://www.facebook.com/Dads-Old-Fashioned-Root-Beer-and-Cream-Soda-117159998301204/', 'https://www.facebook.com/Dog-N-Suds-Bottled-Root-Beer-117372294947833/', 'https://www.facebook.com/Gales-Root-Beer-207365072632626/', 'https://www.facebook.com/MugRootBeer/', 'https://www.facebook.com/fitzsrootbeer'}
    Twitter TEXT,  -- values: {'https://twitter.com/1919rootbeer', 'https://twitter.com/ilovedads'}
    WholesaleCost REAL,  -- e.g. 0.420
    CurrentRetailPrice REAL  -- e.g. 1.000
);

-- Table: rootbeerreview (713 rows)
CREATE TABLE rootbeerreview (
    CustomerID INTEGER,  -- e.g. 101811; FK -> customers.CustomerID
    BrandID INTEGER,  -- e.g. 10012; FK -> rootbeerbrand.BrandID
    StarRating INTEGER,  -- e.g. 5
    ReviewDate DATE,  -- e.g. '2013-07-15'
    Review TEXT,  -- e.g. 'You could have done better Sactown.'
    PRIMARY KEY (CustomerID, BrandID),
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID),
    FOREIGN KEY (BrandID) REFERENCES rootbeerbrand(BrandID)
);

-- Table: transaction (6312 rows)
CREATE TABLE transaction (
    TransactionID INTEGER PRIMARY KEY,  -- e.g. 100000
    CreditCardNumber INTEGER,  -- e.g. 6011583832864739
    CustomerID INTEGER,  -- e.g. 864896; FK -> customers.CustomerID
    TransactionDate DATE,  -- e.g. '2014-07-07'
    CreditCardType TEXT,  -- values: {'American Express', 'Discover', 'MasterCard', 'Visa'}
    LocationID INTEGER,  -- e.g. 2; FK -> location.LocationID
    RootBeerID INTEGER,  -- e.g. 105661; FK -> rootbeer.RootBeerID
    PurchasePrice REAL,  -- e.g. 3.000
    FOREIGN KEY (CustomerID) REFERENCES customers(CustomerID),
    FOREIGN KEY (LocationID) REFERENCES location(LocationID),
    FOREIGN KEY (RootBeerID) REFERENCES rootbeer(RootBeerID)
);
```