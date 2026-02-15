```sql
-- Database: california_schools

/*
Schema: NULL
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
    "CDSCode" TEXT NOT NULL PRIMARY KEY,
        -- <example>'01100170109835'</example>
        -- <fk> -> schools."CDSCode"</fk>
    "Academic Year" TEXT NOT NULL,
        -- <values>{'2014-2015'}</values>
    "County Code" TEXT NOT NULL,
        -- <example>'01'</example>
    "District Code" INTEGER NOT NULL,
        -- <example>10017</example>
    "School Code" TEXT NOT NULL,
        -- <example>'0109835'</example>
    "County Name" TEXT NOT NULL,
        -- <example>'Alameda'</example>
    "District Name" TEXT NOT NULL,
        -- <example>'Alameda County Office of Education'</example>
    "School Name" TEXT NOT NULL,
        -- <example>'FAME Public Charter'</example>
    "District Type" TEXT NOT NULL,
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
    "IRC" INTEGER NULL,
        -- <example>1</example>
    "Low Grade" TEXT NOT NULL,
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P'}</values>
    "High Grade" TEXT NOT NULL,
        -- <values>{'1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9', 'Adult', 'K', 'P', 'Post Secondary'}</values>
    "Enrollment (K-12)" REAL NOT NULL,
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
    "2013-14 CALPADS Fall 1 Certification Status" INTEGER NOT NULL,
        -- <example>1</example>
    FOREIGN KEY ("CDSCode") REFERENCES schools("CDSCode")
);

/*
Schema: NULL
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
    "cds" TEXT NOT NULL PRIMARY KEY,
        -- <example>'10101080000000'</example>
        -- <fk> -> schools."CDSCode"</fk>
    "rtype" TEXT NOT NULL,
        -- <values>{'D', 'S'}</values>
    "sname" TEXT NULL,
        -- <example>'FAME Public Charter'</example>
    "dname" TEXT NOT NULL,
        -- <example>'Alameda County Office of Education'</example>
    "cname" TEXT NOT NULL,
        -- <example>'Alameda'</example>
    "enroll12" INTEGER NOT NULL,
        -- <example>398</example>
    "NumTstTakr" INTEGER NOT NULL,
        -- <example>88</example>
    "AvgScrRead" INTEGER NULL,
        -- <example>418</example>
    "AvgScrMath" INTEGER NULL,
        -- <example>418</example>
    "AvgScrWrite" INTEGER NULL,
        -- <example>417</example>
    "NumGE1500" INTEGER NULL,
        -- <example>14</example>
    FOREIGN KEY ("cds") REFERENCES schools("CDSCode")
);

/*
Schema: NULL
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
    "CDSCode" TEXT NOT NULL PRIMARY KEY,
        -- <example>'01100170000000'</example>
    "NCESDist" TEXT NULL,
        -- <example>'0691051'</example>
    "NCESSchool" TEXT NULL,
        -- <example>'10546'</example>
    "StatusType" TEXT NOT NULL,
        -- <values>{'Active', 'Closed', 'Merged', 'Pending'}</values>
    "County" TEXT NOT NULL,
        -- <example>'Alameda'</example>
    "District" TEXT NOT NULL,
        -- <example>'Alameda County Office of Education'</example>
    "School" TEXT NULL,
        -- <example>'FAME Public Charter'</example>
    "Street" TEXT NULL,
        -- <example>'313 West Winton Avenue'</example>
    "StreetAbr" TEXT NULL,
        -- <example>'313 West Winton Ave.'</example>
    "City" TEXT NULL,
        -- <example>'Hayward'</example>
    "Zip" TEXT NULL,
        -- <example>'94544-1136'</example>
    "State" TEXT NULL,
        -- <values>{'CA'}</values>
    "MailStreet" TEXT NULL,
        -- <example>'313 West Winton Avenue'</example>
    "MailStrAbr" TEXT NULL,
        -- <example>'313 West Winton Ave.'</example>
    "MailCity" TEXT NULL,
        -- <example>'Hayward'</example>
    "MailZip" TEXT NULL,
        -- <example>'94544-1136'</example>
    "MailState" TEXT NULL,
        -- <values>{'CA'}</values>
    "Phone" TEXT NULL,
        -- <example>'(510) 887-0152'</example>
    "Ext" TEXT NULL,
        -- <example>'130'</example>
    "Website" TEXT NULL,
        -- <example>'www.acoe.org'</example>
    "OpenDate" DATE NULL,
        -- <example>'2005-08-29'</example>
    "ClosedDate" DATE NULL,
        -- <example>'2015-07-31'</example>
    "Charter" INTEGER NULL,
        -- <example>1</example>
    "CharterNum" TEXT NULL,
        -- <example>'0728'</example>
    "FundingType" TEXT NULL,
        -- <values>{'Directly funded', 'Locally funded', 'Not in CS funding model'}</values>
    "DOC" TEXT NOT NULL,
        -- <values>{'00', '02', '03', '31', '34', '42', '52', '54', '56', '58', '98', '99'}</values>
    "DOCType" TEXT NOT NULL,
        -- <values>{'Administration Only', 'Community College District', 'County Office of Education (COE)', 'Elementary School District', 'High School District', 'Joint Powers Authority (JPA)', 'Non-School Locations', 'Regional Occupation Center/Program (ROC/P)', 'State Board of Education', 'State Special Schools', 'Statewide Benefit Charter', 'Unified School District'}</values>
    "SOC" TEXT NULL,
        -- <values>{'08', '09', '10', '11', '13', '14', '15', '31', '60', '61', '62', '63', '64', '65', '66', '67', '68', '69', '70', '98'}</values>
    "SOCType" TEXT NULL,
        -- <values>{'Adult Education Centers', 'Alternative Schools of Choice', 'Continuation High Schools', 'County Community', 'District Community Day Schools', 'Elemen Schools In 1 School Dist. (Public)', 'Elementary Schools (Public)', 'High Schools (Public)', 'High Schools In 1 School Dist. (Public)', 'Intermediate/Middle Schools (Public)', 'Junior High Schools (Public)', 'Juvenile Court Schools', 'K-12 Schools (Public)', 'Opportunity Schools', 'Other County Or District Programs', 'Preschool', 'ROC/ROP', 'Special Education Schools (Public)', 'State Special Schools', 'Youth Authority Facilities'}</values>
    "EdOpsCode" TEXT NULL,
        -- <values>{'ALTSOC', 'COMM', 'COMMDAY', 'CON', 'HOMHOS', 'JUV', 'OPP', 'ROP', 'SPEC', 'SPECON', 'SSS', 'TRAD', 'YTH'}</values>
    "EdOpsName" TEXT NULL,
        -- <values>{'Alternative School of Choice', 'Community Day School', 'Continuation School', 'County Community School', 'District Special Education Consortia School', 'Home and Hospital', 'Juvenile Court School', 'Opportunity School', 'ROP', 'Special Education School', 'State Special School', 'Traditional', 'Youth Authority School'}</values>
    "EILCode" TEXT NULL,
        -- <values>{'A', 'ELEM', 'ELEMHIGH', 'HS', 'INTMIDJR', 'PS', 'UG'}</values>
    "EILName" TEXT NULL,
        -- <values>{'Adult', 'Elementary', 'Elementary-High Combination', 'High School', 'Intermediate/Middle/Junior High', 'Preschool', 'Ungraded'}</values>
    "GSoffered" TEXT NULL,
        -- <example>'K-12'</example>
    "GSserved" TEXT NULL,
        -- <example>'K-12'</example>
    "Virtual" TEXT NULL,
        -- <values>{'F', 'N', 'P'}</values>
    "Magnet" INTEGER NULL,
        -- <example>0</example>
    "Latitude" REAL NULL,
        -- <example>37.658</example>
    "Longitude" REAL NULL,
        -- <example>-122.097</example>
    "AdmFName1" TEXT NULL,
        -- <example>'L Karen'</example>
    "AdmLName1" TEXT NULL,
        -- <example>'Monroe'</example>
    "AdmEmail1" TEXT NULL,
        -- <example>'lkmonroe@acoe.org'</example>
    "AdmFName2" TEXT NULL,
        -- <example>'Sau-Lim (Lance)'</example>
    "AdmLName2" TEXT NULL,
        -- <example>'Tsang'</example>
    "AdmEmail2" TEXT NULL,
        -- <example>'stsang@unityhigh.org'</example>
    "AdmFName3" TEXT NULL,
        -- <example>'Drew'</example>
    "AdmLName3" TEXT NULL,
        -- <example>'Sarratore'</example>
    "AdmEmail3" TEXT NULL,
        -- <example>'dsarratore@vincentacademy.org'</example>
    "LastUpdate" DATE NOT NULL
        -- <example>'2015-06-23'</example>
);
```