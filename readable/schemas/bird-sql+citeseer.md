```sql
-- Database: citeseer

-- Table: cites (4732 rows)
CREATE TABLE cites (
    cited_paper_id TEXT NOT NULL,
        -- <example>'100157'</example>
    citing_paper_id TEXT NOT NULL,
        -- <example>'100157'</example>
    PRIMARY KEY (cited_paper_id, citing_paper_id)
);

-- Table: content (105165 rows)
CREATE TABLE content (
    paper_id TEXT NOT NULL,
        -- <example>'100157'</example>
        -- <fk> -> paper.paper_id</fk>
    word_cited_id TEXT NOT NULL,
        -- <example>'word1163'</example>
    PRIMARY KEY (paper_id, word_cited_id),
    FOREIGN KEY (paper_id) REFERENCES paper(paper_id)
);

-- Table: paper (3312 rows)
CREATE TABLE paper (
    paper_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'100157'</example>
    class_label TEXT NOT NULL
        -- <values>{'AI', 'Agents', 'DB', 'HCI', 'IR', 'ML'}</values>
);
```