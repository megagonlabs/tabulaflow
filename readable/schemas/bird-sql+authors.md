```sql
-- Database: authors

-- Table: Author (247030 rows)
CREATE TABLE Author (
    Id INTEGER NULL PRIMARY KEY,
        -- <example>9</example>
    Name TEXT NULL,
        -- <example>'Ernest Jordan'</example>
    Affiliation TEXT NULL
        -- <example>'Cavendish Laboratory|Cambridge University'</example>
);

-- Table: Conference (4545 rows)
CREATE TABLE Conference (
    Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    ShortName TEXT NULL,
        -- <example>'IADIS'</example>
    FullName TEXT NULL,
        -- <example>'International Association for Development of the Information Society'</example>
    HomePage TEXT NULL
        -- <example>''</example>
);

-- Table: Journal (15151 rows)
CREATE TABLE Journal (
    Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    ShortName TEXT NULL,
        -- <example>'ICOM'</example>
    FullName TEXT NULL,
        -- <example>'Zeitschrift Für Interaktive Und Kooperative Medien'</example>
    HomePage TEXT NULL
        -- <example>'http://www.i-com-media.de'</example>
);

-- Table: Paper (2254920 rows)
CREATE TABLE Paper (
    Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Title TEXT NULL,
        -- <example>'Stitching videos streamed by mobile phones in real-time'</example>
    Year INTEGER NULL,
        -- <example>2009</example>
    ConferenceId INTEGER NULL,
        -- <example>167</example>
        -- <fk> -> Conference.Id</fk>
    JournalId INTEGER NULL,
        -- <example>0</example>
        -- <fk> -> Journal.Id</fk>
    Keyword TEXT NULL,
        -- <example>'mobile video capturing|real-time|video stitching'</example>
    FOREIGN KEY (ConferenceId) REFERENCES Conference(Id),
    FOREIGN KEY (JournalId) REFERENCES Journal(Id)
);

-- Table: PaperAuthor (2315574 rows)
CREATE TABLE PaperAuthor (
    PaperId INTEGER NULL,
        -- <example>4</example>
        -- <fk> -> Paper.Id</fk>
    AuthorId INTEGER NULL,
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