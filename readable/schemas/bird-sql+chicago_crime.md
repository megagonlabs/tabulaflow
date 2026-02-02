```sql
-- Database: chicago_crime

-- Table: Community_Area (77 rows)
CREATE TABLE Community_Area (
    community_area_no INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    community_area_name TEXT NULL,
        -- <example>'Rogers Park'</example>
    side TEXT NULL,
        -- <values>{'Central', 'Far North ', 'Far Southeast ', 'Far Southwest ', 'North ', 'Northwest ', 'South ', 'Southwest ', 'West '}</values>
    population TEXT NULL
        -- <example>'54,991'</example>
);

-- Table: Crime (268002 rows)
CREATE TABLE Crime (
    report_no INTEGER NULL PRIMARY KEY,
        -- <example>23757</example>
    case_number TEXT NULL,
        -- <example>'JB100159'</example>
    date TEXT NULL,
        -- <example>'1/1/2018 2:46'</example>
    block TEXT NULL,
        -- <example>'039XX W CORNELIA AVE'</example>
    iucr_no TEXT NULL,
        -- <example>'110'</example>
        -- <fk> -> IUCR.iucr_no</fk>
    location_description TEXT NULL,
        -- <example>'AUTO'</example>
    arrest TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    domestic TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    beat INTEGER NULL,
        -- <example>1732</example>
    district_no INTEGER NULL,
        -- <example>17</example>
        -- <fk> -> District.district_no</fk>
    ward_no INTEGER NULL,
        -- <example>30</example>
        -- <fk> -> Ward.ward_no</fk>
    community_area_no INTEGER NULL,
        -- <example>21</example>
        -- <fk> -> Community_Area.community_area_no</fk>
    fbi_code_no TEXT NULL,
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

-- Table: District (22 rows)
CREATE TABLE District (
    district_no INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    district_name TEXT NULL,
        -- <example>'Central'</example>
    address TEXT NULL,
        -- <example>'1718 South State Street'</example>
    zip_code INTEGER NULL,
        -- <example>60616</example>
    commander TEXT NULL,
        -- <example>'Jake M. Alderden'</example>
    email TEXT NULL,
        -- <example>' CAPS001District@chicagopolice.org'</example>
    phone TEXT NULL,
        -- <example>'312-745-4290'</example>
    fax TEXT NULL,
        -- <example>'312-745-3694'</example>
    tty TEXT NULL,
        -- <example>'312-745-3693'</example>
    twitter TEXT NULL
        -- <example>' ChicagoCAPS01'</example>
);

-- Table: FBI_Code (26 rows)
CREATE TABLE FBI_Code (
    fbi_code_no TEXT NULL PRIMARY KEY,
        -- <example>'01A'</example>
    title TEXT NULL,
        -- <example>'Homicide 1st & 2nd Degree'</example>
    description TEXT NULL,
        -- <example>'The killing of one human being by another.'</example>
    crime_against TEXT NULL
        -- <values>{'Persons and Society', 'Persons', 'Property', 'Society'}</values>
);

-- Table: IUCR (401 rows)
CREATE TABLE IUCR (
    iucr_no TEXT NULL PRIMARY KEY,
        -- <example>'031A'</example>
    primary_description TEXT NULL,
        -- <example>'HOMICIDE'</example>
    secondary_description TEXT NULL,
        -- <example>'FIRST DEGREE MURDER'</example>
    index_code TEXT NULL
        -- <values>{'I', 'N'}</values>
);

-- Table: Neighborhood (246 rows)
CREATE TABLE Neighborhood (
    neighborhood_name TEXT NULL PRIMARY KEY,
        -- <example>'Albany Park'</example>
    community_area_no INTEGER NULL,
        -- <example>14</example>
        -- <fk> -> Community_Area.community_area_no</fk>
    FOREIGN KEY (community_area_no) REFERENCES Community_Area(community_area_no)
);

-- Table: Ward (50 rows)
CREATE TABLE Ward (
    ward_no INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    alderman_first_name TEXT NULL,
        -- <example>'Daniel'</example>
    alderman_last_name TEXT NULL,
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
    city_hall_office_room INTEGER NULL,
        -- <example>200</example>
    city_hall_office_phone TEXT NULL,
        -- <example>'312.744.6836'</example>
    city_hall_office_fax TEXT NULL,
        -- <example>'312.744.6712'</example>
    Population INTEGER NULL
        -- <example>56149</example>
);
```