```sql
-- Database: address

/*
Schema: NULLTable: CBSA
Rows: 465
Sample rows:
| CBSA   | CBSA_name                   | CBSA_type   |
|--------|-----------------------------|-------------|
| 10300  | Adrian, MI                  | Micro       |
| 10380  | Aguadilla-Isabela, PR       | Metro       |
| 10420  | Akron, OH                   | Metro       |
| 10500  | Albany, GA                  | Metro       |
| 10580  | Albany-Schenectady-Troy, NY | Metro       |
| ...    | ...                         | ...         |
*/
CREATE TABLE CBSA (
    CBSA INTEGER NOT NULL PRIMARY KEY,
        -- <example>10300</example>
    CBSA_name TEXT NOT NULL,
        -- <example>'Adrian, MI'</example>
    CBSA_type TEXT NOT NULL
        -- <values>{'Metro', 'Micro'}</values>
);

/*
Schema: NULLTable: alias
Rows: 41701
Sample rows:
| zip_code   | alias      |
|------------|------------|
| 501        | Holtsville |
| 544        | Holtsville |
| 601        | Adjuntas   |
| 602        | Aguada     |
| 603        | Aguadilla  |
| ...        | ...        |
*/
CREATE TABLE alias (
    zip_code INTEGER NOT NULL PRIMARY KEY,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    alias TEXT NOT NULL,
        -- <example>'Holtsville'</example>
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

/*
Schema: NULLTable: area_code
Rows: 53796
Sample rows:
| zip_code   | area_code   |
|------------|-------------|
| 501        | 631         |
| 544        | 631         |
| 601        | 787         |
| 601        | 939         |
| 602        | 787         |
| ...        | ...         |
*/
CREATE TABLE area_code (
    zip_code INTEGER NOT NULL,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    area_code INTEGER NOT NULL,
        -- <example>631</example>
    PRIMARY KEY (zip_code, area_code),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

/*
Schema: NULLTable: avoid
Rows: 24114
Sample rows:
| zip_code   | bad_alias                |
|------------|--------------------------|
| 501        | Internal Revenue Service |
| 544        | Internal Revenue Service |
| 601        | Colinas Del Gigante      |
| 601        | Jard De Adjuntas         |
| 601        | URB San Joaquin          |
| ...        | ...                      |
*/
CREATE TABLE avoid (
    zip_code INTEGER NOT NULL,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    bad_alias TEXT NOT NULL,
        -- <example>'Internal Revenue Service'</example>
    PRIMARY KEY (zip_code, bad_alias),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

/*
Schema: NULLTable: congress
Rows: 540
Sample rows:
| cognress_rep_id   | first_name   | last_name   | CID       | party      | state   | abbreviation   | House                  | District   | land_area   |
|-------------------|--------------|-------------|-----------|------------|---------|----------------|------------------------|------------|-------------|
| AK                | Young        | Don         | N00008091 | Republican | Alaska  | AK             | House of Repsentatives | [NULL]     | 571951.26   |
| AK-S1             | Begich       | Mark        | N00009585 | Democrat   | Alaska  | AK             | Senate                 | [NULL]     | 570641.0    |
| AK-S2             | Murkowski    | Lisa        | N00033101 | Republican | Alaska  | AK             | Senate                 | [NULL]     | 570641.0    |
| AL-1              | Byrne        | Bradley     | N00031938 | Republican | Alabama | AL             | House of Repsentatives | 1.0        | 6066.83     |
| AL-2              | Roby         | Martha      | N00031177 | Republican | Alabama | AL             | House of Repsentatives | 2.0        | 10141.63    |
| ...               | ...          | ...         | ...       | ...        | ...     | ...            | ...                    | ...        | ...         |
*/
CREATE TABLE congress (
    cognress_rep_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'AK'</example>
    first_name TEXT NOT NULL,
        -- <example>'Young'</example>
    last_name TEXT NOT NULL,
        -- <example>'Don'</example>
    CID TEXT NOT NULL,
        -- <example>'N00008091'</example>
    party TEXT NOT NULL,
        -- <values>{'Democrat', 'Independent', 'Republican'}</values>
    state TEXT NOT NULL,
        -- <example>'Alaska'</example>
    abbreviation TEXT NOT NULL,
        -- <example>'AK'</example>
        -- <fk> -> state.abbreviation</fk>
    House TEXT NOT NULL,
        -- <values>{'House of Repsentatives', 'Senate'}</values>
    District INTEGER NULL,
        -- <example>1</example>
    land_area REAL NOT NULL,
        -- <example>571951.260</example>
    FOREIGN KEY (abbreviation) REFERENCES state(abbreviation)
);

/*
Schema: NULLTable: country
Rows: 51001
Sample rows:
| zip_code   | county    | state   |
|------------|-----------|---------|
| 501        | SUFFOLK   | NY      |
| 544        | SUFFOLK   | NY      |
| 601        | ADJUNTAS  | PR      |
| 602        | AGUADA    | PR      |
| 603        | AGUADILLA | PR      |
| ...        | ...       | ...     |
*/
CREATE TABLE country (
    zip_code INTEGER NOT NULL,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    county TEXT NOT NULL,
        -- <example>'SUFFOLK'</example>
    state TEXT NULL,
        -- <example>'NY'</example>
        -- <fk> -> state.abbreviation</fk>
    PRIMARY KEY (zip_code, county),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code),
    FOREIGN KEY (state) REFERENCES state(abbreviation)
);

/*
Schema: NULLTable: state
Rows: 62
Sample rows:
| abbreviation   | name                  |
|----------------|-----------------------|
| AA             | Armed Forces Americas |
| AE             | Armed Forces Europe   |
| AK             | Alaska                |
| AL             | Alabama               |
| AP             | Armed Forces Pacific  |
| ...            | ...                   |
*/
CREATE TABLE state (
    abbreviation TEXT NOT NULL PRIMARY KEY,
        -- <example>'AA'</example>
    name TEXT NOT NULL
        -- <example>'Armed Forces Americas'</example>
);

/*
Schema: NULLTable: zip_congress
Rows: 45231
Sample rows:
| zip_code   | district   |
|------------|------------|
| 501        | NY-1       |
| 601        | PR         |
| 602        | PR         |
| 603        | PR         |
| 604        | PR         |
| ...        | ...        |
*/
CREATE TABLE zip_congress (
    zip_code INTEGER NOT NULL,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    district TEXT NOT NULL,
        -- <example>'NY-1'</example>
        -- <fk> -> congress.cognress_rep_id</fk>
    PRIMARY KEY (zip_code, district),
    FOREIGN KEY (district) REFERENCES congress(cognress_rep_id),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

/*
Schema: NULLTable: zip_data
Rows: 41563
Sample rows:
| zip_code   | city       | state   | multi_county   | type               | organization         | time_zone   | daylight_savings   | latitude   | longitude   | elevation   | state_fips   | county_fips   | region    | division        | population_2020   | population_2010   | households   | avg_house_value   | avg_income_per_household   | persons_per_household   | white_population   | black_population   | hispanic_population   | asian_population   | american_indian_population   | hawaiian_population   | other_population   | male_population   | female_population   | median_age   | male_median_age   | female_median_age   | residential_mailboxes   | business_mailboxes   | total_delivery_receptacles   | businesses   | 1st_quarter_payroll   | annual_payroll   | employees   | water_area   | land_area   | single_family_delivery_units   | multi_family_delivery_units   | total_beneficiaries   | retired_workers   | disabled_workers   | parents_and_widowed   | spouses   | children   | over_65   | monthly_benefits_all   | monthly_benefits_retired_workers   | monthly_benefits_widowed   | CBSA    |
|------------|------------|---------|----------------|--------------------|----------------------|-------------|--------------------|------------|-------------|-------------|--------------|---------------|-----------|-----------------|-------------------|-------------------|--------------|-------------------|----------------------------|-------------------------|--------------------|--------------------|-----------------------|--------------------|------------------------------|-----------------------|--------------------|-------------------|---------------------|--------------|-------------------|---------------------|-------------------------|----------------------|------------------------------|--------------|-----------------------|------------------|-------------|--------------|-------------|--------------------------------|-------------------------------|-----------------------|-------------------|--------------------|-----------------------|-----------|------------|-----------|------------------------|------------------------------------|----------------------------|---------|
| 501        | Holtsville | NY      | No             | Unique Post Office | I R S Service Center | Eastern     | Yes                | 40.817923  | -73.045317  | 25          | 36           | 103           | Northeast | Middle Atlantic | 0                 | 0                 | 0            | 0                 | 0                          | 0.0                     | 0                  | 0                  | 0                     | 0                  | 0                            | 0                     | 0                  | 0                 | 0                   | 0.0          | 0.0               | 0.0                 | 0                       | 1                    | 1                            | 2            | 0                     | 0                | 0           | 0.0          | 0.0         | 0                              | 0                             | 0                     | 0                 | 0                  | 0                     | 0         | 0          | 0         | 0                      | 0                                  | 0                          | 35620.0 |
| 544        | Holtsville | NY      | No             | Unique Post Office | Irs Service Center   | Eastern     | Yes                | 40.788827  | -73.039405  | 25          | 36           | 103           | Northeast | Middle Atlantic | 0                 | 0                 | 0            | 0                 | 0                          | 0.0                     | 0                  | 0                  | 0                     | 0                  | 0                            | 0                     | 0                  | 0                 | 0                   | 0.0          | 0.0               | 0.0                 | 0                       | 0                    | 0                            | 0            | 0                     | 0                | 0           | 0.0          | 0.0         | 0                              | 0                             | 0                     | 0                 | 0                  | 0                     | 0         | 0          | 0         | 0                      | 0                                  | 0                          | 35620.0 |
| 601        | Adjuntas   | PR      | No             | Post Office        | [NULL]               | Atlantic    | No                 | 18.196747  | -66.736735  | 0           | 72           | 1             | [NULL]    | [NULL]          | 11737             | 18570             | 6525         | 86200             | 13092                      | 2.84                    | 17479              | 663                | 18486                 | 7                  | 113                          | 10                    | 558                | 9078              | 9492                | 35.9         | 34.5              | 37.1                | 4133                    | 221                  | 5173                         | 0            | 0                     | 0                | 0           | 0.309        | 64.348      | 2419                           | 1264                          | 0                     | 0                 | 0                  | 0                     | 0         | 0          | 0         | 0                      | 0                                  | 0                          | 38660.0 |
| 602        | Aguada     | PR      | No             | Post Office        | [NULL]               | Atlantic    | No                 | 18.352927  | -67.177532  | 0           | 72           | 3             | [NULL]    | [NULL]          | 24263             | 41520             | 15002        | 86300             | 16358                      | 2.76                    | 36828              | 2860               | 41265                 | 42                 | 291                          | 32                    | 2634               | 20396             | 21124               | 37.5         | 36.6              | 38.5                | 8791                    | 519                  | 11302                        | 0            | 0                     | 0                | 0           | 1.71         | 30.621      | 5473                           | 827                           | 0                     | 0                 | 0                  | 0                     | 0         | 0          | 0         | 0                      | 0                                  | 0                          | 10380.0 |
| 603        | Aguadilla  | PR      | No             | Post Office        | [NULL]               | Atlantic    | No                 | 18.458585  | -67.129867  | 0           | 72           | 5             | [NULL]    | [NULL]          | 40361             | 54689             | 21161        | 122400            | 16603                      | 2.53                    | 46501              | 5042               | 53877                 | 135                | 313                          | 35                    | 4177               | 26597             | 28092               | 38.2         | 36.6              | 39.8                | 15953                   | 764                  | 19186                        | 0            | 0                     | 0                | 0           | 0.07         | 31.617      | 9621                           | 2947                          | 0                     | 0                 | 0                  | 0                     | 0         | 0          | 0         | 0                      | 0                                  | 0                          | 10380.0 |
| ...        | ...        | ...     | ...            | ...                | ...                  | ...         | ...                | ...        | ...         | ...         | ...          | ...           | ...       | ...             | ...               | ...               | ...          | ...               | ...                        | ...                     | ...                | ...                | ...                   | ...                | ...                          | ...                   | ...                | ...               | ...                 | ...          | ...               | ...                 | ...                     | ...                  | ...                          | ...          | ...                   | ...              | ...         | ...          | ...         | ...                            | ...                           | ...                   | ...               | ...                | ...                   | ...       | ...        | ...       | ...                    | ...                                | ...                        | ...     |
*/
CREATE TABLE zip_data (
    zip_code INTEGER NOT NULL PRIMARY KEY,
        -- <example>501</example>
    city TEXT NOT NULL,
        -- <example>'Holtsville'</example>
    state TEXT NOT NULL,
        -- <example>'NY'</example>
        -- <fk> -> state.abbreviation</fk>
    multi_county TEXT NOT NULL,
        -- <values>{'No', 'Yes'}</values>
    type TEXT NOT NULL,
        -- <values>{'APO/FPO Military', 'Branch', 'Branch-Unique', 'Community Post Office ', 'Non Postal Community Name', 'Non Postal Community Name-Unique', 'P.O. Box Only', 'Post Office', 'Unique Post Office'}</values>
    organization TEXT NULL,
        -- <example>'I R S Service Center'</example>
    time_zone TEXT NULL,
        -- <values>{'Alaska', 'American Samoa', 'Atlantic', 'Central', 'Eastern', 'Guam', 'Hawaii-Aleutian Islands', 'Marshall Islands', 'Micronesia', 'Mountain', 'Pacific', 'Palau'}</values>
    daylight_savings TEXT NOT NULL,
        -- <values>{'No', 'Yes'}</values>
    latitude REAL NULL,
        -- <example>40.818</example>
    longitude REAL NULL,
        -- <example>-73.045</example>
    elevation INTEGER NULL,
        -- <example>25</example>
    state_fips INTEGER NULL,
        -- <example>36</example>
    county_fips INTEGER NULL,
        -- <example>103</example>
    region TEXT NULL,
        -- <values>{'Midwest', 'Northeast', 'South', 'West'}</values>
    division TEXT NULL,
        -- <values>{'East North Central', 'East South Central', 'Middle Atlantic', 'Mountain', 'New England', 'Pacific', 'South Atlantic', 'West North Central', 'West South Central'}</values>
    population_2020 INTEGER NULL,
        -- <example>0</example>
    population_2010 INTEGER NULL,
        -- <example>0</example>
    households INTEGER NULL,
        -- <example>0</example>
    avg_house_value INTEGER NULL,
        -- <example>0</example>
    avg_income_per_household INTEGER NULL,
        -- <example>0</example>
    persons_per_household REAL NULL,
        -- <example>0.000</example>
    white_population INTEGER NULL,
        -- <example>0</example>
    black_population INTEGER NULL,
        -- <example>0</example>
    hispanic_population INTEGER NULL,
        -- <example>0</example>
    asian_population INTEGER NULL,
        -- <example>0</example>
    american_indian_population INTEGER NULL,
        -- <example>0</example>
    hawaiian_population INTEGER NULL,
        -- <example>0</example>
    other_population INTEGER NULL,
        -- <example>0</example>
    male_population INTEGER NULL,
        -- <example>0</example>
    female_population INTEGER NULL,
        -- <example>0</example>
    median_age REAL NULL,
        -- <example>0.000</example>
    male_median_age REAL NULL,
        -- <example>0.000</example>
    female_median_age REAL NULL,
        -- <example>0.000</example>
    residential_mailboxes INTEGER NULL,
        -- <example>0</example>
    business_mailboxes INTEGER NULL,
        -- <example>1</example>
    total_delivery_receptacles INTEGER NULL,
        -- <example>1</example>
    businesses INTEGER NULL,
        -- <example>2</example>
    "1st_quarter_payroll" INTEGER NULL,
        -- <example>0</example>
    annual_payroll INTEGER NULL,
        -- <example>0</example>
    employees INTEGER NULL,
        -- <example>0</example>
    water_area REAL NULL,
        -- <example>0.000</example>
    land_area REAL NULL,
        -- <example>0.000</example>
    single_family_delivery_units INTEGER NULL,
        -- <example>0</example>
    multi_family_delivery_units INTEGER NULL,
        -- <example>0</example>
    total_beneficiaries INTEGER NULL,
        -- <example>0</example>
    retired_workers INTEGER NULL,
        -- <example>0</example>
    disabled_workers INTEGER NULL,
        -- <example>0</example>
    parents_and_widowed INTEGER NULL,
        -- <example>0</example>
    spouses INTEGER NULL,
        -- <example>0</example>
    children INTEGER NULL,
        -- <example>0</example>
    over_65 INTEGER NULL,
        -- <example>0</example>
    monthly_benefits_all INTEGER NULL,
        -- <example>0</example>
    monthly_benefits_retired_workers INTEGER NULL,
        -- <example>0</example>
    monthly_benefits_widowed INTEGER NULL,
        -- <example>0</example>
    CBSA INTEGER NULL,
        -- <example>35620</example>
        -- <fk> -> CBSA.CBSA</fk>
    FOREIGN KEY (state) REFERENCES state(abbreviation),
    FOREIGN KEY (CBSA) REFERENCES CBSA(CBSA)
);
```