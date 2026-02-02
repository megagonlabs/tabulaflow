```sql
-- Database: synthea

-- Table: all_prevalences (244 rows)
CREATE TABLE all_prevalences (
    ITEM TEXT NULL PRIMARY KEY,
        -- <example>'0.3 Ml Epinephrine 0.5 Mg/Ml Auto Injector'</example>
    "POPULATION TYPE" TEXT NULL,
        -- <values>{'LIVING'}</values>
    OCCURRENCES INTEGER NULL,
        -- <example>868</example>
    "POPULATION COUNT" INTEGER NULL,
        -- <example>1000</example>
    "PREVALENCE RATE" REAL NULL,
        -- <example>0.868</example>
    "PREVALENCE PERCENTAGE" REAL NULL
        -- <example>86.800</example>
);

-- Table: allergies (572 rows)
CREATE TABLE allergies (
    START TEXT NULL,
        -- <example>'3/11/95'</example>
    STOP TEXT NULL,
        -- <example>'12/22/14'</example>
    PATIENT TEXT NULL,
        -- <example>'00341a88-1cc1-4b39-b0f9-05b0531991a0'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NULL,
        -- <example>'ddc8a625-07e6-4a02-a616-e0ce07b5f305'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NULL,
        -- <example>232347008</example>
    DESCRIPTION TEXT NULL,
        -- <example>'Allergy to dairy product'</example>
    PRIMARY KEY (PATIENT, ENCOUNTER, CODE),
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

-- Table: careplans (12125 rows)
CREATE TABLE careplans (
    ID TEXT NULL,
        -- <example>'e031962d-d13d-4ede-a449-040417d5e4fb'</example>
    START DATE NULL,
        -- <example>'2009-01-11'</example>
    STOP DATE NULL,
        -- <example>'2009-04-07'</example>
    PATIENT TEXT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NULL,
        -- <example>'4d451e22-a354-40c9-8b33-b6126158666d'</example>
        -- <fk> -> encounters.ID</fk>
    CODE REAL NULL,
        -- <example>53950000.000</example>
    DESCRIPTION TEXT NULL,
        -- <example>'Respiratory therapy'</example>
    REASONCODE INTEGER NULL,
        -- <example>10509002</example>
    REASONDESCRIPTION TEXT NULL,
        -- <example>'Acute bronchitis (disorder)'</example>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

-- Table: claims (20523 rows)
CREATE TABLE claims (
    ID TEXT NULL PRIMARY KEY,
        -- <example>'0004caaf-fd7a-4f64-bda6-dce5ebd1196c'</example>
    PATIENT TEXT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    BILLABLEPERIOD DATE NULL,
        -- <example>'2008-03-11'</example>
    ORGANIZATION TEXT NULL,
        -- <values>{'temp organization'}</values>
    ENCOUNTER TEXT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> encounters.ID</fk>
    DIAGNOSIS TEXT NULL,
    TOTAL INTEGER NULL,
        -- <example>100</example>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

-- Table: conditions (7040 rows)
CREATE TABLE conditions (
    START DATE NULL,
        -- <example>'2009-01-08'</example>
    STOP DATE NULL,
        -- <example>'2009-01-21'</example>
    PATIENT TEXT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NULL,
        -- <example>'4d451e22-a354-40c9-8b33-b6126158666d'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NULL,
        -- <example>10509002</example>
    DESCRIPTION TEXT NULL,
        -- <example>'Acute bronchitis (disorder)'</example>
        -- <fk> -> all_prevalences.ITEM</fk>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient),
    FOREIGN KEY (DESCRIPTION) REFERENCES all_prevalences(ITEM)
);

-- Table: encounters (20524 rows)
CREATE TABLE encounters (
    ID TEXT NULL PRIMARY KEY,
        -- <example>'000c20ea-5c3d-43a3-9608-bd37c22f13c8'</example>
    DATE DATE NULL,
        -- <example>'2008-03-11'</example>
    PATIENT TEXT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    CODE INTEGER NULL,
        -- <example>185349003</example>
    DESCRIPTION TEXT NULL,
        -- <example>'Outpatient Encounter'</example>
    REASONCODE INTEGER NULL,
        -- <example>10509002</example>
    REASONDESCRIPTION TEXT NULL,
        -- <example>'Acute bronchitis (disorder)'</example>
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

-- Table: immunizations (13189 rows)
CREATE TABLE immunizations (
    DATE DATE NULL,
        -- <example>'2007-11-02'</example>
    PATIENT TEXT NULL,
        -- <example>'70cbc79e-dd9d-4e3b-8158-a92d85951f94'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NULL,
        -- <example>'898ab2de-8a71-4fb3-b239-b768b915284a'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NULL,
        -- <example>8</example>
    DESCRIPTION TEXT NULL,
        -- <values>{'DTaP', 'HPV  quadrivalent', 'Hep A  ped/adol  2 dose', 'Hep B  adolescent or pediatric', 'Hib (PRP-OMP)', 'IPV', 'Influenza  seasonal  injectable  preservative free', 'MMR', 'Pneumococcal conjugate PCV 13', 'Td (adult) preservative free', 'Tdap', 'meningococcal MCV4P', 'pneumococcal polysaccharide vaccine  23 valent', 'rotavirus  monovalent', 'varicella', 'zoster'}</values>
    PRIMARY KEY (DATE, PATIENT, ENCOUNTER, CODE),
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

-- Table: medications (6048 rows)
CREATE TABLE medications (
    START DATE NULL,
        -- <example>'1918-04-17'</example>
    STOP DATE NULL,
        -- <example>'2008-06-04'</example>
    PATIENT TEXT NULL,
        -- <example>'ce11bcba-c83c-43ae-802d-b20ee8715afe'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NULL,
        -- <example>'6334071d-e6b0-42c1-a082-2a08e123de4e'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NULL,
        -- <example>834060</example>
    DESCRIPTION TEXT NULL,
        -- <example>'Penicillin V Potassium 250 MG'</example>
    REASONCODE INTEGER NULL,
        -- <example>43878008</example>
    REASONDESCRIPTION TEXT NULL,
        -- <example>'Streptococcal sore throat (disorder)'</example>
    PRIMARY KEY (START, PATIENT, ENCOUNTER, CODE),
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

-- Table: observations (78899 rows)
CREATE TABLE observations (
    DATE DATE NULL,
        -- <example>'2008-03-11'</example>
    PATIENT TEXT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NULL,
        -- <example>'5114a5b4-64b8-47b2-82a6-0ce24aae0943'</example>
        -- <fk> -> encounters.ID</fk>
    CODE TEXT NULL,
        -- <example>'8302-2'</example>
    DESCRIPTION TEXT NULL,
        -- <example>'Body Height'</example>
    VALUE REAL NULL,
        -- <example>166.030</example>
    UNITS TEXT NULL,
        -- <values>{'%', '(score)', 'Cel', 'cm', 'kU/L', 'kg', 'kg/m2', 'mL/min/{1.73_m2}', 'mg/dL', 'mg/g', 'mm', 'mmHg', 'mmol/L', 'ng/mL', 'years', '{T-score}', '{count}'}</values>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);

-- Table: patients (1462 rows)
CREATE TABLE patients (
    patient TEXT NULL PRIMARY KEY,
        -- <example>'00269bb7-e3ab-43a9-9cdf-cdf9b6e3b2b3'</example>
    birthdate DATE NULL,
        -- <example>'1929-04-08'</example>
    deathdate DATE NULL,
        -- <example>'2029-11-11'</example>
    ssn TEXT NULL,
        -- <example>'999-78-5976'</example>
    drivers TEXT NULL,
        -- <example>'S99992928'</example>
    passport TEXT NULL,
        -- <example>'FALSE'</example>
    prefix TEXT NULL,
        -- <values>{'Mr.', 'Mrs.', 'Ms.'}</values>
    first TEXT NULL,
        -- <example>'Rosamaria'</example>
    last TEXT NULL,
        -- <example>'Pfannerstill'</example>
    suffix TEXT NULL,
        -- <values>{'JD', 'MD', 'PhD'}</values>
    maiden TEXT NULL,
        -- <example>'Schuster'</example>
    marital TEXT NULL,
        -- <values>{'M', 'S'}</values>
    race TEXT NULL,
        -- <values>{'asian', 'black', 'hispanic', 'white'}</values>
    ethnicity TEXT NULL,
        -- <example>'dominican'</example>
    gender TEXT NULL,
        -- <values>{'F', 'M'}</values>
    birthplace TEXT NULL,
        -- <example>'Pittsfield MA US'</example>
    address TEXT NULL
        -- <example>'18797 Karson Burgs Suite 444 Palmer Town MA 01069 US'</example>
);

-- Table: procedures (10184 rows)
CREATE TABLE procedures (
    DATE DATE NULL,
        -- <example>'2013-02-09'</example>
    PATIENT TEXT NULL,
        -- <example>'71949668-1c2e-43ae-ab0a-64654608defb'</example>
        -- <fk> -> patients.patient</fk>
    ENCOUNTER TEXT NULL,
        -- <example>'6f2e3935-b203-493e-a9c0-f23e847b9798'</example>
        -- <fk> -> encounters.ID</fk>
    CODE INTEGER NULL,
        -- <example>23426006</example>
    DESCRIPTION TEXT NULL,
        -- <example>'Measurement of respiratory function (procedure)'</example>
    REASONCODE INTEGER NULL,
        -- <example>10509002</example>
    REASONDESCRIPTION TEXT NULL,
        -- <example>'Acute bronchitis (disorder)'</example>
    FOREIGN KEY (ENCOUNTER) REFERENCES encounters(ID),
    FOREIGN KEY (PATIENT) REFERENCES patients(patient)
);
```