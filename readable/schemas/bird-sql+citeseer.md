```sql
-- Database: citeseer

-- Table: cites (4732 rows)
CREATE TABLE cites (
    cited_paper_id TEXT NOT NULL,  -- e.g. '100157'
    citing_paper_id TEXT NOT NULL,  -- e.g. '100157'
    PRIMARY KEY (cited_paper_id, citing_paper_id)
);

-- Table: content (105165 rows)
CREATE TABLE content (
    paper_id TEXT NOT NULL,  -- e.g. '100157'; FK -> paper.paper_id
    word_cited_id TEXT NOT NULL,  -- e.g. 'word1163'
    PRIMARY KEY (paper_id, word_cited_id),
    FOREIGN KEY (paper_id) REFERENCES paper(paper_id)
);

-- Table: paper (3312 rows)
CREATE TABLE paper (
    paper_id TEXT NOT NULL PRIMARY KEY,  -- e.g. '100157'
    class_label TEXT NOT NULL  -- values: {'AI', 'Agents', 'DB', 'HCI', 'IR', 'ML'}
);
```