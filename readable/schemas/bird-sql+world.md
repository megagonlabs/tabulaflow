```sql
-- Database: world

-- Table: City (4079 rows)
CREATE TABLE City (
    ID INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NOT NULL,
        -- <example>'Kabul'</example>
    CountryCode TEXT NOT NULL,
        -- <example>'AFG'</example>
        -- <fk> -> Country.Code</fk>
    District TEXT NOT NULL,
        -- <example>'Kabol'</example>
    Population INTEGER NOT NULL,
        -- <example>1780000</example>
    FOREIGN KEY (CountryCode) REFERENCES Country(Code)
);

-- Table: Country (239 rows)
CREATE TABLE Country (
    Code TEXT NOT NULL PRIMARY KEY,
        -- <example>'ABW'</example>
    Name TEXT NOT NULL,
        -- <example>'Aruba'</example>
    Continent TEXT NOT NULL,
        -- <values>{'Africa', 'Antarctica', 'Asia', 'Europe', 'North America', 'Oceania', 'South America'}</values>
    Region TEXT NOT NULL,
        -- <example>'Caribbean'</example>
    SurfaceArea REAL NOT NULL,
        -- <example>193.000</example>
    IndepYear INTEGER NULL,
        -- <example>1919</example>
    Population INTEGER NOT NULL,
        -- <example>103000</example>
    LifeExpectancy REAL NULL,
        -- <example>78.400</example>
    GNP REAL NULL,
        -- <example>828.000</example>
    GNPOld REAL NULL,
        -- <example>793.000</example>
    LocalName TEXT NOT NULL,
        -- <example>'Aruba'</example>
    GovernmentForm TEXT NOT NULL,
        -- <example>'Nonmetropolitan Territory of The Netherlands'</example>
    HeadOfState TEXT NULL,
        -- <example>'Beatrix'</example>
    Capital INTEGER NULL,
        -- <example>129</example>
    Code2 TEXT NOT NULL
        -- <example>'AW'</example>
);

-- Table: CountryLanguage (984 rows)
CREATE TABLE CountryLanguage (
    CountryCode TEXT NOT NULL,
        -- <example>'ABW'</example>
        -- <fk> -> Country.Code</fk>
    Language TEXT NOT NULL,
        -- <example>'Dutch'</example>
    IsOfficial TEXT NOT NULL,
        -- <values>{'F', 'T'}</values>
    Percentage REAL NOT NULL,
        -- <example>5.300</example>
    PRIMARY KEY (CountryCode, Language),
    FOREIGN KEY (CountryCode) REFERENCES Country(Code)
);
```