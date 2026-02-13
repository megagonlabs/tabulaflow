```sql
-- Database: california_schools

/*
Table: frpm
Rows: 9986
Sample rows:
| CDSCode        | Academic Year   | County Code   | District Code   | School Code   | County Name   | District Name                      | School Name                                   | District Type                    | School Type                 | Educational Option Type   | NSLP Provision Status   | Charter School (Y/N)   | Charter School Number   | Charter Funding Type   | IRC   | Low Grade   | High Grade   | Enrollment (K-12)   | Free Meal Count (K-12)   | Percent (%) Eligible Free (K-12)   | FRPM Count (K-12)   | Percent (%) Eligible FRPM (K-12)   | Enrollment (Ages 5-17)   | Free Meal Count (Ages 5-17)   | Percent (%) Eligible Free (Ages 5-17)   | FRPM Count (Ages 5-17)   | Percent (%) Eligible FRPM (Ages 5-17)   | 2013-14 CALPADS Fall 1 Certification Status   |
|----------------|-----------------|---------------|-----------------|---------------|---------------|------------------------------------|-----------------------------------------------|----------------------------------|-----------------------------|---------------------------|-------------------------|------------------------|-------------------------|------------------------|-------|-------------|--------------|---------------------|--------------------------|------------------------------------|---------------------|------------------------------------|--------------------------|-------------------------------|-----------------------------------------|--------------------------|-----------------------------------------|-----------------------------------------------|
| 01100170109835 | 2014-2015       | 01            | 10017           | 0109835       | Alameda       | Alameda County Office of Education | FAME Public Charter                           | County Office of Education (COE) | K-12 Schools (Public)       | Traditional               | [NULL]                  | 1                      | 0728                    | Directly funded        | 1     | K           | 12           | 1087.0              | 565.0                    | 0.519779208831647                  | 715.0               | 0.657773689052438                  | 1070.0                   | 553.0                         | 0.516822429906542                       | 702.0                    | 0.65607476635514                        | 1                                             |
| 01100170112607 | 2014-2015       | 01            | 10017           | 0112607       | Alameda       | Alameda County Office of Education | Envision Academy for Arts & Technology        | County Office of Education (COE) | High Schools (Public)       | Traditional               | [NULL]                  | 1                      | 0811                    | Directly funded        | 1     | 9           | 12           | 395.0               | 186.0                    | 0.470886075949367                  | 186.0               | 0.470886075949367                  | 376.0                    | 182.0                         | 0.484042553191489                       | 182.0                    | 0.484042553191489                       | 1                                             |
| 01100170118489 | 2014-2015       | 01            | 10017           | 0118489       | Alameda       | Alameda County Office of Education | Aspire California College Preparatory Academy | County Office of Education (COE) | High Schools (Public)       | Traditional               | [NULL]                  | 1                      | 1049                    | Directly funded        | 1     | 9           | 12           | 244.0               | 134.0                    | 0.549180327868853                  | 175.0               | 0.717213114754098                  | 230.0                    | 128.0                         | 0.556521739130435                       | 168.0                    | 0.730434782608696                       | 1                                             |
| 01100170123968 | 2014-2015       | 01            | 10017           | 0123968       | Alameda       | Alameda County Office of Education | Community School for Creative Education       | County Office of Education (COE) | Elementary Schools (Public) | Traditional               | Breakfast Provision 2   | 1                      | 1284                    | Directly funded        | 1     | K           | 8            | 191.0               | 113.0                    | 0.591623036649215                  | 139.0               | 0.727748691099476                  | 190.0                    | 113.0                         | 0.594736842105263                       | 139.0                    | 0.731578947368421                       | 1                                             |
| 01100170124172 | 2014-2015       | 01            | 10017           | 0124172       | Alameda       | Alameda County Office of Education | Yu Ming Charter                               | County Office of Education (COE) | Elementary Schools (Public) | Traditional               | [NULL]                  | 1                      | 1296                    | Directly funded        | 1     | K           | 8            | 257.0               | 14.0                     | 0.0544747081712062                 | 21.0                | 0.0817120622568093                 | 257.0                    | 14.0                          | 0.0544747081712062                      | 21.0                     | 0.0817120622568093                      | 1                                             |
| ...            | ...             | ...           | ...             | ...           | ...           | ...                                | ...                                           | ...                              | ...                         | ...                       | ...                     | ...                    | ...                     | ...                    | ...   | ...         | ...          | ...                 | ...                      | ...                                | ...                 | ...                                | ...                      | ...                           | ...                                     | ...                      | ...                                     | ...                                           |
*/
CREATE TABLE frpm (
    CDSCode TEXT NOT NULL PRIMARY KEY,
        -- <description>School CDS code — the California Department of Education (CDE) school identifier for this FRPM row; uniquely identifies the school (table primary key) and links to schools.CDSCode and satscores.cds.</description>
        -- <example>'01100170109835'</example>
        -- <fk> -> schools.CDSCode</fk>
        -- <fk> -> satscores.cds</fk>
    "Academic Year" TEXT NOT NULL,
        -- <description>Academic year for which the FRPM record applies (school-year span, e.g., '2014-2015').</description>
        -- <values>{'2014-2015'}</values>
    "County Code" TEXT NOT NULL,
        -- <description>County code identifying the county where the school/district is located; used to link the record to County Name or other county-level data.</description>
        -- <example>'01'</example>
    "District Code" INTEGER NOT NULL,
        -- <description>School district identifier — the local district code that associates a school record with its district (example: 10017).</description>
        -- <example>10017</example>
    "School Code" TEXT NOT NULL,
        -- <description>School code — the district-assigned school identifier (local school number) commonly used together with County Code and District Code to identify a specific school (example: '0109835').</description>
        -- <example>'0109835'</example>
    "County Name" TEXT NOT NULL,
        -- <description>County name for the school's district (e.g., Alameda, Tuolumne).</description>
        -- <example>'Alameda'</example>
    "District Name" TEXT NOT NULL,
        -- <description>School district name — the official name of the district that oversees or administers the school (e.g., Alameda County Office of Education).</description>
        -- <example>'Alameda County Office of Education'</example>
    "School Name" TEXT NOT NULL,
        -- <description>School name — the official name of the school as reported in the free and reduced‑price meals dataset (e.g., Neal Dow Elementary, Valley Oaks Charter, FAME Public Charter).</description>
        -- <example>'FAME Public Charter'</example>
    "District Type" TEXT NOT NULL,
        -- <description>Administrative district category identifying the type of district that oversees the school; used to group schools by their administrative authority.</description>
        -- <values>{'County Office of Education (COE)', 'Elementary School District', 'High School District', 'Non-School Locations', 'State Board of Education', 'State Special Schools', 'Statewide Benefit Charter', 'Unified School District'}</values>
    "School Type" TEXT NULL,
        -- <description>School type — categorical label describing the school's instructional or organizational category (e.g., elementary, middle/intermediate, high school, K–12, preschool, continuation, special education).</description>
        -- <values>{'Alternative Schools of Choice', 'Continuation High Schools', 'County Community', 'District Community Day Schools', 'Elemen Schools In 1 School Dist. (Public)', 'Elementary Schools (Public)', 'High Schools (Public)', 'High Schools In 1 School Dist. (Public)', 'Intermediate/Middle Schools (Public)', 'Junior High Schools (Public)', 'Juvenile Court Schools', 'K-12 Schools (Public)', 'Opportunity Schools', 'Preschool', 'Special Education Schools (Public)', 'State Special Schools', 'Youth Authority Facilities'}</values>
    "Educational Option Type" TEXT NULL,
        -- <description>Educational option offered by the school — a short categorical label indicating the type of program or instructional setting (for example: Traditional, Juvenile Court School, Youth Authority School).</description>
        -- <values>{'Alternative School of Choice', 'Community Day School', 'Continuation School', 'County Community School', 'District Special Education Consortia School', 'Home and Hospital', 'Juvenile Court School', 'Opportunity School', 'Special Education School', 'State Special School', 'Traditional', 'Youth Authority School'}</values>
    "NSLP Provision Status" TEXT NULL,
        -- <description>NSLP provision model for the school, indicating which National School Lunch Program provisioning approach is used to determine meal reimbursement and eligibility.</description>
        -- <values>{'Breakfast Provision 2', 'CEP', 'Lunch Provision 2', 'Multiple Provision Types', 'Provision 1', 'Provision 2', 'Provision 3'}</values>
    "Charter School (Y/N)" INTEGER NULL,
        -- <description>Charter status indicator for the school (Y/N) — flags whether the school is a charter school.</description>
        -- <example>1</example>
    "Charter School Number" TEXT NULL,
        -- <description>Charter school identification number — the state-assigned charter number for charter schools (typically a 4‑digit code); null for non‑charter schools.</description>
        -- <example>'0728'</example>
    "Charter Funding Type" TEXT NULL,
        -- <description>Charter school funding arrangement — indicates whether a charter is directly funded, locally funded, or not in the California Schools funding model.</description>
        -- <values>{'Directly funded', 'Locally funded', 'Not in CS funding model'}</values>
    "Low Grade" TEXT NOT NULL,
        -- <description>Lowest grade level served by the school (e.g., K for kindergarten, P for preschool).</description>
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P'}</values>
    "High Grade" TEXT NOT NULL,
        -- <description>Highest grade level served by the school (as reported in the free and reduced-price meals dataset).</description>
        -- <values>{'1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P', 'Post Secondary'}</values>
    "Enrollment (K-12)" REAL NOT NULL,
        -- <description>K–12 enrollment count for the school (students in grades 1–12); used as the denominator when calculating free- and FRPM-eligibility rates.</description>
        -- <example>1087.000</example>
    "Free Meal Count (K-12)" REAL NULL,
        -- <description>Count of students eligible for free meals in grades K–12, used to compute the eligible-free rate (Free Meal Count ÷ Enrollment).</description>
        -- <example>565.000</example>
    "Percent (%) Eligible Free (K-12)" REAL NULL,
        -- <description>Proportion of K–12 students eligible for free meals (Free Meal Count (K-12) divided by Enrollment (K-12)).</description>
        -- <example>0.520</example>
    "FRPM Count (K-12)" REAL NULL,
        -- <description>Count of K–12 students eligible for free or reduced‑price meals, used as the numerator for the corresponding FRPM percentage.</description>
        -- <example>715.000</example>
    "Percent (%) Eligible FRPM (K-12)" REAL NULL,
        -- <description>Share of K–12 students eligible for free or reduced‑price meals (FRPM), expressed as the proportion of enrolled K–12 students.</description>
        -- <example>0.658</example>
    "Enrollment (Ages 5-17)" REAL NULL,
        -- <description>Count of students enrolled at the school aged 5–17 (used as the denominator for calculating free and free-or-reduced-price-meal eligibility rates for ages 5–17).</description>
        -- <example>1070.000</example>
    "Free Meal Count (Ages 5-17)" REAL NULL,
        -- <description>Count of students ages 5–17 eligible for free (no‑cost) school meals; used to compute the eligible-free rate (Free Meal Count ÷ Enrollment).</description>
        -- <example>553.000</example>
    "Percent (%) Eligible Free (Ages 5-17)" REAL NULL,
        -- <description>Proportion of students ages 5–17 eligible for free meals — calculated as Free Meal Count (Ages 5–17) divided by Enrollment (Ages 5–17).</description>
        -- <example>0.517</example>
    "FRPM Count (Ages 5-17)" REAL NULL,
        -- <description>Count of students aged 5–17 at the school who are eligible for free or reduced-price meals (FRPM).</description>
        -- <example>702.000</example>
    "Percent (%) Eligible FRPM (Ages 5-17)" REAL NULL,
        -- <description>Share of students ages 5–17 eligible for free or reduced‑price meals (FRPM), given as a decimal proportion of enrolled students in that age range (e.g., 0.656 ≈ 65.6%).</description>
        -- <example>0.656</example>
    "2013-14 CALPADS Fall 1 Certification Status" INTEGER NOT NULL,
        -- <description>CALPADS Fall 1 (2013–14) certification status for the school's FRPM record — an indicator coded as status values denoting whether the 2013–14 Fall 1 FRPM submission was certified.</description>
        -- <example>1</example>
    FOREIGN KEY (CDSCode) REFERENCES schools(CDSCode),
    FOREIGN KEY (CDSCode) REFERENCES satscores(cds)
);

/*
Table: satscores
Rows: 2269
Sample rows:
| cds           | rtype   | sname                                         | dname                              | cname   | enroll12   | NumTstTakr   | AvgScrRead   | AvgScrMath   | AvgScrWrite   | NumGE1500   |
|---------------|---------|-----------------------------------------------|------------------------------------|---------|------------|--------------|--------------|--------------|---------------|-------------|
| 1100170000000 | D       | [NULL]                                        | Alameda County Office of Education | Alameda | 398        | 88           | 418.0        | 418.0        | 417.0         | 14.0        |
| 1100170109835 | S       | FAME Public Charter                           | Alameda County Office of Education | Alameda | 62         | 17           | 503.0        | 546.0        | 505.0         | 9.0         |
| 1100170112607 | S       | Envision Academy for Arts & Technology        | Alameda County Office of Education | Alameda | 75         | 71           | 397.0        | 387.0        | 395.0         | 5.0         |
| 1100170118489 | S       | Aspire California College Preparatory Academy | Alameda County Office of Education | Alameda | 61         | 0            | [NULL]       | [NULL]       | [NULL]        | [NULL]      |
| 1611190000000 | D       | [NULL]                                        | Alameda Unified                    | Alameda | 922        | 544          | 521.0        | 546.0        | 519.0         | 333.0       |
| ...           | ...     | ...                                           | ...                                | ...     | ...        | ...          | ...          | ...          | ...           | ...         |
*/
CREATE TABLE satscores (
    cds TEXT NOT NULL PRIMARY KEY,
        -- <description>California Department of Education (CDS) school/district identifier — the unique CDS code used to identify and link a district or school (matches schools.CDSCode).</description>
        -- <example>'10101080000000'</example>
        -- <fk> -> schools.CDSCode</fk>
    sname TEXT NULL,
        -- <description>School name — the reported school-level name associated with the SAT score record; often NULL for district-level (rtype = 'D') summary rows.</description>
        -- <example>'FAME Public Charter'</example>
    dname TEXT NOT NULL,
        -- <description>District name — the name of the school district associated with the SAT score record (for example, 'Alameda County Office of Education').</description>
        -- <example>'Alameda County Office of Education'</example>
    cname TEXT NOT NULL,
        -- <description>County name where the school is located.</description>
        -- <example>'Alameda'</example>
    enroll12 INTEGER NOT NULL,
        -- <description>Enrollment in grades 1–12 — total number of students enrolled in grades 1 through 12 at the school for the reported year, used to contextualize SAT participation and test-taker rates.</description>
        -- <example>398</example>
    NumTstTakr INTEGER NOT NULL,
        -- <description>Count of students who took the SAT for the record (school or district); the raw number of test takers used to compute participation rates and to weight average scores.</description>
        -- <example>88</example>
    AvgScrRead INTEGER NULL,
        -- <description>School-level average SAT Reading score (mean of the Reading-section scores of students who took the SAT at that school).</description>
        -- <example>418</example>
    AvgScrMath INTEGER NULL,
        -- <description>Average SAT Math score for the school's test takers</description>
        -- <example>418</example>
    AvgScrWrite INTEGER NULL,
        -- <description>Average SAT Writing score for the school’s test takers — the mean Writing-section SAT score among students from the school (null when no scores are reported).</description>
        -- <example>417</example>
    NumGE1500 INTEGER NULL,
        -- <description>Count of test takers whose total SAT score is greater than or equal to 1500.</description>
        -- <example>14</example>
    FOREIGN KEY (cds) REFERENCES schools(CDSCode)
);

/*
Table: schools
Rows: 17686
Sample rows:
| CDSCode        | NCESDist   | NCESSchool   | StatusType   | County   | District                           | School                                        | Street                           | StreetAbr                     | City     | Zip        | State   | MailStreet                       | MailStrAbr                    | MailCity   | MailZip    | MailState   | Phone          | Ext    | Website                                     | OpenDate   | ClosedDate   | Charter   | CharterNum   | FundingType     | DOC   | DOCType                          | SOC    | SOCType                     | EdOpsCode   | EdOpsName   | EILCode   | EILName                     | GSoffered   | GSserved   | Virtual   | Magnet   | Latitude   | Longitude   | AdmFName1   | AdmLName1   | AdmEmail1                                         | AdmFName2   | AdmLName2   | AdmEmail2   | AdmFName3   | AdmLName3   | AdmEmail3   | LastUpdate   |
|----------------|------------|--------------|--------------|----------|------------------------------------|-----------------------------------------------|----------------------------------|-------------------------------|----------|------------|---------|----------------------------------|-------------------------------|------------|------------|-------------|----------------|--------|---------------------------------------------|------------|--------------|-----------|--------------|-----------------|-------|----------------------------------|--------|-----------------------------|-------------|-------------|-----------|-----------------------------|-------------|------------|-----------|----------|------------|-------------|-------------|-------------|---------------------------------------------------|-------------|-------------|-------------|-------------|-------------|-------------|--------------|
| 01100170000000 | 0691051    | [NULL]       | Active       | Alameda  | Alameda County Office of Education | [NULL]                                        | 313 West Winton Avenue           | 313 West Winton Ave.          | Hayward  | 94544-1136 | CA      | 313 West Winton Avenue           | 313 West Winton Ave.          | Hayward    | 94544-1136 | CA          | (510) 887-0152 | [NULL] | www.acoe.org                                | [NULL]     | [NULL]       | [NULL]    | [NULL]       | [NULL]          | 00    | County Office of Education (COE) | [NULL] | [NULL]                      | [NULL]      | [NULL]      | [NULL]    | [NULL]                      | [NULL]      | [NULL]     | [NULL]    | [NULL]   | 37.658212  | -122.09713  | L Karen     | Monroe      | lkmonroe@acoe.org                                 | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | 2015-06-23   |
| 01100170109835 | 0691051    | 10546        | Closed       | Alameda  | Alameda County Office of Education | FAME Public Charter                           | 39899 Balentine Drive, Suite 335 | 39899 Balentine Dr., Ste. 335 | Newark   | 94560-5359 | CA      | 39899 Balentine Drive, Suite 335 | 39899 Balentine Dr., Ste. 335 | Newark     | 94560-5359 | CA          | [NULL]         | [NULL] | [NULL]                                      | 2005-08-29 | 2015-07-31   | 1.0       | 0728         | Directly funded | 00    | County Office of Education (COE) | 65     | K-12 Schools (Public)       | TRAD        | Traditional | ELEMHIGH  | Elementary-High Combination | K-12        | K-12       | P         | 0.0      | 37.521436  | -121.99391  | [NULL]      | [NULL]      | [NULL]                                            | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | 2015-09-01   |
| 01100170112607 | 0691051    | 10947        | Active       | Alameda  | Alameda County Office of Education | Envision Academy for Arts & Technology        | 1515 Webster Street              | 1515 Webster St.              | Oakland  | 94612-3355 | CA      | 1515 Webster Street              | 1515 Webster St.              | Oakland    | 94612      | CA          | (510) 596-8901 | [NULL] | www.envisionacademy.org/                    | 2006-08-28 | [NULL]       | 1.0       | 0811         | Directly funded | 00    | County Office of Education (COE) | 66     | High Schools (Public)       | TRAD        | Traditional | HS        | High School                 | 9-12        | 9-12       | N         | 0.0      | 37.80452   | -122.26815  | Laura       | Robell      | laura@envisionacademy.org                         | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | 2015-06-18   |
| 01100170118489 | 0691051    | 12283        | Closed       | Alameda  | Alameda County Office of Education | Aspire California College Preparatory Academy | 2125 Jefferson Avenue            | 2125 Jefferson Ave.           | Berkeley | 94703-1414 | CA      | 1001 22nd Avenue, Suite 100      | 1001 22nd Ave., Ste. 100      | Oakland    | 94606      | CA          | [NULL]         | [NULL] | www.aspirepublicschools.org                 | 2008-08-21 | 2015-06-30   | 1.0       | 1049         | Directly funded | 00    | County Office of Education (COE) | 66     | High Schools (Public)       | TRAD        | Traditional | HS        | High School                 | 9-12        | 9-12       | N         | 0.0      | 37.868991  | -122.27844  | [NULL]      | [NULL]      | [NULL]                                            | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | 2015-07-01   |
| 01100170123968 | 0691051    | 12844        | Active       | Alameda  | Alameda County Office of Education | Community School for Creative Education       | 2111 International Boulevard     | 2111 International Blvd.      | Oakland  | 94606-4903 | CA      | 2111 International Boulevard     | 2111 International Blvd.      | Oakland    | 94606-4903 | CA          | (510) 686-4131 | [NULL] | www.communityschoolforcreativeeducation.org | 2011-08-22 | [NULL]       | 1.0       | 1284         | Directly funded | 00    | County Office of Education (COE) | 60     | Elementary Schools (Public) | TRAD        | Traditional | ELEM      | Elementary                  | K-8         | K-7        | N         | 0.0      | 37.784648  | -122.23863  | Clifford    | Thompson    | cliffordt@communityschoolforcreativeeducation.org | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | [NULL]      | 2016-07-18   |
| ...            | ...        | ...          | ...          | ...      | ...                                | ...                                           | ...                              | ...                           | ...      | ...        | ...     | ...                              | ...                           | ...        | ...        | ...         | ...            | ...    | ...                                         | ...        | ...          | ...       | ...          | ...             | ...   | ...                              | ...    | ...                         | ...         | ...         | ...       | ...                         | ...         | ...        | ...       | ...      | ...        | ...         | ...         | ...         | ...                                               | ...         | ...         | ...         | ...         | ...         | ...         | ...          |
*/
CREATE TABLE schools (
    CDSCode TEXT NOT NULL PRIMARY KEY,
        -- <description>School CDS code — the state's canonical school identifier (County+District+School) used to link school records across datasets.</description>
        -- <example>'01100170000000'</example>
    NCESDist TEXT NULL,
        -- <description>7-digit NCES school-district identifier — a National Center for Education Statistics code where the first two digits indicate the state and the last five identify the district.</description>
        -- <example>'0691051'</example>
    NCESSchool TEXT NULL,
        -- <description>NCES school identification number — a five-digit school ID that, when combined with NCESDist, produces the unique 12‑digit NCES identifier for the school.</description>
        -- <example>'10546'</example>
    StatusType TEXT NOT NULL,
        -- <description>Operational status of the district or school, indicating whether the entity is active, closed, merged, or pending.</description>
        -- <values>{'Active', 'Closed', 'Merged', 'Pending'}</values>
    County TEXT NOT NULL,
        -- <description>County name — the county in which the school is located (used for geographic or administrative grouping).</description>
        -- <example>'Alameda'</example>
    District TEXT NOT NULL,
        -- <description>School district name — the official name of the school district that administers or oversees the school (e.g., Winship‑Robbins, Paso Robles Joint Union High, Firebaugh‑Las Deltas Unified).</description>
        -- <example>'Alameda County Office of Education'</example>
    School TEXT NULL,
        -- <description>School name — the official public name of the school as recorded in the state dataset (for example, 'Big Bear Elementary', 'Roseland Charter').</description>
        -- <example>'FAME Public Charter'</example>
    Street TEXT NULL,
        -- <description>Street address of the school’s physical location; may be empty for closed or retired schools.</description>
        -- <example>'313 West Winton Avenue'</example>
    StreetAbr TEXT NULL,
        -- <description>Abbreviated street address for the school’s physical location (e.g., '313 West Winton Ave.'). Some records—particularly closed or retired schools—may be missing this value.</description>
        -- <example>'313 West Winton Ave.'</example>
    City TEXT NULL,
        -- <description>City of the school's physical location (name of the city where the school is located; e.g., Rancho Santa Fe, Duarte, Pleasanton).</description>
        -- <example>'Hayward'</example>
    Zip TEXT NULL,
        -- <description>School ZIP code (postal code) for the school's address, typically a 5-digit or 9-digit ZIP+4 value (e.g., 95626-9217).</description>
        -- <example>'94544-1136'</example>
    State TEXT NULL,
        -- <description>State in which the school is located.</description>
        -- <values>{'CA'}</values>
    MailStreet TEXT NULL,
        -- <description>Unabbreviated mailing street address for the school’s mailing location (full street line, e.g., house number, street name, suite).</description>
        -- <example>'313 West Winton Avenue'</example>
    MailStrAbr TEXT NULL,
        -- <description>Abbreviated mailing street address for the school’s mailing location — when a mailing street is not provided this field is populated from StreetAbr.</description>
        -- <example>'313 West Winton Ave.'</example>
    MailCity TEXT NULL,
        -- <description>Mailing city for the school’s mailing address — when a separate mailing city is not provided this field is populated from the school’s City value; many records do not have a distinct mailing city.</description>
        -- <example>'Hayward'</example>
    MailZip TEXT NULL,
        -- <description>Mailing-address ZIP code (may include 9‑digit ZIP+4); if a school did not provide a mailing ZIP, this field was filled from the primary Zip column.</description>
        -- <example>'94544-1136'</example>
    MailState TEXT NULL,
        -- <description>Mailing state for the school's mailing address; if MailState is blank, it has been populated with the school's State value for convenience.</description>
        -- <values>{'CA'}</values>
    Phone TEXT NULL,
        -- <description>School main phone number (primary contact), stored as free-form text — may include digits, spaces, parentheses, hyphens and extensions; sometimes blank for closed or unreported schools.</description>
        -- <example>'(510) 887-0152'</example>
    Ext TEXT NULL,
        -- <description>Phone extension for the school's main contact — internal office extension paired with the Phone number.</description>
        -- <example>'130'</example>
    Website TEXT NULL,
        -- <description>Website URL for the school, district, or administrative authority (when provided).</description>
        -- <example>'www.acoe.org'</example>
    OpenDate DATE NULL,
        -- <description>School open date — the calendar date the school first opened (may be NULL). Example values: 1962-07-01, 2015-08-20.</description>
        -- <example>'2005-08-29'</example>
    ClosedDate DATE NULL,
        -- <description>School closure date — the date the school closed (NULL if the school is still open).</description>
        -- <example>'2015-07-31'</example>
    Charter INTEGER NULL,
        -- <description>Charter school indicator — marks whether the school is a charter (coded 1 = charter; 0 or NULL = not a charter or not provided).</description>
        -- <example>1</example>
    CharterNum TEXT NULL,
        -- <description>Charter school number — the four‑digit identifier assigned to a charter school (e.g., 1766).</description>
        -- <example>'0728'</example>
    FundingType TEXT NULL,
        -- <description>Charter school funding model for the school — indicates, when applicable, how a charter school is funded under California’s charter funding system (may be null for non‑charter schools).</description>
        -- <values>{'Directly funded', 'Locally funded', 'Not in CS funding model'}</values>
    DOC TEXT NOT NULL,
        -- <description>District ownership code — a short code that identifies the category of the school's administrative authority (used to classify the administrative owner of a district or school). Paired with DOCType for the human‑readable category name.</description>
        -- <values>{'00', '02', '03', '31', '34', '42', '52', '54', '56', '58', '98', '99'}</values>
    DOCType TEXT NOT NULL,
        -- <description>District ownership type — textual label describing the District Ownership Code (DOC), indicating the administrative authority category for the school or district.</description>
        -- <values>{'Administration Only', 'Community College District', 'County Office of Education (COE)', 'Elementary School District', 'High School District', 'Joint Powers Authority (JPA)', 'Non-School Locations', 'Regional Occupation Center/Program (ROC/P)', 'State Board of Education', 'State Special Schools', 'Statewide Benefit Charter', 'Unified School District'}</values>
    SOC TEXT NULL,
        -- <description>School ownership code identifying the school's category — a short code used to classify the type/ownership of the school (maps to categories such as preschool, elementary, intermediate/middle, high school, K–12, special education, youth authority facilities, and other county/district program types).</description>
        -- <values>{'08', '09', '10', '11', '13', '14', '15', '31', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '70', '98'}</values>
    SOCType TEXT NULL,
        -- <description>School ownership/type label — the human-readable description of the school's ownership or operational category that corresponds to the SOC code, used to describe the kind of school (e.g., elementary, high school, county community, state special school).</description>
        -- <values>{'Adult Education Centers', 'Alternative Schools of Choice', 'Continuation High Schools', 'County Community', 'District Community Day Schools', 'Elemen Schools In 1 School Dist. (Public)', 'Elementary Schools (Public)', 'High Schools (Public)', 'High Schools In 1 School Dist. (Public)', 'Intermediate/Middle Schools (Public)', 'Junior High Schools (Public)', 'Juvenile Court Schools', 'K-12 Schools (Public)', 'Opportunity Schools', 'Other County Or District Programs', 'Preschool', 'ROC/ROP', 'Special Education Schools (Public)', 'State Special Schools', 'Youth Authority Facilities'}</values>
    EdOpsCode TEXT NULL,
        -- <description>Education-option code — a short code that identifies the type of educational option or program a school offers (see EdOpsName for the full descriptive name).</description>
        -- <values>{'ALTSOC', 'COMM', 'COMMDAY', 'CON', 'HOMHOS', 'JUV', 'OPP', 'ROP', 'SPEC', 'SPECON', 'SSS', 'TRAD', 'YTH'}</values>
    EdOpsName TEXT NULL,
        -- <description>Educational option name — the long-form label describing the educational option or program the school offers (a descriptive name for the EdOpsCode).</description>
        -- <values>{'Alternative School of Choice', 'Community Day School', 'Continuation School', 'County Community School', 'District Special Education Consortia School', 'Home and Hospital', 'Juvenile Court School', 'Opportunity School', 'ROP', 'Special Education School', 'State Special School', 'Traditional', 'Youth Authority School'}</values>
    EILCode TEXT NULL,
        -- <description>Educational instruction level code — short code indicating the institution’s instruction level (the grade-span category the school serves).</description>
        -- <values>{'A', 'ELEM', 'ELEMHIGH', 'HS', 'INTMIDJR', 'PS', 'UG'}</values>
    EILName TEXT NULL,
        -- <description>Educational instruction level name — long-form label describing the grade range the institution serves.</description>
        -- <values>{'Adult', 'Elementary', 'Elementary-High Combination', 'High School', 'Intermediate/Middle/Junior High', 'Preschool', 'Ungraded'}</values>
    GSoffered TEXT NULL,
        -- <description>Grade span offered — the lowest and highest grades a school or administrative authority provides or supports; may differ from the grade span actually served (e.g., 'K-12').</description>
        -- <example>'K-12'</example>
    GSserved TEXT NULL,
        -- <description>Grade span served — the lowest through highest grade levels with enrolled students, as reported in the certified CALPADS Fall 1 collection; reflects only K–12 enrollment and may differ from the grade span offered.</description>
        -- <example>'K-12'</example>
    Virtual TEXT NULL,
        -- <description>Type of virtual instruction offered by the school — indicates whether instruction is provided virtually (students and teachers separated by time and/or location, interacting via computers or telecommunications).</description>
        -- <values>{'F', 'N', 'P'}</values>
    Magnet INTEGER NULL,
        -- <description>Magnet school indicator — identifies whether the school is a magnet school or offers a magnet program.</description>
        -- <example>0</example>
    Latitude REAL NULL,
        -- <description>School geographic latitude in decimal degrees (positive = north), used with Longitude to geolocate the school.</description>
        -- <example>37.658</example>
    Longitude REAL NULL,
        -- <description>Longitude of the school's geographic location (degrees east of the Prime Meridian; negative values indicate locations west of Greenwich).</description>
        -- <example>-122.097</example>
    AdmFName1 TEXT NULL,
        -- <description>Administrator's first name — the superintendent's or principal's first name; provided only for active or pending districts/schools when administrator contact info is available.</description>
        -- <example>'L Karen'</example>
    AdmLName1 TEXT NULL,
        -- <description>Administrator last name for the school's primary administrator (superintendent or principal); typically populated only for active or pending schools.</description>
        -- <example>'Monroe'</example>
    AdmEmail1 TEXT NULL,
        -- <description>Administrator's email address for the school's primary administrator (superintendent or principal); typically provided only for active or pending schools and may be null for closed or unreported records.</description>
        -- <example>'lkmonroe@acoe.org'</example>
    AdmFName2 TEXT NULL,
        -- <description>Second administrator's first name — the given name of the school's second listed administrator (may duplicate AdmFName1).</description>
        -- <example>'Sau-Lim (Lance)'</example>
    AdmLName2 TEXT NULL,
        -- <description>Administrator last name (second contact) — the family/surname of the school's second listed administrator (pairs with AdmFName2).</description>
        -- <example>'Tsang'</example>
    AdmEmail2 TEXT NULL,
        -- <description>Email address of the school's second-listed administrator (secondary contact).</description>
        -- <example>'stsang@unityhigh.org'</example>
    LastUpdate DATE NOT NULL
        -- <description>Record last-update date — the date when this schools table record was most recently updated.</description>
        -- <example>'2015-06-23'</example>
);
```