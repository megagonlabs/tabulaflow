```sql
-- Database: thrombosis_prediction

/*
Table: Examination
Rows: 806
Sample rows:
| ID     | Examination Date   | aCL IgG   | aCL IgM   | ANA   | ANA Pattern   | aCL IgA   | Diagnosis         | KCT    | RVVT   | LAC    | Symptoms   | Thrombosis   |
|--------|--------------------|-----------|-----------|-------|---------------|-----------|-------------------|--------|--------|--------|------------|--------------|
| 14872  | 1997-05-27         | 1.3       | 1.6       | 256   | P             | 0         | MCTD, AMI         | [NULL] | [NULL] | -      | AMI        | 1            |
| 48473  | 1992-12-21         | 4.3       | 4.6       | 256   | P,S           | 3         | SLE               | -      | -      | -      | [NULL]     | 0            |
| 102490 | 1995-04-20         | 2.3       | 2.5       | 0     | [NULL]        | 4         | PSS               | [NULL] | [NULL] | [NULL] | [NULL]     | 0            |
| 108788 | 1997-05-06         | 0.0       | 0.0       | 16    | S             | 0         | [NULL]            | [NULL] | [NULL] | -      | [NULL]     | 0            |
| 122405 | 1998-04-02         | 0.0       | 4.0       | 4     | P             | 0         | SLE, SjS, vertigo | [NULL] | [NULL] | [NULL] | [NULL]     | 0            |
| ...    | ...                | ...       | ...       | ...   | ...           | ...       | ...               | ...    | ...    | ...    | ...        | ...          |
*/
CREATE TABLE Examination (
    ID INTEGER NULL,
        -- <example>14872</example>
        -- <fk> -> Patient.ID</fk>
    "Examination Date" DATE NULL,
        -- <example>'1997-05-27'</example>
    "aCL IgG" REAL NOT NULL,
        -- <example>1.300</example>
    "aCL IgM" REAL NOT NULL,
        -- <example>1.600</example>
    ANA INTEGER NULL,
        -- <example>256</example>
    "ANA Pattern" TEXT NULL,
        -- <example>'P'</example>
    "aCL IgA" INTEGER NOT NULL,
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
    Thrombosis INTEGER NOT NULL,
        -- <example>1</example>
    FOREIGN KEY (ID) REFERENCES Patient(ID)
);

/*
Table: Laboratory
Rows: 13908
Sample rows:
| ID    | Date       | GOT    | GPT    | LDH    | ALP    | TP     | ALB    | UA     | UN     | CRE    | T-BIL   | T-CHO   | TG     | CPK    | GLU    | WBC   | RBC   | HGB   | HCT   | PLT   | PT     | APTT   | FG     | PIC    | TAT    | TAT2   | U-PRO   | IGG    | IGA    | IGM    | CRP    | RA     | RF     | C3     | C4     | RNP    | SM     | SC170   | SSA    | SSB    | CENTROMEA   | DNA    | DNA-II   |
|-------|------------|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|---------|--------|--------|--------|-------|-------|-------|-------|-------|--------|--------|--------|--------|--------|--------|---------|--------|--------|--------|--------|--------|--------|--------|--------|--------|--------|---------|--------|--------|-------------|--------|----------|
| 27654 | 1991-09-11 | 34.0   | 36.0   | 567.0  | 166.0  | 4.5    | 3.3    | 3.8    | 29.0   | 0.8    | 0.3     | 165.0   | [NULL] | 9.0    | [NULL] | 5.0   | 2.6   | 6.4   | 20.3  | 227   | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | 339.0  | 145.0  | 46.0   | 0.6    | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL]      | [NULL] | [NULL]   |
| 27654 | 1991-09-17 | 29.0   | 31.0   | 579.0  | 154.0  | 5.1    | 3.4    | 4.2    | 36.0   | 0.8    | [NULL]  | [NULL]  | [NULL] | [NULL] | [NULL] | 10.4  | 2.9   | 6.7   | 21.6  | 242   | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | 771.0  | 188.0  | 132.0  | 0.6    | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL]      | [NULL] | [NULL]   |
| 27654 | 1991-09-19 | 26.0   | 22.0   | 684.0  | 138.0  | 5.5    | 3.6    | 4.9    | 34.0   | 0.9    | [NULL]  | [NULL]  | [NULL] | [NULL] | 88.0   | 10.5  | 3.4   | 7.9   | 24.7  | 233   | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | 2.7    | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL]      | [NULL] | [NULL]   |
| 27654 | 1991-09-20 | 23.0   | 18.0   | 552.0  | 131.0  | 4.2    | 2.9    | 4.8    | 22.0   | 0.7    | 0.2     | 134.0   | [NULL] | 10.0   | [NULL] | 10.3  | 2.6   | 6.1   | 19.3  | 201   | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | 430.0  | 118.0  | 56.0   | 1.2    | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL]      | [NULL] | [NULL]   |
| 27654 | 1991-09-21 | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL]  | [NULL] | [NULL] | [NULL] | 14.3  | 3.2   | 7.2   | 23.4  | 215   | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL]      | [NULL] | [NULL]   |
| ...   | ...        | ...    | ...    | ...    | ...    | ...    | ...    | ...    | ...    | ...    | ...     | ...     | ...    | ...    | ...    | ...   | ...   | ...   | ...   | ...   | ...    | ...    | ...    | ...    | ...    | ...    | ...     | ...    | ...    | ...    | ...    | ...    | ...    | ...    | ...    | ...    | ...    | ...     | ...    | ...    | ...         | ...    | ...      |
*/
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

/*
Table: Patient
Rows: 1238
Sample rows:
| ID    | SEX   | Birthday   | Description   | First Date   | Admission   | Diagnosis    |
|-------|-------|------------|---------------|--------------|-------------|--------------|
| 2110  | F     | 1934-02-13 | 1994-02-14    | 1993-02-10   | +           | RA susp.     |
| 11408 | F     | 1937-05-02 | 1996-12-01    | 1973-01-01   | +           | PSS          |
| 12052 | F     | 1956-04-14 | 1991-08-13    | [NULL]       | +           | SLE          |
| 14872 | F     | 1953-09-21 | 1997-08-13    | [NULL]       | +           | MCTD         |
| 27654 | F     | 1936-03-25 | [NULL]        | 1992-02-03   | +           | RA, SLE susp |
| ...   | ...   | ...        | ...           | ...          | ...         | ...          |
*/
CREATE TABLE Patient (
    ID INTEGER NOT NULL PRIMARY KEY,
        -- <example>2110</example>
    SEX TEXT NOT NULL,
        -- <values>{'', 'F', 'M'}</values>
    Birthday DATE NULL,
        -- <example>'1934-02-13'</example>
    Description DATE NULL,
        -- <example>'1994-02-14'</example>
    "First Date" DATE NULL,
        -- <example>'1993-02-10'</example>
    Admission TEXT NOT NULL,
        -- <values>{'', '+', '+(', '-'}</values>
    Diagnosis TEXT NOT NULL
        -- <example>'RA susp.'</example>
);
```