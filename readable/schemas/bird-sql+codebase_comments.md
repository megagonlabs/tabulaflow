```sql
-- Database: codebase_comments

/*
Table: Method
Rows: 3508215
Sample rows:
| Id   | Name                                     | FullComment                                    | Summary                                                                                                                | ApiCalls                                                                                                                                                                                                    | CommentIsXml   | SampledAt          | SolutionId   | Lang   | NameTokenized                        |
|------|------------------------------------------|------------------------------------------------|------------------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------|--------------------|--------------|--------|--------------------------------------|
| 1    | HtmlSharp.HtmlParser.Feed                | Feeds data into the parser                     | [NULL]                                                                                                                 | System.String.IsNullOrEmpty HtmlSharp.HtmlParser.GoAhead HtmlSharp.HtmlParser.EndData HtmlSharp.HtmlParser.PopTag                                                                                           | 0              | 636430963695654788 | 1            | [NULL] | html parser feed                     |
| 2    | HtmlSharp.HtmlParser.ParseDoctypeElement | interneral -- scan past <!ELEMENT declarations | [NULL]                                                                                                                 | HtmlSharp.HtmlParser.ScanName System.Collections.Generic.KeyValuePair.Value System.String.Substring System.String.Contains System.StringComparison.Ordinal System.String.IndexOf                            | 0              | 636430963695709898 | 1            | [NULL] | html parser parse doctype element    |
| 3    | IQ.Data.DbQueryProvider.GetQueryText     | <summary>
        /// Converts the query expression into text that corresponds to the command that ...       /// </summary>
        /// <param name="expression"></param>
        /// <returns></returns>                                                | Converts the query expression into text that corresponds to the command that would be executed.  Useful for debugging. | IQ.Data.DbQueryProvider.Translate IQ.Data.QueryLanguage.Format IQ.Data.SelectGatherer.Gather System....ectModel.ReadOnlyCollection.Select System.Collections.Generic.IEnumerable.ToArray System.String.Join | 1              | 636430963721734366 | 2            | en     | db query provider get query text     |
| 4    | IQ.Data.DbQueryProvider.Execute          | <summary>
        /// Execute the query expression (does translation, etc.)
        /// </summary>
        /// <param name="expression"></param>
        /// <returns></returns>                                                | Execute the query expression                                                                                           | IQ.Data.DbQueryProvider.GetExecutionPlan System.Linq.Expressions.LambdaExpression.Type System.Linq.E...essions.Expression.Lambda System.Linq.Expressions.LambdaExpression.Compile System.Linq.Expressions.E | 1              | 636430963721804459 | 2            | fr     | db query provider execute            |
| 5    | IQ.Data.DbQueryProvider.GetExecutionPlan | <summary>
        /// Convert the query expression into an execution plan
        /// </summary>
        /// <param name="expression"></param>
        /// <returns></returns>                                                | Convert the query expression into an execution plan                                                                    | System.Linq.Expressions.LambdaExpression.Body IQ.Data.DbQueryProvider.Translate IQ.RootQueryableFind...Expressions.Expression.Property System.Linq.Expressions.Expression.Convert IQ.Data.QueryPolicy.Build | 1              | 636430963721804459 | 2            | en     | db query provider get execution plan |
| ...  | ...                                      | ...                                            | ...                                                                                                                    | ...                                                                                                                                                                                                         | ...            | ...                | ...          | ...    | ...                                  |
*/
CREATE TABLE Method (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Name TEXT NOT NULL,
        -- <example>'HtmlSharp.HtmlParser.Feed'</example>
    FullComment TEXT NOT NULL,
        -- <example>'Feeds data into the parser'</example>
    Summary TEXT NULL,
        -- <example>'Converts the query expression into text that corre...and that would be executed.  Useful for debugging.'</example>
    ApiCalls TEXT NOT NULL,
        -- <example>'System.String.IsNullOrEmpty HtmlSharp.HtmlParser.G...arp.HtmlParser.EndData HtmlSharp.HtmlParser.PopTag'</example>
    CommentIsXml INTEGER NOT NULL,
        -- <example>0</example>
    SampledAt INTEGER NOT NULL,
        -- <example>636430963695654788</example>
    SolutionId INTEGER NOT NULL,
        -- <example>1</example>
    Lang TEXT NULL,
        -- <example>'en'</example>
    NameTokenized TEXT NOT NULL
        -- <example>'html parser feed'</example>
);

/*
Table: MethodParameter
Rows: 5132027
Sample rows:
| Id   | MethodId   | Type                               | Name         |
|------|------------|------------------------------------|--------------|
| 1    | 1          | System.String                      | data         |
| 2    | 2          | System.Int32                       | i            |
| 3    | 2          | System.Int32                       | declstartpos |
| 4    | 3          | System.Linq.Expressions.Expression | expression   |
| 5    | 3          | IQ.Data.SelectExpression           | s            |
| ...  | ...        | ...                                | ...          |
*/
CREATE TABLE MethodParameter (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    MethodId TEXT NOT NULL,
        -- <example>'1'</example>
    Type TEXT NOT NULL,
        -- <example>'System.String'</example>
    Name TEXT NOT NULL
        -- <example>'data'</example>
);

/*
Table: Repo
Rows: 140990
Sample rows:
| Id   | Url                                                   | Stars   | Forks   | Watchers   | ProcessedTime      |
|------|-------------------------------------------------------|---------|---------|------------|--------------------|
| 1    | https://github.com/wallerdev/htmlsharp.git            | 14      | 2       | 14         | 636430963247108053 |
| 2    | https://github.com/unclebob/nslim.git                 | 6       | 3       | 6          | 636472436323838240 |
| 3    | https://github.com/maravillas/linq-to-delicious.git   | 6       | 0       | 6          | 636430963280029575 |
| 4    | https://github.com/mauriciodeamorim/tdd.encontro2.git | 3       | 0       | 3          | 636430963299356346 |
| 5    | https://github.com/aroder/heatmap.git                 | 1       | 0       | 1          | 636472436346806990 |
| ...  | ...                                                   | ...     | ...     | ...        | ...                |
*/
CREATE TABLE Repo (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Url TEXT NOT NULL,
        -- <example>'https://github.com/wallerdev/htmlsharp.git'</example>
    Stars INTEGER NOT NULL,
        -- <example>14</example>
    Forks INTEGER NOT NULL,
        -- <example>2</example>
    Watchers INTEGER NOT NULL,
        -- <example>14</example>
    ProcessedTime INTEGER NOT NULL
        -- <example>636430963247108053</example>
);

/*
Table: Solution
Rows: 338087
Sample rows:
| Id   | RepoId   | Path                                             | ProcessedTime      | WasCompiled   |
|------|----------|--------------------------------------------------|--------------------|---------------|
| 1    | 1        | wallerdev_htmlsharp\HtmlSharp.sln                | 636430963695642191 | 1             |
| 2    | 3        | maravillas_linq-to-delicious\tasty.sln           | 636430963721734366 | 1             |
| 3    | 4        | mauriciodeamorim_tdd.encontro2\Tdd.Encontro2.sln | 636430963735704849 | 1             |
| 4    | 5        | aroder_heatmap\CenStatsHeatMap.sln               | 636430963750457674 | 0             |
| 5    | 6        | managedfusion_managedfusion\ManagedFusion.sln    | 636430963775379234 | 1             |
| ...  | ...      | ...                                              | ...                | ...           |
*/
CREATE TABLE Solution (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    RepoId INTEGER NOT NULL,
        -- <example>1</example>
    Path TEXT NOT NULL,
        -- <example>'wallerdev_htmlsharp\HtmlSharp.sln'</example>
    ProcessedTime INTEGER NOT NULL,
        -- <example>636430963695642191</example>
    WasCompiled INTEGER NOT NULL
        -- <example>1</example>
);
```