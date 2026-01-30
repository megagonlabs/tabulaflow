```sql
-- Database: world

-- Table: City (4079 rows)
CREATE TABLE City (
    ID INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    Name TEXT NOT NULL,  -- e.g. 'Kabul'
    CountryCode TEXT NOT NULL,  -- e.g. 'AFG'; FK -> Country.Code
    District TEXT NOT NULL,  -- e.g. 'Kabol'
    Population INTEGER NOT NULL,  -- e.g. 1780000
    FOREIGN KEY (CountryCode) REFERENCES Country(Code)
);

-- Table: Country (239 rows)
CREATE TABLE Country (
    Code TEXT NOT NULL PRIMARY KEY,  -- e.g. 'ABW'
    Name TEXT NOT NULL,  -- e.g. 'Aruba'
    Continent TEXT NOT NULL,  -- values: {'Africa', 'Antarctica', 'Asia', 'Europe', 'North America', 'Oceania', 'South America'}
    Region TEXT NOT NULL,  -- e.g. 'Caribbean'
    SurfaceArea REAL NOT NULL,  -- e.g. 193.000
    IndepYear INTEGER,  -- e.g. 1919
    Population INTEGER NOT NULL,  -- e.g. 103000
    LifeExpectancy REAL,  -- e.g. 78.400
    GNP REAL,  -- e.g. 828.000
    GNPOld REAL,  -- e.g. 793.000
    LocalName TEXT NOT NULL,  -- e.g. 'Aruba'
    GovernmentForm TEXT NOT NULL,  -- e.g. 'Nonmetropolitan Territory of The Netherlands'
    HeadOfState TEXT,  -- e.g. 'Beatrix'
    Capital INTEGER,  -- e.g. 129
    Code2 TEXT NOT NULL  -- e.g. 'AW'
);

-- Table: CountryLanguage (984 rows)
CREATE TABLE CountryLanguage (
    CountryCode TEXT NOT NULL,  -- e.g. 'ABW'; FK -> Country.Code
    Language TEXT NOT NULL,  -- e.g. 'Dutch'
    IsOfficial TEXT NOT NULL,  -- values: {'F', 'T'}
    Percentage REAL NOT NULL,  -- e.g. 5.300
    PRIMARY KEY (CountryCode, Language),
    FOREIGN KEY (CountryCode) REFERENCES Country(Code)
);
```