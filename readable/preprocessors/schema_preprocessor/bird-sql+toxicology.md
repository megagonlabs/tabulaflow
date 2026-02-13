```sql
-- Database: toxicology

/*
Table: atom
Rows: 12333
Sample rows:
| atom_id   | molecule_id   | element   |
|-----------|---------------|-----------|
| TR000_1   | TR000         | cl        |
| TR000_2   | TR000         | c         |
| TR000_3   | TR000         | cl        |
| TR000_4   | TR000         | cl        |
| TR000_5   | TR000         | h         |
| ...       | ...           | ...       |
*/
CREATE TABLE atom (
    atom_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Atom identifier — unique atom ID indicating the molecule and atom index, formatted as TRXXX_i (for example, TR000_1).</description>
        -- <example>'TR000_1'</example>
    molecule_id TEXT NOT NULL,
        -- <description>Molecule identifier for the atom’s parent molecule (molecule code like 'TR186' — appears as the prefix of atom_id, e.g., atom_id 'TR186_3').</description>
        -- <example>'TR000'</example>
        -- <fk> -> molecule.molecule_id</fk>
    element TEXT NOT NULL,
        -- <description>atom element symbol identifying the chemical element of the atom (stored as a short element code, e.g., standard atomic symbols)</description>
        -- <example>'cl'</example>
    FOREIGN KEY (molecule_id) REFERENCES molecule(molecule_id)
);

/*
Table: bond
Rows: 12379
Sample rows:
| bond_id     | molecule_id   | bond_type   |
|-------------|---------------|-------------|
| TR000_1_2   | TR000         | -           |
| TR000_2_3   | TR000         | -           |
| TR000_2_4   | TR000         | -           |
| TR000_2_5   | TR000         | -           |
| TR001_10_11 | TR001         | =           |
| ...         | ...           | ...         |
*/
CREATE TABLE bond (
    bond_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Bond identifier combining the molecule id and the two atom indices; format TRxxx_A1_A2 (TRxxx = molecule, A1/A2 = atom positions).</description>
        -- <example>'TR000_1_2'</example>
    molecule_id TEXT NOT NULL,
        -- <description>Molecule identifier linking this bond to the molecule that contains it.</description>
        -- <example>'TR000'</example>
        -- <fk> -> molecule.molecule_id</fk>
    bond_type TEXT NULL,
        -- <description>chemical bond order indicator — a symbol representing whether the connection between two atoms is a single, double, or triple bond.</description>
        -- <values>{'#', '-', '='}</values>
    FOREIGN KEY (molecule_id) REFERENCES molecule(molecule_id)
);

/*
Table: connected
Rows: 24758
Sample rows:
| atom_id   | atom_id2   | bond_id   |
|-----------|------------|-----------|
| TR000_1   | TR000_2    | TR000_1_2 |
| TR000_2   | TR000_1    | TR000_1_2 |
| TR000_2   | TR000_3    | TR000_2_3 |
| TR000_3   | TR000_2    | TR000_2_3 |
| TR000_2   | TR000_4    | TR000_2_4 |
| ...       | ...        | ...       |
*/
CREATE TABLE connected (
    atom_id TEXT NOT NULL,
        -- <description>first atom identifier in a connected atom pair; specifies the first atom involved in the connection (example: 'TR242_29').</description>
        -- <example>'TR000_1'</example>
        -- <fk> -> atom.atom_id</fk>
    atom_id2 TEXT NOT NULL,
        -- <description>Second atom identifier in a connection — the atom at the other end of the bond.</description>
        -- <example>'TR000_2'</example>
        -- <fk> -> atom.atom_id</fk>
    bond_id TEXT NOT NULL,
        -- <description>Bond identifier for the connection between the two atoms — references the corresponding bond record (bond.bond_id).</description>
        -- <example>'TR000_1_2'</example>
        -- <fk> -> bond.bond_id</fk>
    PRIMARY KEY (atom_id, atom_id2),
    FOREIGN KEY (bond_id) REFERENCES bond(bond_id),
    FOREIGN KEY (atom_id2) REFERENCES atom(atom_id),
    FOREIGN KEY (atom_id) REFERENCES atom(atom_id)
);

/*
Table: molecule
Rows: 343
Sample rows:
| molecule_id   | label   |
|---------------|---------|
| TR000         | +       |
| TR001         | +       |
| TR002         | -       |
| TR004         | -       |
| TR006         | +       |
| ...           | ...     |
*/
CREATE TABLE molecule (
    molecule_id TEXT NOT NULL PRIMARY KEY,
        -- <description>Molecule identifier code, typically in the form 'TR###' (for example 'TR000' or 'TR398'), used to name each molecule in the dataset.</description>
        -- <example>'TR000'</example>
    label TEXT NOT NULL
        -- <description>Carcinogenicity label for the molecule indicating whether the molecule is classified as carcinogenic.</description>
        -- <values>{'+', '-'}</values>
);
```