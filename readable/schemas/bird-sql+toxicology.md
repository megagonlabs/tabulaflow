```sql
-- Database: toxicology

-- Table: atom (12333 rows)
CREATE TABLE atom (
    atom_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'TR000_1'</example>
    molecule_id TEXT NULL,
        -- <example>'TR000'</example>
        -- <fk> -> molecule.molecule_id</fk>
    element TEXT NULL,
        -- <example>'cl'</example>
    FOREIGN KEY (molecule_id) REFERENCES molecule(molecule_id)
);

-- Table: bond (12379 rows)
CREATE TABLE bond (
    bond_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'TR000_1_2'</example>
    molecule_id TEXT NULL,
        -- <example>'TR000'</example>
        -- <fk> -> molecule.molecule_id</fk>
    bond_type TEXT NULL,
        -- <values>{'#', '-', '='}</values>
    FOREIGN KEY (molecule_id) REFERENCES molecule(molecule_id)
);

-- Table: connected (24758 rows)
CREATE TABLE connected (
    atom_id TEXT NOT NULL,
        -- <example>'TR000_1'</example>
        -- <fk> -> atom.atom_id</fk>
    atom_id2 TEXT NOT NULL,
        -- <example>'TR000_2'</example>
        -- <fk> -> atom.atom_id</fk>
    bond_id TEXT NULL,
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
        -- <example>'TR000'</example>
    label TEXT NULL
        -- <values>{'+', '-'}</values>
);
```