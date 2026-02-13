```sql
-- Database: citeseer

/*
Table: cites
Rows: 4732
Sample rows:
| cited_paper_id   | citing_paper_id        |
|------------------|------------------------|
| 100157           | 100157                 |
| 100157           | 364207                 |
| 100157           | 38848                  |
| 100157           | bradshaw97introduction |
| 100157           | bylund99coordinating   |
| ...              | ...                    |
*/
CREATE TABLE cites (
    cited_paper_id TEXT NOT NULL,
        -- <example>'100157'</example>
    citing_paper_id TEXT NOT NULL,
        -- <example>'100157'</example>
    PRIMARY KEY (cited_paper_id, citing_paper_id)
);

/*
Table: content
Rows: 105165
Sample rows:
| paper_id   | word_cited_id   |
|------------|-----------------|
| 100157     | word1163        |
| 100157     | word1509        |
| 100157     | word1614        |
| 100157     | word1642        |
| 100157     | word1663        |
| ...        | ...             |
*/
CREATE TABLE content (
    paper_id TEXT NOT NULL,
        -- <example>'100157'</example>
        -- <fk> -> paper.paper_id</fk>
    word_cited_id TEXT NOT NULL,
        -- <example>'word1163'</example>
    PRIMARY KEY (paper_id, word_cited_id),
    FOREIGN KEY (paper_id) REFERENCES paper(paper_id)
);

/*
Table: paper
Rows: 3312
Sample rows:
| paper_id   | class_label   |
|------------|---------------|
| 100157     | Agents        |
| 100598     | IR            |
| 101570     | ML            |
| 10227      | ML            |
| 102637     | AI            |
| ...        | ...           |
*/
CREATE TABLE paper (
    paper_id TEXT NOT NULL PRIMARY KEY,
        -- <example>'100157'</example>
    class_label TEXT NOT NULL
        -- <values>{'AI', 'Agents', 'DB', 'HCI', 'IR', 'ML'}</values>
);
```