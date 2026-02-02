```sql
-- Database: address

-- Table: CBSA (465 rows)
CREATE TABLE CBSA (
    CBSA INTEGER NULL PRIMARY KEY,
        -- <example>10300</example>
    CBSA_name TEXT NULL,
        -- <example>'Adrian, MI'</example>
    CBSA_type TEXT NULL
        -- <values>{'Metro', 'Micro'}</values>
);

-- Table: alias (41701 rows)
CREATE TABLE alias (
    zip_code INTEGER NULL PRIMARY KEY,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    alias TEXT NULL,
        -- <example>'Holtsville'</example>
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

-- Table: area_code (53796 rows)
CREATE TABLE area_code (
    zip_code INTEGER NULL,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    area_code INTEGER NULL,
        -- <example>631</example>
    PRIMARY KEY (zip_code, area_code),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

-- Table: avoid (24114 rows)
CREATE TABLE avoid (
    zip_code INTEGER NULL,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    bad_alias TEXT NULL,
        -- <example>'Internal Revenue Service'</example>
    PRIMARY KEY (zip_code, bad_alias),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

-- Table: congress (540 rows)
CREATE TABLE congress (
    cognress_rep_id TEXT NULL PRIMARY KEY,
        -- <example>'AK'</example>
    first_name TEXT NULL,
        -- <example>'Young'</example>
    last_name TEXT NULL,
        -- <example>'Don'</example>
    CID TEXT NULL,
        -- <example>'N00008091'</example>
    party TEXT NULL,
        -- <values>{'Democrat', 'Independent', 'Republican'}</values>
    state TEXT NULL,
        -- <example>'Alaska'</example>
    abbreviation TEXT NULL,
        -- <example>'AK'</example>
        -- <fk> -> state.abbreviation</fk>
    House TEXT NULL,
        -- <values>{'House of Repsentatives', 'Senate'}</values>
    District INTEGER NULL,
        -- <example>1</example>
    land_area REAL NULL,
        -- <example>571951.260</example>
    FOREIGN KEY (abbreviation) REFERENCES state(abbreviation)
);

-- Table: country (51001 rows)
CREATE TABLE country (
    zip_code INTEGER NULL,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    county TEXT NULL,
        -- <example>'SUFFOLK'</example>
    state TEXT NULL,
        -- <example>'NY'</example>
        -- <fk> -> state.abbreviation</fk>
    PRIMARY KEY (zip_code, county),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code),
    FOREIGN KEY (state) REFERENCES state(abbreviation)
);

-- Table: state (62 rows)
CREATE TABLE state (
    abbreviation TEXT NULL PRIMARY KEY,
        -- <example>'AA'</example>
    name TEXT NULL
        -- <example>'Armed Forces Americas'</example>
);

-- Table: zip_congress (45231 rows)
CREATE TABLE zip_congress (
    zip_code INTEGER NULL,
        -- <example>501</example>
        -- <fk> -> zip_data.zip_code</fk>
    district TEXT NULL,
        -- <example>'NY-1'</example>
        -- <fk> -> congress.cognress_rep_id</fk>
    PRIMARY KEY (zip_code, district),
    FOREIGN KEY (district) REFERENCES congress(cognress_rep_id),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

-- Table: zip_data (41563 rows)
CREATE TABLE zip_data (
    zip_code INTEGER NULL PRIMARY KEY,
        -- <example>501</example>
    city TEXT NULL,
        -- <example>'Holtsville'</example>
    state TEXT NULL,
        -- <example>'NY'</example>
        -- <fk> -> state.abbreviation</fk>
    multi_county TEXT NULL,
        -- <values>{'No', 'Yes'}</values>
    type TEXT NULL,
        -- <values>{'APO/FPO Military', 'Branch', 'Branch-Unique', 'Community Post Office ', 'Non Postal Community Name', 'Non Postal Community Name-Unique', 'P.O. Box Only', 'Post Office', 'Unique Post Office'}</values>
    organization TEXT NULL,
        -- <example>'I R S Service Center'</example>
    time_zone TEXT NULL,
        -- <values>{'Alaska', 'American Samoa', 'Atlantic', 'Central', 'Eastern', 'Guam', 'Hawaii-Aleutian Islands', 'Marshall Islands', 'Micronesia', 'Mountain', 'Pacific', 'Palau'}</values>
    daylight_savings TEXT NULL,
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