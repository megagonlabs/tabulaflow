```sql
-- Database: synthea

/*
Table: all_prevalences
Rows: 244
Sample rows:
| ITEM                                 | POPULATION TYPE   | OCCURRENCES   | POPULATION COUNT   | PREVALENCE RATE   | PREVALENCE PERCENTAGE   |
|--------------------------------------|-------------------|---------------|--------------------|-------------------|-------------------------|
| Viral Sinusitis (Disorder)           | LIVING            | 868           | 1000               | 0.868             | 86.8                    |
| Streptococcal Sore Throat (Disorder) | LIVING            | 487           | 1000               | 0.487             | 48.7                    |
| Laceration Of Thigh                  | LIVING            | 117           | 1000               | 0.117             | 11.7                    |
| Acute Viral Pharyngitis (Disorder)   | LIVING            | 772           | 1000               | 0.772             | 77.2                    |
| Acute Bronchitis (Disorder)          | LIVING            | 749           | 1000               | 0.749             | 74.9                    |
| ...                                  | ...               | ...           | ...                | ...               | ...                     |
*/
CREATE TABLE all_prevalences (
    ITEM TEXT NOT NULL PRIMARY KEY,
        -- <example>'0.3 Ml Epinephrine 0.5 Mg/Ml Auto Injector'</example>
    "POPULATION TYPE" TEXT NOT NULL,
        -- <values>{'LIVING'}</values>
    OCCURRENCES INTEGER NOT NULL,
        -- <example>868</example>
    "POPULATION COUNT" INTEGER NOT NULL,
        -- <example>1000</example>
    "PREVALENCE RATE" REAL NOT NULL,
        -- <example>0.868</example>
    "PREVALENCE PERCENTAGE" REAL NOT NULL
        -- <example>86.800</example>
);

/*
Table: allergies
Rows: 572
Sample rows:
| START   | STOP   | PATIENT                              | ENCOUNTER                            | CODE      | DESCRIPTION              |
|---------|--------|--------------------------------------|--------------------------------------|-----------|--------------------------|
| 3/11/95 | [NULL] | ab6d8296-d3c7-4fef-9215-40b156db67ac | 9d87c22d-a777-426b-b020-cfa469229f82 | 425525006 | Allergy to dairy product |
| 3/11/95 | [NULL] | ab6d8296-d3c7-4fef-9215-40b156db67ac | 9d87c22d-a777-426b-b020-cfa469229f82 | 419263009 | Allergy to tree pollen   |
| 3/11/95 | [NULL] | ab6d8296-d3c7-4fef-9215-40b156db67ac | 9d87c22d-a777-426b-b020-cfa469229f82 | 418689008 | Allergy to grass pollen  |
| 3/11/95 | [NULL] | ab6d8296-d3c7-4fef-9215-40b156db67ac | 9d87c22d-a777-426b-b020-cfa469229f82 | 232347008 | Dander (animal) allergy  |
| 3/11/95 | [NULL] | ab6d8296-d3c7-4fef-9215-40b156db67ac | 9d87c22d-a777-426b-b020-cfa469229f82 | 232350006 | House dust mite allergy  |
| ...     | ...    | ...                                  | ...                                  | ...       | ...                      |
*/
CREATE TABLE allergies (
    START TEXT NOT NULL,
        -- <example>'3/11/95'</example>
    STOP TEXT NULL,
        -- <example>'12/22/14'</example>
    PATIENT TEXT NOT NULL,
        -- <example>'00341a88-1cc1-4b39-b0f9-05b0531991a0'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NOT NULL,
        -- <example>'ddc8a625-07e6-4a02-a616-e0ce07b5f305'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NOT NULL,
        -- <example>232347008</example>
    DESCRIPTION TEXT NOT NULL,
        -- <example>'Allergy to dairy product'</example>
    PRIMARY KEY (PATIENT, ENCOUNTER, CODE),
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

/*
Table: careplans
Rows: 12125
Sample rows:
| ID                                   | START      | STOP       | PATIENT                              | ENCOUNTER                            | CODE              | DESCRIPTION                           | REASONCODE   | REASONDESCRIPTION           |
|--------------------------------------|------------|------------|--------------------------------------|--------------------------------------|-------------------|---------------------------------------|--------------|-----------------------------|
| e031962d-d13d-4ede-a449-040417d5e4fb | 2009-01-11 | 2009-04-07 | 71949668-1c2e-43ae-ab0a-64654608defb | 4d451e22-a354-40c9-8b33-b6126158666d | 53950000.0        | Respiratory therapy                   | 10509002     | Acute bronchitis (disorder) |
| e031962d-d13d-4ede-a449-040417d5e4fb | 2009-01-11 | 2009-04-07 | 71949668-1c2e-43ae-ab0a-64654608defb | 4d451e22-a354-40c9-8b33-b6126158666d | 304510005.0       | Recommendation to avoid exercise      | 10509002     | Acute bronchitis (disorder) |
| e031962d-d13d-4ede-a449-040417d5e4fb | 2009-01-11 | 2009-04-07 | 71949668-1c2e-43ae-ab0a-64654608defb | 4d451e22-a354-40c9-8b33-b6126158666d | 371605008.0       | Deep breathing and coughing exercises | 10509002     | Acute bronchitis (disorder) |
| 26b879b7-0066-4bd6-b59c-099909720155 | 2010-10-16 | 2010-10-23 | 71949668-1c2e-43ae-ab0a-64654608defb | bed7ecff-b41c-422b-beac-ea00c8b02837 | 869761000000107.0 | Urinary tract infection care          | 38822007     | Cystitis                    |
| 26b879b7-0066-4bd6-b59c-099909720155 | 2010-10-16 | 2010-10-23 | 71949668-1c2e-43ae-ab0a-64654608defb | bed7ecff-b41c-422b-beac-ea00c8b02837 | 223472008.0       | Discussion about hygiene              | 38822007     | Cystitis                    |
| ...                                  | ...        | ...        | ...                                  | ...                                  | ...               | ...                                   | ...          | ...                         |
*/
CREATE TABLE careplans (
    ID TEXT NOT NULL,
        -- <example>'e031962d-d13d-4ede-a449-040417d5e4fb'</example>
    START DATE NOT NULL,
        -- <example>'2009-01-11'</example>
    STOP DATE NULL,
        -- <example>'2009-04-07'</example>
    PATIENT TEXT NOT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NOT NULL,
        -- <example>'4d451e22-a354-40c9-8b33-b6126158666d'</example>
        -- <fk> -> encounters.ID</fk>
    CODE REAL NOT NULL,
        -- <example>53950000.000</example>
    DESCRIPTION TEXT NOT NULL,
        -- <example>'Respiratory therapy'</example>
    REASONCODE INTEGER NULL,
        -- <example>10509002</example>
    REASONDESCRIPTION TEXT NULL,
        -- <example>'Acute bronchitis (disorder)'</example>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

/*
Table: claims
Rows: 20523
Sample rows:
| ID                                   | PATIENT                              | BILLABLEPERIOD   | ORGANIZATION      | ENCOUNTER                            | DIAGNOSIS   | TOTAL   |
|--------------------------------------|--------------------------------------|------------------|-------------------|--------------------------------------|-------------|---------|
| 1a9e880e-27a1-4465-8adc-222b1996a14a | 71949668-1c2e-43ae-ab0a-64654608defb | 2008-03-11       | temp organization | 71949668-1c2e-43ae-ab0a-64654608defb | [NULL]      | 100     |
| 46c0f5f1-a926-4837-84d8-0603fad8a46f | 71949668-1c2e-43ae-ab0a-64654608defb | 2009-01-11       | temp organization | 71949668-1c2e-43ae-ab0a-64654608defb | [NULL]      | 100     |
| b532157d-4056-436b-963d-6445523ed9b3 | 71949668-1c2e-43ae-ab0a-64654608defb | 2009-04-07       | temp organization | 71949668-1c2e-43ae-ab0a-64654608defb | [NULL]      | 100     |
| 8bf9cfff-00e5-4714-9d71-927752c71f08 | 71949668-1c2e-43ae-ab0a-64654608defb | 2010-06-04       | temp organization | 71949668-1c2e-43ae-ab0a-64654608defb | [NULL]      | 100     |
| 5ef9ef1b-6ec5-4cb8-a125-2dcc310bc654 | 71949668-1c2e-43ae-ab0a-64654608defb | 2010-10-16       | temp organization | 71949668-1c2e-43ae-ab0a-64654608defb | [NULL]      | 100     |
| ...                                  | ...                                  | ...              | ...               | ...                                  | ...         | ...     |
*/
CREATE TABLE claims (
    ID TEXT NOT NULL PRIMARY KEY,
        -- <example>'0004caaf-fd7a-4f64-bda6-dce5ebd1196c'</example>
    PATIENT TEXT NOT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    BILLABLEPERIOD DATE NOT NULL,
        -- <example>'2008-03-11'</example>
    ORGANIZATION TEXT NOT NULL,
        -- <values>{'temp organization'}</values>
    ENCOUNTER TEXT NOT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> encounters.ID</fk>
    DIAGNOSIS TEXT NULL,
    TOTAL INTEGER NOT NULL,
        -- <example>100</example>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

/*
Table: conditions
Rows: 7040
Sample rows:
| START      | STOP       | PATIENT                              | ENCOUNTER                            | CODE      | DESCRIPTION                        |
|------------|------------|--------------------------------------|--------------------------------------|-----------|------------------------------------|
| 2009-01-08 | 2009-01-21 | 71949668-1c2e-43ae-ab0a-64654608defb | 4d451e22-a354-40c9-8b33-b6126158666d | 10509002  | Acute bronchitis (disorder)        |
| 2010-10-16 | 2010-10-23 | 71949668-1c2e-43ae-ab0a-64654608defb | bed7ecff-b41c-422b-beac-ea00c8b02837 | 38822007  | Cystitis                           |
| 2013-02-07 | 2013-02-27 | 71949668-1c2e-43ae-ab0a-64654608defb | 6f2e3935-b203-493e-a9c0-f23e847b9798 | 10509002  | Acute bronchitis (disorder)        |
| 2013-10-19 | 2014-05-17 | 71949668-1c2e-43ae-ab0a-64654608defb | da4fd626-e74e-4930-91be-7fb3da7ea098 | 72892002  | Normal pregnancy                   |
| 2014-01-28 | 2014-02-10 | 71949668-1c2e-43ae-ab0a-64654608defb | b2e12445-b771-4738-944b-95cf6bbe76eb | 195662009 | Acute viral pharyngitis (disorder) |
| ...        | ...        | ...                                  | ...                                  | ...       | ...                                |
*/
CREATE TABLE conditions (
    START DATE NOT NULL,
        -- <example>'2009-01-08'</example>
    STOP DATE NULL,
        -- <example>'2009-01-21'</example>
    PATIENT TEXT NOT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NOT NULL,
        -- <example>'4d451e22-a354-40c9-8b33-b6126158666d'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NOT NULL,
        -- <example>10509002</example>
    DESCRIPTION TEXT NOT NULL,
        -- <example>'Acute bronchitis (disorder)'</example>
        -- <fk> -> all_prevalences.ITEM</fk>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient),
    FOREIGN KEY (DESCRIPTION) REFERENCES all_prevalences(ITEM)
);

/*
Table: encounters
Rows: 20524
Sample rows:
| ID                                   | DATE       | PATIENT                              | CODE      | DESCRIPTION                | REASONCODE   | REASONDESCRIPTION           |
|--------------------------------------|------------|--------------------------------------|-----------|----------------------------|--------------|-----------------------------|
| 5114a5b4-64b8-47b2-82a6-0ce24aae0943 | 2008-03-11 | 71949668-1c2e-43ae-ab0a-64654608defb | 185349003 | Outpatient Encounter       | [NULL]       | [NULL]                      |
| 4d451e22-a354-40c9-8b33-b6126158666d | 2009-01-11 | 71949668-1c2e-43ae-ab0a-64654608defb | 185345009 | Encounter for symptom      | 10509002.0   | Acute bronchitis (disorder) |
| bdb926b8-5b6d-4366-bbe9-76fe3f3fbc4f | 2009-04-07 | 71949668-1c2e-43ae-ab0a-64654608defb | 185349003 | Outpatient Encounter       | [NULL]       | [NULL]                      |
| f45c623f-a5e7-47a0-8cce-cfe19d16c47a | 2010-06-04 | 71949668-1c2e-43ae-ab0a-64654608defb | 698314001 | Consultation for treatment | [NULL]       | [NULL]                      |
| bed7ecff-b41c-422b-beac-ea00c8b02837 | 2010-10-16 | 71949668-1c2e-43ae-ab0a-64654608defb | 185345009 | Encounter for symptom      | 38822007.0   | Cystitis                    |
| ...                                  | ...        | ...                                  | ...       | ...                        | ...          | ...                         |
*/
CREATE TABLE encounters (
    ID TEXT NOT NULL PRIMARY KEY,
        -- <example>'000c20ea-5c3d-43a3-9608-bd37c22f13c8'</example>
    DATE DATE NOT NULL,
        -- <example>'2008-03-11'</example>
    PATIENT TEXT NOT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    CODE INTEGER NOT NULL,
        -- <example>185349003</example>
    DESCRIPTION TEXT NOT NULL,
        -- <example>'Outpatient Encounter'</example>
    REASONCODE INTEGER NULL,
        -- <example>10509002</example>
    REASONDESCRIPTION TEXT NULL,
        -- <example>'Acute bronchitis (disorder)'</example>
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

/*
Table: immunizations
Rows: 13189
Sample rows:
| DATE       | PATIENT                              | ENCOUNTER                            | CODE   | DESCRIPTION                                        |
|------------|--------------------------------------|--------------------------------------|--------|----------------------------------------------------|
| 2008-03-11 | 71949668-1c2e-43ae-ab0a-64654608defb | 5114a5b4-64b8-47b2-82a6-0ce24aae0943 | 140    | Influenza  seasonal  injectable  preservative free |
| 2009-04-07 | 71949668-1c2e-43ae-ab0a-64654608defb | bdb926b8-5b6d-4366-bbe9-76fe3f3fbc4f | 140    | Influenza  seasonal  injectable  preservative free |
| 2012-07-02 | 71949668-1c2e-43ae-ab0a-64654608defb | 36796523-2672-4680-84c5-2d9a2b080ddb | 140    | Influenza  seasonal  injectable  preservative free |
| 2012-07-02 | 71949668-1c2e-43ae-ab0a-64654608defb | 36796523-2672-4680-84c5-2d9a2b080ddb | 113    | Td (adult) preservative free                       |
| 2015-05-03 | 71949668-1c2e-43ae-ab0a-64654608defb | 323e1478-fdbf-4904-80a6-2b7e4526fc22 | 140    | Influenza  seasonal  injectable  preservative free |
| ...        | ...                                  | ...                                  | ...    | ...                                                |
*/
CREATE TABLE immunizations (
    DATE DATE NOT NULL,
        -- <example>'2007-11-02'</example>
    PATIENT TEXT NOT NULL,
        -- <example>'70cbc79e-dd9d-4e3b-8158-a92d85951f94'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NOT NULL,
        -- <example>'898ab2de-8a71-4fb3-b239-b768b915284a'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NOT NULL,
        -- <example>8</example>
    DESCRIPTION TEXT NOT NULL,
        -- <values>{'DTaP', 'HPV  quadrivalent', 'Hep A  ped/adol  2 dose', 'Hep B  adolescent or pediatric', 'Hib (PRP-OMP)', 'IPV', 'Influenza  seasonal  injectable  preservative free', 'MMR', 'Pneumococcal conjugate PCV 13', 'Td (adult) preservative free', 'Tdap', 'meningococcal MCV4P', 'pneumococcal polysaccharide vaccine  23 valent', 'rotavirus  monovalent', 'varicella', 'zoster'}</values>
    PRIMARY KEY (DATE, PATIENT, ENCOUNTER, CODE),
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

/*
Table: medications
Rows: 6048
Sample rows:
| START      | STOP       | PATIENT                              | ENCOUNTER                            | CODE    | DESCRIPTION                                         | REASONCODE   | REASONDESCRIPTION                    |
|------------|------------|--------------------------------------|--------------------------------------|---------|-----------------------------------------------------|--------------|--------------------------------------|
| 1988-09-05 | [NULL]     | 71949668-1c2e-43ae-ab0a-64654608defb | 5114a5b4-64b8-47b2-82a6-0ce24aae0943 | 834060  | Penicillin V Potassium 250 MG                       | 43878008.0   | Streptococcal sore throat (disorder) |
| 2007-06-04 | 2008-06-04 | 71949668-1c2e-43ae-ab0a-64654608defb | 5114a5b4-64b8-47b2-82a6-0ce24aae0943 | 1367439 | NuvaRing 0.12/0.015 MG per 24HR 21 Day Vaginal Ring | [NULL]       | [NULL]                               |
| 2009-01-11 | 2009-01-21 | 71949668-1c2e-43ae-ab0a-64654608defb | 4d451e22-a354-40c9-8b33-b6126158666d | 608680  | Acetaminophen 160 MG                                | 10509002.0   | Acute bronchitis (disorder)          |
| 2010-06-04 | 2011-06-04 | 71949668-1c2e-43ae-ab0a-64654608defb | f45c623f-a5e7-47a0-8cce-cfe19d16c47a | 748879  | Levora 0.15/30 28 Day Pack                          | [NULL]       | [NULL]                               |
| 2010-10-16 | 2010-10-23 | 71949668-1c2e-43ae-ab0a-64654608defb | bed7ecff-b41c-422b-beac-ea00c8b02837 | 568530  | Nitrofurantoin 5 MG/ML [Furadantin]                 | 38822007.0   | Cystitis                             |
| ...        | ...        | ...                                  | ...                                  | ...     | ...                                                 | ...          | ...                                  |
*/
CREATE TABLE medications (
    START DATE NOT NULL,
        -- <example>'1918-04-17'</example>
    STOP DATE NULL,
        -- <example>'2008-06-04'</example>
    PATIENT TEXT NOT NULL,
        -- <example>'ce11bcba-c83c-43ae-802d-b20ee8715afe'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NOT NULL,
        -- <example>'6334071d-e6b0-42c1-a082-2a08e123de4e'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NOT NULL,
        -- <example>834060</example>
    DESCRIPTION TEXT NOT NULL,
        -- <example>'Penicillin V Potassium 250 MG'</example>
    REASONCODE INTEGER NULL,
        -- <example>43878008</example>
    REASONDESCRIPTION TEXT NULL,
        -- <example>'Streptococcal sore throat (disorder)'</example>
    PRIMARY KEY (START, PATIENT, ENCOUNTER, CODE),
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

/*
Table: observations
Rows: 78899
Sample rows:
| DATE       | PATIENT                              | ENCOUNTER                            | CODE    | DESCRIPTION              | VALUE   | UNITS   |
|------------|--------------------------------------|--------------------------------------|---------|--------------------------|---------|---------|
| 2008-03-11 | 71949668-1c2e-43ae-ab0a-64654608defb | 5114a5b4-64b8-47b2-82a6-0ce24aae0943 | 8302-2  | Body Height              | 166.03  | cm      |
| 2008-03-11 | 71949668-1c2e-43ae-ab0a-64654608defb | 5114a5b4-64b8-47b2-82a6-0ce24aae0943 | 29463-7 | Body Weight              | 54.42   | kg      |
| 2008-03-11 | 71949668-1c2e-43ae-ab0a-64654608defb | 5114a5b4-64b8-47b2-82a6-0ce24aae0943 | 39156-5 | Body Mass Index          | 19.74   | kg/m2   |
| 2008-03-11 | 71949668-1c2e-43ae-ab0a-64654608defb | 5114a5b4-64b8-47b2-82a6-0ce24aae0943 | 8480-6  | Systolic Blood Pressure  | 139.0   | mmHg    |
| 2008-03-11 | 71949668-1c2e-43ae-ab0a-64654608defb | 5114a5b4-64b8-47b2-82a6-0ce24aae0943 | 8462-4  | Diastolic Blood Pressure | 89.0    | mmHg    |
| ...        | ...                                  | ...                                  | ...     | ...                      | ...     | ...     |
*/
CREATE TABLE observations (
    DATE DATE NOT NULL,
        -- <example>'2008-03-11'</example>
    PATIENT TEXT NOT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NULL,
        -- <example>'5114a5b4-64b8-47b2-82a6-0ce24aae0943'</example>
        -- <fk> -> encounters.ID</fk>
    CODE TEXT NOT NULL,
        -- <example>'8302-2'</example>
    DESCRIPTION TEXT NOT NULL,
        -- <example>'Body Height'</example>
    VALUE REAL NULL,
        -- <example>166.030</example>
    UNITS TEXT NULL,
        -- <values>{'%', '(score)', 'Cel', 'cm', 'kU/L', 'kg', 'kg/m2', 'mL/min/{1.73_m2}', 'mg/dL', 'mg/g', 'mm', 'mmHg', 'mmol/L', 'ng/mL', 'years', '{T-score}', '{count}'}</values>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

/*
Table: patients
Rows: 1462
Sample rows:
| patient                              | birthdate   | deathdate   | ssn         | drivers   | passport   | prefix   | first     | last         | suffix   | maiden   | marital   | race     | ethnicity    | gender   | birthplace       | address                                              |
|--------------------------------------|-------------|-------------|-------------|-----------|------------|----------|-----------|--------------|----------|----------|-----------|----------|--------------|----------|------------------|------------------------------------------------------|
| 4ee2c837-e60f-4c54-9fdf-8686bc70760b | 1929-04-08  | 2029-11-11  | 999-78-5976 | [NULL]    | [NULL]     | [NULL]   | Rosamaria | Pfannerstill | [NULL]   | [NULL]   | [NULL]    | black    | dominican    | F        | Pittsfield MA US | 18797 Karson Burgs Suite 444 Palmer Town MA 01069 US |
| efaf74f9-3de3-45dd-a5d5-26d08e8a3190 | 2016-12-15  | 2020-02-19  | 999-59-9186 | [NULL]    | [NULL]     | [NULL]   | Loan      | Bashirian    | [NULL]   | [NULL]   | [NULL]    | white    | american     | F        | Medford MA US    | 301 Eula Radial Suite 298 Brockton MA 02305 US       |
| aaa4c718-2f48-4c13-9ad0-d287cf280824 | 1943-11-28  | 2017-10-22  | 999-43-3780 | S99992928 | FALSE      | Mr.      | Angelo    | Buckridge    | [NULL]   | [NULL]   | S         | black    | african      | M        | Framingham MA US | 8693 Fred Crossroad New Bedford MA 02746 US          |
| a1851c06-804e-4f31-9d8f-388cd52d4ad0 | 1954-10-22  | 2017-10-13  | 999-53-5542 | S99975961 | X98167138X | Mrs.     | Cami      | Terry        | [NULL]   | Schuster | M         | white    | english      | F        | Hudson MA US     | 344 Olson Road Apt. 936 Attleboro MA 02703 US        |
| 48074b70-4db4-4ab0-b9e8-361bd2ba6216 | 1935-04-08  | 2017-09-06  | 999-34-8549 | S99997003 | X65866752X | Mr.      | Giovanni  | Russel       | [NULL]   | [NULL]   | M         | hispanic | puerto_rican | M        | Westfield MA US  | 5780 Corwin Trafficway Dartmouth MA 02714 US         |
| ...                                  | ...         | ...         | ...         | ...       | ...        | ...      | ...       | ...          | ...      | ...      | ...       | ...      | ...          | ...      | ...              | ...                                                  |
*/
CREATE TABLE patients (
    patient TEXT NOT NULL PRIMARY KEY,
        -- <example>'00269bb7-e3ab-43a9-9cdf-cdf9b6e3b2b3'</example>
    birthdate DATE NOT NULL,
        -- <example>'1929-04-08'</example>
    deathdate DATE NULL,
        -- <example>'2029-11-11'</example>
    ssn TEXT NOT NULL,
        -- <example>'999-78-5976'</example>
    drivers TEXT NULL,
        -- <example>'S99992928'</example>
    passport TEXT NULL,
        -- <example>'FALSE'</example>
    prefix TEXT NULL,
        -- <values>{'Mr.', 'Mrs.', 'Ms.'}</values>
    first TEXT NOT NULL,
        -- <example>'Rosamaria'</example>
    last TEXT NOT NULL,
        -- <example>'Pfannerstill'</example>
    suffix TEXT NULL,
        -- <values>{'JD', 'MD', 'PhD'}</values>
    maiden TEXT NULL,
        -- <example>'Schuster'</example>
    marital TEXT NULL,
        -- <values>{'M', 'S'}</values>
    race TEXT NOT NULL,
        -- <values>{'asian', 'black', 'hispanic', 'white'}</values>
    ethnicity TEXT NOT NULL,
        -- <example>'dominican'</example>
    gender TEXT NOT NULL,
        -- <values>{'F', 'M'}</values>
    birthplace TEXT NOT NULL,
        -- <example>'Pittsfield MA US'</example>
    address TEXT NOT NULL
        -- <example>'18797 Karson Burgs Suite 444 Palmer Town MA 01069 US'</example>
);

/*
Table: procedures
Rows: 10184
Sample rows:
| DATE       | PATIENT                              | ENCOUNTER                            | CODE      | DESCRIPTION                                     | REASONCODE   | REASONDESCRIPTION           |
|------------|--------------------------------------|--------------------------------------|-----------|-------------------------------------------------|--------------|-----------------------------|
| 2013-02-09 | 71949668-1c2e-43ae-ab0a-64654608defb | 6f2e3935-b203-493e-a9c0-f23e847b9798 | 23426006  | Measurement of respiratory function (procedure) | 10509002.0   | Acute bronchitis (disorder) |
| 2013-10-19 | 71949668-1c2e-43ae-ab0a-64654608defb | da4fd626-e74e-4930-91be-7fb3da7ea098 | 252160004 | Standard pregnancy test                         | 72892002.0   | Normal pregnancy            |
| 2014-05-17 | 71949668-1c2e-43ae-ab0a-64654608defb | 988f02a3-bf7e-485a-8d26-3378ddc9524c | 237001001 | Augmentation of labor                           | 72892002.0   | Normal pregnancy            |
| 2014-05-17 | 71949668-1c2e-43ae-ab0a-64654608defb | 988f02a3-bf7e-485a-8d26-3378ddc9524c | 11466000  | Cesarean section                                | 72892002.0   | Normal pregnancy            |
| 2016-06-04 | 71949668-1c2e-43ae-ab0a-64654608defb | 8ae1f76d-fdf1-40b7-9c9d-66b530701d9d | 169553002 | Insertion of subcutaneous contraceptive         | [NULL]       | [NULL]                      |
| ...        | ...                                  | ...                                  | ...       | ...                                             | ...          | ...                         |
*/
CREATE TABLE procedures (
    DATE DATE NOT NULL,
        -- <example>'2013-02-09'</example>
    PATIENT TEXT NOT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NOT NULL,
        -- <example>'6f2e3935-b203-493e-a9c0-f23e847b9798'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NOT NULL,
        -- <example>23426006</example>
    DESCRIPTION TEXT NOT NULL,
        -- <example>'Measurement of respiratory function (procedure)'</example>
    REASONCODE INTEGER NULL,
        -- <example>10509002</example>
    REASONDESCRIPTION TEXT NULL,
        -- <example>'Acute bronchitis (disorder)'</example>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);
```