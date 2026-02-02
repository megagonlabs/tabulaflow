```sql
-- Database: toxicology

-- Table: atom (12333 rows)
CREATE TABLE atom (
    atom_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Atom identifier string combining the molecule code and atom index (format TRxxx_i). Example: TR238_12.</description>
        -- <example>'TR000_1'</example>
    molecule_id TEXT NULL,
        -- <description>Parent molecule identifier for the atom — links each atom row to its molecule (references molecule.molecule_id). Values use the TRxxx code that matches the prefix of atom.atom_id (e.g., TR186).</description>
        -- <example>'TR000'</example>
        -- <fk> -> molecule.molecule_id</fk>
    element TEXT NULL,
        -- <description>Chemical element of the atom — the chemical element (element symbol) represented by that atom within the molecule.</description>
        -- <example>'cl'</example>
    FOREIGN KEY (molecule_id) REFERENCES molecule(molecule_id)
);

-- Table: bond (12379 rows)
CREATE TABLE bond (
    bond_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Unique bond identifier encoding the molecule and the two connected atom IDs (format: TRxxx_A1_A2, e.g. TR301_28_32).</description>
        -- <example>'TR000_1_2'</example>
    molecule_id TEXT NULL,
        -- <description>Parent molecule identifier for the bond — indicates which molecule contains this bond (every row populated; 444 distinct molecule IDs across 12,379 rows).</description>
        -- <example>'TR000'</example>
        -- <fk> -> molecule.molecule_id</fk>
    bond_type TEXT NULL,
        -- <description>Bond order indicator — denotes the bond order between two atoms (maps '-' → single bond, '=' → double bond, '#' → triple bond). One row is NULL; most rows are single bonds.</description>
        -- <values>{'#', '-', '='}</values>
    FOREIGN KEY (molecule_id) REFERENCES molecule(molecule_id)
);

-- Table: connected (24758 rows)
CREATE TABLE connected (
    atom_id TEXT NOT NULL,
        -- <description>First atom identifier in a connected atom pair (the first atom of the bond; part of the composite primary key and a foreign key to atom.atom_id).</description>
        -- <example>'TR000_1'</example>
        -- <fk> -> atom.atom_id</fk>
    atom_id2 TEXT NOT NULL,
        -- <description>Identifier of the second atom in a connected atom pair.</description>
        -- <example>'TR000_2'</example>
        -- <fk> -> atom.atom_id</fk>
    bond_id TEXT NULL,
        -- <description>Bond identifier linking the atom pair — a foreign key to bond.bond_id that specifies which bond the two connected atoms belong to. Always populated and matches an entry in the bond table; each bond appears in connected twice (one row per atom ordering).</description>
        -- <example>'TR000_1_2'</example>
        -- <fk> -> bond.bond_id</fk>
    PRIMARY KEY (atom_id, atom_id2),
    FOREIGN KEY (bond_id) REFERENCES bond(bond_id),
    FOREIGN KEY (atom_id2) REFERENCES atom(atom_id),
    FOREIGN KEY (atom_id) REFERENCES atom(atom_id)
);

-- Table: molecule (343 rows)
CREATE TABLE molecule (
    molecule_id TEXT NOT NULL PRIMARY KEY,
        -- <description>molecule identifier — short alphanumeric code in the form 'TR' plus digits used to reference a molecule (examples: TR398, TR158, TR134).</description>
        -- <example>'TR000'</example>
    label TEXT NULL
        -- <description>Carcinogenicity label for the molecule ("+" = carcinogenic, "-" = non‑carcinogenic).</description>
        -- <values>{'+', '-'}</values>
);
```