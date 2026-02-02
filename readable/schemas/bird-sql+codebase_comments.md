```sql
-- Database: codebase_comments

-- Table: Method (3508215 rows)
CREATE TABLE Method (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NULL,
        -- <example>'HtmlSharp.HtmlParser.Feed'</example>
    FullComment TEXT NULL,
        -- <example>'Feeds data into the parser'</example>
    Summary TEXT NULL,
        -- <example>'Converts the query expression into text that corre...and that would be executed.  Useful for debugging.'</example>
    ApiCalls TEXT NULL,
        -- <example>'System.String.IsNullOrEmpty HtmlSharp.HtmlParser.G...arp.HtmlParser.EndData HtmlSharp.HtmlParser.PopTag'</example>
    CommentIsXml INTEGER NULL,
        -- <example>0</example>
    SampledAt INTEGER NULL,
        -- <example>636430963695654788</example>
    SolutionId INTEGER NULL,
        -- <example>1</example>
    Lang TEXT NULL,
        -- <example>'en'</example>
    NameTokenized TEXT NULL
        -- <example>'html parser feed'</example>
);

-- Table: MethodParameter (5132027 rows)
CREATE TABLE MethodParameter (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    MethodId TEXT NULL,
        -- <example>'1'</example>
    Type TEXT NULL,
        -- <example>'System.String'</example>
    Name TEXT NULL
        -- <example>'data'</example>
);

-- Table: Repo (140990 rows)
CREATE TABLE Repo (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Url TEXT NULL,
        -- <example>'https://github.com/wallerdev/htmlsharp.git'</example>
    Stars INTEGER NULL,
        -- <example>14</example>
    Forks INTEGER NULL,
        -- <example>2</example>
    Watchers INTEGER NULL,
        -- <example>14</example>
    ProcessedTime INTEGER NULL
        -- <example>636430963247108053</example>
);

-- Table: Solution (338087 rows)
CREATE TABLE Solution (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    RepoId INTEGER NULL,
        -- <example>1</example>
    Path TEXT NULL,
        -- <example>'wallerdev_htmlsharp\HtmlSharp.sln'</example>
    ProcessedTime INTEGER NULL,
        -- <example>636430963695642191</example>
    WasCompiled INTEGER NULL
        -- <example>1</example>
);
```