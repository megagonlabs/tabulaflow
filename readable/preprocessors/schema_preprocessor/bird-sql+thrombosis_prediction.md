```sql
-- Database: thrombosis_prediction

-- Table: Examination (806 rows)
CREATE TABLE Examination (
    ID INTEGER NULL,
        -- <description>patient identifier referencing Patient.ID — identifies which patient each examination record belongs to; nullable and not unique (multiple exam rows may share the same ID). In this dataset 36 of 806 rows are NULL; 770 non-null values map to 763 distinct IDs (7 duplicates). Many Examination.ID values do not match the Patient table (736 rows have no matching Patient.ID), suggesting broken or external references.</description>
        -- <example>14872</example>
        -- <fk> -> Patient.ID</fk>
    "Examination Date" DATE NULL,
        -- <description>examination date — date when the patient’s clinical examination was performed; in this dataset values range from 1989-04-18 to 1998-04-17 and 10 of 806 rows are null.</description>
        -- <example>'1997-05-27'</example>
    "aCL IgG" REAL NULL,
        -- <description>Anti‑cardiolipin IgG antibody level — patient serum concentration of anti‑cardiolipin (IgG) antibodies; typically used to detect antiphospholipid antibodies and support diagnosis/monitoring of antiphospholipid syndrome or other autoimmune activity.</description>
        -- <example>1.300</example>
    "aCL IgM" REAL NULL,
        -- <description>Anti‑cardiolipin (aCL) IgM antibody level in patient serum — numeric measurement of IgM-class anticardiolipin antibodies used in autoimmune/thrombosis assessment; higher values indicate greater antibody presence (observed in dataset: 806 non-null records; range 0–187,122; mean ≈ 238).</description>
        -- <example>1.600</example>
    ANA INTEGER NULL,
        -- <description>Anti‑nuclear antibody (ANA) result — numeric ANA titer/result recorded as discrete levels (commonly 0, 16, 64, 256, 4096); used to indicate ANA negativity/positivity and approximate titre.</description>
        -- <example>256</example>
    "ANA Pattern" TEXT NULL,
        -- <description>ANA immunofluorescence staining pattern — short letter codes (single letters or comma‑separated combinations) indicating the pattern seen on the ANA test; many records are missing (≈32% null).</description>
        -- <example>'P'</example>
    "aCL IgA" INTEGER NULL,
        -- <description>Anti‑cardiolipin (aCL) IgA antibody level — patient anti‑cardiolipin IgA measurement used in autoimmune/antiphospholipid evaluation. Many records are zero (409 of 806); observed range 0–48547, mean ≈66, 52 distinct values.</description>
        -- <example>0</example>
    Diagnosis TEXT NULL,
        -- <description>Clinical diagnosis recorded at the examination — free-text disease names (often comma-separated), e.g. SLE, SjS, MCTD; many rows are missing (331 of 806).</description>
        -- <example>'MCTD, AMI'</example>
    KCT TEXT NULL,
        -- <description>Kaolin Clotting Time (KCT) test result — an indicator of coagulation abnormality associated with lupus anticoagulant; positive indicates an abnormal/prolonged clotting result. Sparsely recorded in this dataset (present in 146 of 806 rows, 660 null/empty).</description>
        -- <values>{'+', '-'}</values>
    RVVT TEXT NULL,
        -- <description>Russell viper venom (RVVT) test result — a coagulation assay used to detect lupus anticoagulant; indicates whether the test is positive or negative (note: this column has many missing values in this dataset).</description>
        -- <values>{'+', '-'}</values>
    LAC TEXT NULL,
        -- <description>Lupus anticoagulant (LAC) qualitative result — flag for presence of lupus anticoagulant (positive vs negative); strongly under-recorded in this table (584 of 806 rows NULL, ~72%).</description>
        -- <values>{'+', '-'}</values>
    Symptoms TEXT NULL,
        -- <description>Other clinical symptoms recorded at the examination (free-text). Examples: CNS lupus, brain infarction, pulmonary emboli, DVT, leg ulcer. Sparse — present in 80 of 806 rows.</description>
        -- <example>'AMI'</example>
    Thrombosis INTEGER NULL,
        -- <description>Thrombosis severity indicator — ordinal code for thrombosis extent (0 = none, 1 = most severe, 2 = severe, 3 = mild).</description>
        -- <example>1</example>
    FOREIGN KEY (ID) REFERENCES Patient(ID)
);

-- Table: Laboratory (13908 rows)
CREATE TABLE Laboratory (
    ID INTEGER NOT NULL,
        -- <description>Patient identifier for a laboratory record.</description>
        -- <example>27654</example>
        -- <fk> -> Patient.ID</fk>
    Date DATE NOT NULL,
        -- <description>Date of the laboratory test (date when the specimen was collected / tests were performed).</description>
        -- <example>'1991-09-11'</example>
    GOT INTEGER NULL,
        -- <description>Serum aspartate aminotransferase (AST / GOT) activity — a clinical marker of hepatocellular or muscle injury (values above the normal range, N < 60, indicate elevation).</description>
        -- <example>34</example>
    GPT INTEGER NULL,
        -- <description>Alanine aminotransferase (ALT, also reported as GPT) — serum liver enzyme used to detect and monitor hepatocellular injury; values above the reference suggest liver cell damage (reference < 60 U/L).</description>
        -- <example>36</example>
    LDH INTEGER NULL,
        -- <description>Lactate dehydrogenase (LDH) level — serum enzyme concentration used as a nonspecific marker of tissue damage or hemolysis; values above the typical laboratory cutoff (~500) are considered elevated. Dataset notes: 11,305 of 13,908 rows populated (observed range ~25–67,080; mean ≈ 322).</description>
        -- <example>567</example>
    ALP INTEGER NULL,
        -- <description>Serum alkaline phosphatase level — routine liver/bone enzyme measurement; typical clinical cutoff noted as <300. Contains values ranging from 11 to 1308 (mean ≈122) with about 19.8% missing.</description>
        -- <example>166</example>
    TP REAL NULL,
        -- <description>Total serum protein — patient total protein concentration in serum, a general marker of nutritional and liver status (typical normal range ≈ 6.0–8.5). In this dataset 11,118 of 13,908 rows are non‑null; values range ~0–9.9 with mean ≈ 7.12.</description>
        -- <example>4.500</example>
    ALB REAL NULL,
        -- <description>Serum albumin concentration — patient's blood albumin level used to assess nutritional and liver status; normal range ≈ 3.5–5.5 (commonly reported in g/dL). Dataset: 11,068/13,908 records non‑null (mean ≈ 4.14, min 1.0, max 5.8).</description>
        -- <example>3.300</example>
    UA REAL NULL,
        -- <description>Serum uric acid level measured at each laboratory visit — used to assess hyperuricemia. In this dataset the column is populated in 11,103 of 13,908 rows (~79.8%), with values ranging ~0.4–17.3 and a mean ≈4.40. Reference thresholds are higher in males than females (commonly ≳8.0 for males, ≳6.5 for females).</description>
        -- <example>3.800</example>
    UN INTEGER NULL,
        -- <description>Serum urea nitrogen (blood urea nitrogen, BUN) level — numeric measure of urea nitrogen in the patient’s blood; values above ~30 are generally considered elevated. Observed range in the table: 0–152 (mean ≈ 15.4); 11,238 non-null entries (≈80.8% populated), 2,670 nulls (≈19.2%).</description>
        -- <example>29</example>
    CRE REAL NULL,
        -- <description>Serum creatinine level — blood creatinine concentration used to assess kidney (renal) function; values > 1.5 are typically considered above the normal range.</description>
        -- <example>0.800</example>
    "T-BIL" REAL NULL,
        -- <description>Total bilirubin (serum) level from the laboratory panel — a measure of bilirubin in blood; values above ≈2.0 are generally considered elevated (indicative of cholestasis/hepatic dysfunction).</description>
        -- <example>0.300</example>
    "T-CHO" INTEGER NULL,
        -- <description>Total cholesterol (T-CHO) level measured at each laboratory visit; used to assess lipid status (schema note: normal < 250). Present in 10,664 of 13,908 records (~76.7%); observed values range 37–568 with mean ≈203 and 325 distinct values.</description>
        -- <example>165</example>
    TG INTEGER NULL,
        -- <description>Serum triglyceride level — patient blood triglyceride concentration (clinical normal < 200).</description>
        -- <example>185</example>
    CPK INTEGER NULL,
        -- <description>Serum creatine phosphokinase (CPK) — enzyme level used to detect muscle or myocardial injury; values typically considered normal < 250.</description>
        -- <example>9</example>
    GLU INTEGER NULL,
        -- <description>Blood glucose level measured in the laboratory (likely mg/dL). High missingness — ~87.8% of rows are NULL; among non‑null values (n=2,705) observed range is 62–499 with mean ≈115.7. Used to assess glycaemia (hyperglycaemia/hypoglycaemia) at the time of the lab draw.</description>
        -- <example>88</example>
    WBC REAL NULL,
        -- <description>white blood cell count — peripheral blood leukocyte count (typical adult reference ≈ 3.5–9.0).</description>
        -- <example>5.000</example>
    RBC REAL NULL,
        -- <description>Red blood cell count — patient’s red blood cell concentration (RBC). Typical adult reference ≈ 3.5–6.0; in this table values range from 0.4 to 6.6 (mean ≈ 4.32). 1,827 of 13,908 rows are null.</description>
        -- <example>2.600</example>
    HGB REAL NULL,
        -- <description>Hemoglobin concentration in the patient's blood — a laboratory measure used to assess anemia and oxygen‑carrying capacity; commonly referenced normal range ≈ 10–17 (dataset range ~1.3–18.9, mean ≈ 12.4).</description>
        -- <example>6.400</example>
    HCT REAL NULL,
        -- <description>Hematocrit percentage — the proportion of blood volume made up of red blood cells (packed cell volume), a clinical indicator of anemia or polycythemia. Typical reference ~29–52%. Dataset notes: mean ≈ 37.9, observed range 3–56, ~13% missing; very low values (e.g., 3) likely represent outliers or data entry errors.</description>
        -- <example>20.300</example>
    PLT INTEGER NULL,
        -- <description>Platelet count — patient platelet measurement used to assess bleeding and clotting status (clinically ~100–400). Dataset: 11,287 non‑null values (mean ≈263); observed range 5–5844 — contains extreme outliers that may indicate entry/unit errors and should be checked.</description>
        -- <example>227</example>
    PT REAL NULL,
        -- <description>Prothrombin time (PT) — a coagulation test measuring time to form a blood clot (seconds); elevated values indicate prolonged clotting. Normal range ≲ 14 s. Note: this field is sparsely populated (~4.5% of Laboratory rows contain a value).</description>
        -- <example>11.300</example>
    APTT INTEGER NULL,
        -- <description>Activated partial thromboplastin time (APTT) — coagulation time in seconds (reference: <45 s). Values are very sparse in this dataset (51 non-null of 13,908) and span 57–146 s (mean ≈97.3 s), so recorded values are typically above the reference and coverage is limited.</description>
        -- <example>108</example>
    FG REAL NULL,
        -- <description>Fibrinogen level in the patient's blood (clinical fibrinogen). Normal range reported in metadata: ~150–450. In this dataset FG is very sparse (~455 non-null of 13,908 rows, ≈3.3%) and observed values range ≈23.8–106.5 (mean ≈43.3) — units/scale are not specified and appear inconsistent with the metadata range, so confirm units before using.</description>
        -- <example>27.000</example>
    PIC INTEGER NULL,
        -- <description>Plasma PIC (plasmin–α2‑plasmin inhibitor complex) level — a fibrinolysis/coagulation marker (units not recorded).</description>
        -- <example>320</example>
    TAT INTEGER NULL,
        -- <description>Thrombin–antithrombin complex (TAT) level — a coagulation marker reflecting thrombin generation; very sparsely populated (142 non-null of 13,908 rows, ~1%), observed values range ~63–183 with mean ≈121.</description>
        -- <example>77</example>
    TAT2 INTEGER NULL,
        -- <description>Additional/alternate thrombin–antithrombin (TAT) assay result — a second TAT measurement (likely the same analyte as TAT); units not recorded. Sparse: present in few rows.</description>
        -- <example>113</example>
    "U-PRO" TEXT NULL,
        -- <description>Urine protein (proteinuria) result — the measured amount of protein in the patient’s urine, recorded as numeric values or semi‑quantitative codes (e.g., '0', '30', '300', '>=1000', 'TR', '+1(30)', '-' for negative). Typical clinical reference noted in source: ~0–30 (normal). Many rows are null and the column mixes exact amounts and shorthand/trace notations.</description>
        -- <values>{'%%', '+1(30)', '+2(100)', '-', '-15', '0', '1', '100', '2', '3', '30', '300', '4', '>=1000', '>=300', 'TR'}</values>
    IGG INTEGER NULL,
        -- <description>Serum immunoglobulin G (IgG) level — total IgG concentration in patient serum, used to assess humoral (antibody-mediated) immunity. Dataset contains 2,680 non-null measurements (of 13,908 rows); observed values range ≈3–6510 with mean ≈1800. Metadata/notes suggest a typical reference range near 900–2000.</description>
        -- <example>339</example>
    IGA INTEGER NULL,
        -- <description>Serum immunoglobulin A (IgA) level — patient IgA concentration used to assess humoral immunity; commonly interpreted against a reference range of ~80–500 (units not specified). Sparsely populated in this table (2,680 of 13,908 records non-null); observed values range from 1 to 1,765.</description>
        -- <example>145</example>
    IGM INTEGER NULL,
        -- <description>Immunoglobulin M (IgM) level — serum IgM measurement; normal reference roughly 40–400 (units not recorded). Note: sparsely populated (≈19% non-null) and contains extreme values/outliers (observed range 0–1573).</description>
        -- <example>46</example>
    CRP TEXT NULL,
        -- <description>C-reactive protein result (inflammation marker) — values are mostly numeric strings but also include censored entries and missing markers (e.g. '<0.3', '-', NULL); convert/canonicalize to numeric (handle '<' as below detection limit) before analysis; clinically elevated ≳1.0.</description>
        -- <example>'0.6'</example>
    RA TEXT NULL,
        -- <description>Rheumatoid factor test result — qualitative interpretation of the rheumatoid factor (presence/absence and relative strength), used to support diagnosis of rheumatoid arthritis and other autoimmune disorders. Symbols like '+' and '-' denote positive/negative; variants such as '+-' or numeric modifiers (e.g. '2+') indicate borderline or stronger reactivity. Note: this field is frequently missing (~80% NULL).</description>
        -- <values>{'+', '+-', '-', '2+', '7-'}</values>
    RF TEXT NULL,
        -- <description>Rheumatoid factor test result — recorded as the reported value or qualifier (examples: '<20.5', '<40', 'negative', or numeric strings such as '57.9'). Contains many missing values.</description>
        -- <example>'<20.5'</example>
    C3 INTEGER NULL,
        -- <description>Complement C3 level — patient serum complement C3 test result used to assess complement-system activity (commonly interpreted with normal >35). Observed values in the table range ~15–196 with mean ≈70.7; substantial missingness (5,461 non-null of 13,908 rows).</description>
        -- <example>30</example>
    C4 INTEGER NULL,
        -- <description>Serum complement component 4 (C4) — patient serum complement protein level used to assess complement activation/deficiency; values ≤10 are considered low (normal >10). Many records in this dataset are missing.</description>
        -- <example>14</example>
    RNP TEXT NULL,
        -- <description>Anti-ribonucleoprotein (RNP) antibody test result — records whether anti‑RNP antibodies were detected (reported as text, typically numeric titer values or 'negative'). Used in autoimmune-disease evaluation. The column is very sparse (≈99% missing).</description>
        -- <values>{'0', '1', '15', '16', '256', '4', '64', 'negative'}</values>
    SM TEXT NULL,
        -- <description>anti‑SM (anti‑Smith) autoantibody test result used to help diagnose systemic lupus erythematosus (SLE). This laboratory antibody result is recorded infrequently in the dataset — only 128 non-null entries out of 13,908 rows.</description>
        -- <values>{'0', '1', '2', '8', 'negative'}</values>
    SC170 TEXT NULL,
        -- <description>Anti‑Scl‑70 (anti‑topoisomerase I) antibody test result — a serological marker used in the diagnosis of scleroderma; recorded values are sparse (only ~28 non-null out of 13,908 rows) and appear as 'negative' or small integer titers/codes (e.g. 0, 1, 4, 16).</description>
        -- <values>{'0', '1', '16', '4', 'negative'}</values>
    SSA TEXT NULL,
        -- <description>Anti‑SSA (Ro) autoantibody test result — qualitative/semiquantitative indicator of anti‑SSA (Ro) antibodies used in autoimmune disease workup.</description>
        -- <values>{'0', '1', '16', '256', '4', '64', 'negative'}</values>
    SSB TEXT NULL,
        -- <description>Anti-SSB (La) antibody test result — recorded as text codes/levels (examples: 'negative', '0', '1', '2', '8', '32'). Most entries are missing.</description>
        -- <values>{'0', '1', '2', '32', '8', 'negative'}</values>
    CENTROMEA TEXT NULL,
        -- <description>Anti‑centromere antibody test result — qualitative indicator used in autoimmune serology (presence/absence); recorded inconsistently and has very sparse coverage in this table.</description>
        -- <values>{'0', 'negative'}</values>
    DNA TEXT NULL,
        -- <description>Anti‑DNA (anti‑dsDNA) antibody level — reported in IU/mL (used to help diagnose/monitor autoimmune disease; common clinical cutoff ~<8 IU/mL). Sparsely populated in this table (69 non‑null values out of 13,908).</description>
        -- <example>'41.9'</example>
    PRIMARY KEY (ID, Date),
    FOREIGN KEY (ID) REFERENCES Patient(ID)
);

-- Table: Patient (1238 rows)
CREATE TABLE Patient (
    ID INTEGER NOT NULL PRIMARY KEY,
        -- <description>Patient identifier — unique identifier for each patient (one row per patient); non‑null and distinct across all 1,238 records.</description>
        -- <example>2110</example>
    SEX TEXT NULL,
        -- <description>Patient sex — recorded sex at registration. Values: 'F' = female, 'M' = male; empty string indicates missing/unrecorded.</description>
        -- <values>{'', 'F', 'M'}</values>
    Birthday DATE NULL,
        -- <description>Patient date of birth — mostly complete (1,237 of 1,238 rows present); observed values range from 1912-08-28 to 2007-05-28.</description>
        -- <example>'1934-02-13'</example>
    Description DATE NULL,
        -- <description>Initial patient-record date — the first date when this patient's information was entered into the dataset (initial recorded visit/date).</description>
        -- <example>'1994-02-14'</example>
    "First Date" DATE NULL,
        -- <description>Date of the patient's first recorded hospital visit or registration (first recorded encounter). May be missing for some patients — 251 of 1,238 rows are null; recorded values span 1972-08-02 to 1998-08-28.</description>
        -- <example>'1993-02-10'</example>
    Admission TEXT NULL,
        -- <description>Patient admission status indicating if the patient was admitted to hospital or followed as an outpatient.</description>
        -- <values>{'', '+', '+(', '-'}</values>
    Diagnosis TEXT NULL
        -- <description>Primary patient diagnosis — free-text disease name(s) recorded for each patient (mostly populated; 1 blank of 1,238). Common entries include SLE, SJS, RA.</description>
        -- <example>'RA susp.'</example>
);
```