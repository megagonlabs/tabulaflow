```sql
-- Database: thrombosis_prediction

/*
Schema: NULL
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
    "ID" INTEGER NULL,
        -- <description>patient identifier referencing Patient.ID (foreign key linking this examination record to a patient)</description>
        -- <example>14872</example>
        -- <fk> -> Patient."ID"</fk>
    "Examination Date" DATE NULL,
        -- <description>Examination date — the calendar date on which the patient's examination (tests and observations) was performed and recorded.</description>
        -- <example>'1997-05-27'</example>
    "aCL IgG" REAL NOT NULL,
        -- <description>Anti-cardiolipin (aCL) IgG antibody concentration in the patient's blood — a measure of antiphospholipid antibody level used when evaluating autoimmune disorders and thrombosis risk.</description>
        -- <example>1.300</example>
    "aCL IgM" REAL NOT NULL,
        -- <description>Anti-cardiolipin (aCL) IgM antibody concentration measured at the examination — a serologic marker used to detect antiphospholipid antibodies and help assess thrombosis/autoimmune risk.</description>
        -- <example>1.600</example>
    "ANA" INTEGER NULL,
        -- <description>Anti‑nuclear antibody (ANA) titer — the measured ANA concentration/titer indicating presence and level of antinuclear antibodies, used to assess autoimmune activity (e.g., sample values like 256).</description>
        -- <example>256</example>
    "ANA Pattern" TEXT NULL,
        -- <description>ANA staining pattern from the antinuclear antibody (ANA) test</description>
        -- <example>'P'</example>
    "aCL IgA" INTEGER NOT NULL,
        -- <description>Anti‑cardiolipin IgA antibody level — concentration of anti‑cardiolipin (IgA) measured at the examination, used to detect antiphospholipid antibodies and help assess thrombotic risk.</description>
        -- <example>0</example>
    "Diagnosis" TEXT NULL,
        -- <description>Patient diagnoses — one or more comma-separated disease names or short clinical findings (may include comorbid conditions or symptoms); examples: 'MCTD, AMI', 'SLE', 'SjS'.</description>
        -- <example>'MCTD, AMI'</example>
    "KCT" TEXT NULL,
        -- <description>KCT result — kaolin clotting time, a coagulation‑screening test used to detect lupus anticoagulant and other clotting abnormalities.</description>
        -- <values>{'+', '-'}</values>
    "RVVT" TEXT NULL,
        -- <description>RVVT test result — Russell Viper Venom Time clotting assay interpretation (positive or negative).</description>
        -- <values>{'+', '-'}</values>
    "LAC" TEXT NULL,
        -- <description>Lupus anticoagulant (LAC) test result — a qualitative indicator of the presence of lupus anticoagulant associated with coagulation abnormalities.</description>
        -- <values>{'+', '-'}</values>
    "Symptoms" TEXT NULL,
        -- <description>Examination symptoms and clinical events — free-text notes of signs, symptoms or related clinical events observed at the examination (e.g., AMI, brain infarction/stroke, pulmonary emboli, DVT, leg ulcer, CNS lupus).</description>
        -- <example>'AMI'</example>
    "Thrombosis" INTEGER NOT NULL,
        -- <description>Thrombosis severity score — ordinal code for presence and severity of thrombosis (0 = no thrombosis; 1 = most serious; 2 = severe; 3 = mild).</description>
        -- <example>1</example>
    FOREIGN KEY ("ID") REFERENCES Patient("ID")
);

/*
Schema: NULL
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
    "ID" INTEGER NOT NULL,
        -- <description>Patient identifier for the laboratory record (links this row to a Patient)</description>
        -- <example>27654</example>
        -- <fk> -> Patient."ID"</fk>
    "Date" DATE NOT NULL,
        -- <description>Laboratory test date — the calendar date when the laboratory measurements were taken (recorded as YYYY-MM-DD; e.g., 1991-09-11).</description>
        -- <example>'1991-09-11'</example>
    "GOT" INTEGER NULL,
        -- <description>AST (GOT) liver enzyme level — measurement of glutamic oxaloacetic transaminase used to help assess hepatocellular injury or muscle damage; values above the usual reference (commonly <60) indicate possible tissue injury.</description>
        -- <example>34</example>
    "GPT" INTEGER NULL,
        -- <description>Serum alanine aminotransferase (ALT) activity — a liver enzyme used to detect hepatocellular injury or inflammation (commonly considered normal < 60).</description>
        -- <example>36</example>
    "LDH" INTEGER NULL,
        -- <description>Serum lactate dehydrogenase (LDH) level — a laboratory marker of tissue damage or cell turnover; values above ~500 are typically considered elevated.</description>
        -- <example>567</example>
    "ALP" INTEGER NULL,
        -- <description>Alkaline phosphatase (ALP) — patient serum ALP enzyme level; values above ~300 are considered elevated (indicating possible liver or bone pathology).</description>
        -- <example>166</example>
    "TP" REAL NULL,
        -- <description>Total protein level in the patient's blood (total serum protein), used to assess nutritional status and liver function; typical reference range approximately 6.0–8.5.</description>
        -- <example>4.500</example>
    "ALB" REAL NULL,
        -- <description>Serum albumin level — blood albumin concentration used to assess nutritional status and liver/kidney function; typical normal range ≈ 3.5–5.5.</description>
        -- <example>3.300</example>
    "UA" REAL NULL,
        -- <description>Serum uric acid concentration (measure of uric acid in the blood), used to assess hyperuricemia; clinical thresholds often cited: >8.0 (male) and >6.5 (female).</description>
        -- <example>3.800</example>
    "UN" INTEGER NULL,
        -- <description>Serum urea nitrogen — blood urea nitrogen level used to assess renal function and protein metabolism; values above the typical reference (<30) suggest renal impairment, dehydration, or increased protein catabolism.</description>
        -- <example>29</example>
    "CRE" REAL NULL,
        -- <description>Serum creatinine level — blood creatinine concentration used to assess kidney (renal) function; values below ~1.5 are considered normal (per original metadata).</description>
        -- <example>0.800</example>
    "T-BIL" REAL NULL,
        -- <description>Total bilirubin level in the patient's blood — a clinical marker of liver function and bilirubin clearance; values above ~2.0 (common normal upper limit) indicate elevated bilirubin/jaundice and possible hepatobiliary dysfunction.</description>
        -- <example>0.300</example>
    "T-CHO" INTEGER NULL,
        -- <description>Serum total cholesterol — the patient's total blood (serum) cholesterol level; values ≥250 are above the typical normal range (<250).</description>
        -- <example>165</example>
    "TG" INTEGER NULL,
        -- <description>Serum triglyceride level — the patient's blood triglyceride concentration; values above ~200 are commonly considered elevated (hypertriglyceridemia).</description>
        -- <example>185</example>
    "CPK" INTEGER NULL,
        -- <description>Creatine phosphokinase (CPK) level — serum enzyme measurement used to detect muscle injury (including myocardial or skeletal muscle); higher values indicate muscle damage. Metadata notes a typical upper bound of < 250.</description>
        -- <example>9</example>
    "GLU" INTEGER NULL,
        -- <description>Blood glucose level measured in the laboratory (patient blood glucose); values above about 180 are indicative of hyperglycemia and may reflect abnormal glucose control.</description>
        -- <example>88</example>
    "WBC" REAL NULL,
        -- <description>White blood cell count (peripheral leukocyte count) — patient’s measured WBC; typical reference range approximately 3.5–9.0 (as recorded).</description>
        -- <example>5.000</example>
    "RBC" REAL NULL,
        -- <description>Red blood cell count (RBC) — numeric measure of the patient’s red blood cells from a blood sample, used to evaluate anemia or erythrocytosis (typical reference ~3.5–6.0).</description>
        -- <example>2.600</example>
    "HGB" REAL NULL,
        -- <description>Blood hemoglobin concentration — the patient’s hemoglobin level used to evaluate anemia and oxygen-carrying capacity; typical reference range ≈ 10–17 (from original metadata).</description>
        -- <example>6.400</example>
    "HCT" REAL NULL,
        -- <description>Hematocrit — percentage of blood volume composed of red blood cells, used to assess anemia or polycythemia; typical reference range ~29–52%.</description>
        -- <example>20.300</example>
    "PLT" INTEGER NULL,
        -- <description>Platelet count — measure of circulating platelets used to evaluate bleeding and clotting risk; typical reference range ≈ 100–400.</description>
        -- <example>227</example>
    "PT" REAL NULL,
        -- <description>Prothrombin time — result of the PT coagulation test (seconds), used to assess blood clotting; normal range reported as <14 seconds.</description>
        -- <example>11.300</example>
    "APTT" INTEGER NULL,
        -- <description>Activated partial thromboplastin time (APTT) test result — a measure of intrinsic-pathway blood coagulation; prolonged values indicate slower clotting. Normal range: < 45 seconds.</description>
        -- <example>108</example>
    "FG" REAL NULL,
        -- <description>Fibrinogen level — a laboratory measure of plasma fibrinogen used to assess coagulation and clotting risk; typical reference range noted in the metadata is 150–450 (units not specified).</description>
        -- <example>27.000</example>
    "PIC" INTEGER NULL,
        -- <description>Plasmin–α2‑plasmin inhibitor complex (PIC) level — a blood fibrinolysis marker reflecting plasmin activity and fibrin degradation; elevated values suggest increased fibrinolysis or thrombotic activity.</description>
        -- <example>320</example>
    "TAT" INTEGER NULL,
        -- <description>Thrombin–antithrombin complex (TAT) level — a blood marker of thrombin generation and coagulation activation; elevated values indicate increased clotting/thrombogenic activity.</description>
        -- <example>77</example>
    "TAT2" INTEGER NULL,
        -- <description>Second thrombin–antithrombin complex measurement (TAT2), a laboratory marker of thrombin generation used to detect and monitor activation of coagulation; typically recorded as a follow-up or repeat TAT value to track changes over time.</description>
        -- <example>113</example>
    "U-PRO" TEXT NULL,
        -- <description>Urine protein result (proteinuria) — coded protein measurement reported using numeric values and qualitative codes.</description>
        -- <values>{'%%', '+1(30)', '+2(100)', '-', '-15', '0', '1', '100', '2', '3', '30', '300', '4', '>=1000', '>=300', 'TR'}</values>
    "IGG" INTEGER NULL,
        -- <description>Serum immunoglobulin G concentration — the patient’s IgG antibody level used to assess humoral immunity; dataset notes a typical reference range of about 900–2000 (units not specified), though recorded values in this table can vary (example: 339).</description>
        -- <example>339</example>
    "IGA" INTEGER NULL,
        -- <description>Serum immunoglobulin A (IgA) level — patient IgA concentration used to assess humoral immunity and some autoimmune conditions; dataset notes a typical normal range of about 80–500.</description>
        -- <example>145</example>
    "IGM" INTEGER NULL,
        -- <description>IgM antibody level (immunoglobulin M) — measures the patient’s IgM in blood; commonly used to assess recent or ongoing immune response. Normal range approximately 40–400 (units as in original lab reporting).</description>
        -- <example>46</example>
    "CRP" TEXT NULL,
        -- <description>C-reactive protein (CRP) measurement — a marker of systemic inflammation; values are typically numeric (examples: 0.48, 2.11, 6.5) but the column also contains non-numeric markers such as '-' or '+-' to indicate negative/indeterminate results; normal CRP is generally < 1.0.</description>
        -- <example>'0.6'</example>
    "RA" TEXT NULL,
        -- <description>Rheumatoid factor test result — qualitative indicator of the presence/degree of rheumatoid factor, commonly recorded with symbols or short codes (e.g. '-', '+', '+-', '2+', '7-').</description>
        -- <values>{'+', '+-', '-', '2+', '7-'}</values>
    "RF" TEXT NULL,
        -- <description>Rheumatoid factor (RF) test result — reported as a numeric or comparative text value (e.g. '<20.5', '324.4'); values above approximately 20 are typically considered elevated and suggest presence of rheumatoid factor.</description>
        -- <example>'<20.5'</example>
    "C3" INTEGER NULL,
        -- <description>Complement component 3 (C3) serum level — a laboratory complement test result (decreased values indicate complement consumption); values >35 are considered within the normal range.</description>
        -- <example>30</example>
    "C4" INTEGER NULL,
        -- <description>Complement C4 level (serum complement component 4), a clinical immunology marker used to assess complement system activity; normal range reported as >10.</description>
        -- <example>14</example>
    "RNP" TEXT NULL,
        -- <description>Anti-ribonuclear protein (RNP) antibody test result — reported as numeric titers or 'negative', used to detect anti‑RNP autoantibodies when evaluating autoimmune diseases (e.g., SLE).</description>
        -- <values>{'0', '1', '15', '16', '256', '4', '64', 'negative'}</values>
    "SM" TEXT NULL,
        -- <description>Anti‑SM (anti‑Smith) autoantibody test result — assay result used to help diagnose and monitor systemic lupus erythematosus (SLE); recorded as the reported value (e.g., 'negative' or numeric titer).</description>
        -- <values>{'0', '1', '2', '8', 'negative'}</values>
    "SC170" TEXT NULL,
        -- <description>Anti‑Scl‑70 (anti–topoisomerase I) antibody test result — indicates presence or level of anti‑Scl‑70 antibodies used to detect and monitor scleroderma; entries may be numeric titers or 'negative'.</description>
        -- <values>{'0', '1', '16', '4', 'negative'}</values>
    "SSA" TEXT NULL,
        -- <description>Anti‑SSA (Ro) antibody test result — indicates presence/level of anti‑SSA antibodies in the patient’s serum; used when evaluating or monitoring autoimmune diseases (e.g., Sjögren’s syndrome, SLE).</description>
        -- <values>{'0', '1', '16', '256', '4', '64', 'negative'}</values>
    "SSB" TEXT NULL,
        -- <description>Anti-SSB (La) antibody result — indicates presence/level of anti-SSB autoantibodies used to support diagnosis of autoimmune disorders (for example Sjögren's syndrome or SLE); a value of 'negative' denotes a normal (absent) result.</description>
        -- <values>{'0', '1', '2', '32', '8', 'negative'}</values>
    "CENTROMEA" TEXT NULL,
        -- <description>Anti‑centromere antibody test result indicating presence or absence of anti‑centromere antibodies used in evaluation of scleroderma / limited cutaneous systemic sclerosis.</description>
        -- <values>{'0', 'negative'}</values>
    "DNA" TEXT NULL,
        -- <description>Anti‑double‑stranded DNA (anti‑DNA) antibody level — a serologic measure used to detect and monitor autoimmune disease activity (notably systemic lupus erythematosus); reported in IU/mL (typical normal < 8 IU/mL).</description>
        -- <example>'41.9'</example>
    "DNA-II" INTEGER NULL,
        -- <description>Anti-DNA antibody level — numeric measurement of anti‑DNA (anti‑dsDNA) antibodies; values below 8 are generally considered within the normal range, higher values indicate elevated anti‑DNA associated with autoimmune activity.</description>
    PRIMARY KEY ("ID", "Date"),
    FOREIGN KEY ("ID") REFERENCES Patient("ID")
);

/*
Schema: NULL
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
    "ID" INTEGER NOT NULL PRIMARY KEY,
        -- <description>patient identifier — the unique primary key for the Patient table used to identify and link a patient across related records (e.g., Examination and Laboratory).</description>
        -- <example>2110</example>
    "SEX" TEXT NOT NULL,
        -- <description>Patient sex — the recorded gender of the patient; may be missing or left blank when unknown or unspecified.</description>
        -- <values>{'', 'F', 'M'}</values>
    "Birthday" DATE NULL,
        -- <description>Patient date of birth (birthdate of the patient; may be null when not recorded)</description>
        -- <example>'1934-02-13'</example>
    "Description" DATE NULL,
        -- <description>date when the patient's information was first recorded (first documentation date); null if not recorded</description>
        -- <example>'1994-02-14'</example>
    "First Date" DATE NULL,
        -- <description>Patient's first visit date to the hospital (date of the first recorded encounter).</description>
        -- <example>'1993-02-10'</example>
    "Admission" TEXT NOT NULL,
        -- <description>Patient admission status flag indicating whether the patient was managed as an inpatient or outpatient; encoded with symbolic legacy values and occasional empty/malformed entries.</description>
        -- <values>{'', '+', '+(', '-'}</values>
    "Diagnosis" TEXT NOT NULL
        -- <description>Patient diagnosis — one or more disease names (often comma-separated), sometimes annotated with qualifiers (e.g., 'susp.' for suspected).</description>
        -- <example>'RA susp.'</example>
);
```