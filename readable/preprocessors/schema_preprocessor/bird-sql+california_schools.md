```sql
-- Database: california_schools

-- Table: frpm (9986 rows)
CREATE TABLE frpm (
    CDSCode TEXT NOT NULL PRIMARY KEY,
        -- <description>California school CDS code — the unique school identifier for each frpm record; non-null and unique across the table (9,986 distinct values for 9,986 rows). Links to schools.CDSCode.</description>
        -- <example>'01100170109835'</example>
        -- <fk> -> schools.CDSCode</fk>
    "Academic Year" TEXT NULL,
        -- <description>Academic year for which the free and reduced-price meals data are reported (dataset contains only 2014–2015).</description>
        -- <values>{'2014-2015'}</values>
    "County Code" TEXT NULL,
        -- <description>County code identifying the county of the school/district.</description>
        -- <example>'01'</example>
    "District Code" INTEGER NULL,
        -- <description>School district identifier — numeric code that uniquely identifies the school district for each FRPM record.</description>
        -- <example>10017</example>
    "School Code" TEXT NULL,
        -- <description>Local school code — the (usually zero‑padded) school identifier used in the FRPM table; combined with county and district codes to identify a specific school within state data.</description>
        -- <example>'0109835'</example>
    "County Name" TEXT NULL,
        -- <description>County name of the school district — identifies the California county where the school is located (contains 9,986 non-null values with 58 distinct counties; e.g., Los Angeles, San Diego, Orange).</description>
        -- <example>'Alameda'</example>
    "District Name" TEXT NULL,
        -- <description>School district name for the FRPM record — the district that operates the school receiving the free and reduced-price meals data (matches the district associated with the record’s CDSCode).</description>
        -- <example>'Alameda County Office of Education'</example>
    "School Name" TEXT NULL,
        -- <description>School name — the school's official name as reported in the Free and Reduced‑Price Meals (FRPM) dataset (e.g., Neal Dow Elementary; Valley Oaks Charter; Pio Pico Elementary).</description>
        -- <example>'FAME Public Charter'</example>
    "District Type" TEXT NULL,
        -- <description>School district category indicating the administrative type of the district that operates the school.</description>
        -- <values>{'County Office of Education (COE)', 'Elementary School District', 'High School District', 'Non-School Locations', 'State Board of Education', 'State Special Schools', 'Statewide Benefit Charter', 'Unified School District'}</values>
    "School Type" TEXT NULL,
        -- <description>School type classification indicating the school's instructional or program category (used to group schools by level and program for free and reduced‑price meals reporting).</description>
        -- <values>{'Alternative Schools of Choice', 'Continuation High Schools', 'County Community', 'District Community Day Schools', 'Elemen Schools In 1 School Dist. (Public)', 'Elementary Schools (Public)', 'High Schools (Public)', 'High Schools In 1 School Dist. (Public)', 'Intermediate/Middle Schools (Public)', 'Junior High Schools (Public)', 'Juvenile Court Schools', 'K-12 Schools (Public)', 'Opportunity Schools', 'Preschool', 'Special Education Schools (Public)', 'State Special Schools', 'Youth Authority Facilities'}</values>
    "Educational Option Type" TEXT NULL,
        -- <description>Educational option type — the program category describing the kind of educational program or instructional option the school provides (used for reporting and classification).</description>
        -- <values>{'Alternative School of Choice', 'Community Day School', 'Continuation School', 'County Community School', 'District Special Education Consortia School', 'Home and Hospital', 'Juvenile Court School', 'Opportunity School', 'Special Education School', 'State Special School', 'Traditional', 'Youth Authority School'}</values>
    "NSLP Provision Status" TEXT NULL,
        -- <description>NSLP provision type indicating which National School Lunch Program participation model governs meal service and eligibility at the school (e.g., Community Eligibility Provision or Provision 1/2/3); many records are blank in this dataset.</description>
        -- <values>{'Breakfast Provision 2', 'CEP', 'Lunch Provision 2', 'Multiple Provision Types', 'Provision 1', 'Provision 2', 'Provision 3'}</values>
    "Charter School (Y/N)" INTEGER NULL,
        -- <description>Charter school indicator (1 = yes, 0 = no).</description>
        -- <example>1</example>
    "Charter School Number" TEXT NULL,
        -- <description>Charter school number — the state/agency-assigned identifier for charter schools (typically a 4‑digit code, often stored with leading zeros). Nullable; present in 1,167 of 9,986 rows with 1,152 distinct values (examples: '0728', '1093', '1382').</description>
        -- <example>'0728'</example>
    "Charter Funding Type" TEXT NULL,
        -- <description>Charter school funding model — the funding category assigned to a school's charter (populated only for charter schools). Many rows are NULL: 1,167 non-null out of 9,986 (~11.7%), so the field is sparsely populated.</description>
        -- <values>{'Directly funded', 'Locally funded', 'Not in CS funding model'}</values>
    "Low Grade" TEXT NULL,
        -- <description>Lowest grade level served by the school (grade code such as a number, 'K' for kindergarten, 'P' for preschool, or 'Adult').</description>
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P'}</values>
    "High Grade" TEXT NULL,
        -- <description>Highest grade level served by the school, reported with grade labels (e.g., numeric grades, 'K' for kindergarten, 'P' for preschool, 'Adult', or 'Post Secondary').</description>
        -- <values>{'1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P', 'Post Secondary'}</values>
    "Enrollment (K-12)" REAL NULL,
        -- <description>K–12 enrollment — total number of students enrolled at the school in grades Kindergarten through 12; used as the denominator for FRPM eligibility rates (no missing values in this table; observed range 1–5,333, mean ≈621).</description>
        -- <example>1087.000</example>
    "Free Meal Count (K-12)" REAL NULL,
        -- <description>Count of K–12 students eligible for free meals at the school, used with enrollment to compute the percent eligible for free meals.</description>
        -- <example>565.000</example>
    "Percent (%) Eligible Free (K-12)" REAL NULL,
        -- <description>Percentage of K–12 students eligible for free meals at the school (calculated as Free Meal Count (K-12) ÷ Enrollment (K-12); stored as a decimal fraction).</description>
        -- <example>0.520</example>
    "FRPM Count (K-12)" REAL NULL,
        -- <description>Count of K–12 students at the school who are eligible for free or reduced-price meals (headcount). Commonly combined with enrollment to compute FRPM eligibility percentages.</description>
        -- <example>715.000</example>
    "Percent (%) Eligible FRPM (K-12)" REAL NULL,
        -- <description>Share of K–12 students eligible for free or reduced-price meals (FRPM); stored as a proportion (0–1) — e.g. 0.612 = 61.2%. Observed range ≈ 0.0022–1.0; 9,936 non-null values out of 9,986 rows.</description>
        -- <example>0.658</example>
    "Enrollment (Ages 5-17)" REAL NULL,
        -- <description>Number of enrolled students ages 5–17 who are counted for free or reduced-price meal (FRPM) reporting at the school.</description>
        -- <example>1070.000</example>
    "Free Meal Count (Ages 5-17)" REAL NULL,
        -- <description>Count of students ages 5–17 eligible for free meals (free-meal recipients). Used to compute the eligible-free rate = Free Meal Count (Ages 5–17) ÷ Enrollment (Ages 5–17). Contains values from 1 to 3,864 (mean ≈ 304); 78 of 9,986 rows are NULL.</description>
        -- <example>553.000</example>
    "Percent (%) Eligible Free (Ages 5-17)" REAL NULL,
        -- <description>Proportion of students ages 5–17 eligible for free meals (reported as a decimal fraction 0–1). Mostly populated — 9,908 of 9,986 rows (~99.2%); observed values range ~0.0018 to 1. No values outside the 0–1 range.</description>
        -- <example>0.517</example>
    "FRPM Count (Ages 5-17)" REAL NULL,
        -- <description>Number of students ages 5–17 at the school who are eligible for free or reduced-price meals (FRPM), used to compute FRPM eligibility rates for the 5–17 age group.</description>
        -- <example>702.000</example>
    "Percent (%) Eligible FRPM (Ages 5-17)" REAL NULL,
        -- <description>Percentage of students ages 5–17 eligible for free or reduced‑price meals (expressed as a decimal proportion, 0–1).</description>
        -- <example>0.656</example>
    "2013-14 CALPADS Fall 1 Certification Status" INTEGER NULL,
        -- <description>2013–14 CALPADS Fall 1 certification status for the FRPM record — integer certification code (constant value: 1 for all rows).</description>
        -- <example>1</example>
    FOREIGN KEY (CDSCode) REFERENCES schools(CDSCode)
);

-- Table: satscores (2269 rows)
CREATE TABLE satscores (
    cds TEXT NOT NULL PRIMARY KEY,
        -- <description>California Department of Education (CDS) school identifier — the unique school code used to link each SAT score record to the schools table.</description>
        -- <example>'10101080000000'</example>
        -- <fk> -> schools.CDSCode</fk>
    sname TEXT NULL,
        -- <description>School name as reported on the SAT scores record — the name of the school associated with the SAT score data (examples: 'FAME Public Charter', 'Prospects High (Alternative)', 'Otay Ranch Senior High').</description>
        -- <example>'FAME Public Charter'</example>
    dname TEXT NULL,
        -- <description>School district name — the name of the school district associated with each SAT scores record (e.g., 'Los Angeles Unified').</description>
        -- <example>'Alameda County Office of Education'</example>
    cname TEXT NULL,
        -- <description>County name where the school is located (e.g., Los Angeles, San Diego, San Bernardino).</description>
        -- <example>'Alameda'</example>
    enroll12 INTEGER NOT NULL,
        -- <description>K–12 enrollment count for the school (number of students in grades 1–12).</description>
        -- <example>398</example>
    NumTstTakr INTEGER NOT NULL,
        -- <description>Number of SAT test takers per reporting entity — count of students recorded as having taken the SAT for the row’s reporting unit (typically a school).</description>
        -- <example>88</example>
    AvgScrRead INTEGER NULL,
        -- <description>Average SAT Reading section score for the school's test takers (average for the reported administration).</description>
        -- <example>418</example>
    AvgScrMath INTEGER NULL,
        -- <description>Average SAT Math score for the school's test takers (mean Math section score among students who took the SAT); NULL when no Math scores were reported. In this dataset 1,673 of 2,269 records are populated — observed range 289–699, overall mean ≈ 484.</description>
        -- <example>418</example>
    AvgScrWrite INTEGER NULL,
        -- <description>Average SAT Writing score for the school — the school-level mean of individual students' SAT Writing scores.</description>
        -- <example>417</example>
    NumGE1500 INTEGER NULL,
        -- <description>Count of test takers whose total SAT score is greater than or equal to 1500.</description>
        -- <example>14</example>
    FOREIGN KEY (cds) REFERENCES schools(CDSCode)
);

-- Table: schools (17686 rows)
CREATE TABLE schools (
    CDSCode TEXT NOT NULL PRIMARY KEY,
        -- <description>California Department of Education school identifier (CDSCode) — the unique statewide school code (14-digit CDS code) used as the primary key and to join school records across datasets.</description>
        -- <example>'01100170000000'</example>
    NCESDist TEXT NULL,
        -- <description>7‑digit NCES school-district identifier — first two digits indicate the state and the last five identify the district; concatenated with NCESSchool to form the unique 12‑digit NCES school ID.</description>
        -- <example>'0691051'</example>
    NCESSchool TEXT NULL,
        -- <description>NCES school identifier — zero-padded 5-digit NCES school ID; when combined with NCESDist (7-digit district ID) it forms the full 12-digit NCES school identifier.</description>
        -- <example>'10546'</example>
    StatusType TEXT NOT NULL,
        -- <description>School operational status — indicates whether the school record is currently operating (Active), no longer operating (Closed), has been combined into another record/district (Merged), or is planned/not yet open (Pending).</description>
        -- <values>{'Active', 'Closed', 'Merged', 'Pending'}</values>
    County TEXT NOT NULL,
        -- <description>County name for the school's location (California county; 58 distinct values; no missing values).</description>
        -- <example>'Alameda'</example>
    District TEXT NOT NULL,
        -- <description>School district name — the name of the district that administers the school (e.g., Los Angeles Unified, San Diego Unified).</description>
        -- <example>'Alameda County Office of Education'</example>
    School TEXT NULL,
        -- <description>School name — the official name of the school as listed in the California schools dataset.</description>
        -- <example>'FAME Public Charter'</example>
    Street TEXT NULL,
        -- <description>Street address of the school's physical location (unabbreviated). Often used with City/Zip or Latitude/Longitude for mapping; some records (e.g., closed or retired schools) may be empty. Example values: '313 West Winton Avenue', '929 West 69th Street'.</description>
        -- <example>'313 West Winton Avenue'</example>
    StreetAbr TEXT NULL,
        -- <description>Abbreviated street address for the school’s physical location — a shortened/mailing version of the street address (e.g., '1051 South Sunkist St.', '1398 Sperber Rd.'). May be empty for closed or retired schools; most records are populated (~98.3%).</description>
        -- <example>'313 West Winton Ave.'</example>
    City TEXT NULL,
        -- <description>City — municipality where the school is located.</description>
        -- <example>'Hayward'</example>
    Zip TEXT NULL,
        -- <description>School ZIP/postal code for the school's address — typically a 5-digit ZIP or a 5+4 ZIP+4 (hyphenated) string; a small number of records are blank.</description>
        -- <example>'94544-1136'</example>
    State TEXT NULL,
        -- <description>State of the school's address — identifies the U.S. state for each school; in this dataset almost all records are California (value 'CA') with a small number of NULLs.</description>
        -- <values>{'CA'}</values>
    MailStreet TEXT NULL,
        -- <description>Unabbreviated mailing street address for the school, district, or administrative authority — when missing this field is often filled with the Street value; some closed or retired entities have no mailing address.</description>
        -- <example>'313 West Winton Avenue'</example>
    MailStrAbr TEXT NULL,
        -- <description>Abbreviated mailing street address for the school's mailing address — when missing, populated from StreetAbr (many records match StreetAbr).</description>
        -- <example>'313 West Winton Ave.'</example>
    MailCity TEXT NULL,
        -- <description>Mailing city for the school's mailing address — populated with the School.City value when a separate mailing city was not provided.</description>
        -- <example>'Hayward'</example>
    MailZip TEXT NULL,
        -- <description>Mailing ZIP code for the school’s mailing address — typically five-digit or ZIP+4 (hyphenated); when a separate mailing ZIP was not provided it was filled from the primary Zip field.</description>
        -- <example>'94544-1136'</example>
    MailState TEXT NULL,
        -- <description>Mailing state for the school’s mailing address — the two-letter U.S. state for the mailing address (almost always 'CA' in this dataset).</description>
        -- <values>{'CA'}</values>
    Phone TEXT NULL,
        -- <description>School phone number — the primary public telephone contact for the school (often formatted with area code in parentheses). Many records are populated (~66%); formatting varies and most non-null values are unique. Extensions, if present, are recorded in the separate Ext column.</description>
        -- <example>'(510) 887-0152'</example>
    Ext TEXT NULL,
        -- <description>Phone extension for the school's contact (internal dial extension for the school, district, or administrative authority). Sparsely populated: 540 non-empty values (≈3.1% of 17,686 rows) and 379 distinct entries.</description>
        -- <example>'130'</example>
    Website TEXT NULL,
        -- <description>Public website address for the school, district, or administrative authority (public-facing URL). Often provided as a domain with or without an http(s) prefix and may include trailing slashes; many records are empty (~39% populated) and formatting is inconsistent.</description>
        -- <example>'www.acoe.org'</example>
    OpenDate DATE NULL,
        -- <description>School opening date — the first reported open date for the school (when the school began operation). Contains historic and modern values; in this dataset it has 16,317 non-null values out of 17,686 rows (≈92%), with distinct dates = 1,406 and observed range 1850-07-01 to 2017-09-22.</description>
        -- <example>'2005-08-29'</example>
    ClosedDate DATE NULL,
        -- <description>School closure date — the calendar date the school closed (NULL for schools that remain active). 5,694 rows populated; earliest closed: 1980-07-01, latest closed: 2016-09-01.</description>
        -- <example>'2015-07-31'</example>
    Charter INTEGER NULL,
        -- <description>Charter school indicator — 1 = charter school, 0 = non-charter; NULL when unknown or not provided.</description>
        -- <example>1</example>
    CharterNum TEXT NULL,
        -- <description>Charter school number — a 4-digit identifier assigned to a charter school (often blank for non‑charter schools).</description>
        -- <example>'0728'</example>
    FundingType TEXT NULL,
        -- <description>Charter school funding source — indicates how a charter is funded (e.g., Directly funded, Locally funded, or Not in CS funding model). Mostly blank for non‑charter schools (≈91% of records are null).</description>
        -- <values>{'Directly funded', 'Locally funded', 'Not in CS funding model'}</values>
    DOC TEXT NOT NULL,
        -- <description>District ownership code identifying the category of the administrative authority that governs the school (e.g., county office, unified district, elementary district). Note: the dataset’s non‑school location category contains only the California Education Authority. Most records use codes for Unified (54) and Elementary (52) districts.</description>
        -- <values>{'00', '02', '03', '31', '34', '42', '52', '54', '56', '58', '98', '99'}</values>
    DOCType TEXT NOT NULL,
        -- <description>District ownership category label — the human-readable description of the administrative authority category (the text equivalent of DOC), e.g., County Office of Education, Unified School District, Joint Powers Authority.</description>
        -- <values>{'Administration Only', 'Community College District', 'County Office of Education (COE)', 'Elementary School District', 'High School District', 'Joint Powers Authority (JPA)', 'Non-School Locations', 'Regional Occupation Center/Program (ROC/P)', 'State Board of Education', 'State Special Schools', 'Statewide Benefit Charter', 'Unified School District'}</values>
    SOC TEXT NULL,
        -- <description>School Ownership Code — numeric code indicating the school’s category/type (identifies whether a site is an elementary, middle, high, special‑education, preschool, etc.).</description>
        -- <values>{'08', '09', '10', '11', '13', '14', '15', '31', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '70', '98'}</values>
    SOCType TEXT NULL,
        -- <description>School ownership category — human-readable label describing the school's ownership/type (the text equivalent of the SOC numeric code).</description>
        -- <values>{'Adult Education Centers', 'Alternative Schools of Choice', 'Continuation High Schools', 'County Community', 'District Community Day Schools', 'Elemen Schools In 1 School Dist. (Public)', 'Elementary Schools (Public)', 'High Schools (Public)', 'High Schools In 1 School Dist. (Public)', 'Intermediate/Middle Schools (Public)', 'Junior High Schools (Public)', 'Juvenile Court Schools', 'K-12 Schools (Public)', 'Opportunity Schools', 'Other County Or District Programs', 'Preschool', 'ROC/ROP', 'Special Education Schools (Public)', 'State Special Schools', 'Youth Authority Facilities'}</values>
    EdOpsCode TEXT NULL,
        -- <description>Education-option code — a short code identifying the school's instructional or program type (maps to EdOpsName for the full label). Examples: TRAD, CON, COMMDAY, YTH.</description>
        -- <values>{'ALTSOC', 'COMM', 'COMMDAY', 'CON', 'HOMHOS', 'JUV', 'OPP', 'ROP', 'SPEC', 'SPECON', 'SSS', 'TRAD', 'YTH'}</values>
    EdOpsName TEXT NULL,
        -- <description>Educational option name — the long-form, human-readable label describing the educational option or program a school offers (maps to the short EdOpsCode). Contains a small set of standard labels (13 distinct values) and about 32% missing values, so expect many records to be blank.</description>
        -- <values>{'Alternative School of Choice', 'Community Day School', 'Continuation School', 'County Community School', 'District Special Education Consortia School', 'Home and Hospital', 'Juvenile Court School', 'Opportunity School', 'ROP', 'Special Education School', 'State Special School', 'Traditional', 'Youth Authority School'}</values>
    EILCode TEXT NULL,
        -- <description>educational instruction level code — short code indicating the institution’s instructional level (the grade range served); paired with EILName for the human-readable label.</description>
        -- <values>{'A', 'ELEM', 'ELEMHIGH', 'HS', 'INTMIDJR', 'PS', 'UG'}</values>
    EILName TEXT NULL,
        -- <description>Educational instruction level name — the long-form text label that describes the school's grade-range category (the human-readable description corresponding to EILCode).</description>
        -- <values>{'Adult', 'Elementary', 'Elementary-High Combination', 'High School', 'Intermediate/Middle/Junior High', 'Preschool', 'Ungraded'}</values>
    GSoffered TEXT NULL,
        -- <description>Grade span offered — the lowest and highest grades the school (or district/authority) reports it offers; this is an advertised/available grade range and may differ from the grade span actually served in CALPADS. (Examples: "K-5", "9-12", "K-12".)</description>
        -- <example>'K-12'</example>
    GSserved TEXT NULL,
        -- <description>Grade span served — the lowest and highest grades with student enrollment as reported to CALPADS (Fall 1). Only K–12 enrollment is included; this may differ from the grade span offered by the school. Typical values are ranges like 'K-5', '6-8', single grades like '12', or null when not reported.</description>
        -- <example>'K-12'</example>
    Virtual TEXT NULL,
        -- <description>Virtual instruction status — indicates whether and to what extent the school offers virtual (remote/online) instruction (i.e., students and teachers separated by time and/or location, interacting via computers/telecommunications); codes in the source denote full, partial/hybrid, or no virtual program.</description>
        -- <values>{'F', 'N', 'P'}</values>
    Magnet INTEGER NULL,
        -- <description>Magnet school indicator — binary flag marking whether a school is a magnet or offers a magnet program (1 = magnet program, 0 = not; NULL = unknown).</description>
        -- <example>0</example>
    Latitude REAL NULL,
        -- <description>Latitude of the school's physical location (degrees north of the equator); used to geolocate the school. Approximately 12,863 of 17,686 records are populated (≈72.7%); values range ~32.55°–44.22° with mean ≈36.01°.</description>
        -- <example>37.658</example>
    Longitude REAL NULL,
        -- <description>Longitude — east–west geographic coordinate of the school location in decimal degrees (negative = degrees west of the prime meridian). Many records are missing (≈27% null); recorded values range roughly from −124.285 to −83.781 (some values appear outside typical California longitudes).</description>
        -- <example>-122.097</example>
    AdmFName1 TEXT NULL,
        -- <description>Administrator's first name (superintendent or principal) for the school — a personal given name. Many records are blank (about 34% missing); there are 2,327 distinct non-empty names (examples: David, Michael, John, Julie, Susan).</description>
        -- <example>'L Karen'</example>
    AdmLName1 TEXT NULL,
        -- <description>Administrator's last name (principal or superintendent) for the school — last name of the primary administrator when provided; many records are blank for closed or non-reporting schools.</description>
        -- <example>'Monroe'</example>
    AdmEmail1 TEXT NULL,
        -- <description>Primary administrator email address — the superintendent’s or principal’s contact email; typically provided for active or pending schools and often blank for closed/retired records.</description>
        -- <example>'lkmonroe@acoe.org'</example>
    AdmFName2 TEXT NULL,
        -- <description>Second administrator first name — first name of the second-listed school administrator (often empty; frequently duplicates AdmFName1).</description>
        -- <example>'Sau-Lim (Lance)'</example>
    AdmLName2 TEXT NULL,
        -- <description>Second administrator's last name — the last name of the school's second listed administrator (secondary administrator). Often empty: most records are NULL; when populated there are many distinct surnames and only a few exact duplicates of AdmLName1.</description>
        -- <example>'Tsang'</example>
    AdmEmail2 TEXT NULL,
        -- <description>Second administrator contact email — the email address for the school's second listed administrator (provided for some schools).</description>
        -- <example>'stsang@unityhigh.org'</example>
    LastUpdate DATE NOT NULL
        -- <description>Record last update — when the school's row was most recently modified.</description>
        -- <example>'2015-06-23'</example>
);
```