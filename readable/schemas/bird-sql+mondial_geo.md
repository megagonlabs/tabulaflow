```sql
-- Database: mondial_geo

/*
Table: borders
Rows: 320
Sample rows:
| Country1   | Country2   | Length   |
|------------|------------|----------|
| A          | CH         | 164.0    |
| A          | CZ         | 362.0    |
| A          | D          | 784.0    |
| A          | FL         | 37.0     |
| A          | H          | 366.0    |
| ...        | ...        | ...      |
*/
CREATE TABLE borders (
    Country1 TEXT NOT NULL,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Country2 TEXT NOT NULL,
        -- <example>'CH'</example>
        -- <fk> -> country.Code</fk>
    Length REAL NOT NULL,
        -- <example>164.000</example>
    PRIMARY KEY (Country1, Country2),
    FOREIGN KEY (Country2) REFERENCES country(Code),
    FOREIGN KEY (Country1) REFERENCES country(Code)
);

/*
Table: city
Rows: 3111
Sample rows:
| Name    | Country   | Province            | Population   | Longitude   | Latitude   |
|---------|-----------|---------------------|--------------|-------------|------------|
| Aachen  | D         | Nordrhein Westfalen | 247113.0     | [NULL]      | [NULL]     |
| Aalborg | DK        | Denmark             | 113865.0     | 10.0        | 57.0       |
| Aarau   | CH        | AG                  | [NULL]       | [NULL]      | [NULL]     |
| Aarhus  | DK        | Denmark             | 194345.0     | 10.1        | 56.1       |
| Aarri   | WAN       | Nigeria             | 111000.0     | [NULL]      | [NULL]     |
| ...     | ...       | ...                 | ...          | ...         | ...        |
*/
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

/*
Table: continent
Rows: 5
All rows:
| Name              |     Area |
|-------------------|----------|
| Africa            | 30254700 |
| America           | 39872000 |
| Asia              | 45095300 |
| Australia/Oceania |  8503470 |
| Europe            |  9562490 |
*/
CREATE TABLE continent (
    Name TEXT NOT NULL PRIMARY KEY,
        -- <values>{'Africa', 'America', 'Asia', 'Australia/Oceania', 'Europe'}</values>
    Area REAL NOT NULL
        -- <example>30254700.000</example>
);

/*
Table: country
Rows: 238
Sample rows:
| Name                | Code   | Capital     | Province            | Area     | Population   |
|---------------------|--------|-------------|---------------------|----------|--------------|
| Austria             | A      | Vienna      | Vienna              | 83850.0  | 8023244      |
| Afghanistan         | AFG    | Kabul       | Afghanistan         | 647500.0 | 22664136     |
| Antigua and Barbuda | AG     | Saint Johns | Antigua and Barbuda | 442.0    | 65647        |
| Albania             | AL     | Tirane      | Albania             | 28750.0  | 3249136      |
| American Samoa      | AMSA   | Pago Pago   | American Samoa      | 199.0    | 65628        |
| ...                 | ...    | ...         | ...                 | ...      | ...          |
*/
CREATE TABLE country (
    Name TEXT NOT NULL,
        -- <example>'Afghanistan'</example>
    Code TEXT NOT NULL PRIMARY KEY,
        -- <example>'A'</example>
    Capital TEXT NULL,
        -- <example>'Vienna'</example>
    Province TEXT NULL,
        -- <example>'Vienna'</example>
    Area REAL NOT NULL,
        -- <example>83850.000</example>
    Population INTEGER NOT NULL
        -- <example>8023244</example>
);

/*
Table: desert
Rows: 63
Sample rows:
| Name                   | Area     | Longitude   | Latitude   |
|------------------------|----------|-------------|------------|
| Arabian Desert         | 50000.0  | 26.0        | 33.0       |
| Atacama                | 181300.0 | -69.25      | -24.5      |
| Azaouad                | 80000.0  | 0.0         | 20.0       |
| Baja California Desert | 30000.0  | -116.0      | 31.0       |
| Chihuahua              | 360000.0 | -105.0      | 31.0       |
| ...                    | ...      | ...         | ...        |
*/
CREATE TABLE desert (
    Name TEXT NOT NULL PRIMARY KEY,
        -- <example>'Arabian Desert'</example>
    Area REAL NOT NULL,
        -- <example>50000.000</example>
    Longitude REAL NULL,
        -- <example>26.000</example>
    Latitude REAL NULL
        -- <example>33.000</example>
);

/*
Table: economy
Rows: 238
Sample rows:
| Country   | GDP      | Agriculture   | Service   | Industry   | Inflation   |
|-----------|----------|---------------|-----------|------------|-------------|
| A         | 152000.0 | 2.0           | 34.0      | 64.0       | 2.3         |
| AFG       | 12800.0  | 65.0          | 15.0      | 20.0       | [NULL]      |
| AG        | 425.0    | 3.5           | 19.3      | 77.2       | 3.5         |
| AL        | 4100.0   | 55.0          | [NULL]    | [NULL]     | 16.0        |
| AMSA      | 462.2    | [NULL]        | [NULL]    | [NULL]     | [NULL]      |
| ...       | ...      | ...           | ...       | ...        | ...         |
*/
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

/*
Table: encompasses
Rows: 242
Sample rows:
| Country   | Continent         | Percentage   |
|-----------|-------------------|--------------|
| A         | Europe            | 100.0        |
| AFG       | Asia              | 100.0        |
| AG        | America           | 100.0        |
| AL        | Europe            | 100.0        |
| AMSA      | Australia/Oceania | 100.0        |
| ...       | ...               | ...          |
*/
CREATE TABLE encompasses (
    Country TEXT NOT NULL,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Continent TEXT NOT NULL,
        -- <values>{'Africa', 'America', 'Asia', 'Australia/Oceania', 'Europe'}</values>
        -- <fk> -> continent.Name</fk>
    Percentage REAL NOT NULL,
        -- <example>100.000</example>
    PRIMARY KEY (Country, Continent),
    FOREIGN KEY (Continent) REFERENCES continent(Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

/*
Table: ethnicGroup
Rows: 540
Sample rows:
| Country   | Name   | Percentage   |
|-----------|--------|--------------|
| GE        | Abkhaz | 1.8          |
| EAU       | Acholi | 4.0          |
| DJI       | Afar   | 35.0         |
| ER        | Afar   | 4.0          |
| ETH       | Afar   | 4.0          |
| ...       | ...    | ...          |
*/
CREATE TABLE ethnicGroup (
    Country TEXT NOT NULL,
        -- <example>'GE'</example>
        -- <fk> -> country.Code</fk>
    Name TEXT NOT NULL,
        -- <example>'Abkhaz'</example>
    Percentage REAL NOT NULL,
        -- <example>1.800</example>
    PRIMARY KEY (Country, Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

/*
Table: geo_desert
Rows: 155
Sample rows:
| Desert          | Country   | Province    |
|-----------------|-----------|-------------|
| Desert          | Coun      | Province    |
| Rub Al Chali    | UAE       | Abu Dhabi   |
| Dascht-e-Margoh | AFG       | Afghanistan |
| Rigestan        | AFG       | Afghanistan |
| Karakum         | TM        | Ahal        |
| ...             | ...       | ...         |
*/
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

/*
Table: geo_estuary
Rows: 266
Sample rows:
| River                     | Country   | Province    |
|---------------------------|-----------|-------------|
| River                     | Coun      | Province    |
| Bahr el-Djebel/Albert-Nil | SUD       | Aali an Nil |
| Bahr el-Ghasal            | SUD       | Aali an Nil |
| Sobat                     | SUD       | Aali an Nil |
| Pjandsh                   | AFG       | Afghanistan |
| ...                       | ...       | ...         |
*/
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

/*
Table: geo_island
Rows: 202
Sample rows:
| Island   | Country   | Province   |
|----------|-----------|------------|
| Aland    | Alan      | 650        |
| Alicudi  | Lipa      | 5.2        |
| Ambon    | Molu      | 775        |
| Ameland  | West      | 57.6       |
| Amrum    | Nord      | 20.5       |
| ...      | ...       | ...        |
*/
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

/*
Table: geo_lake
Rows: 254
Sample rows:
| Lake               | Country   | Province   |
|--------------------|-----------|------------|
| Lake               | Coun      | Province   |
| Barrage de Mbakaou | CAM       | Adamaoua   |
| Lake Nicaragua     | CR        | Alajuela   |
| Lake Ohrid         | AL        | Albania    |
| Lake Prespa        | AL        | Albania    |
| ...                | ...       | ...        |
*/
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

/*
Table: geo_mountain
Rows: 296
Sample rows:
| Mountain     | Country   | Province    |
|--------------|-----------|-------------|
| Mountain     | Coun      | Province    |
| Gran Sasso   | I         | Abruzzo     |
| Tirich Mir   | AFG       | Afghanistan |
| Ararat       | TR        | Agri        |
| Mt Blackburn | USA       | Alaska      |
| ...          | ...       | ...         |
*/
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

/*
Table: geo_river
Rows: 852
Sample rows:
| River                     | Country   | Province    |
|---------------------------|-----------|-------------|
| River                     | Coun      | Province    |
| Bahr el-Djebel/Albert-Nil | SUD       | Aali an Nil |
| Bahr el-Ghasal            | SUD       | Aali an Nil |
| Pibor                     | SUD       | Aali an Nil |
| Sobat                     | SUD       | Aali an Nil |
| ...                       | ...       | ...         |
*/
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

/*
Table: geo_sea
Rows: 736
Sample rows:
| Sea               | Country   | Province   |
|-------------------|-----------|------------|
| Sea               | Coun      | Province   |
| Mediterranean Sea | I         | Abruzzo    |
| Persian Gulf      | UAE       | Abu Dhabi  |
| Mediterranean Sea | TR        | Adana      |
| Pacific Ocean     | J         | Aichi      |
| ...               | ...       | ...        |
*/
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

/*
Table: geo_source
Rows: 220
Sample rows:
| River      | Country   | Province    |
|------------|-----------|-------------|
| River      | Coun      | Province    |
| White Nile | SUD       | Aali an Nil |
| Amudarja   | AFG       | Afghanistan |
| Pjandsh    | AFG       | Afghanistan |
| Murat      | TR        | Agri        |
| ...        | ...       | ...         |
*/
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

/*
Table: isMember
Rows: 8009
Sample rows:
| Country   | Organization   | Type               |
|-----------|----------------|--------------------|
| Coun      | Organization   | Type               |
| A         | AfDB           | nonregional member |
| A         | AG             | observer           |
| A         | ANC            | member             |
| A         | AsDB           | nonregional member |
| ...       | ...            | ...                |
*/
CREATE TABLE isMember (
    Country TEXT NOT NULL,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Organization TEXT NOT NULL,
        -- <example>'AG'</example>
        -- <fk> -> organization.Abbreviation</fk>
    Type TEXT NOT NULL,
        -- <example>'Type'</example>
    PRIMARY KEY (Country, Organization),
    FOREIGN KEY (Organization) REFERENCES organization(Abbreviation),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

/*
Table: island
Rows: 276
Sample rows:
| Name    | Islands               | Area   | Height   | Type     | Longitude   | Latitude   |
|---------|-----------------------|--------|----------|----------|-------------|------------|
| Aland   | Aland Islands         | 650.0  | [NULL]   | [NULL]   | 20.0        | 60.1       |
| Alicudi | Lipari Islands        | 5.2    | 675.0    | volcanic | 14.4        | 38.6       |
| Ambon   | Moluccan Islands      | 775.0  | 1225.0   | [NULL]   | 128.2       | -3.7       |
| Ameland | Westfriesische Inseln | 57.6   | [NULL]   | [NULL]   | 5.75        | 53.5       |
| Amrum   | Nordfriesische Inseln | 20.5   | 32.0     | [NULL]   | 8.3         | 54.65      |
| ...     | ...                   | ...    | ...      | ...      | ...         | ...        |
*/
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

/*
Table: islandIn
Rows: 350
Sample rows:
| Island    | Sea            | Lake   | River   |
|-----------|----------------|--------|---------|
| Island    | Sea            | Lake   | River   |
| Svalbard  | Norwegian Sea  | [NULL] | [NULL]  |
| Svalbard  | Barents Sea    | [NULL] | [NULL]  |
| Svalbard  | Arctic Ocean   | [NULL] | [NULL]  |
| Greenland | Atlantic Ocean | [NULL] | [NULL]  |
| ...       | ...            | ...    | ...     |
*/
CREATE TABLE islandIn (
    Island TEXT NOT NULL,
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

/*
Table: lake
Rows: 130
Sample rows:
| Name               | Area   | Depth   | Altitude   | Type       | River       | Longitude   | Latitude   |
|--------------------|--------|---------|------------|------------|-------------|-------------|------------|
| Ammersee           | 46.6   | 81.1    | 533.0      | [NULL]     | Ammer       | 11.6        | 48.0       |
| Arresoe            | 40.2   | 5.6     | [NULL]     | [NULL]     | [NULL]      | 12.1        | 56.0       |
| Atlin Lake         | 798.0  | 283.0   | 668.0      | [NULL]     | Yukon River | -133.75     | 59.5       |
| Balaton            | 594.0  | 12.5    | 104.0      | [NULL]     | [NULL]      | 17.6        | 46.8       |
| Barrage de Mbakaou | [NULL] | [NULL]  | [NULL]     | artificial | Sanaga      | 12.75       | 6.4        |
| ...                | ...    | ...     | ...        | ...        | ...         | ...         | ...        |
*/
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
    Longitude REAL NOT NULL,
        -- <example>11.600</example>
    Latitude REAL NOT NULL
        -- <example>48.000</example>
);

/*
Table: language
Rows: 144
Sample rows:
| Country   | Name           | Percentage   |
|-----------|----------------|--------------|
| AFG       | Afghan Persian | 50.0         |
| NAM       | Afrikaans      | 60.0         |
| MK        | Albanian       | 21.0         |
| MNE       | Albanian       | 5.3          |
| IR        | Arabic         | 1.0          |
| ...       | ...            | ...          |
*/
CREATE TABLE language (
    Country TEXT NOT NULL,
        -- <example>'AFG'</example>
        -- <fk> -> country.Code</fk>
    Name TEXT NOT NULL,
        -- <example>'Afghan Persian'</example>
    Percentage REAL NOT NULL,
        -- <example>50.000</example>
    PRIMARY KEY (Country, Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

/*
Table: located
Rows: 858
Sample rows:
| City    | Province                        | Country   | River   | Lake         | Sea               |
|---------|---------------------------------|-----------|---------|--------------|-------------------|
| City    | Province                        | Coun      | River   | Lake         | Sea               |
| Shkoder | Albania                         | AL        | [NULL]  | Lake Skutari | [NULL]            |
| Durres  | Albania                         | AL        | [NULL]  | [NULL]       | Mediterranean Sea |
| Vlore   | Albania                         | AL        | [NULL]  | [NULL]       | Mediterranean Sea |
| Kavalla | Anatoliki Makedhonia kai Thraki | GR        | [NULL]  | [NULL]       | Mediterranean Sea |
| ...     | ...                             | ...       | ...     | ...          | ...               |
*/
CREATE TABLE located (
    City TEXT NOT NULL,
        -- <example>'City'</example>
        -- <fk>composite</fk>
    Province TEXT NOT NULL,
        -- <example>'Province'</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    Country TEXT NOT NULL,
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

/*
Table: locatedOn
Rows: 435
Sample rows:
| City        | Province         | Country   | Island        |
|-------------|------------------|-----------|---------------|
| City        | Province         | Coun      | Island        |
| Aberdeen    | Grampian         | GB        | Great Britain |
| Aberystwyth | Ceredigion       | GB        | Great Britain |
| Adamstown   | Pitcairn Islands | PITC      | Pitcairn      |
| Agana       | Guam             | GUAM      | Guam          |
| ...         | ...              | ...       | ...           |
*/
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

/*
Table: mergesWith
Rows: 55
Sample rows:
| Sea1        | Sea2           |
|-------------|----------------|
| Sea1        | Sea2           |
| Andaman Sea | Gulf of Bengal |
| Andaman Sea | Indian Ocean   |
| Andaman Sea | Malakka Strait |
| Arabian Sea | Gulf of Aden   |
| ...         | ...            |
*/
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

/*
Table: mountain
Rows: 0
*/
CREATE TABLE mountain (
    Name TEXT NOT NULL PRIMARY KEY,
    Mountains TEXT NOT NULL,
    Height REAL NOT NULL,
    Type TEXT NOT NULL,
    Longitude REAL NOT NULL,
    Latitude REAL NOT NULL
);

/*
Table: mountainOnIsland
Rows: 68
Sample rows:
| Mountain     | Island           |
|--------------|------------------|
| Mountain     | Island           |
| Andringitra  | Madagaskar       |
| Asahi-Dake   | Hokkaido         |
| Barbeau Peak | Ellesmere Island |
| Ben Nevis    | Great Britain    |
| ...          | ...              |
*/
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

/*
Table: organization
Rows: 154
Sample rows:
| Abbreviation   | Name                                          | City     | Country   | Province      | Established   |
|----------------|-----------------------------------------------|----------|-----------|---------------|---------------|
| Abbreviation   | Name                                          | City     | Coun      | Province      | Established   |
| ABEDA          | Arab Bank for Economic Development in Africa  | Khartoum | SUD       | al Khartum    | 1974-02-18    |
| ACC            | Arab Cooperation Council                      | [NULL]   | [NULL]    | [NULL]        | 1989-02-16    |
| ACCT           | Agency for Cultural and Technical Cooperation | Paris    | F         | Ile de France | 1970-03-21    |
| ACP            | African, Caribbean, and Pacific Countries     | Brussels | B         | Brabant       | 1976-04-01    |
| ...            | ...                                           | ...      | ...       | ...           | ...           |
*/
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

/*
Table: politics
Rows: 239
Sample rows:
| Country   | Independence   | Dependent   | Government              |
|-----------|----------------|-------------|-------------------------|
| Coun      | Independence   | Depe        | Government              |
| A         | 1918-11-12     | [NULL]      | federal republic        |
| AFG       | 1919-08-19     | [NULL]      | transitional government |
| AG        | 1981-11-01     | [NULL]      | parliamentary democracy |
| AL        | 1912-11-28     | [NULL]      | emerging democracy      |
| ...       | ...            | ...         | ...                     |
*/
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

/*
Table: population
Rows: 238
Sample rows:
| Country   | Population_Growth   | Infant_Mortality   |
|-----------|---------------------|--------------------|
| A         | 0.41                | 6.2                |
| AFG       | 4.78                | 149.7              |
| AG        | 0.76                | 17.2               |
| AL        | 1.34                | 49.2               |
| AMSA      | 1.22                | 10.18              |
| ...       | ...                 | ...                |
*/
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

/*
Table: province
Rows: 1450
Sample rows:
| Name                 | Country   | Population   | Area     | Capital    | CapProv              |
|----------------------|-----------|--------------|----------|------------|----------------------|
| Aali an Nil          | SUD       | 1599605      | 238792.0 | Malakal    | Aali an Nil          |
| Aberconwy and Colwyn | GB        | 110700       | 1130.0   | Colwyn Bay | Aberconwy and Colwyn |
| Abruzzo              | I         | 1263000      | 10794.0  | LAquila    | Abruzzo              |
| Abu Dhabi            | UAE       | 670000       | 67350.0  | [NULL]     | [NULL]               |
| Acre                 | BR        | 483483       | 153149.0 | Rio Branco | Acre                 |
| ...                  | ...       | ...          | ...      | ...        | ...                  |
*/
CREATE TABLE province (
    Name TEXT NOT NULL,
        -- <example>'AG'</example>
    Country TEXT NOT NULL,
        -- <example>'CH'</example>
        -- <fk> -> country.Code</fk>
    Population INTEGER NOT NULL,
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

/*
Table: religion
Rows: 454
Sample rows:
| Country   | Name                        | Percentage   |
|-----------|-----------------------------|--------------|
| BERM      | African Methodist Episcopal | 11.0         |
| AUS       | Anglican                    | 26.1         |
| AXA       | Anglican                    | 29.0         |
| BERM      | Anglican                    | 23.0         |
| BS        | Anglican                    | 20.0         |
| ...       | ...                         | ...          |
*/
CREATE TABLE religion (
    Country TEXT NOT NULL,
        -- <example>'BERM'</example>
        -- <fk> -> country.Code</fk>
    Name TEXT NOT NULL,
        -- <example>'African Methodist Episcopal'</example>
    Percentage REAL NOT NULL,
        -- <example>11.000</example>
    PRIMARY KEY (Country, Name),
    FOREIGN KEY (Country) REFERENCES country(Code)
);

/*
Table: river
Rows: 218
Sample rows:
| Name            | River      | Lake          | Sea    | Length   | SourceLongitude   | SourceLatitude   | Mountains             | SourceAltitude   | EstuaryLongitude   | EstuaryLatitude   |
|-----------------|------------|---------------|--------|----------|-------------------|------------------|-----------------------|------------------|--------------------|-------------------|
| Aare            | Rhein      | Brienzersee   | [NULL] | 288.0    | 8.2               | 46.55            | Alps                  | 2310.0           | 8.22               | 47.61             |
| Adda            | Po         | Lago di Como  | [NULL] | 313.0    | 10.3              | 46.55            | Alps                  | 2235.0           | 9.88               | 45.13             |
| Akagera         | [NULL]     | Lake Victoria | [NULL] | 275.0    | 29.3              | -2.5             | East African Rift     | 2700.0           | 33.0               | -1.0              |
| Allegheny River | Ohio River | [NULL]        | [NULL] | 523.0    | -77.9             | 41.9             | Appalachian Mountains | 759.0            | -80.0              | 40.42             |
| Aller           | Weser      | [NULL]        | [NULL] | 211.0    | 11.23             | 52.1             | [NULL]                | 130.0            | 9.18               | 52.94             |
| ...             | ...        | ...           | ...    | ...      | ...               | ...              | ...                   | ...              | ...                | ...               |
*/
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

/*
Table: sea
Rows: 35
Sample rows:
| Name           | Depth   |
|----------------|---------|
| Andaman Sea    | 3113.0  |
| Arabian Sea    | 5203.0  |
| Arctic Ocean   | 5608.0  |
| Atlantic Ocean | 9219.0  |
| Baltic Sea     | 459.0   |
| ...            | ...     |
*/
CREATE TABLE sea (
    Name TEXT NOT NULL PRIMARY KEY,
        -- <example>'Andaman Sea'</example>
    Depth REAL NOT NULL
        -- <example>3113.000</example>
);

/*
Table: target
Rows: 205
Sample rows:
| Country   | Target        |
|-----------|---------------|
| Coun      | Target        |
| A         | Christian     |
| AFG       | non-Christian |
| AL        | non-Christian |
| AMSA      | Christian     |
| ...       | ...           |
*/
CREATE TABLE target (
    Country TEXT NOT NULL PRIMARY KEY,
        -- <example>'A'</example>
        -- <fk> -> country.Code</fk>
    Target TEXT NOT NULL,
        -- <values>{'Christian', 'Target', 'non-Christian'}</values>
    FOREIGN KEY (Country) REFERENCES country(Code)
);
```