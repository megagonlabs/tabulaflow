```sql
-- Database: mondial_geo

-- Table: borders (320 rows)
CREATE TABLE borders (
    Country1 TEXT NOT NULL,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Country2 TEXT NOT NULL,
        -- <example>'CH'</example>
        -- <fk> -> country.Code</fk>
    Length REAL NULL,
        -- <example>164.000</example>
    PRIMARY KEY (Country1, Country2),
    FOREIGN KEY (Country2) REFERENCES country(Code),
    FOREIGN KEY (Country1) REFERENCES country(Code)
);

-- Table: city (3111 rows)
CREATE TABLE city (
    Name TEXT NOT NULL,
        -- <example>'Aachen'</example>
    Country TEXT NOT NULL,
        -- <example>'D'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NOT NULL,
        -- <example>'Nordrhein Westfalen'</example>
        -- <fk>composite</fk>
    Population INTEGER NULL,
        -- <example>247113</example>
    Longitude REAL NULL,
        -- <example>10.000</example>
    Latitude REAL NULL,
        -- <example>57.000</example>
    PRIMARY KEY (Name, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: continent (5 rows)
CREATE TABLE continent (
    Name TEXT NOT NULL PRIMARY KEY,
        -- <values>{'Africa', 'America', 'Asia', 'Australia/Oceania', 'Europe'}</values>
    Area REAL NULL
        -- <example>30254700.000</example>
);

-- Table: country (238 rows)
CREATE TABLE country (
    Name TEXT NOT NULL,
        -- <example>'Afghanistan'</example>
    Code TEXT NOT NULL PRIMARY KEY,
        -- <example>'A'</example>
    Capital TEXT NULL,
        -- <example>'Vienna'</example>
    Province TEXT NULL,
        -- <example>'Vienna'</example>
    Area REAL NULL,
        -- <example>83850.000</example>
    Population INTEGER NULL
        -- <example>8023244</example>
);

-- Table: desert (63 rows)
CREATE TABLE desert (
    Name TEXT NOT NULL PRIMARY KEY,
        -- <example>'Arabian Desert'</example>
    Area REAL NULL,
        -- <example>50000.000</example>
    Longitude REAL NULL,
        -- <example>26.000</example>
    Latitude REAL NULL
        -- <example>33.000</example>
);

-- Table: economy (238 rows)
CREATE TABLE economy (
    Country TEXT NOT NULL PRIMARY KEY,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    GDP REAL NULL,
        -- <example>152000.000</example>
    Agriculture REAL NULL,
        -- <example>2.000</example>
    Service REAL NULL,
        -- <example>34.000</example>
    Industry REAL NULL,
        -- <example>64.000</example>
    Inflation REAL NULL,
        -- <example>2.300</example>
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: encompasses (242 rows)
CREATE TABLE encompasses (
    Country TEXT NOT NULL,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Continent TEXT NOT NULL,
        -- <values>{'Africa', 'America', 'Asia', 'Australia/Oceania', 'Europe'}</values>
        -- <fk> -> continent.Name</fk>
    Percentage REAL NULL,
        -- <example>100.000</example>
    PRIMARY KEY (Country, Continent),
    FOREIGN KEY (Continent) REFERENCES continent(Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: ethnicGroup (540 rows)
CREATE TABLE ethnicGroup (
    Country TEXT NOT NULL,
        -- <example>'GE'</example>
        -- <fk> -> country.Code</fk>
    Name TEXT NOT NULL,
        -- <example>'Abkhaz'</example>
    Percentage REAL NULL,
        -- <example>1.800</example>
    PRIMARY KEY (Country, Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: geo_desert (155 rows)
CREATE TABLE geo_desert (
    Desert TEXT NOT NULL,
        -- <example>'Desert'</example>
        -- <fk> -> desert.Name</fk>
    Country TEXT NOT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NOT NULL,
        -- <example>'Abu Dhabi'</example>
        -- <fk>composite</fk>
    PRIMARY KEY (Desert, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Desert) REFERENCES desert(Name)
);

-- Table: geo_estuary (266 rows)
CREATE TABLE geo_estuary (
    River TEXT NOT NULL,
        -- <example>'River'</example>
        -- <fk> -> river.Name</fk>
    Country TEXT NOT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NOT NULL,
        -- <example>'AG'</example>
        -- <fk>composite</fk>
    PRIMARY KEY (River, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (River) REFERENCES river(Name)
);

-- Table: geo_island (202 rows)
CREATE TABLE geo_island (
    Island TEXT NOT NULL,
        -- <example>'Aland'</example>
        -- <fk> -> island.Name</fk>
    Country TEXT NOT NULL,
        -- <example>'Alan'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NOT NULL,
        -- <example>'101'</example>
        -- <fk>composite</fk>
    PRIMARY KEY (Island, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Island) REFERENCES island(Name)
);

-- Table: geo_lake (254 rows)
CREATE TABLE geo_lake (
    Lake TEXT NOT NULL,
        -- <example>'Lake'</example>
        -- <fk> -> lake.Name</fk>
    Country TEXT NOT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NOT NULL,
        -- <example>'Adamaoua'</example>
        -- <fk>composite</fk>
    PRIMARY KEY (Lake, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Lake) REFERENCES lake(Name)
);

-- Table: geo_mountain (296 rows)
CREATE TABLE geo_mountain (
    Mountain TEXT NOT NULL,
        -- <example>'Mountain'</example>
        -- <fk> -> mountain.Name</fk>
    Country TEXT NOT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NOT NULL,
        -- <example>'Abruzzo'</example>
        -- <fk>composite</fk>
    PRIMARY KEY (Mountain, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Mountain) REFERENCES mountain(Name)
);

-- Table: geo_river (852 rows)
CREATE TABLE geo_river (
    River TEXT NOT NULL,
        -- <example>'River'</example>
        -- <fk> -> river.Name</fk>
    Country TEXT NOT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NOT NULL,
        -- <example>'AG'</example>
        -- <fk>composite</fk>
    PRIMARY KEY (River, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (River) REFERENCES river(Name)
);

-- Table: geo_sea (736 rows)
CREATE TABLE geo_sea (
    Sea TEXT NOT NULL,
        -- <example>'Sea'</example>
        -- <fk> -> sea.Name</fk>
    Country TEXT NOT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NOT NULL,
        -- <example>'Abruzzo'</example>
        -- <fk>composite</fk>
    PRIMARY KEY (Sea, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (Sea) REFERENCES sea(Name)
);

-- Table: geo_source (220 rows)
CREATE TABLE geo_source (
    River TEXT NOT NULL,
        -- <example>'River'</example>
        -- <fk> -> river.Name</fk>
    Country TEXT NOT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NOT NULL,
        -- <example>'Aali an Nil'</example>
        -- <fk>composite</fk>
    PRIMARY KEY (River, Country, Province),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code),
    FOREIGN KEY (River) REFERENCES river(Name)
);

-- Table: isMember (8009 rows)
CREATE TABLE isMember (
    Country TEXT NOT NULL,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Organization TEXT NOT NULL,
        -- <example>'AG'</example>
        -- <fk> -> organization.Abbreviation</fk>
    Type TEXT NULL,
        -- <example>'Type'</example>
    PRIMARY KEY (Country, Organization),
    FOREIGN KEY (Organization) REFERENCES organization(Abbreviation),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: island (276 rows)
CREATE TABLE island (
    Name TEXT NOT NULL PRIMARY KEY,
        -- <example>'Aland'</example>
    Islands TEXT NULL,
        -- <example>'Aland Islands'</example>
    Area REAL NULL,
        -- <example>650.000</example>
    Height REAL NULL,
        -- <example>675.000</example>
    Type TEXT NULL,
        -- <values>{'atoll', 'coral', 'lime', 'volcanic'}</values>
    Longitude REAL NULL,
        -- <example>20.000</example>
    Latitude REAL NULL
        -- <example>60.100</example>
);

-- Table: islandIn (350 rows)
CREATE TABLE islandIn (
    Island TEXT NULL,
        -- <example>'Island'</example>
        -- <fk> -> island.Name</fk>
    Sea TEXT NULL,
        -- <example>'Sea'</example>
        -- <fk> -> sea.Name</fk>
    Lake TEXT NULL,
        -- <values>{'Lake Huron', 'Lake Manicouagan', 'Lake Nicaragua', 'Lake Toba', 'Lake', 'Ozero Baikal'}</values>
        -- <fk> -> lake.Name</fk>
    River TEXT NULL,
        -- <values>{'River'}</values>
        -- <fk> -> river.Name</fk>
    FOREIGN KEY (River) REFERENCES river(Name),
    FOREIGN KEY (Lake) REFERENCES lake(Name),
    FOREIGN KEY (Sea) REFERENCES sea(Name),
    FOREIGN KEY (Island) REFERENCES island(Name)
);

-- Table: lake (130 rows)
CREATE TABLE lake (
    Name TEXT NOT NULL PRIMARY KEY,
        -- <example>'Ammersee'</example>
    Area REAL NULL,
        -- <example>46.600</example>
    Depth REAL NULL,
        -- <example>81.100</example>
    Altitude REAL NULL,
        -- <example>533.000</example>
    Type TEXT NULL,
        -- <values>{'acid', 'artificial', 'caldera', 'crater', 'impact', 'salt'}</values>
    River TEXT NULL,
        -- <example>'Ammer'</example>
    Longitude REAL NULL,
        -- <example>11.600</example>
    Latitude REAL NULL
        -- <example>48.000</example>
);

-- Table: language (144 rows)
CREATE TABLE language (
    Country TEXT NOT NULL,
        -- <example>'AFG'</example>
        -- <fk> -> country.Code</fk>
    Name TEXT NOT NULL,
        -- <example>'Afghan Persian'</example>
    Percentage REAL NULL,
        -- <example>50.000</example>
    PRIMARY KEY (Country, Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: located (858 rows)
CREATE TABLE located (
    City TEXT NULL,
        -- <example>'City'</example>
        -- <fk>composite</fk>
    Province TEXT NULL,
        -- <example>'Province'</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    Country TEXT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    River TEXT NULL,
        -- <example>'River'</example>
        -- <fk> -> river.Name</fk>
    Lake TEXT NULL,
        -- <example>'Lake'</example>
        -- <fk> -> lake.Name</fk>
    Sea TEXT NULL,
        -- <example>'Sea'</example>
        -- <fk> -> sea.Name</fk>
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (City, Province) REFERENCES city(Name, Province),
    FOREIGN KEY (Sea) REFERENCES sea(Name),
    FOREIGN KEY (Lake) REFERENCES lake(Name),
    FOREIGN KEY (River) REFERENCES river(Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: locatedOn (435 rows)
CREATE TABLE locatedOn (
    City TEXT NOT NULL,
        -- <example>'Aberdeen'</example>
        -- <fk>composite</fk>
    Province TEXT NOT NULL,
        -- <example>'Province'</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    Country TEXT NOT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Island TEXT NOT NULL,
        -- <example>'Island'</example>
        -- <fk> -> island.Name</fk>
    PRIMARY KEY (City, Province, Country, Island),
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (City, Province) REFERENCES city(Name, Province),
    FOREIGN KEY (Island) REFERENCES island(Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: mergesWith (55 rows)
CREATE TABLE mergesWith (
    Sea1 TEXT NOT NULL,
        -- <example>'Andaman Sea'</example>
        -- <fk> -> sea.Name</fk>
    Sea2 TEXT NOT NULL,
        -- <example>'Sea2'</example>
        -- <fk> -> sea.Name</fk>
    PRIMARY KEY (Sea1, Sea2),
    FOREIGN KEY (Sea2) REFERENCES sea(Name),
    FOREIGN KEY (Sea1) REFERENCES sea(Name)
);

-- Table: mountain (0 rows)
CREATE TABLE mountain (
    Name TEXT NOT NULL PRIMARY KEY,
    Mountains TEXT NULL,
    Height REAL NULL,
    Type TEXT NULL,
    Longitude REAL NULL,
    Latitude REAL NULL
);

-- Table: mountainOnIsland (68 rows)
CREATE TABLE mountainOnIsland (
    Mountain TEXT NOT NULL,
        -- <example>'Andringitra'</example>
        -- <fk> -> mountain.Name</fk>
    Island TEXT NOT NULL,
        -- <example>'Island'</example>
        -- <fk> -> island.Name</fk>
    PRIMARY KEY (Mountain, Island),
    FOREIGN KEY (Island) REFERENCES island(Name),
    FOREIGN KEY (Mountain) REFERENCES mountain(Name)
);

-- Table: organization (154 rows)
CREATE TABLE organization (
    Abbreviation TEXT NOT NULL PRIMARY KEY,
        -- <example>'ABEDA'</example>
    Name TEXT NOT NULL,
        -- <example>'ASEAN-Mekong Basin Development Group'</example>
    City TEXT NULL,
        -- <example>'City'</example>
        -- <fk>composite</fk>
    Country TEXT NULL,
        -- <example>'Coun'</example>
        -- <fk>composite</fk>
        -- <fk> -> country.Code</fk>
    Province TEXT NULL,
        -- <example>'Province'</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    Established DATE NULL,
        -- <example>'Established'</example>
    FOREIGN KEY (Province, Country) REFERENCES province(Name, Country),
    FOREIGN KEY (City, Province) REFERENCES city(Name, Province),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: politics (239 rows)
CREATE TABLE politics (
    Country TEXT NOT NULL PRIMARY KEY,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Independence DATE NULL,
        -- <example>'Independence'</example>
    Dependent TEXT NULL,
        -- <values>{'AUS', 'DK', 'Depe', 'F', 'GB', 'N', 'NL', 'NZ', 'TJ', 'USA'}</values>
        -- <fk> -> country.Code</fk>
    Government TEXT NULL,
        -- <example>'Government'</example>
    FOREIGN KEY (Dependent) REFERENCES country(Code),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: population (238 rows)
CREATE TABLE population (
    Country TEXT NOT NULL PRIMARY KEY,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Population_Growth REAL NULL,
        -- <example>0.410</example>
    Infant_Mortality REAL NULL,
        -- <example>6.200</example>
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: province (1450 rows)
CREATE TABLE province (
    Name TEXT NOT NULL,
        -- <example>'AG'</example>
    Country TEXT NOT NULL,
        -- <example>'CH'</example>
        -- <fk> -> country.Code</fk>
    Population INTEGER NULL,
        -- <example>1599605</example>
    Area REAL NULL,
        -- <example>238792.000</example>
    Capital TEXT NULL,
        -- <example>'Malakal'</example>
    CapProv TEXT NULL,
        -- <example>'Aali an Nil'</example>
    PRIMARY KEY (Name, Country),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: religion (454 rows)
CREATE TABLE religion (
    Country TEXT NOT NULL,
        -- <example>'BERM'</example>
        -- <fk> -> country.Code</fk>
    Name TEXT NOT NULL,
        -- <example>'African Methodist Episcopal'</example>
    Percentage REAL NULL,
        -- <example>11.000</example>
    PRIMARY KEY (Country, Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

-- Table: river (218 rows)
CREATE TABLE river (
    Name TEXT NOT NULL PRIMARY KEY,
        -- <example>'Aare'</example>
    River TEXT NULL,
        -- <example>'Rhein'</example>
    Lake TEXT NULL,
        -- <example>'Brienzersee'</example>
        -- <fk> -> lake.Name</fk>
    Sea TEXT NULL,
        -- <example>'Atlantic Ocean'</example>
    Length REAL NULL,
        -- <example>288.000</example>
    SourceLongitude REAL NULL,
        -- <example>8.200</example>
    SourceLatitude REAL NULL,
        -- <example>46.550</example>
    Mountains TEXT NULL,
        -- <example>'Alps'</example>
    SourceAltitude REAL NULL,
        -- <example>2310.000</example>
    EstuaryLongitude REAL NULL,
        -- <example>8.220</example>
    EstuaryLatitude REAL NULL,
        -- <example>47.610</example>
    FOREIGN KEY (Lake) REFERENCES lake(Name)
);

-- Table: sea (35 rows)
CREATE TABLE sea (
    Name TEXT NOT NULL PRIMARY KEY,
        -- <example>'Andaman Sea'</example>
    Depth REAL NULL
        -- <example>3113.000</example>
);

-- Table: target (205 rows)
CREATE TABLE target (
    Country TEXT NOT NULL PRIMARY KEY,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Target TEXT NULL,
        -- <values>{'Christian', 'Target', 'non-Christian'}</values>
    FOREIGN KEY (Country) REFERENCES country(Code)
);
```