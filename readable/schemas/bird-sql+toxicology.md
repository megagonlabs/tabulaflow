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
        -- <example>'TR000_1'</example>
    molecule_id TEXT NOT NULL,
        -- <example>'TR000'</example>
        -- <fk> -> molecule.molecule_id</fk>
    element TEXT NOT NULL,
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
        -- <example>'TR000_1_2'</example>
    molecule_id TEXT NOT NULL,
        -- <example>'TR000'</example>
        -- <fk> -> molecule.molecule_id</fk>
    bond_type TEXT NULL,
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
        -- <example>'TR000_1'</example>
        -- <fk> -> atom.atom_id</fk>
    atom_id2 TEXT NOT NULL,
        -- <example>'TR000_2'</example>
        -- <fk> -> atom.atom_id</fk>
    bond_id TEXT NOT NULL,
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
        -- <example>'TR000'</example>
    label TEXT NOT NULL
        -- <values>{'+', '-'}</values>
);
```