```sql
-- Database: california_schools

-- Table: frpm (9986 rows)
CREATE TABLE frpm (
    CDSCode TEXT NOT NULL PRIMARY KEY,  -- e.g. '01100170109835'; FK -> schools.CDSCode
    "Academic Year" TEXT,  -- values: {'2014-2015'}
    "County Code" TEXT,  -- e.g. '01'
    "District Code" INTEGER,  -- e.g. 10017
    "School Code" TEXT,  -- e.g. '0109835'
    "County Name" TEXT,  -- e.g. 'Alameda'
    "District Name" TEXT,  -- e.g. 'Alameda County Office of Education'
    "School Name" TEXT,  -- e.g. 'FAME Public Charter'
    "District Type" TEXT,  -- values: {'County Office of Education (COE)', 'Elementary School District', 'High School District', 'Non-School Locations', 'State Board of Education', 'State Special Schools', 'Statewide Benefit Charter', 'Unified School District'}
    "School Type" TEXT,  -- values: {'Alternative Schools of Choice', 'Continuation High Schools', 'County Community', 'District Community Day Schools', 'Elemen Schools In 1 School Dist. (Public)', 'Elementary Schools (Public)', 'High Schools (Public)', 'High Schools In 1 School Dist. (Public)', 'Intermediate/Middle Schools (Public)', 'Junior High Schools (Public)', 'Juvenile Court Schools', 'K-12 Schools (Public)', 'Opportunity Schools', 'Preschool', 'Special Education Schools (Public)', 'State Special Schools', 'Youth Authority Facilities'}
    "Educational Option Type" TEXT,  -- values: {'Alternative School of Choice', 'Community Day School', 'Continuation School', 'County Community School', 'District Special Education Consortia School', 'Home and Hospital', 'Juvenile Court School', 'Opportunity School', 'Special Education School', 'State Special School', 'Traditional', 'Youth Authority School'}
    "NSLP Provision Status" TEXT,  -- values: {'Breakfast Provision 2', 'CEP', 'Lunch Provision 2', 'Multiple Provision Types', 'Provision 1', 'Provision 2', 'Provision 3'}
    "Charter School (Y/N)" INTEGER,  -- e.g. 1
    "Charter School Number" TEXT,  -- e.g. '0728'
    "Charter Funding Type" TEXT,  -- values: {'Directly funded', 'Locally funded', 'Not in CS funding model'}
    IRC INTEGER,  -- e.g. 1
    "Low Grade" TEXT,  -- values: {'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P'}
    "High Grade" TEXT,  -- values: {'1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P', 'Post Secondary'}
    "Enrollment (K-12)" REAL,  -- e.g. 1087.000
    "Free Meal Count (K-12)" REAL,  -- e.g. 565.000
    "Percent (%) Eligible Free (K-12)" REAL,  -- e.g. 0.520
    "FRPM Count (K-12)" REAL,  -- e.g. 715.000
    "Percent (%) Eligible FRPM (K-12)" REAL,  -- e.g. 0.658
    "Enrollment (Ages 5-17)" REAL,  -- e.g. 1070.000
    "Free Meal Count (Ages 5-17)" REAL,  -- e.g. 553.000
    "Percent (%) Eligible Free (Ages 5-17)" REAL,  -- e.g. 0.517
    "FRPM Count (Ages 5-17)" REAL,  -- e.g. 702.000
    "Percent (%) Eligible FRPM (Ages 5-17)" REAL,  -- e.g. 0.656
    "2013-14 CALPADS Fall 1 Certification Status" INTEGER,  -- e.g. 1
    FOREIGN KEY (CDSCode) REFERENCES schools(CDSCode)
);

-- Table: satscores (2269 rows)
CREATE TABLE satscores (
    cds TEXT NOT NULL PRIMARY KEY,  -- e.g. '10101080000000'; FK -> schools.CDSCode
    rtype TEXT NOT NULL,  -- values: {'D', 'S'}
    sname TEXT,  -- e.g. 'FAME Public Charter'
    dname TEXT,  -- e.g. 'Alameda County Office of Education'
    cname TEXT,  -- e.g. 'Alameda'
    enroll12 INTEGER NOT NULL,  -- e.g. 398
    NumTstTakr INTEGER NOT NULL,  -- e.g. 88
    AvgScrRead INTEGER,  -- e.g. 418
    AvgScrMath INTEGER,  -- e.g. 418
    AvgScrWrite INTEGER,  -- e.g. 417
    NumGE1500 INTEGER,  -- e.g. 14
    FOREIGN KEY (cds) REFERENCES schools(CDSCode)
);

-- Table: schools (17686 rows)
CREATE TABLE schools (
    CDSCode TEXT NOT NULL PRIMARY KEY,  -- e.g. '01100170000000'
    NCESDist TEXT,  -- e.g. '0691051'
    NCESSchool TEXT,  -- e.g. '10546'
    StatusType TEXT NOT NULL,  -- values: {'Active', 'Closed', 'Merged', 'Pending'}
    County TEXT NOT NULL,  -- e.g. 'Alameda'
    District TEXT NOT NULL,  -- e.g. 'Alameda County Office of Education'
    School TEXT,  -- e.g. 'FAME Public Charter'
    Street TEXT,  -- e.g. '313 West Winton Avenue'
    StreetAbr TEXT,  -- e.g. '313 West Winton Ave.'
    City TEXT,  -- e.g. 'Hayward'
    Zip TEXT,  -- e.g. '94544-1136'
    State TEXT,  -- values: {'CA'}
    MailStreet TEXT,  -- e.g. '313 West Winton Avenue'
    MailStrAbr TEXT,  -- e.g. '313 West Winton Ave.'
    MailCity TEXT,  -- e.g. 'Hayward'
    MailZip TEXT,  -- e.g. '94544-1136'
    MailState TEXT,  -- values: {'CA'}
    Phone TEXT,  -- e.g. '(510) 887-0152'
    Ext TEXT,  -- e.g. '130'
    Website TEXT,  -- e.g. 'www.acoe.org'
    OpenDate DATE,  -- e.g. '2005-08-29'
    ClosedDate DATE,  -- e.g. '2015-07-31'
    Charter INTEGER,  -- e.g. 1
    CharterNum TEXT,  -- e.g. '0728'
    FundingType TEXT,  -- values: {'Directly funded', 'Locally funded', 'Not in CS funding model'}
    DOC TEXT NOT NULL,  -- values: {'00', '02', '03', '31', '34', '42', '52', '54', '56', '58', '98', '99'}
    DOCType TEXT NOT NULL,  -- values: {'Administration Only', 'Community College District', 'County Office of Education (COE)', 'Elementary School District', 'High School District', 'Joint Powers Authority (JPA)', 'Non-School Locations', 'Regional Occupation Center/Program (ROC/P)', 'State Board of Education', 'State Special Schools', 'Statewide Benefit Charter', 'Unified School District'}
    SOC TEXT,  -- values: {'08', '09', '10', '11', '13', '14', '15', '31', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '70', '98'}
    SOCType TEXT,  -- values: {'Adult Education Centers', 'Alternative Schools of Choice', 'Continuation High Schools', 'County Community', 'District Community Day Schools', 'Elemen Schools In 1 School Dist. (Public)', 'Elementary Schools (Public)', 'High Schools (Public)', 'High Schools In 1 School Dist. (Public)', 'Intermediate/Middle Schools (Public)', 'Junior High Schools (Public)', 'Juvenile Court Schools', 'K-12 Schools (Public)', 'Opportunity Schools', 'Other County Or District Programs', 'Preschool', 'ROC/ROP', 'Special Education Schools (Public)', 'State Special Schools', 'Youth Authority Facilities'}
    EdOpsCode TEXT,  -- values: {'ALTSOC', 'COMM', 'COMMDAY', 'CON', 'HOMHOS', 'JUV', 'OPP', 'ROP', 'SPEC', 'SPECON', 'SSS', 'TRAD', 'YTH'}
    EdOpsName TEXT,  -- values: {'Alternative School of Choice', 'Community Day School', 'Continuation School', 'County Community School', 'District Special Education Consortia School', 'Home and Hospital', 'Juvenile Court School', 'Opportunity School', 'ROP', 'Special Education School', 'State Special School', 'Traditional', 'Youth Authority School'}
    EILCode TEXT,  -- values: {'A', 'ELEM', 'ELEMHIGH', 'HS', 'INTMIDJR', 'PS', 'UG'}
    EILName TEXT,  -- values: {'Adult', 'Elementary', 'Elementary-High Combination', 'High School', 'Intermediate/Middle/Junior High', 'Preschool', 'Ungraded'}
    GSoffered TEXT,  -- e.g. 'K-12'
    GSserved TEXT,  -- e.g. 'K-12'
    Virtual TEXT,  -- values: {'F', 'N', 'P'}
    Magnet INTEGER,  -- e.g. 0
    Latitude REAL,  -- e.g. 37.658
    Longitude REAL,  -- e.g. -122.097
    AdmFName1 TEXT,  -- e.g. 'L Karen'
    AdmLName1 TEXT,  -- e.g. 'Monroe'
    AdmEmail1 TEXT,  -- e.g. 'lkmonroe@acoe.org'
    AdmFName2 TEXT,  -- e.g. 'Sau-Lim (Lance)'
    AdmLName2 TEXT,  -- e.g. 'Tsang'
    AdmEmail2 TEXT,  -- e.g. 'stsang@unityhigh.org'
    AdmFName3 TEXT,  -- e.g. 'Drew'
    AdmLName3 TEXT,  -- e.g. 'Sarratore'
    AdmEmail3 TEXT,  -- e.g. 'dsarratore@vincentacademy.org'
    LastUpdate DATE NOT NULL  -- e.g. '2015-06-23'
);
```