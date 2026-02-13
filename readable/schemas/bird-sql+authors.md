```sql
-- Database: authors

/*
Schema: NULLTable: Author
Rows: 247030
Sample rows:
| Id   | Name              | Affiliation                               |
|------|-------------------|-------------------------------------------|
| 9    | Ernest Jordan     | [NULL]                                    |
| 14   | K. MORIBE         | [NULL]                                    |
| 15   | D. Jakominich     | [NULL]                                    |
| 25   | William H. Nailon | [NULL]                                    |
| 37   | P. B. Littlewood  | Cavendish Laboratory|Cambridge University |
| ...  | ...               | ...                                       |
*/
CREATE TABLE Author (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>9</example>
    Name TEXT NULL,
        -- <example>'Ernest Jordan'</example>
    Affiliation TEXT NULL
        -- <example>'Cavendish Laboratory|Cambridge University'</example>
);

/*
Schema: NULLTable: Conference
Rows: 4545
Sample rows:
| Id   | ShortName   | FullName                                                             | HomePage                                                        |
|------|-------------|----------------------------------------------------------------------|-----------------------------------------------------------------|
| 1    | IADIS       | International Association for Development of the Information Society |                                                                 |
| 2    | IADT        | Issues and Applications of Database Technology                       | http://www.informatik.uni-trier.de/~ley/db/conf/iadt/index.html |
| 4    |             | IBM Germany Scientific Symposium Series                              | http://www.informatik.uni-trier.de/~ley/db/conf/ibm/index.html  |
| 5    | ICOMP       | International Conference on Internet Computing                       | http://www.informatik.uni-trier.de/~ley/db/conf/ic/index.html   |
| 6    | ICAC        | International Conference on Autonomic Computing                      | http://www.autonomic-conference.org/                            |
| ...  | ...         | ...                                                                  | ...                                                             |
*/
CREATE TABLE Conference (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    ShortName TEXT NOT NULL,
        -- <example>'IADIS'</example>
    FullName TEXT NOT NULL,
        -- <example>'International Association for Development of the Information Society'</example>
    HomePage TEXT NOT NULL
        -- <example>''</example>
);

/*
Schema: NULLTable: Journal
Rows: 15151
Sample rows:
| Id   | ShortName   | FullName                                                                  | HomePage                                          |
|------|-------------|---------------------------------------------------------------------------|---------------------------------------------------|
| 1    | ICOM        | Zeitschrift Für Interaktive Und Kooperative Medien                        | http://www.i-com-media.de                         |
| 2    | AEPIA       | Inteligencia Artificial,revista Iberoamericana De Inteligencia Artificial | http://aepia.dsic.upv.es/revista/                 |
| 3    | IBMRD       | Ibm Journal of Research and Development                                   | http://www-tr.watson.ibm.com/journal/rdindex.html |
| 4    | IBMSJ       | Ibm Systems Journal                                                       | http://researchweb.watson.ibm.com/journal/        |
| 5    |             | Iet Software/iee Proceedings - Software                                   | http://www.ietdl.org/IET-SEN                      |
| ...  | ...         | ...                                                                       | ...                                               |
*/
CREATE TABLE Journal (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    ShortName TEXT NOT NULL,
        -- <example>'ICOM'</example>
    FullName TEXT NOT NULL,
        -- <example>'Zeitschrift Für Interaktive Und Kooperative Medien'</example>
    HomePage TEXT NOT NULL
        -- <example>'http://www.i-com-media.de'</example>
);

/*
Schema: NULLTable: Paper
Rows: 2254920
Sample rows:
| Id   | Title                                                                                   | Year   | ConferenceId   | JournalId   | Keyword                                                        |
|------|-----------------------------------------------------------------------------------------|--------|----------------|-------------|----------------------------------------------------------------|
| 1    | Stitching videos streamed by mobile phones in real-time                                 | 2009   | 167            | 0           | mobile video capturing|real-time|video stitching               |
| 2    | A nonlocal convection–diffusion equation                                                | 2007   | 0              | 7234        | Nonlocal diffusion; Convection–diffusion; Asymptotic behaviour |
| 3    | Area Effects in Cepaea                                                                  | 1963   | 0              | 16867       | [NULL]                                                         |
| 4    | Multiple paternity in a natural population of a salamander with long-term sperm storage | 2005   | 0              | 6130        | [NULL]                                                         |
| 5    | Complexity of Finding Short Resolution Proofs                                           | 1997   | 158            | 0           | [NULL]                                                         |
| ...  | ...                                                                                     | ...    | ...            | ...         | ...                                                            |
*/
CREATE TABLE Paper (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Title TEXT NULL,
        -- <example>'Stitching videos streamed by mobile phones in real-time'</example>
    Year INTEGER NOT NULL,
        -- <example>2009</example>
    ConferenceId INTEGER NOT NULL,
        -- <example>167</example>
        -- <fk> -> Conference.Id</fk>
    JournalId INTEGER NOT NULL,
        -- <example>0</example>
        -- <fk> -> Journal.Id</fk>
    Keyword TEXT NULL,
        -- <example>'mobile video capturing|real-time|video stitching'</example>
    FOREIGN KEY (ConferenceId) REFERENCES Conference(Id),
    FOREIGN KEY (JournalId) REFERENCES Journal(Id)
);

/*
Schema: NULLTable: PaperAuthor
Rows: 2315574
Sample rows:
| PaperId   | AuthorId   | Name                | Affiliation                                           |
|-----------|------------|---------------------|-------------------------------------------------------|
| 4         | 1456512    | ADAM G. JONES       | [NULL]                                                |
| 5         | 1102257    | Kazuo Iwama         | Kyushu University 812 Fukuoka Japan 812 Fukuoka Japan |
| 6         | 1806301    | Asgeir Finnseth     | [NULL]                                                |
| 6         | 2252569    | Guðmundur Jökulsson | [NULL]                                                |
| 7         | 1491002    | M. H. Friedman      | [NULL]                                                |
| ...       | ...        | ...                 | ...                                                   |
*/
CREATE TABLE PaperAuthor (
    PaperId INTEGER NOT NULL,
        -- <example>4</example>
        -- <fk> -> Paper.Id</fk>
    AuthorId INTEGER NOT NULL,
        -- <example>1456512</example>
        -- <fk> -> Author.Id</fk>
    Name TEXT NULL,
        -- <example>'ADAM G. JONES'</example>
    Affiliation TEXT NULL,
        -- <example>'Kyushu University 812 Fukuoka Japan 812 Fukuoka Japan'</example>
    FOREIGN KEY (PaperId) REFERENCES Paper(Id),
    FOREIGN KEY (AuthorId) REFERENCES Author(Id)
);
```