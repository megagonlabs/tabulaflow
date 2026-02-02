```sql
-- Database: california_schools

-- Table: frpm (9986 rows)
CREATE TABLE frpm (
    CDSCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'01100170109835'</example>
        -- <fk> -> schools.CDSCode</fk>
    "Academic Year" TEXT NULL,
        -- <values>{'2014-2015'}</values>
    "County Code" TEXT NULL,
        -- <example>'01'</example>
    "District Code" INTEGER NULL,
        -- <example>10017</example>
    "School Code" TEXT NULL,
        -- <example>'0109835'</example>
    "County Name" TEXT NULL,
        -- <example>'Alameda'</example>
    "District Name" TEXT NULL,
        -- <example>'Alameda County Office of Education'</example>
    "School Name" TEXT NULL,
        -- <example>'FAME Public Charter'</example>
    "District Type" TEXT NULL,
        -- <values>{'County Office of Education (COE)', 'Elementary School District', 'High School District', 'Non-School Locations', 'State Board of Education', 'State Special Schools', 'Statewide Benefit Charter', 'Unified School District'}</values>
    "School Type" TEXT NULL,
        -- <values>{'Alternative Schools of Choice', 'Continuation High Schools', 'County Community', 'District Community Day Schools', 'Elemen Schools In 1 School Dist. (Public)', 'Elementary Schools (Public)', 'High Schools (Public)', 'High Schools In 1 School Dist. (Public)', 'Intermediate/Middle Schools (Public)', 'Junior High Schools (Public)', 'Juvenile Court Schools', 'K-12 Schools (Public)', 'Opportunity Schools', 'Preschool', 'Special Education Schools (Public)', 'State Special Schools', 'Youth Authority Facilities'}</values>
    "Educational Option Type" TEXT NULL,
        -- <values>{'Alternative School of Choice', 'Community Day School', 'Continuation School', 'County Community School', 'District Special Education Consortia School', 'Home and Hospital', 'Juvenile Court School', 'Opportunity School', 'Special Education School', 'State Special School', 'Traditional', 'Youth Authority School'}</values>
    "NSLP Provision Status" TEXT NULL,
        -- <values>{'Breakfast Provision 2', 'CEP', 'Lunch Provision 2', 'Multiple Provision Types', 'Provision 1', 'Provision 2', 'Provision 3'}</values>
    "Charter School (Y/N)" INTEGER NULL,
        -- <example>1</example>
    "Charter School Number" TEXT NULL,
        -- <example>'0728'</example>
    "Charter Funding Type" TEXT NULL,
        -- <values>{'Directly funded', 'Locally funded', 'Not in CS funding model'}</values>
    IRC INTEGER NULL,
        -- <example>1</example>
    "Low Grade" TEXT NULL,
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P'}</values>
    "High Grade" TEXT NULL,
        -- <values>{'1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P', 'Post Secondary'}</values>
    "Enrollment (K-12)" REAL NULL,
        -- <example>1087.000</example>
    "Free Meal Count (K-12)" REAL NULL,
        -- <example>565.000</example>
    "Percent (%) Eligible Free (K-12)" REAL NULL,
        -- <example>0.520</example>
    "FRPM Count (K-12)" REAL NULL,
        -- <example>715.000</example>
    "Percent (%) Eligible FRPM (K-12)" REAL NULL,
        -- <example>0.658</example>
    "Enrollment (Ages 5-17)" REAL NULL,
        -- <example>1070.000</example>
    "Free Meal Count (Ages 5-17)" REAL NULL,
        -- <example>553.000</example>
    "Percent (%) Eligible Free (Ages 5-17)" REAL NULL,
        -- <example>0.517</example>
    "FRPM Count (Ages 5-17)" REAL NULL,
        -- <example>702.000</example>
    "Percent (%) Eligible FRPM (Ages 5-17)" REAL NULL,
        -- <example>0.656</example>
    "2013-14 CALPADS Fall 1 Certification Status" INTEGER NULL,
        -- <example>1</example>
    FOREIGN KEY (CDSCode) REFERENCES schools(CDSCode)
);

-- Table: satscores (2269 rows)
CREATE TABLE satscores (
    cds TEXT NOT NULL PRIMARY KEY,
        -- <example>'10101080000000'</example>
        -- <fk> -> schools.CDSCode</fk>
    rtype TEXT NOT NULL,
        -- <values>{'D', 'S'}</values>
    sname TEXT NULL,
        -- <example>'FAME Public Charter'</example>
    dname TEXT NULL,
        -- <example>'Alameda County Office of Education'</example>
    cname TEXT NULL,
        -- <example>'Alameda'</example>
    enroll12 INTEGER NOT NULL,
        -- <example>398</example>
    NumTstTakr INTEGER NOT NULL,
        -- <example>88</example>
    AvgScrRead INTEGER NULL,
        -- <example>418</example>
    AvgScrMath INTEGER NULL,
        -- <example>418</example>
    AvgScrWrite INTEGER NULL,
        -- <example>417</example>
    NumGE1500 INTEGER NULL,
        -- <example>14</example>
    FOREIGN KEY (cds) REFERENCES schools(CDSCode)
);

-- Table: schools (17686 rows)
CREATE TABLE schools (
    CDSCode TEXT NOT NULL PRIMARY KEY,
        -- <example>'01100170000000'</example>
    NCESDist TEXT NULL,
        -- <example>'0691051'</example>
    NCESSchool TEXT NULL,
        -- <example>'10546'</example>
    StatusType TEXT NOT NULL,
        -- <values>{'Active', 'Closed', 'Merged', 'Pending'}</values>
    County TEXT NOT NULL,
        -- <example>'Alameda'</example>
    District TEXT NOT NULL,
        -- <example>'Alameda County Office of Education'</example>
    School TEXT NULL,
        -- <example>'FAME Public Charter'</example>
    Street TEXT NULL,
        -- <example>'313 West Winton Avenue'</example>
    StreetAbr TEXT NULL,
        -- <example>'313 West Winton Ave.'</example>
    City TEXT NULL,
        -- <example>'Hayward'</example>
    Zip TEXT NULL,
        -- <example>'94544-1136'</example>
    State TEXT NULL,
        -- <values>{'CA'}</values>
    MailStreet TEXT NULL,
        -- <example>'313 West Winton Avenue'</example>
    MailStrAbr TEXT NULL,
        -- <example>'313 West Winton Ave.'</example>
    MailCity TEXT NULL,
        -- <example>'Hayward'</example>
    MailZip TEXT NULL,
        -- <example>'94544-1136'</example>
    MailState TEXT NULL,
        -- <values>{'CA'}</values>
    Phone TEXT NULL,
        -- <example>'(510) 887-0152'</example>
    Ext TEXT NULL,
        -- <example>'130'</example>
    Website TEXT NULL,
        -- <example>'www.acoe.org'</example>
    OpenDate DATE NULL,
        -- <example>'2005-08-29'</example>
    ClosedDate DATE NULL,
        -- <example>'2015-07-31'</example>
    Charter INTEGER NULL,
        -- <example>1</example>
    CharterNum TEXT NULL,
        -- <example>'0728'</example>
    FundingType TEXT NULL,
        -- <values>{'Directly funded', 'Locally funded', 'Not in CS funding model'}</values>
    DOC TEXT NOT NULL,
        -- <values>{'00', '02', '03', '31', '34', '42', '52', '54', '56', '58', '98', '99'}</values>
    DOCType TEXT NOT NULL,
        -- <values>{'Administration Only', 'Community College District', 'County Office of Education (COE)', 'Elementary School District', 'High School District', 'Joint Powers Authority (JPA)', 'Non-School Locations', 'Regional Occupation Center/Program (ROC/P)', 'State Board of Education', 'State Special Schools', 'Statewide Benefit Charter', 'Unified School District'}</values>
    SOC TEXT NULL,
        -- <values>{'08', '09', '10', '11', '13', '14', '15', '31', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '70', '98'}</values>
    SOCType TEXT NULL,
        -- <values>{'Adult Education Centers', 'Alternative Schools of Choice', 'Continuation High Schools', 'County Community', 'District Community Day Schools', 'Elemen Schools In 1 School Dist. (Public)', 'Elementary Schools (Public)', 'High Schools (Public)', 'High Schools In 1 School Dist. (Public)', 'Intermediate/Middle Schools (Public)', 'Junior High Schools (Public)', 'Juvenile Court Schools', 'K-12 Schools (Public)', 'Opportunity Schools', 'Other County Or District Programs', 'Preschool', 'ROC/ROP', 'Special Education Schools (Public)', 'State Special Schools', 'Youth Authority Facilities'}</values>
    EdOpsCode TEXT NULL,
        -- <values>{'ALTSOC', 'COMM', 'COMMDAY', 'CON', 'HOMHOS', 'JUV', 'OPP', 'ROP', 'SPEC', 'SPECON', 'SSS', 'TRAD', 'YTH'}</values>
    EdOpsName TEXT NULL,
        -- <values>{'Alternative School of Choice', 'Community Day School', 'Continuation School', 'County Community School', 'District Special Education Consortia School', 'Home and Hospital', 'Juvenile Court School', 'Opportunity School', 'ROP', 'Special Education School', 'State Special School', 'Traditional', 'Youth Authority School'}</values>
    EILCode TEXT NULL,
        -- <values>{'A', 'ELEM', 'ELEMHIGH', 'HS', 'INTMIDJR', 'PS', 'UG'}</values>
    EILName TEXT NULL,
        -- <values>{'Adult', 'Elementary', 'Elementary-High Combination', 'High School', 'Intermediate/Middle/Junior High', 'Preschool', 'Ungraded'}</values>
    GSoffered TEXT NULL,
        -- <example>'K-12'</example>
    GSserved TEXT NULL,
        -- <example>'K-12'</example>
    Virtual TEXT NULL,
        -- <values>{'F', 'N', 'P'}</values>
    Magnet INTEGER NULL,
        -- <example>0</example>
    Latitude REAL NULL,
        -- <example>37.658</example>
    Longitude REAL NULL,
        -- <example>-122.097</example>
    AdmFName1 TEXT NULL,
        -- <example>'L Karen'</example>
    AdmLName1 TEXT NULL,
        -- <example>'Monroe'</example>
    AdmEmail1 TEXT NULL,
        -- <example>'lkmonroe@acoe.org'</example>
    AdmFName2 TEXT NULL,
        -- <example>'Sau-Lim (Lance)'</example>
    AdmLName2 TEXT NULL,
        -- <example>'Tsang'</example>
    AdmEmail2 TEXT NULL,
        -- <example>'stsang@unityhigh.org'</example>
    AdmFName3 TEXT NULL,
        -- <example>'Drew'</example>
    AdmLName3 TEXT NULL,
        -- <example>'Sarratore'</example>
    AdmEmail3 TEXT NULL,
        -- <example>'dsarratore@vincentacademy.org'</example>
    LastUpdate DATE NOT NULL
        -- <example>'2015-06-23'</example>
);
```