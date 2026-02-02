```sql
-- Database: thrombosis_prediction

-- Table: Examination (806 rows)
CREATE TABLE Examination (
    ID INTEGER NULL,
        -- <example>14872</example>
        -- <fk> -> Patient.ID</fk>
    "Examination Date" DATE NULL,
        -- <example>'1997-05-27'</example>
    "aCL IgG" REAL NULL,
        -- <example>1.300</example>
    "aCL IgM" REAL NULL,
        -- <example>1.600</example>
    ANA INTEGER NULL,
        -- <example>256</example>
    "ANA Pattern" TEXT NULL,
        -- <example>'P'</example>
    "aCL IgA" INTEGER NULL,
        -- <example>0</example>
    Diagnosis TEXT NULL,
        -- <example>'MCTD, AMI'</example>
    KCT TEXT NULL,
        -- <values>{'+', '-'}</values>
    RVVT TEXT NULL,
        -- <values>{'+', '-'}</values>
    LAC TEXT NULL,
        -- <values>{'+', '-'}</values>
    Symptoms TEXT NULL,
        -- <example>'AMI'</example>
    Thrombosis INTEGER NULL,
        -- <example>1</example>
    FOREIGN KEY (ID) REFERENCES Patient(ID)
);

-- Table: Laboratory (13908 rows)
CREATE TABLE Laboratory (
    ID INTEGER NOT NULL,
        -- <example>27654</example>
        -- <fk> -> Patient.ID</fk>
    Date DATE NOT NULL,
        -- <example>'1991-09-11'</example>
    GOT INTEGER NULL,
        -- <example>34</example>
    GPT INTEGER NULL,
        -- <example>36</example>
    LDH INTEGER NULL,
        -- <example>567</example>
    ALP INTEGER NULL,
        -- <example>166</example>
    TP REAL NULL,
        -- <example>4.500</example>
    ALB REAL NULL,
        -- <example>3.300</example>
    UA REAL NULL,
        -- <example>3.800</example>
    UN INTEGER NULL,
        -- <example>29</example>
    CRE REAL NULL,
        -- <example>0.800</example>
    "T-BIL" REAL NULL,
        -- <example>0.300</example>
    "T-CHO" INTEGER NULL,
        -- <example>165</example>
    TG INTEGER NULL,
        -- <example>185</example>
    CPK INTEGER NULL,
        -- <example>9</example>
    GLU INTEGER NULL,
        -- <example>88</example>
    WBC REAL NULL,
        -- <example>5.000</example>
    RBC REAL NULL,
        -- <example>2.600</example>
    HGB REAL NULL,
        -- <example>6.400</example>
    HCT REAL NULL,
        -- <example>20.300</example>
    PLT INTEGER NULL,
        -- <example>227</example>
    PT REAL NULL,
        -- <example>11.300</example>
    APTT INTEGER NULL,
        -- <example>108</example>
    FG REAL NULL,
        -- <example>27.000</example>
    PIC INTEGER NULL,
        -- <example>320</example>
    TAT INTEGER NULL,
        -- <example>77</example>
    TAT2 INTEGER NULL,
        -- <example>113</example>
    "U-PRO" TEXT NULL,
        -- <values>{'%%', '+1(30)', '+2(100)', '-', '-15', '0', '1', '100', '2', '3', '30', '300', '4', '>=1000', '>=300', 'TR'}</values>
    IGG INTEGER NULL,
        -- <example>339</example>
    IGA INTEGER NULL,
        -- <example>145</example>
    IGM INTEGER NULL,
        -- <example>46</example>
    CRP TEXT NULL,
        -- <example>'0.6'</example>
    RA TEXT NULL,
        -- <values>{'+', '+-', '-', '2+', '7-'}</values>
    RF TEXT NULL,
        -- <example>'<20.5'</example>
    C3 INTEGER NULL,
        -- <example>30</example>
    C4 INTEGER NULL,
        -- <example>14</example>
    RNP TEXT NULL,
        -- <values>{'0', '1', '15', '16', '256', '4', '64', 'negative'}</values>
    SM TEXT NULL,
        -- <values>{'0', '1', '2', '8', 'negative'}</values>
    SC170 TEXT NULL,
        -- <values>{'0', '1', '16', '4', 'negative'}</values>
    SSA TEXT NULL,
        -- <values>{'0', '1', '16', '256', '4', '64', 'negative'}</values>
    SSB TEXT NULL,
        -- <values>{'0', '1', '2', '32', '8', 'negative'}</values>
    CENTROMEA TEXT NULL,
        -- <values>{'0', 'negative'}</values>
    DNA TEXT NULL,
        -- <example>'41.9'</example>
    "DNA-II" INTEGER NULL,
    PRIMARY KEY (ID, Date),
    FOREIGN KEY (ID) REFERENCES Patient(ID)
);

-- Table: Patient (1238 rows)
CREATE TABLE Patient (
    ID INTEGER NOT NULL PRIMARY KEY,
        -- <example>2110</example>
    SEX TEXT NULL,
        -- <values>{'', 'F', 'M'}</values>
    Birthday DATE NULL,
        -- <example>'1934-02-13'</example>
    Description DATE NULL,
        -- <example>'1994-02-14'</example>
    "First Date" DATE NULL,
        -- <example>'1993-02-10'</example>
    Admission TEXT NULL,
        -- <values>{'', '+', '+(', '-'}</values>
    Diagnosis TEXT NULL
        -- <example>'RA susp.'</example>
);
```