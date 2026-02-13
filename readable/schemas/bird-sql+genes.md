```sql
-- Database: genes

/*
Schema: NULLTable: Classification
Rows: 862
Sample rows:
| GeneID   | Localization   |
|----------|----------------|
| G234064  | cytoplasm      |
| G234065  | cytoplasm      |
| G234070  | cytoskeleton   |
| G234073  | cytoplasm      |
| G234074  | cytoplasm      |
| ...      | ...            |
*/
CREATE TABLE Classification (
    GeneID TEXT NOT NULL PRIMARY KEY,
        -- <example>'G234064'</example>
    Localization TEXT NOT NULL
        -- <example>'cytoplasm'</example>
);

/*
Schema: NULLTable: Genes
Rows: 4346
Sample rows:
| GeneID   | Essential     | Class                           | Complex               | Phenotype   | Motif   | Chromosome   | Function                                                                      | Localization   |
|----------|---------------|---------------------------------|-----------------------|-------------|---------|--------------|-------------------------------------------------------------------------------|----------------|
| G234064  | Essential     | GTP/GDP-exchange factors (GEFs) | Translation complexes | ?           | PS00824 | 1            | CELLULAR ORGANIZATION (proteins are localized to the corresponding organelle) | cytoplasm      |
| G234064  | Essential     | GTP/GDP-exchange factors (GEFs) | Translation complexes | ?           | PS00824 | 1            | PROTEIN SYNTHESIS                                                             | cytoplasm      |
| G234064  | Essential     | GTP/GDP-exchange factors (GEFs) | Translation complexes | ?           | PS00825 | 1            | CELLULAR ORGANIZATION (proteins are localized to the corresponding organelle) | cytoplasm      |
| G234064  | Essential     | GTP/GDP-exchange factors (GEFs) | Translation complexes | ?           | PS00825 | 1            | PROTEIN SYNTHESIS                                                             | cytoplasm      |
| G234065  | Non-Essential | ATPases                         | ?                     | ?           | ?       | 1            | CELL RESCUE, DEFENSE, CELL DEATH AND AGEING                                   | cytoplasm      |
| ...      | ...           | ...                             | ...                   | ...         | ...     | ...          | ...                                                                           | ...            |
*/
CREATE TABLE Genes (
    GeneID TEXT NOT NULL,
        -- <example>'G234064'</example>
        -- <fk> -> Classification.GeneID</fk>
    Essential TEXT NOT NULL,
        -- <values>{'?', 'Ambiguous-Essential', 'Essential', 'Non-Essential'}</values>
    Class TEXT NOT NULL,
        -- <example>'GTP/GDP-exchange factors (GEFs)'</example>
    Complex TEXT NOT NULL,
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

/*
Schema: NULLTable: Interactions
Rows: 910
Sample rows:
| GeneID1   | GeneID2   | Type             | Expression_Corr   |
|-----------|-----------|------------------|-------------------|
| G234064   | G234126   | Genetic-Physical | 0.914095071       |
| G234064   | G235065   | Genetic-Physical | 0.751584888       |
| G234065   | G234371   | Genetic          | 0.823773738       |
| G234065   | G234854   | Physical         | 0.939001091       |
| G234073   | G234065   | Physical         | 0.749192312       |
| ...       | ...       | ...              | ...               |
*/
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