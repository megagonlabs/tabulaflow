```sql
-- Database: codebase_comments

-- Table: Method (3508215 rows)
CREATE TABLE Method (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    Name TEXT,  -- e.g. 'HtmlSharp.HtmlParser.Feed'
    FullComment TEXT,  -- e.g. 'Feeds data into the parser'
    Summary TEXT,  -- e.g. 'Converts the query expression into text that corre...and that would be executed.  Useful for debugging.'
    ApiCalls TEXT,  -- e.g. 'System.String.IsNullOrEmpty HtmlSharp.HtmlParser.G...arp.HtmlParser.EndData HtmlSharp.HtmlParser.PopTag'
    CommentIsXml INTEGER,  -- e.g. 0
    SampledAt INTEGER,  -- e.g. 636430963695654788
    SolutionId INTEGER,  -- e.g. 1
    Lang TEXT,  -- e.g. 'en'
    NameTokenized TEXT  -- e.g. 'html parser feed'
);

-- Table: MethodParameter (5132027 rows)
CREATE TABLE MethodParameter (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    MethodId TEXT,  -- e.g. '1'
    Type TEXT,  -- e.g. 'System.String'
    Name TEXT  -- e.g. 'data'
);

-- Table: Repo (140990 rows)
CREATE TABLE Repo (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    Url TEXT,  -- e.g. 'https://github.com/wallerdev/htmlsharp.git'
    Stars INTEGER,  -- e.g. 14
    Forks INTEGER,  -- e.g. 2
    Watchers INTEGER,  -- e.g. 14
    ProcessedTime INTEGER  -- e.g. 636430963247108053
);

-- Table: Solution (338087 rows)
CREATE TABLE Solution (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    RepoId INTEGER,  -- e.g. 1
    Path TEXT,  -- e.g. 'wallerdev_htmlsharp\HtmlSharp.sln'
    ProcessedTime INTEGER,  -- e.g. 636430963695642191
    WasCompiled INTEGER  -- e.g. 1
);
```