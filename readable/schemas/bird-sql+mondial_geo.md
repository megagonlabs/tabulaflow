```sql
-- Database: mondial_geo

-- Table: borders (320 rows)
CREATE TABLE borders (
    Country1 TEXT NOT NULL,  -- e.g. 'A'; FK -> country.Code
    Country2 TEXT NOT NULL,  -- e.g. 'CH'; FK -> country.Code
    Length REAL,  -- e.g. 164.000
    PRIMARY KEY (Country1, Country2),
    FOREIGN KEY (Country2) REFERENCES country(Code),
    FOREIGN KEY (Country1) REFERENCES country(Code)
);

-- Table: city (3111 rows)
CREATE TABLE city (
    Name TEXT NOT NULL,  -- e.g. 'Aachen'
    Country TEXT NOT NULL,  -- e.g. 'D'; FK (composite); FK -> country.Code
    Province TEXT NOT NULL,  -- e.g. 'Nordrhein Westfalen'; FK (composite)
    Population INTEGER,  -- e.g. 247113
    Longitude REAL,  -- e.g. 10.000
    Latitude REAL,  -- e.g. 57.000
    PRIMARY KEY (Name, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: continent (5 rows)
CREATE TABLE continent (
    Name TEXT NOT NULL PRIMARY KEY,  -- values: {'Africa', 'America', 'Asia', 'Australia/Oceania', 'Europe'}
    Area REAL  -- e.g. 30254700.000
);

-- Table: country (238 rows)
CREATE TABLE country (
    Name TEXT NOT NULL,  -- e.g. 'Afghanistan'
    Code TEXT NOT NULL PRIMARY KEY,  -- e.g. 'A'
    Capital TEXT,  -- e.g. 'Vienna'
    Province TEXT,  -- e.g. 'Vienna'
    Area REAL,  -- e.g. 83850.000
    Population INTEGER  -- e.g. 8023244
);

-- Table: desert (63 rows)
CREATE TABLE desert (
    Name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'Arabian Desert'
    Area REAL,  -- e.g. 50000.000
    Longitude REAL,  -- e.g. 26.000
    Latitude REAL  -- e.g. 33.000
);

-- Table: economy (238 rows)
CREATE TABLE economy (
    Country TEXT NOT NULL PRIMARY KEY,  -- e.g. 'A'; FK -> country.Code
    GDP REAL,  -- e.g. 152000.000
    Agriculture REAL,  -- e.g. 2.000
    Service REAL,  -- e.g. 34.000
    Industry REAL,  -- e.g. 64.000
    Inflation REAL,  -- e.g. 2.300
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: encompasses (242 rows)
CREATE TABLE encompasses (
    Country TEXT NOT NULL,  -- e.g. 'A'; FK -> country.Code
    Continent TEXT NOT NULL,  -- values: {'Africa', 'America', 'Asia', 'Australia/Oceania', 'Europe'}; FK -> continent.Name
    Percentage REAL,  -- e.g. 100.000
    PRIMARY KEY (Country, Continent),
    FOREIGN KEY (Continent) REFERENCES continent(Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: ethnicGroup (540 rows)
CREATE TABLE ethnicGroup (
    Country TEXT NOT NULL,  -- e.g. 'GE'; FK -> country.Code
    Name TEXT NOT NULL,  -- e.g. 'Abkhaz'
    Percentage REAL,  -- e.g. 1.800
    PRIMARY KEY (Country, Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: geo_desert (155 rows)
CREATE TABLE geo_desert (
    Desert TEXT NOT NULL,  -- e.g. 'Desert'; FK -> desert.Name
    Country TEXT NOT NULL,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    Province TEXT NOT NULL,  -- e.g. 'Abu Dhabi'; FK (composite)
    PRIMARY KEY (Desert, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Desert) REFERENCES desert(Name)
);

-- Table: geo_estuary (266 rows)
CREATE TABLE geo_estuary (
    River TEXT NOT NULL,  -- e.g. 'River'; FK -> river.Name
    Country TEXT NOT NULL,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    Province TEXT NOT NULL,  -- e.g. 'AG'; FK (composite)
    PRIMARY KEY (River, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (River) REFERENCES river(Name)
);

-- Table: geo_island (202 rows)
CREATE TABLE geo_island (
    Island TEXT NOT NULL,  -- e.g. 'Aland'; FK -> island.Name
    Country TEXT NOT NULL,  -- e.g. 'Alan'; FK (composite); FK -> country.Code
    Province TEXT NOT NULL,  -- e.g. '101'; FK (composite)
    PRIMARY KEY (Island, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Island) REFERENCES island(Name)
);

-- Table: geo_lake (254 rows)
CREATE TABLE geo_lake (
    Lake TEXT NOT NULL,  -- e.g. 'Lake'; FK -> lake.Name
    Country TEXT NOT NULL,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    Province TEXT NOT NULL,  -- e.g. 'Adamaoua'; FK (composite)
    PRIMARY KEY (Lake, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Lake) REFERENCES lake(Name)
);

-- Table: geo_mountain (296 rows)
CREATE TABLE geo_mountain (
    Mountain TEXT NOT NULL,  -- e.g. 'Mountain'; FK -> mountain.Name
    Country TEXT NOT NULL,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    Province TEXT NOT NULL,  -- e.g. 'Abruzzo'; FK (composite)
    PRIMARY KEY (Mountain, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Mountain) REFERENCES mountain(Name)
);

-- Table: geo_river (852 rows)
CREATE TABLE geo_river (
    River TEXT NOT NULL,  -- e.g. 'River'; FK -> river.Name
    Country TEXT NOT NULL,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    Province TEXT NOT NULL,  -- e.g. 'AG'; FK (composite)
    PRIMARY KEY (River, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (River) REFERENCES river(Name)
);

-- Table: geo_sea (736 rows)
CREATE TABLE geo_sea (
    Sea TEXT NOT NULL,  -- e.g. 'Sea'; FK -> sea.Name
    Country TEXT NOT NULL,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    Province TEXT NOT NULL,  -- e.g. 'Abruzzo'; FK (composite)
    PRIMARY KEY (Sea, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Sea) REFERENCES sea(Name)
);

-- Table: geo_source (220 rows)
CREATE TABLE geo_source (
    River TEXT NOT NULL,  -- e.g. 'River'; FK -> river.Name
    Country TEXT NOT NULL,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    Province TEXT NOT NULL,  -- e.g. 'Aali an Nil'; FK (composite)
    PRIMARY KEY (River, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (River) REFERENCES river(Name)
);

-- Table: isMember (8009 rows)
CREATE TABLE isMember (
    Country TEXT NOT NULL,  -- e.g. 'A'; FK -> country.Code
    Organization TEXT NOT NULL,  -- e.g. 'AG'; FK -> organization.Abbreviation
    Type TEXT,  -- e.g. 'Type'
    PRIMARY KEY (Country, Organization),
    FOREIGN KEY (Organization) REFERENCES organization(Abbreviation),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: island (276 rows)
CREATE TABLE island (
    Name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'Aland'
    Islands TEXT,  -- e.g. 'Aland Islands'
    Area REAL,  -- e.g. 650.000
    Height REAL,  -- e.g. 675.000
    Type TEXT,  -- values: {'atoll', 'coral', 'lime', 'volcanic'}
    Longitude REAL,  -- e.g. 20.000
    Latitude REAL  -- e.g. 60.100
);

-- Table: islandIn (350 rows)
CREATE TABLE islandIn (
    Island TEXT,  -- e.g. 'Island'; FK -> island.Name
    Sea TEXT,  -- e.g. 'Sea'; FK -> sea.Name
    Lake TEXT,  -- values: {'Lake Huron', 'Lake Manicouagan', 'Lake Nicaragua', 'Lake Toba', 'Lake', 'Ozero Baikal'}; FK -> lake.Name
    River TEXT,  -- values: {'River'}; FK -> river.Name
    FOREIGN KEY (River) REFERENCES river(Name),
    FOREIGN KEY (Lake) REFERENCES lake(Name),
    FOREIGN KEY (Sea) REFERENCES sea(Name),
    FOREIGN KEY (Island) REFERENCES island(Name)
);

-- Table: lake (130 rows)
CREATE TABLE lake (
    Name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'Ammersee'
    Area REAL,  -- e.g. 46.600
    Depth REAL,  -- e.g. 81.100
    Altitude REAL,  -- e.g. 533.000
    Type TEXT,  -- values: {'acid', 'artificial', 'caldera', 'crater', 'impact', 'salt'}
    River TEXT,  -- e.g. 'Ammer'
    Longitude REAL,  -- e.g. 11.600
    Latitude REAL  -- e.g. 48.000
);

-- Table: language (144 rows)
CREATE TABLE language (
    Country TEXT NOT NULL,  -- e.g. 'AFG'; FK -> country.Code
    Name TEXT NOT NULL,  -- e.g. 'Afghan Persian'
    Percentage REAL,  -- e.g. 50.000
    PRIMARY KEY (Country, Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: located (858 rows)
CREATE TABLE located (
    City TEXT,  -- e.g. 'City'; FK (composite)
    Province TEXT,  -- e.g. 'Province'; FK (composite); FK (composite)
    Country TEXT,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    River TEXT,  -- e.g. 'River'; FK -> river.Name
    Lake TEXT,  -- e.g. 'Lake'; FK -> lake.Name
    Sea TEXT,  -- e.g. 'Sea'; FK -> sea.Name
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (City, Province) REFERENCES city(Name, Province),
    FOREIGN KEY (Sea) REFERENCES sea(Name),
    FOREIGN KEY (Lake) REFERENCES lake(Name),
    FOREIGN KEY (River) REFERENCES river(Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: locatedOn (435 rows)
CREATE TABLE locatedOn (
    City TEXT NOT NULL,  -- e.g. 'Aberdeen'; FK (composite)
    Province TEXT NOT NULL,  -- e.g. 'Province'; FK (composite); FK (composite)
    Country TEXT NOT NULL,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    Island TEXT NOT NULL,  -- e.g. 'Island'; FK -> island.Name
    PRIMARY KEY (City, Province, Country, Island),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (City, Province) REFERENCES city(Name, Province),
    FOREIGN KEY (Island) REFERENCES island(Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: mergesWith (55 rows)
CREATE TABLE mergesWith (
    Sea1 TEXT NOT NULL,  -- e.g. 'Andaman Sea'; FK -> sea.Name
    Sea2 TEXT NOT NULL,  -- e.g. 'Sea2'; FK -> sea.Name
    PRIMARY KEY (Sea1, Sea2),
    FOREIGN KEY (Sea2) REFERENCES sea(Name),
    FOREIGN KEY (Sea1) REFERENCES sea(Name)
);

-- Table: mountain (0 rows)
CREATE TABLE mountain (
    Name TEXT NOT NULL PRIMARY KEY,
    Mountains TEXT,
    Height REAL,
    Type TEXT,
    Longitude REAL,
    Latitude REAL
);

-- Table: mountainOnIsland (68 rows)
CREATE TABLE mountainOnIsland (
    Mountain TEXT NOT NULL,  -- e.g. 'Andringitra'; FK -> mountain.Name
    Island TEXT NOT NULL,  -- e.g. 'Island'; FK -> island.Name
    PRIMARY KEY (Mountain, Island),
    FOREIGN KEY (Island) REFERENCES island(Name),
    FOREIGN KEY (Mountain) REFERENCES mountain(Name)
);

-- Table: organization (154 rows)
CREATE TABLE organization (
    Abbreviation TEXT NOT NULL PRIMARY KEY,  -- e.g. 'ABEDA'
    Name TEXT NOT NULL,  -- e.g. 'ASEAN-Mekong Basin Development Group'
    City TEXT,  -- e.g. 'City'; FK (composite)
    Country TEXT,  -- e.g. 'Coun'; FK (composite); FK -> country.Code
    Province TEXT,  -- e.g. 'Province'; FK (composite); FK (composite)
    Established DATE,  -- e.g. 'Established'
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (City, Province) REFERENCES city(Name, Province),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: politics (239 rows)
CREATE TABLE politics (
    Country TEXT NOT NULL PRIMARY KEY,  -- e.g. 'A'; FK -> country.Code
    Independence DATE,  -- e.g. 'Independence'
    Dependent TEXT,  -- values: {'AUS', 'DK', 'Depe', 'F', 'GB', 'N', 'NL', 'NZ', 'TJ', 'USA'}; FK -> country.Code
    Government TEXT,  -- e.g. 'Government'
    FOREIGN KEY (Dependent) REFERENCES country(Code),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: population (238 rows)
CREATE TABLE population (
    Country TEXT NOT NULL PRIMARY KEY,  -- e.g. 'A'; FK -> country.Code
    Population_Growth REAL,  -- e.g. 0.410
    Infant_Mortality REAL,  -- e.g. 6.200
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: province (1450 rows)
CREATE TABLE province (
    Name TEXT NOT NULL,  -- e.g. 'AG'
    Country TEXT NOT NULL,  -- e.g. 'CH'; FK -> country.Code
    Population INTEGER,  -- e.g. 1599605
    Area REAL,  -- e.g. 238792.000
    Capital TEXT,  -- e.g. 'Malakal'
    CapProv TEXT,  -- e.g. 'Aali an Nil'
    PRIMARY KEY (Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: religion (454 rows)
CREATE TABLE religion (
    Country TEXT NOT NULL,  -- e.g. 'BERM'; FK -> country.Code
    Name TEXT NOT NULL,  -- e.g. 'African Methodist Episcopal'
    Percentage REAL,  -- e.g. 11.000
    PRIMARY KEY (Country, Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: river (218 rows)
CREATE TABLE river (
    Name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'Aare'
    River TEXT,  -- e.g. 'Rhein'
    Lake TEXT,  -- e.g. 'Brienzersee'; FK -> lake.Name
    Sea TEXT,  -- e.g. 'Atlantic Ocean'
    Length REAL,  -- e.g. 288.000
    SourceLongitude REAL,  -- e.g. 8.200
    SourceLatitude REAL,  -- e.g. 46.550
    Mountains TEXT,  -- e.g. 'Alps'
    SourceAltitude REAL,  -- e.g. 2310.000
    EstuaryLongitude REAL,  -- e.g. 8.220
    EstuaryLatitude REAL,  -- e.g. 47.610
    FOREIGN KEY (Lake) REFERENCES lake(Name)
);

-- Table: sea (35 rows)
CREATE TABLE sea (
    Name TEXT NOT NULL PRIMARY KEY,  -- e.g. 'Andaman Sea'
    Depth REAL  -- e.g. 3113.000
);

-- Table: target (205 rows)
CREATE TABLE target (
    Country TEXT NOT NULL PRIMARY KEY,  -- e.g. 'A'; FK -> country.Code
    Target TEXT,  -- values: {'Christian', 'Target', 'non-Christian'}
    FOREIGN KEY (Country) REFERENCES country(Code)
);
```