```sql
-- Database: genes

-- Table: Classification (862 rows)
CREATE TABLE Classification (
    GeneID TEXT NOT NULL PRIMARY KEY,
        -- <example>'G234064'</example>
    Localization TEXT NOT NULL
        -- <example>'cytoplasm'</example>
);

-- Table: Genes (4346 rows)
CREATE TABLE Genes (
    GeneID TEXT NOT NULL,
        -- <example>'G234064'</example>
        -- <fk> -> Classification.GeneID</fk>
    Essential TEXT NOT NULL,
        -- <values>{'?', 'Ambiguous-Essential', 'Essential', 'Non-Essential'}</values>
    Class TEXT NOT NULL,
        -- <example>'GTP/GDP-exchange factors (GEFs)'</example>
    Complex TEXT NULL,
        -- <example>'Translation complexes'</example>
    Phenotype TEXT NOT NULL,
        -- <values>{'?', 'Auxotrophies, carbon and', 'Carbohydrate and lipid biosynthesis defects', 'Cell cycle defects', 'Cell morphology and organelle mutants', 'Conditional phenotypes', 'Mating and sporulation defects', 'Nucleic acid metabolism defects', 'Sensitivity to aminoacid analogs and other drugs', 'Sensitivity to antibiotics', 'Sensitivity to immunosuppressants', 'Stress response defects', 'Unknown'}</values>
    Motif TEXT NOT NULL,
        -- <example>'PS00824'</example>
    Chromosome INTEGER NOT NULL,
        -- <example>1</example>
    Function TEXT NOT NULL,
        -- <values>{'CELL GROWTH, CELL DIVISION AND DNA SYNTHESIS', 'CELL RESCUE, DEFENSE, CELL DEATH AND AGEING', 'CELLULAR BIOGENESIS (proteins are not localized to the corresponding organelle)', 'CELLULAR COMMUNICATION/SIGNAL TRANSDUCTION', 'CELLULAR ORGANIZATION (proteins are localized to the corresponding organelle)', 'CELLULAR TRANSPORT AND TRANSPORTMECHANISMS', 'ENERGY', 'IONIC HOMEOSTASIS', 'METABOLISM', 'PROTEIN DESTINATION', 'PROTEIN SYNTHESIS', 'TRANSCRIPTION', 'TRANSPORT FACILITATION'}</values>
    Localization TEXT NOT NULL,
        -- <values>{'ER', 'cell wall', 'cytoplasm', 'cytoskeleton', 'endosome', 'extracellular', 'golgi', 'integral membrane', 'lipid particles', 'mitochondria', 'nucleus', 'peroxisome', 'plasma membrane', 'transport vesicles', 'vacuole'}</values>
    FOREIGN KEY (GeneID) REFERENCES Classification(GeneID)
);

-- Table: Interactions (910 rows)
CREATE TABLE Interactions (
    GeneID1 TEXT NOT NULL,
        -- <example>'G234064'</example>
        -- <fk> -> Classification.GeneID</fk>
    GeneID2 TEXT NOT NULL,
        -- <example>'G234126'</example>
        -- <fk> -> Classification.GeneID</fk>
    Type TEXT NOT NULL,
        -- <values>{'Genetic', 'Genetic-Physical', 'Physical'}</values>
    Expression_Corr REAL NOT NULL,
        -- <example>0.914</example>
    PRIMARY KEY (GeneID1, GeneID2),
    FOREIGN KEY (GeneID1) REFERENCES Classification(GeneID),
    FOREIGN KEY (GeneID2) REFERENCES Classification(GeneID)
);
```