```sql
-- Database: address

-- Table: CBSA (465 rows)
CREATE TABLE CBSA (
    CBSA INTEGER PRIMARY KEY,  -- e.g. 10300
    CBSA_name TEXT,  -- e.g. 'Adrian, MI'
    CBSA_type TEXT  -- values: {'Metro', 'Micro'}
);

-- Table: alias (41701 rows)
CREATE TABLE alias (
    zip_code INTEGER PRIMARY KEY,  -- e.g. 501; FK -> zip_data.zip_code
    alias TEXT,  -- e.g. 'Holtsville'
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

-- Table: area_code (53796 rows)
CREATE TABLE area_code (
    zip_code INTEGER,  -- e.g. 501; FK -> zip_data.zip_code
    area_code INTEGER,  -- e.g. 631
    PRIMARY KEY (zip_code, area_code),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

-- Table: avoid (24114 rows)
CREATE TABLE avoid (
    zip_code INTEGER,  -- e.g. 501; FK -> zip_data.zip_code
    bad_alias TEXT,  -- e.g. 'Internal Revenue Service'
    PRIMARY KEY (zip_code, bad_alias),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

-- Table: congress (540 rows)
CREATE TABLE congress (
    cognress_rep_id TEXT PRIMARY KEY,  -- e.g. 'AK'
    first_name TEXT,  -- e.g. 'Young'
    last_name TEXT,  -- e.g. 'Don'
    CID TEXT,  -- e.g. 'N00008091'
    party TEXT,  -- values: {'Democrat', 'Independent', 'Republican'}
    state TEXT,  -- e.g. 'Alaska'
    abbreviation TEXT,  -- e.g. 'AK'; FK -> state.abbreviation
    House TEXT,  -- values: {'House of Repsentatives', 'Senate'}
    District INTEGER,  -- e.g. 1
    land_area REAL,  -- e.g. 571951.260
    FOREIGN KEY (abbreviation) REFERENCES state(abbreviation)
);

-- Table: country (51001 rows)
CREATE TABLE country (
    zip_code INTEGER,  -- e.g. 501; FK -> zip_data.zip_code
    county TEXT,  -- e.g. 'SUFFOLK'
    state TEXT,  -- e.g. 'NY'; FK -> state.abbreviation
    PRIMARY KEY (zip_code, county),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code),
    FOREIGN KEY (state) REFERENCES state(abbreviation)
);

-- Table: state (62 rows)
CREATE TABLE state (
    abbreviation TEXT PRIMARY KEY,  -- e.g. 'AA'
    name TEXT  -- e.g. 'Armed Forces Americas'
);

-- Table: zip_congress (45231 rows)
CREATE TABLE zip_congress (
    zip_code INTEGER,  -- e.g. 501; FK -> zip_data.zip_code
    district TEXT,  -- e.g. 'NY-1'; FK -> congress.cognress_rep_id
    PRIMARY KEY (zip_code, district),
    FOREIGN KEY (district) REFERENCES congress(cognress_rep_id),
    FOREIGN KEY (zip_code) REFERENCES zip_data(zip_code)
);

-- Table: zip_data (41563 rows)
CREATE TABLE zip_data (
    zip_code INTEGER PRIMARY KEY,  -- e.g. 501
    city TEXT,  -- e.g. 'Holtsville'
    state TEXT,  -- e.g. 'NY'; FK -> state.abbreviation
    multi_county TEXT,  -- values: {'No', 'Yes'}
    type TEXT,  -- values: {'APO/FPO Military', 'Branch', 'Branch-Unique', 'Community Post Office ', 'Non Postal Community Name', 'Non Postal Community Name-Unique', 'P.O. Box Only', 'Post Office', 'Unique Post Office'}
    organization TEXT,  -- e.g. 'I R S Service Center'
    time_zone TEXT,  -- values: {'Alaska', 'American Samoa', 'Atlantic', 'Central', 'Eastern', 'Guam', 'Hawaii-Aleutian Islands', 'Marshall Islands', 'Micronesia', 'Mountain', 'Pacific', 'Palau'}
    daylight_savings TEXT,  -- values: {'No', 'Yes'}
    latitude REAL,  -- e.g. 40.818
    longitude REAL,  -- e.g. -73.045
    elevation INTEGER,  -- e.g. 25
    state_fips INTEGER,  -- e.g. 36
    county_fips INTEGER,  -- e.g. 103
    region TEXT,  -- values: {'Midwest', 'Northeast', 'South', 'West'}
    division TEXT,  -- values: {'East North Central', 'East South Central', 'Middle Atlantic', 'Mountain', 'New England', 'Pacific', 'South Atlantic', 'West North Central', 'West South Central'}
    population_2020 INTEGER,  -- e.g. 0
    population_2010 INTEGER,  -- e.g. 0
    households INTEGER,  -- e.g. 0
    avg_house_value INTEGER,  -- e.g. 0
    avg_income_per_household INTEGER,  -- e.g. 0
    persons_per_household REAL,  -- e.g. 0.000
    white_population INTEGER,  -- e.g. 0
    black_population INTEGER,  -- e.g. 0
    hispanic_population INTEGER,  -- e.g. 0
    asian_population INTEGER,  -- e.g. 0
    american_indian_population INTEGER,  -- e.g. 0
    hawaiian_population INTEGER,  -- e.g. 0
    other_population INTEGER,  -- e.g. 0
    male_population INTEGER,  -- e.g. 0
    female_population INTEGER,  -- e.g. 0
    median_age REAL,  -- e.g. 0.000
    male_median_age REAL,  -- e.g. 0.000
    female_median_age REAL,  -- e.g. 0.000
    residential_mailboxes INTEGER,  -- e.g. 0
    business_mailboxes INTEGER,  -- e.g. 1
    total_delivery_receptacles INTEGER,  -- e.g. 1
    businesses INTEGER,  -- e.g. 2
    "1st_quarter_payroll" INTEGER,  -- e.g. 0
    annual_payroll INTEGER,  -- e.g. 0
    employees INTEGER,  -- e.g. 0
    water_area REAL,  -- e.g. 0.000
    land_area REAL,  -- e.g. 0.000
    single_family_delivery_units INTEGER,  -- e.g. 0
    multi_family_delivery_units INTEGER,  -- e.g. 0
    total_beneficiaries INTEGER,  -- e.g. 0
    retired_workers INTEGER,  -- e.g. 0
    disabled_workers INTEGER,  -- e.g. 0
    parents_and_widowed INTEGER,  -- e.g. 0
    spouses INTEGER,  -- e.g. 0
    children INTEGER,  -- e.g. 0
    over_65 INTEGER,  -- e.g. 0
    monthly_benefits_all INTEGER,  -- e.g. 0
    monthly_benefits_retired_workers INTEGER,  -- e.g. 0
    monthly_benefits_widowed INTEGER,  -- e.g. 0
    CBSA INTEGER,  -- e.g. 35620; FK -> CBSA.CBSA
    FOREIGN KEY (state) REFERENCES state(abbreviation),
    FOREIGN KEY (CBSA) REFERENCES CBSA(CBSA)
);
```