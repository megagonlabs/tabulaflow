```sql
-- Database: world

/*
Schema: NULLTable: City
Rows: 4079
Sample rows:
| ID   | Name           | CountryCode   | District      | Population   |
|------|----------------|---------------|---------------|--------------|
| 1    | Kabul          | AFG           | Kabol         | 1780000      |
| 2    | Qandahar       | AFG           | Qandahar      | 237500       |
| 3    | Herat          | AFG           | Herat         | 186800       |
| 4    | Mazar-e-Sharif | AFG           | Balkh         | 127800       |
| 5    | Amsterdam      | NLD           | Noord-Holland | 731200       |
| ...  | ...            | ...           | ...           | ...          |
*/
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

/*
Schema: NULLTable: Country
Rows: 239
Sample rows:
| Code   | Name        | Continent     | Region                    | SurfaceArea   | IndepYear   | Population   | LifeExpectancy   | GNP    | GNPOld   | LocalName             | GovernmentForm                               | HeadOfState             | Capital   | Code2   |
|--------|-------------|---------------|---------------------------|---------------|-------------|--------------|------------------|--------|----------|-----------------------|----------------------------------------------|-------------------------|-----------|---------|
| ABW    | Aruba       | North America | Caribbean                 | 193.0         | [NULL]      | 103000       | 78.4             | 828.0  | 793.0    | Aruba                 | Nonmetropolitan Territory of The Netherlands | Beatrix                 | 129       | AW      |
| AFG    | Afghanistan | Asia          | Southern and Central Asia | 652090.0      | 1919.0      | 22720000     | 45.9             | 5976.0 | [NULL]   | Afganistan/Afqanestan | Islamic Emirate                              | Mohammad Omar           | 1         | AF      |
| AGO    | Angola      | Africa        | Central Africa            | 1246700.0     | 1975.0      | 12878000     | 38.3             | 6648.0 | 7984.0   | Angola                | Republic                                     | José Eduardo dos Santos | 56        | AO      |
| AIA    | Anguilla    | North America | Caribbean                 | 96.0          | [NULL]      | 8000         | 76.1             | 63.2   | [NULL]   | Anguilla              | Dependent Territory of the UK                | Elisabeth II            | 62        | AI      |
| ALB    | Albania     | Europe        | Southern Europe           | 28748.0       | 1912.0      | 3401200      | 71.6             | 3205.0 | 2500.0   | Shqipëria             | Republic                                     | Rexhep Mejdani          | 34        | AL      |
| ...    | ...         | ...           | ...                       | ...           | ...         | ...          | ...              | ...    | ...      | ...                   | ...                                          | ...                     | ...       | ...     |
*/
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
    GNP REAL NOT NULL,
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

/*
Schema: NULLTable: CountryLanguage
Rows: 984
Sample rows:
| CountryCode   | Language   | IsOfficial   | Percentage   |
|---------------|------------|--------------|--------------|
| ABW           | Dutch      | T            | 5.3          |
| ABW           | English    | F            | 9.5          |
| ABW           | Papiamento | F            | 76.7         |
| ABW           | Spanish    | F            | 7.4          |
| AFG           | Balochi    | F            | 0.9          |
| ...           | ...        | ...          | ...          |
*/
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