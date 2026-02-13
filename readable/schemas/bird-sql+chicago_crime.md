```sql
-- Database: chicago_crime

/*
Schema: NULLTable: Community_Area
Rows: 77
Sample rows:
| community_area_no   | community_area_name   | side      | population   |
|---------------------|-----------------------|-----------|--------------|
| 1                   | Rogers Park           | Far North | 54,991       |
| 2                   | West Ridge            | Far North | 71,942       |
| 3                   | Uptown                | Far North | 56,362       |
| 4                   | Lincoln Square        | Far North | 39,493       |
| 5                   | North Center          | North     | 31,867       |
| ...                 | ...                   | ...       | ...          |
*/
CREATE TABLE Community_Area (
    community_area_no INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    community_area_name TEXT NOT NULL,
        -- <example>'Rogers Park'</example>
    side TEXT NOT NULL,
        -- <values>{'Central', 'Far North ', 'Far Southeast ', 'Far Southwest ', 'North ', 'Northwest ', 'South ', 'Southwest ', 'West '}</values>
    population TEXT NOT NULL
        -- <example>'54,991'</example>
);

/*
Schema: NULLTable: Crime
Rows: 268002
Sample rows:
| report_no   | case_number   | date           | block                    | iucr_no   | location_description   | arrest   | domestic   | beat   | district_no   | ward_no   | community_area_no   | fbi_code_no   | latitude    | longitude    |
|-------------|---------------|----------------|--------------------------|-----------|------------------------|----------|------------|--------|---------------|-----------|---------------------|---------------|-------------|--------------|
| 23757       | JB100159      | 1/1/2018 2:46  | 039XX W CORNELIA AVE     | 110       | AUTO                   | FALSE    | FALSE      | 1732   | 17            | 30        | 21                  | 01A           | 41.94456125 | -87.72668181 |
| 23758       | JB100522      | 1/1/2018 11:33 | 026XX N HAMPDEN CT       | 110       | APARTMENT              | FALSE    | FALSE      | 1935   | 19            | 43        | 7                   | 01A           | 41.92972657 | -87.64092074 |
| 23759       | JB100839      | 1/1/2018 18:27 | 047XX S PRINCETON AVE    | 110       | AUTO                   | FALSE    | FALSE      | 935    | 9             | 3         | 37                  | 01A           | 41.808168   | -87.63333646 |
| 23761       | JB101043      | 1/1/2018 22:40 | 081XX S STONY ISLAND AVE | 110       | ALLEY                  | TRUE     | FALSE      | 411    | 4             | 8         | 45                  | 01A           | 41.74698404 | -87.5854287  |
| 23762       | JB105277      | 1/6/2018 12:54 | 015XX E 62ND ST          | 110       | STREET                 | FALSE    | FALSE      | 314    | 3             | 5         | 42                  | 01A           | 41.78289015 | -87.58877343 |
| ...         | ...           | ...            | ...                      | ...       | ...                    | ...      | ...        | ...    | ...           | ...       | ...                 | ...           | ...         | ...          |
*/
CREATE TABLE Crime (
    report_no INTEGER NOT NULL PRIMARY KEY,
        -- <example>23757</example>
    case_number TEXT NOT NULL,
        -- <example>'JB100159'</example>
    date TEXT NOT NULL,
        -- <example>'1/1/2018 2:46'</example>
    block TEXT NOT NULL,
        -- <example>'039XX W CORNELIA AVE'</example>
    iucr_no TEXT NOT NULL,
        -- <example>'110'</example>
        -- <fk> -> IUCR.iucr_no</fk>
    location_description TEXT NULL,
        -- <example>'AUTO'</example>
    arrest TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    domestic TEXT NOT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    beat INTEGER NOT NULL,
        -- <example>1732</example>
    district_no INTEGER NOT NULL,
        -- <example>17</example>
        -- <fk> -> District.district_no</fk>
    ward_no INTEGER NULL,
        -- <example>30</example>
        -- <fk> -> Ward.ward_no</fk>
    community_area_no INTEGER NOT NULL,
        -- <example>21</example>
        -- <fk> -> Community_Area.community_area_no</fk>
    fbi_code_no TEXT NOT NULL,
        -- <example>'01A'</example>
        -- <fk> -> FBI_Code.fbi_code_no</fk>
    latitude TEXT NULL,
        -- <example>'41.94456125'</example>
    longitude TEXT NULL,
        -- <example>'-87.72668181'</example>
    FOREIGN KEY (ward_no) REFERENCES Ward(ward_no),
    FOREIGN KEY (iucr_no) REFERENCES IUCR(iucr_no),
    FOREIGN KEY (district_no) REFERENCES District(district_no),
    FOREIGN KEY (community_area_no) REFERENCES Community_Area(community_area_no),
    FOREIGN KEY (fbi_code_no) REFERENCES FBI_Code(fbi_code_no)
);

/*
Schema: NULLTable: District
Rows: 22
Sample rows:
| district_no   | district_name   | address                      | zip_code   | commander         | email                              | phone        | fax          | tty          | twitter       |
|---------------|-----------------|------------------------------|------------|-------------------|------------------------------------|--------------|--------------|--------------|---------------|
| 1             | Central         | 1718 South State Street      | 60616      | Jake M. Alderden  | CAPS001District@chicagopolice.org  | 312-745-4290 | 312-745-3694 | 312-745-3693 | ChicagoCAPS01 |
| 2             | Wentworth       | 5101 South Wentworh Avenue   | 60609      | Joshua Wallace    | CAPS002District@chicagopolice.org  | 312-747-8366 | 312-747-5396 | 312-747-6656 | ChicagoCAPS02 |
| 3             | Grand Crossing  | 7040 South Cottage Grove Ave | 60637      | Eve T. Quarterman | CAPS003District@chicagopolice.org  | 312-747-8201 | 312-747-5479 | 312-747-9168 | ChicagoCAPS03 |
| 4             | South Chicago   | 2255 East 103rd St           | 60617      | Robert A. Rubio   | caps.004district@chicagopolice.org | 312-747-8205 | 312-747-4559 | 312-747-9169 | ChicagoCAPS04 |
| 5             | Calumet         | 727 East 111th St            | 60628      | Glenn White       | CAPS005District@chicagopolice.org  | 312-747-8210 | 312-747-5935 | 312-747-9170 | ChicagoCAPS05 |
| ...           | ...             | ...                          | ...        | ...               | ...                                | ...          | ...          | ...          | ...           |
*/
CREATE TABLE District (
    district_no INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    district_name TEXT NOT NULL,
        -- <example>'Central'</example>
    address TEXT NOT NULL,
        -- <example>'1718 South State Street'</example>
    zip_code INTEGER NOT NULL,
        -- <example>60616</example>
    commander TEXT NOT NULL,
        -- <example>'Jake M. Alderden'</example>
    email TEXT NOT NULL,
        -- <example>' CAPS001District@chicagopolice.org'</example>
    phone TEXT NOT NULL,
        -- <example>'312-745-4290'</example>
    fax TEXT NOT NULL,
        -- <example>'312-745-3694'</example>
    tty TEXT NULL,
        -- <example>'312-745-3693'</example>
    twitter TEXT NOT NULL
        -- <example>' ChicagoCAPS01'</example>
);

/*
Schema: NULLTable: FBI_Code
Rows: 26
Sample rows:
| fbi_code_no   | title                     | description                                                                                                                                                                                                 | crime_against   |
|---------------|---------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|-----------------|
| 01A           | Homicide 1st & 2nd Degree | The killing of one human being by another.                                                                                                                                                                  | Persons         |
| 01B           | Involuntary Manslaughter  | The killing of another person through negligence.                                                                                                                                                           | Persons         |
| 2             | Criminal Sexual Assault   | Any sexual act directed against another person, forcibly and/or against that person's will or not forcibly or against the person's will in instances where the victim is incapable of giving consent.       | Persons         |
| 3             | Robbery                   | The taking or attempting to take anything of value under confrontational circumstances from the cont...rson by force or threat of force or violence and/or by putting the victim in fear of immediate harm. | Property        |
| 04A           | Aggravated Assault        | An unlawful attack by one person upon another wherein the offender displays a weapon in a threatening manner. Placing someone in reasonable apprehension of receiving a battery.                            | Persons         |
| ...           | ...                       | ...                                                                                                                                                                                                         | ...             |
*/
CREATE TABLE FBI_Code (
    fbi_code_no TEXT NOT NULL PRIMARY KEY,
        -- <example>'01A'</example>
    title TEXT NOT NULL,
        -- <example>'Homicide 1st & 2nd Degree'</example>
    description TEXT NOT NULL,
        -- <example>'The killing of one human being by another.'</example>
    crime_against TEXT NOT NULL
        -- <values>{'Persons and Society', 'Persons', 'Property', 'Society'}</values>
);

/*
Schema: NULLTable: IUCR
Rows: 401
Sample rows:
| iucr_no   | primary_description   | secondary_description    | index_code   |
|-----------|-----------------------|--------------------------|--------------|
| 110       | HOMICIDE              | FIRST DEGREE MURDER      | I            |
| 130       | HOMICIDE              | SECOND DEGREE MURDER     | I            |
| 141       | HOMICIDE              | INVOLUNTARY MANSLAUGHTER | N            |
| 142       | HOMICIDE              | RECKLESS HOMICIDE        | N            |
| 261       | CRIM SEXUAL ASSAULT   | AGGRAVATED: HANDGUN      | I            |
| ...       | ...                   | ...                      | ...          |
*/
CREATE TABLE IUCR (
    iucr_no TEXT NOT NULL PRIMARY KEY,
        -- <example>'031A'</example>
    primary_description TEXT NOT NULL,
        -- <example>'HOMICIDE'</example>
    secondary_description TEXT NOT NULL,
        -- <example>'FIRST DEGREE MURDER'</example>
    index_code TEXT NOT NULL
        -- <values>{'I', 'N'}</values>
);

/*
Schema: NULLTable: Neighborhood
Rows: 246
Sample rows:
| neighborhood_name   | community_area_no   |
|---------------------|---------------------|
| Albany Park         | 14                  |
| Altgeld Gardens     | 54                  |
| Andersonville       | 77                  |
| Archer Heights      | 57                  |
| Armour Square       | 34                  |
| ...                 | ...                 |
*/
CREATE TABLE Neighborhood (
    neighborhood_name TEXT NOT NULL PRIMARY KEY,
        -- <example>'Albany Park'</example>
    community_area_no INTEGER NOT NULL,
        -- <example>14</example>
        -- <fk> -> Community_Area.community_area_no</fk>
    FOREIGN KEY (community_area_no) REFERENCES Community_Area(community_area_no)
);

/*
Schema: NULLTable: Ward
Rows: 50
Sample rows:
| ward_no   | alderman_first_name   | alderman_last_name   | alderman_name_suffix   | ward_office_address    | ward_office_zip   | ward_email               | ward_office_phone   | ward_office_fax   | city_hall_office_room   | city_hall_office_phone   | city_hall_office_fax   | Population   |
|-----------|-----------------------|----------------------|------------------------|------------------------|-------------------|--------------------------|---------------------|-------------------|-------------------------|--------------------------|------------------------|--------------|
| 1         | Daniel                | La Spata             | [NULL]                 | 1958 N. Milwaukee Ave. | 60647             | info@the1stward.com      | 872.206.2685        | 312.448.8829      | 200                     | [NULL]                   | [NULL]                 | 56149        |
| 2         | Brian                 | Hopkins              | [NULL]                 | 1400 N. Ashland        | 60622             | ward02@cityofchicago.org | 312.643.2299        | [NULL]            | 200                     | 312.744.6836             | [NULL]                 | 55805        |
| 3         | Pat                   | Dowell               | [NULL]                 | 5046 S. State St.      | 60609             | ward03@cityofchicago.org | 773.373.9273        | [NULL]            | 200                     | 312.744.8734             | 312.744.6712           | 53039        |
| 4         | Sophia                | King                 | [NULL]                 | 435 E. 35th Street     | 60616             | ward04@cityofchicago.org | 773.536.8103        | 773.536.7296      | 305                     | 312.744.2690             | 312.744.7738           | 54589        |
| 5         | Leslie                | Hairston             | [NULL]                 | 2325 E. 71st Street    | 60649             | ward05@cityofchicago.org | 773.324.5555        | 773.324.1585      | 300                     | 312.744.6832             | 312.744.3195           | 51455        |
| ...       | ...                   | ...                  | ...                    | ...                    | ...               | ...                      | ...                 | ...               | ...                     | ...                      | ...                    | ...          |
*/
CREATE TABLE Ward (
    ward_no INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    alderman_first_name TEXT NOT NULL,
        -- <example>'Daniel'</example>
    alderman_last_name TEXT NOT NULL,
        -- <example>'La Spata'</example>
    alderman_name_suffix TEXT NULL,
        -- <values>{'Jr.'}</values>
    ward_office_address TEXT NULL,
        -- <example>'1958 N. Milwaukee Ave.'</example>
    ward_office_zip TEXT NULL,
        -- <example>'60647'</example>
    ward_email TEXT NULL,
        -- <example>'info@the1stward.com'</example>
    ward_office_phone TEXT NULL,
        -- <example>'872.206.2685'</example>
    ward_office_fax TEXT NULL,
        -- <example>'312.448.8829'</example>
    city_hall_office_room INTEGER NOT NULL,
        -- <example>200</example>
    city_hall_office_phone TEXT NULL,
        -- <example>'312.744.6836'</example>
    city_hall_office_fax TEXT NULL,
        -- <example>'312.744.6712'</example>
    Population INTEGER NOT NULL
        -- <example>56149</example>
);
```