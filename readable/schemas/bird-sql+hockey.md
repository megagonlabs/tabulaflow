```sql
-- Database: hockey

/*
Schema: NULL
Table: AwardsCoaches
Rows: 77
Sample rows:
| coachID    | award                | year   | lgID   | note   |
|------------|----------------------|--------|--------|--------|
| patrile01c | First Team All-Star  | 1930   | NHL    | [NULL] |
| irvindi01c | Second Team All-Star | 1930   | NHL    | [NULL] |
| patrile01c | First Team All-Star  | 1931   | NHL    | [NULL] |
| irvindi01c | Second Team All-Star | 1931   | NHL    | [NULL] |
| patrile01c | First Team All-Star  | 1932   | NHL    | [NULL] |
| ...        | ...                  | ...    | ...    | ...    |
*/
CREATE TABLE AwardsCoaches (
    "coachID" TEXT NOT NULL,
        -- <example>'patrile01c'</example>
        -- <fk> -> Coaches."coachID"</fk>
    "award" TEXT NOT NULL,
        -- <values>{'Baldwin', 'First Team All-Star', 'Jack Adams', 'Schmertz', 'Second Team All-Star'}</values>
    "year" INTEGER NOT NULL,
        -- <example>1930</example>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHL', 'WHA'}</values>
    "note" TEXT NULL,
    FOREIGN KEY ("coachID") REFERENCES Coaches("coachID")
);

/*
Schema: NULL
Table: AwardsMisc
Rows: 124
Sample rows:
| name                                  | ID        | award   | year   | lgID   | note   |
|---------------------------------------|-----------|---------|--------|--------|--------|
| 1960 U.S. Olympic Hockey Team         | [NULL]    | Patrick | 2001   | NHL    | [NULL] |
| 1998 U.S. Olympic Women's Hockey Team | [NULL]    | Patrick | 1998   | NHL    | [NULL] |
| Al Arbour                             | arboual01 | Patrick | 1991   | NHL    | [NULL] |
| Alex Delvecchio                       | delveal01 | Patrick | 1973   | NHL    | [NULL] |
| Art Berglund                          | [NULL]    | Patrick | 1991   | NHL    | [NULL] |
| ...                                   | ...       | ...     | ...    | ...    | ...    |
*/
CREATE TABLE AwardsMisc (
    "name" TEXT NOT NULL PRIMARY KEY,
        -- <example>'1960 U.S. Olympic Hockey Team'</example>
    "ID" TEXT NULL,
        -- <example>'arboual01'</example>
    "award" TEXT NOT NULL,
        -- <values>{'Patrick'}</values>
    "year" INTEGER NOT NULL,
        -- <example>2001</example>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHL'}</values>
    "note" TEXT NULL
        -- <values>{'posthumous'}</values>
);

/*
Schema: NULL
Table: AwardsPlayers
Rows: 2091
Sample rows:
| playerID   | award                | year   | lgID   | note   | pos    |
|------------|----------------------|--------|--------|--------|--------|
| abelsi01   | First Team All-Star  | 1948   | NHL    | [NULL] | C      |
| abelsi01   | First Team All-Star  | 1949   | NHL    | [NULL] | C      |
| abelsi01   | Hart                 | 1948   | NHL    | [NULL] | [NULL] |
| abelsi01   | Second Team All-Star | 1941   | NHL    | [NULL] | LW     |
| abelsi01   | Second Team All-Star | 1950   | NHL    | tie    | C      |
| ...        | ...                  | ...    | ...    | ...    | ...    |
*/
CREATE TABLE AwardsPlayers (
    "playerID" TEXT NOT NULL,
        -- <example>'abelsi01'</example>
        -- <fk> -> Master."playerID"</fk>
    "award" TEXT NOT NULL,
        -- <example>'First Team All-Star'</example>
    "year" INTEGER NOT NULL,
        -- <example>1948</example>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHL', 'WHA'}</values>
    "note" TEXT NULL,
        -- <values>{'Best Defenceman', 'Best Goaltender', 'MVP', 'Most Gentlemanly', 'Rookie', 'Scoring', 'shared', 'tie'}</values>
    "pos" TEXT NULL,
        -- <values>{'C', 'D', 'F', 'G', 'LW', 'RW', 'W'}</values>
    PRIMARY KEY ("playerID", "award", "year"),
    FOREIGN KEY ("playerID") REFERENCES Master("playerID")
);

/*
Schema: NULL
Table: Coaches
Rows: 1812
Sample rows:
| coachID   | year   | tmID   | lgID   | stint   | notes   | g   | w   | l   | t   | postg   | postw   | postl   | postt   |
|-----------|--------|--------|--------|---------|---------|-----|-----|-----|-----|---------|---------|---------|---------|
| abelsi01c | 1952   | CHI    | NHL    | 1       | [NULL]  | 70  | 27  | 28  | 15  | 7       | 3       | 4       | 0       |
| abelsi01c | 1953   | CHI    | NHL    | 1       | [NULL]  | 70  | 12  | 51  | 7   | [NULL]  | [NULL]  | [NULL]  | [NULL]  |
| abelsi01c | 1957   | DET    | NHL    | 2       | [NULL]  | 33  | 16  | 12  | 5   | 4       | 0       | 4       | 0       |
| abelsi01c | 1958   | DET    | NHL    | 1       | [NULL]  | 70  | 25  | 37  | 8   | [NULL]  | [NULL]  | [NULL]  | [NULL]  |
| abelsi01c | 1959   | DET    | NHL    | 1       | [NULL]  | 70  | 26  | 29  | 15  | 6       | 2       | 4       | 0       |
| ...       | ...    | ...    | ...    | ...     | ...     | ... | ... | ... | ... | ...     | ...     | ...     | ...     |
*/
CREATE TABLE Coaches (
    "coachID" TEXT NOT NULL,
        -- <example>'abelsi01c'</example>
    "year" INTEGER NOT NULL,
        -- <example>1952</example>
        -- <fk>composite</fk>
    "tmID" TEXT NOT NULL,
        -- <example>'CHI'</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    "stint" INTEGER NOT NULL,
        -- <example>1</example>
    "notes" TEXT NULL,
        -- <values>{'co-coach with Barry Smith', 'co-coach with Dave Lewis', 'interim'}</values>
    "g" INTEGER NULL,
        -- <example>70</example>
    "w" INTEGER NULL,
        -- <example>27</example>
    "l" INTEGER NULL,
        -- <example>28</example>
    "t" INTEGER NULL,
        -- <example>15</example>
    "postg" TEXT NULL,
        -- <example>'7'</example>
    "postw" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '15', '16', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "postl" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "postt" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    PRIMARY KEY ("coachID", "year", "tmID", "stint"),
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID")
);

/*
Schema: NULL
Table: CombinedShutouts
Rows: 54
Sample rows:
| year   | month   | date   | tmID   | oppID   | R/P   | IDgoalie1   | IDgoalie2   |
|--------|---------|--------|--------|---------|-------|-------------|-------------|
| 1929   | 3       | 14     | TOR    | NYA     | R     | chabolo01   | grantbe01   |
| 1941   | 3       | 15     | MTL    | NYA     | R     | bibeapa01   | gardibe01   |
| 1955   | 3       | 22     | MTL    | BOS     | P     | plantja01   | hodgech01   |
| 1968   | 2       | 14     | OAK    | PHI     | R     | smithga01   | hodgech01   |
| 1970   | 11      | 5      | STL    | BOS     | R     | hallgl01    | wakeler01   |
| ...    | ...     | ...    | ...    | ...     | ...   | ...         | ...         |
*/
CREATE TABLE CombinedShutouts (
    "year" INTEGER NOT NULL,
        -- <example>1929</example>
    "month" INTEGER NOT NULL,
        -- <example>3</example>
    "date" INTEGER NOT NULL,
        -- <example>14</example>
    "tmID" TEXT NOT NULL,
        -- <example>'TOR'</example>
    "oppID" TEXT NOT NULL,
        -- <example>'NYA'</example>
    "R/P" TEXT NOT NULL,
        -- <values>{'P', 'R'}</values>
    "IDgoalie1" TEXT NOT NULL,
        -- <example>'chabolo01'</example>
        -- <fk> -> Master."playerID"</fk>
    "IDgoalie2" TEXT NOT NULL,
        -- <example>'grantbe01'</example>
        -- <fk> -> Master."playerID"</fk>
    FOREIGN KEY ("IDgoalie1") REFERENCES Master("playerID"),
    FOREIGN KEY ("IDgoalie2") REFERENCES Master("playerID")
);

/*
Schema: NULL
Table: Goalies
Rows: 4278
Sample rows:
| playerID   | year   | stint   | tmID   | lgID   | GP   | Min   | W   | L   | T/OL   | ENG    | SHO   | GA   | SA     | PostGP   | PostMin   | PostW   | PostL   | PostT   | PostENG   | PostSHO   | PostGA   | PostSA   |
|------------|--------|---------|--------|--------|------|-------|-----|-----|--------|--------|-------|------|--------|----------|-----------|---------|---------|---------|-----------|-----------|----------|----------|
| abbotge01  | 1943   | 1       | BOS    | NHL    | 1    | 60    | 0   | 1   | 0      | [NULL] | 0     | 7    | [NULL] | [NULL]   | [NULL]    | [NULL]  | [NULL]  | [NULL]  | [NULL]    | [NULL]    | [NULL]   | [NULL]   |
| abrahch01  | 1974   | 1       | NEW    | WHA    | 16   | 870   | 8   | 6   | 1      | 0      | 1     | 47   | 504    | [NULL]   | [NULL]    | [NULL]  | [NULL]  | [NULL]  | [NULL]    | [NULL]    | [NULL]   | [NULL]   |
| abrahch01  | 1975   | 1       | NEW    | WHA    | 41   | 2385  | 18  | 18  | 2      | 1      | 2     | 136  | 1221   | 1        | 1         | 0       | 0       | [NULL]  | 0         | 0         | 0        | [NULL]   |
| abrahch01  | 1976   | 1       | NEW    | WHA    | 45   | 2484  | 15  | 22  | 4      | 0      | 0     | 159  | 1438   | 2        | 90        | 0       | 1       | [NULL]  | 0         | 0         | 5        | 51       |
| adamsjo02  | 1972   | 1       | BOS    | NHL    | 14   | 780   | 9   | 3   | 1      | 0      | 1     | 39   | [NULL] | [NULL]   | [NULL]    | [NULL]  | [NULL]  | [NULL]  | [NULL]    | [NULL]    | [NULL]   | [NULL]   |
| ...        | ...    | ...     | ...    | ...    | ...  | ...   | ... | ... | ...    | ...    | ...   | ...  | ...    | ...      | ...       | ...     | ...     | ...     | ...       | ...       | ...      | ...      |
*/
CREATE TABLE Goalies (
    "playerID" TEXT NOT NULL,
        -- <example>'abbotge01'</example>
        -- <fk> -> Master."playerID"</fk>
    "year" INTEGER NOT NULL,
        -- <example>1943</example>
        -- <fk>composite</fk>
    "stint" INTEGER NOT NULL,
        -- <example>1</example>
    "tmID" TEXT NOT NULL,
        -- <example>'BOS'</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    "GP" TEXT NULL,
        -- <example>'1'</example>
    "Min" TEXT NULL,
        -- <example>'60'</example>
    "W" TEXT NULL,
        -- <example>'0'</example>
    "L" TEXT NULL,
        -- <example>'1'</example>
    "T/OL" TEXT NULL,
        -- <example>'0'</example>
    "ENG" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "SHO" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '15', '2', '22', '3', '4', '5', '6', '7', '8', '9'}</values>
    "GA" TEXT NULL,
        -- <example>'7'</example>
    "SA" TEXT NULL,
        -- <example>'504'</example>
    "PostGP" TEXT NULL,
        -- <example>'1'</example>
    "PostMin" TEXT NULL,
        -- <example>'1'</example>
    "PostW" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '15', '16', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "PostL" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "PostT" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    "PostENG" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    "PostSHO" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    "PostGA" TEXT NULL,
        -- <example>'0'</example>
    "PostSA" TEXT NULL,
        -- <example>'51'</example>
    PRIMARY KEY ("playerID", "year", "stint"),
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID"),
    FOREIGN KEY ("playerID") REFERENCES Master("playerID")
);

/*
Schema: NULL
Table: GoaliesSC
Rows: 31
Sample rows:
| playerID   | year   | tmID   | lgID   | GP   | Min   | W   | L   | T   | SHO   | GA   |
|------------|--------|--------|--------|------|-------|-----|-----|-----|-------|------|
| benedcl01  | 1914   | OT1    | NHA    | 3    | 180   | 0   | 3   | 0   | 0     | 26   |
| benedcl01  | 1919   | OTS    | NHL    | 5    | 300   | 3   | 2   | 0   | 1     | 11   |
| benedcl01  | 1920   | OTS    | NHL    | 5    | 300   | 3   | 2   | 0   | 0     | 12   |
| benedcl01  | 1922   | OTS    | NHL    | 6    | 361   | 5   | 1   | 0   | 1     | 8    |
| benedcl01  | 1925   | MTM    | NHL    | 4    | 240   | 3   | 1   | 0   | 3     | 3    |
| ...        | ...    | ...    | ...    | ...  | ...   | ... | ... | ... | ...   | ...  |
*/
CREATE TABLE GoaliesSC (
    "playerID" TEXT NOT NULL,
        -- <example>'benedcl01'</example>
        -- <fk> -> Master."playerID"</fk>
    "year" INTEGER NOT NULL,
        -- <example>1914</example>
        -- <fk>composite</fk>
    "tmID" TEXT NOT NULL,
        -- <example>'OT1'</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL'}</values>
    "GP" INTEGER NOT NULL,
        -- <example>3</example>
    "Min" INTEGER NOT NULL,
        -- <example>180</example>
    "W" INTEGER NOT NULL,
        -- <example>0</example>
    "L" INTEGER NOT NULL,
        -- <example>3</example>
    "T" INTEGER NOT NULL,
        -- <example>0</example>
    "SHO" INTEGER NOT NULL,
        -- <example>0</example>
    "GA" INTEGER NOT NULL,
        -- <example>26</example>
    PRIMARY KEY ("playerID", "year"),
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID"),
    FOREIGN KEY ("playerID") REFERENCES Master("playerID")
);

/*
Schema: NULL
Table: GoaliesShootout
Rows: 480
Sample rows:
| playerID   | year   | stint   | tmID   | W   | L   | SA   | GA   |
|------------|--------|---------|--------|-----|-----|------|------|
| aebisda01  | 2005   | 1       | COL    | 2   | 1   | 10   | 2    |
| aebisda01  | 2006   | 1       | MTL    | 2   | 2   | 18   | 6    |
| andercr01  | 2005   | 1       | CHI    | 0   | 3   | 7    | 5    |
| andercr01  | 2006   | 1       | FLO    | 1   | 0   | 2    | 0    |
| andercr01  | 2008   | 1       | FLO    | 0   | 4   | 11   | 7    |
| ...        | ...    | ...     | ...    | ... | ... | ...  | ...  |
*/
CREATE TABLE GoaliesShootout (
    "playerID" TEXT NOT NULL,
        -- <example>'aebisda01'</example>
        -- <fk> -> Master."playerID"</fk>
    "year" INTEGER NOT NULL,
        -- <example>2005</example>
        -- <fk>composite</fk>
    "stint" INTEGER NOT NULL,
        -- <example>1</example>
    "tmID" TEXT NOT NULL,
        -- <example>'COL'</example>
        -- <fk>composite</fk>
    "W" INTEGER NOT NULL,
        -- <example>2</example>
    "L" INTEGER NOT NULL,
        -- <example>1</example>
    "SA" INTEGER NOT NULL,
        -- <example>10</example>
    "GA" INTEGER NOT NULL,
        -- <example>2</example>
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID"),
    FOREIGN KEY ("playerID") REFERENCES Master("playerID")
);

/*
Schema: NULL
Table: HOF
Rows: 365
Sample rows:
| year   | hofID      | name          | category   |
|--------|------------|---------------|------------|
| 1969   | abelsi01h  | Sid Abel      | Player     |
| 1960   | adamsch01h | Charles Adams | Builder    |
| 1959   | adamsja01h | Jack Adams    | Player     |
| 1972   | adamswe01h | Weston Adams  | Builder    |
| 1977   | ahearbu01h | Bunny Ahearne | Builder    |
| ...    | ...        | ...           | ...        |
*/
CREATE TABLE HOF (
    "year" INTEGER NOT NULL,
        -- <example>1969</example>
    "hofID" TEXT NOT NULL PRIMARY KEY,
        -- <example>'abelsi01h'</example>
    "name" TEXT NOT NULL,
        -- <example>'Sid Abel'</example>
    "category" TEXT NOT NULL
        -- <values>{'Builder', 'Player', 'Referee/Linesman'}</values>
);

/*
Schema: NULL
Table: Master
Rows: 7761
Sample rows:
| playerID   | coachID   | hofID   | firstName   | lastName   | nameNote   | nameGiven        | nameNick   | height   | weight   | shootCatch   | legendsID   | ihdbID   | hrefID    | firstNHL   | lastNHL   | firstWHA   | lastWHA   | pos   | birthYear   | birthMon   | birthDay   | birthCountry   | birthState   | birthCity    | deathYear   | deathMon   | deathDay   | deathCountry   | deathState   | deathCity   |
|------------|-----------|---------|-------------|------------|------------|------------------|------------|----------|----------|--------------|-------------|----------|-----------|------------|-----------|------------|-----------|-------|-------------|------------|------------|----------------|--------------|--------------|-------------|------------|------------|----------------|--------------|-------------|
| aaltoan01  | [NULL]    | [NULL]  | Antti       | Aalto      | [NULL]     | Antti            | [NULL]     | 73       | 210      | L            | 14862       | 5928     | aaltoan01 | 1997       | 2000      | [NULL]     | [NULL]    | C     | 1975        | 3          | 4          | Finland        | [NULL]       | Lappeenranta | [NULL]      | [NULL]     | [NULL]     | [NULL]         | [NULL]       | [NULL]      |
| abbeybr01  | [NULL]    | [NULL]  | Bruce       | Abbey      | [NULL]     | Bruce            | [NULL]     | 73       | 185      | L            | [NULL]      | 11918    | abbeybr01 | [NULL]     | [NULL]    | 1975       | 1975      | D     | 1951        | 8          | 18         | Canada         | ON           | Toronto      | [NULL]      | [NULL]     | [NULL]     | [NULL]         | [NULL]       | [NULL]      |
| abbotge01  | [NULL]    | [NULL]  | George      | Abbott     | [NULL]     | George Henry     | Preacher   | 67       | 153      | L            | 18411       | 14591    | abbotge01 | 1943       | 1943      | [NULL]     | [NULL]    | G     | 1911        | 8          | 3          | Canada         | ON           | Synenham     | [NULL]      | [NULL]     | [NULL]     | [NULL]         | [NULL]       | [NULL]      |
| abbotre01  | [NULL]    | [NULL]  | Reg         | Abbott     | [NULL]     | Reginald Stewart | [NULL]     | 71       | 164      | L            | 11801       | 11431    | abbotre01 | 1952       | 1952      | [NULL]     | [NULL]    | C     | 1930        | 2          | 4          | Canada         | MB           | Winnipeg     | [NULL]      | [NULL]     | [NULL]     | [NULL]         | [NULL]       | [NULL]      |
| abdelju01  | [NULL]    | [NULL]  | Justin      | Abdelkader | [NULL]     | [NULL]           | [NULL]     | 73       | 195      | L            | 21661       | 81002    | abdelju01 | 2007       | 2011      | [NULL]     | [NULL]    | L     | 1987        | 2          | 25         | USA            | MI           | Muskegon     | [NULL]      | [NULL]     | [NULL]     | [NULL]         | [NULL]       | [NULL]      |
| ...        | ...       | ...     | ...         | ...        | ...        | ...              | ...        | ...      | ...      | ...          | ...         | ...      | ...       | ...        | ...       | ...        | ...       | ...   | ...         | ...        | ...        | ...            | ...          | ...          | ...         | ...        | ...        | ...            | ...          | ...         |
*/
CREATE TABLE Master (
    "playerID" TEXT NULL,
        -- <example>'aaltoan01'</example>
    "coachID" TEXT NULL,
        -- <example>'abelsi01c'</example>
        -- <fk> -> Coaches."coachID"</fk>
    "hofID" TEXT NULL,
        -- <example>'abelsi01h'</example>
    "firstName" TEXT NULL,
        -- <example>'Antti'</example>
    "lastName" TEXT NOT NULL,
        -- <example>'Aalto'</example>
    "nameNote" TEXT NULL,
        -- <values>{'also known as Bellehumeur', 'also known as Block', 'also known as Bowcher', 'also known as Bremberg', 'also known as Burmeister', 'also known as Coleman', 'also known as Couture', 'also known as Desrivieres', 'also known as Kahibaitche', 'also known as Kessler', 'also known as Landiak', 'also known as Linton Muldoon Tracey', 'also known as Mike Jefferson', 'also known as Wochy', 'also listed as Bourdginon', 'born Bodnarchuk', 'born Guoth', 'born Tselios'}</values>
    "nameGiven" TEXT NULL,
        -- <example>'Antti'</example>
    "nameNick" TEXT NULL,
        -- <example>'Preacher'</example>
    "height" TEXT NULL,
        -- <values>{'63', '64', '65', '66', '67', '68', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '80', '81'}</values>
    "weight" TEXT NULL,
        -- <example>'210'</example>
    "shootCatch" TEXT NULL,
        -- <values>{'B', 'L', 'R'}</values>
    "legendsID" TEXT NULL,
        -- <example>'14862'</example>
    "ihdbID" TEXT NULL,
        -- <example>'5928'</example>
    "hrefID" TEXT NULL,
        -- <example>'aaltoan01'</example>
    "firstNHL" TEXT NULL,
        -- <example>'1997'</example>
    "lastNHL" TEXT NULL,
        -- <example>'2000'</example>
    "firstWHA" TEXT NULL,
        -- <values>{'1972', '1973', '1974', '1975', '1976', '1977', '1978'}</values>
    "lastWHA" TEXT NULL,
        -- <values>{'1972', '1973', '1974', '1975', '1976', '1977', '1978'}</values>
    "pos" TEXT NULL,
        -- <values>{'C', 'C/D', 'C/L', 'C/R', 'D', 'D/C', 'D/L', 'D/R', 'F', 'G', 'L', 'L/C', 'L/D', 'R', 'R/C', 'R/D', 'R/L', 'W'}</values>
    "birthYear" TEXT NULL,
        -- <example>'1975'</example>
    "birthMon" TEXT NULL,
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "birthDay" TEXT NULL,
        -- <example>'4'</example>
    "birthCountry" TEXT NULL,
        -- <example>'Finland'</example>
    "birthState" TEXT NULL,
        -- <example>'ON'</example>
    "birthCity" TEXT NULL,
        -- <example>'Lappeenranta'</example>
    "deathYear" TEXT NULL,
        -- <example>'1964'</example>
    "deathMon" TEXT NULL,
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "deathDay" TEXT NULL,
        -- <example>'1'</example>
    "deathCountry" TEXT NULL,
        -- <values>{'Belarus', 'Belgium', 'Canada', 'Czech Republic', 'France', 'Germany', 'Holland', 'Italy', 'Norway', 'Russia', 'Sweden', 'Switzerland', 'Turkey', 'USA'}</values>
    "deathState" TEXT NULL,
        -- <example>'MI'</example>
    "deathCity" TEXT NULL,
        -- <example>'Sault Ste. Marie'</example>
    FOREIGN KEY ("coachID") REFERENCES Coaches("coachID")
);

/*
Schema: NULL
Table: Scoring
Rows: 45967
Sample rows:
| playerID   | year   | stint   | tmID   | lgID   | pos   | GP   | G   | A   | Pts   | PIM   | +/-   | PPG   | PPA    | SHG   | SHA    | GWG   | GTG    | SOG   | PostGP   | PostG   | PostA   | PostPts   | PostPIM   | Post+/-   | PostPPG   | PostPPA   | PostSHG   | PostSHA   | PostGWG   | PostSOG   |
|------------|--------|---------|--------|--------|-------|------|-----|-----|-------|-------|-------|-------|--------|-------|--------|-------|--------|-------|----------|---------|---------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|-----------|
| aaltoan01  | 1997   | 1       | ANA    | NHL    | C     | 3    | 0   | 0   | 0     | 0     | -1    | 0     | 0      | 0     | 0      | 0     | 0      | 1     | [NULL]   | [NULL]  | [NULL]  | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    |
| aaltoan01  | 1998   | 1       | ANA    | NHL    | C     | 73   | 3   | 5   | 8     | 24    | -12   | 2     | 1      | 0     | 0      | 0     | 0      | 61    | 4        | 0       | 0       | 0         | 2         | 0         | 0         | 0         | 0         | 0         | 0         | 0         |
| aaltoan01  | 1999   | 1       | ANA    | NHL    | C     | 63   | 7   | 11  | 18    | 26    | -13   | 1     | 0      | 0     | 0      | 1     | 0      | 102   | [NULL]   | [NULL]  | [NULL]  | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    |
| aaltoan01  | 2000   | 1       | ANA    | NHL    | C     | 12   | 1   | 1   | 2     | 2     | 1     | 0     | 0      | 0     | 0      | 0     | 0      | 18    | [NULL]   | [NULL]  | [NULL]  | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    |
| abbeybr01  | 1975   | 1       | CIN    | WHA    | D     | 17   | 1   | 0   | 1     | 12    | -3    | 0     | [NULL] | 0     | [NULL] | 0     | [NULL] | 2     | [NULL]   | [NULL]  | [NULL]  | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    | [NULL]    |
| ...        | ...    | ...     | ...    | ...    | ...   | ...  | ... | ... | ...   | ...   | ...   | ...   | ...    | ...   | ...    | ...   | ...    | ...   | ...      | ...     | ...     | ...       | ...       | ...       | ...       | ...       | ...       | ...       | ...       | ...       |
*/
CREATE TABLE Scoring (
    "playerID" TEXT NOT NULL,
        -- <example>'aaltoan01'</example>
        -- <fk> -> Master."playerID"</fk>
    "year" INTEGER NOT NULL,
        -- <example>1997</example>
        -- <fk>composite</fk>
    "stint" INTEGER NOT NULL,
        -- <example>1</example>
    "tmID" TEXT NOT NULL,
        -- <example>'ANA'</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    "pos" TEXT NULL,
        -- <example>'C'</example>
    "GP" INTEGER NULL,
        -- <example>3</example>
    "G" INTEGER NULL,
        -- <example>0</example>
    "A" INTEGER NULL,
        -- <example>0</example>
    "Pts" INTEGER NULL,
        -- <example>0</example>
    "PIM" INTEGER NULL,
        -- <example>0</example>
    "+/-" TEXT NULL,
        -- <example>'-1'</example>
    "PPG" TEXT NULL,
        -- <example>'0'</example>
    "PPA" TEXT NULL,
        -- <example>'0'</example>
    "SHG" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "SHA" TEXT NULL,
        -- <values>{'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "GWG" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '16', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "GTG" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    "SOG" TEXT NULL,
        -- <example>'1'</example>
    "PostGP" TEXT NULL,
        -- <example>'4'</example>
    "PostG" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "PostA" TEXT NULL,
        -- <example>'0'</example>
    "PostPts" TEXT NULL,
        -- <example>'0'</example>
    "PostPIM" TEXT NULL,
        -- <example>'2'</example>
    "Post+/-" TEXT NULL,
        -- <example>'0'</example>
    "PostPPG" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "PostPPA" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '18', '19', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "PostSHG" TEXT NULL,
        -- <values>{'0', '1', '2', '3'}</values>
    "PostSHA" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    "PostGWG" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    "PostSOG" TEXT NULL,
        -- <example>'0'</example>
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID"),
    FOREIGN KEY ("playerID") REFERENCES Master("playerID")
);

/*
Schema: NULL
Table: ScoringSC
Rows: 284
Sample rows:
| playerID   | year   | tmID   | lgID   | pos   | GP   | G   | A   | Pts   | PIM   |
|------------|--------|--------|--------|-------|------|-----|-----|-------|-------|
| adamsbi01  | 1920   | VML    | PCHA   | R     | 4    | 0   | 0   | 0     | 0     |
| adamsja01  | 1920   | VML    | PCHA   | C     | 5    | 2   | 1   | 3     | 6     |
| adamsja01  | 1921   | VML    | PCHA   | C     | 5    | 6   | 1   | 7     | 18    |
| anderer02  | 1923   | CAT    | WCHL   | R     | 2    | 0   | 0   | 0     | 2     |
| anderjo03  | 1924   | VIC    | WCHL   | L     | 4    | 1   | 0   | 1     | 10    |
| ...        | ...    | ...    | ...    | ...   | ...  | ... | ... | ...   | ...   |
*/
CREATE TABLE ScoringSC (
    "playerID" TEXT NOT NULL,
        -- <example>'adamsbi01'</example>
        -- <fk> -> Master."playerID"</fk>
    "year" INTEGER NOT NULL,
        -- <example>1920</example>
        -- <fk>composite</fk>
    "tmID" TEXT NOT NULL,
        -- <example>'VML'</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL'}</values>
    "pos" TEXT NOT NULL,
        -- <example>'R'</example>
    "GP" INTEGER NOT NULL,
        -- <example>4</example>
    "G" INTEGER NOT NULL,
        -- <example>0</example>
    "A" INTEGER NOT NULL,
        -- <example>0</example>
    "Pts" INTEGER NOT NULL,
        -- <example>0</example>
    "PIM" INTEGER NOT NULL,
        -- <example>0</example>
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID"),
    FOREIGN KEY ("playerID") REFERENCES Master("playerID")
);

/*
Schema: NULL
Table: ScoringShootout
Rows: 2072
Sample rows:
| playerID   | year   | stint   | tmID   | S   | G   | GDG   |
|------------|--------|---------|--------|-----|-----|-------|
| adamske01  | 2006   | 1       | PHO    | 1   | 0   | 0     |
| afanadm01  | 2005   | 1       | TBL    | 1   | 0   | 0     |
| afanadm01  | 2006   | 1       | TBL    | 2   | 1   | 1     |
| afinoma01  | 2005   | 1       | BUF    | 5   | 3   | 2     |
| afinoma01  | 2006   | 1       | BUF    | 6   | 2   | 1     |
| ...        | ...    | ...     | ...    | ... | ... | ...   |
*/
CREATE TABLE ScoringShootout (
    "playerID" TEXT NOT NULL,
        -- <example>'adamske01'</example>
        -- <fk> -> Master."playerID"</fk>
    "year" INTEGER NOT NULL,
        -- <example>2006</example>
        -- <fk>composite</fk>
    "stint" INTEGER NOT NULL,
        -- <example>1</example>
    "tmID" TEXT NOT NULL,
        -- <example>'PHO'</example>
        -- <fk>composite</fk>
    "S" INTEGER NOT NULL,
        -- <example>1</example>
    "G" INTEGER NOT NULL,
        -- <example>0</example>
    "GDG" INTEGER NOT NULL,
        -- <example>0</example>
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID"),
    FOREIGN KEY ("playerID") REFERENCES Master("playerID")
);

/*
Schema: NULL
Table: ScoringSup
Rows: 137
Sample rows:
| playerID   | year   | PPA    | SHA    |
|------------|--------|--------|--------|
| actonke01  | 1988   | [NULL] | 1      |
| adamsgr01  | 1988   | 1      | [NULL] |
| adamsgr01  | 1989   | 1      | [NULL] |
| allismi01  | 1987   | 5      | [NULL] |
| archida01  | 1989   | 4      | [NULL] |
| ...        | ...    | ...    | ...    |
*/
CREATE TABLE ScoringSup (
    "playerID" TEXT NOT NULL,
        -- <example>'actonke01'</example>
        -- <fk> -> Master."playerID"</fk>
    "year" INTEGER NOT NULL,
        -- <example>1988</example>
    "PPA" TEXT NULL,
        -- <example>'1'</example>
    "SHA" TEXT NULL,
        -- <values>{'1', '2', '3', '4'}</values>
    FOREIGN KEY ("playerID") REFERENCES Master("playerID")
);

/*
Schema: NULL
Table: SeriesPost
Rows: 832
Sample rows:
| year   | round   | series   | tmIDWinner   | lgIDWinner   | tmIDLoser   | lgIDLoser   | W   | L   | T   | GoalsWinner   | GoalsLoser   | note   |
|--------|---------|----------|--------------|--------------|-------------|-------------|-----|-----|-----|---------------|--------------|--------|
| 1912   | SCF     | [NULL]   | VA1          | PCHA         | QU1         | NHA         | 2   | 1   | 0   | 16            | 12           | EX     |
| 1913   | F       | [NULL]   | TBS          | NHA          | MOC         | NHA         | 1   | 1   | 0   | 6             | 2            | TG     |
| 1913   | SCF     | [NULL]   | TBS          | NHA          | VA1         | PCHA        | 3   | 0   | 0   | 13            | 8            | [NULL] |
| 1914   | F       | [NULL]   | OT1          | NHA          | MOW         | NHA         | 1   | 1   | 0   | 4             | 1            | TG     |
| 1914   | SCF     | [NULL]   | VML          | PCHA         | OT1         | NHA         | 3   | 0   | 0   | 26            | 8            | [NULL] |
| ...    | ...     | ...      | ...          | ...          | ...         | ...         | ... | ... | ... | ...           | ...          | ...    |
*/
CREATE TABLE SeriesPost (
    "year" INTEGER NOT NULL,
        -- <example>1912</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "round" TEXT NOT NULL,
        -- <example>'SCF'</example>
    "series" TEXT NULL,
        -- <example>'A'</example>
    "tmIDWinner" TEXT NOT NULL,
        -- <example>'VA1'</example>
        -- <fk>composite</fk>
    "lgIDWinner" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    "tmIDLoser" TEXT NOT NULL,
        -- <example>'QU1'</example>
        -- <fk>composite</fk>
    "lgIDLoser" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    "W" INTEGER NOT NULL,
        -- <example>2</example>
    "L" INTEGER NOT NULL,
        -- <example>1</example>
    "T" INTEGER NOT NULL,
        -- <example>0</example>
    "GoalsWinner" INTEGER NOT NULL,
        -- <example>16</example>
    "GoalsLoser" INTEGER NOT NULL,
        -- <example>12</example>
    "note" TEXT NULL,
        -- <values>{'DEF', 'EX', 'ND', 'TG'}</values>
    FOREIGN KEY ("year", "tmIDWinner") REFERENCES Teams("year", "tmID"),
    FOREIGN KEY ("year", "tmIDLoser") REFERENCES Teams("year", "tmID")
);

/*
Schema: NULL
Table: TeamSplits
Rows: 1519
Sample rows:
| year   | lgID   | tmID   | hW   | hL   | hT   | hOTL   | rW   | rL   | rT   | rOTL   | SepW   | SepL   | SepT   | SepOL   | OctW   | OctL   | OctT   | OctOL   | NovW   | NovL   | NovT   | NovOL   | DecW   | DecL   | DecT   | DecOL   | JanW   | JanL   | JanT   | JanOL   | FebW   | FebL   | FebT   | FebOL   | MarW   | MarL   | MarT   | MarOL   | AprW   | AprL   | AprT   | AprOL   |
|--------|--------|--------|------|------|------|--------|------|------|------|--------|--------|--------|--------|---------|--------|--------|--------|---------|--------|--------|--------|---------|--------|--------|--------|---------|--------|--------|--------|---------|--------|--------|--------|---------|--------|--------|--------|---------|--------|--------|--------|---------|
| 1909   | NHA    | COB    | 2    | 4    | 0    | [NULL] | 2    | 4    | 0    | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | 1      | 1      | 0      | [NULL]  | 2      | 3      | 0      | [NULL]  | 1      | 4      | 0      | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  |
| 1909   | NHA    | HAI    | 3    | 3    | 0    | [NULL] | 1    | 5    | 0    | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | 1      | 3      | 0      | [NULL]  | 2      | 5      | 0      | [NULL]  | 1      | 0      | 0      | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  |
| 1909   | NHA    | LES    | 2    | 4    | 0    | [NULL] | 0    | 6    | 0    | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | 0      | 3      | 0      | [NULL]  | 1      | 5      | 0      | [NULL]  | 1      | 2      | 0      | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  |
| 1909   | NHA    | MOS    | 3    | 2    | 1    | [NULL] | 0    | 6    | 0    | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | 1      | 2      | 1      | [NULL]  | 1      | 5      | 0      | [NULL]  | 1      | 1      | 0      | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  |
| 1909   | NHA    | MOW    | 6    | 0    | 0    | [NULL] | 5    | 1    | 0    | [NULL] | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  | 2      | 1      | 0      | [NULL]  | 6      | 0      | 0      | [NULL]  | 3      | 0      | 0      | [NULL]  | [NULL] | [NULL] | [NULL] | [NULL]  |
| ...    | ...    | ...    | ...  | ...  | ...  | ...    | ...  | ...  | ...  | ...    | ...    | ...    | ...    | ...     | ...    | ...    | ...    | ...     | ...    | ...    | ...    | ...     | ...    | ...    | ...    | ...     | ...    | ...    | ...    | ...     | ...    | ...    | ...    | ...     | ...    | ...    | ...    | ...     | ...    | ...    | ...    | ...     |
*/
CREATE TABLE TeamSplits (
    "year" INTEGER NOT NULL,
        -- <example>1909</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    "tmID" TEXT NOT NULL,
        -- <example>'COB'</example>
        -- <fk>composite</fk>
    "hW" INTEGER NOT NULL,
        -- <example>2</example>
    "hL" INTEGER NOT NULL,
        -- <example>4</example>
    "hT" INTEGER NULL,
        -- <example>0</example>
    "hOTL" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "rW" INTEGER NOT NULL,
        -- <example>2</example>
    "rL" INTEGER NOT NULL,
        -- <example>4</example>
    "rT" INTEGER NULL,
        -- <example>0</example>
    "rOTL" TEXT NULL,
        -- <values>{'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "SepW" TEXT NULL,
        -- <values>{'1'}</values>
    "SepL" TEXT NULL,
        -- <values>{'1'}</values>
    "SepT" TEXT NULL,
    "SepOL" TEXT NULL,
        -- <values>{'0'}</values>
    "OctW" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "OctL" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "OctT" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6'}</values>
    "OctOL" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    "NovW" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "NovL" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "NovT" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8'}</values>
    "NovOL" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    "DecW" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "DecL" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "DecT" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    "DecOL" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    "JanW" INTEGER NULL,
        -- <example>1</example>
    "JanL" INTEGER NULL,
        -- <example>1</example>
    "JanT" INTEGER NULL,
        -- <example>0</example>
    "JanOL" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    "FebW" INTEGER NULL,
        -- <example>2</example>
    "FebL" INTEGER NULL,
        -- <example>3</example>
    "FebT" INTEGER NULL,
        -- <example>0</example>
    "FebOL" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    "MarW" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "MarL" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '15', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "MarT" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    "MarOL" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6'}</values>
    "AprW" TEXT NULL,
        -- <values>{'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "AprL" TEXT NULL,
        -- <values>{'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "AprT" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    "AprOL" TEXT NULL,
        -- <values>{'0', '1', '2', '3'}</values>
    PRIMARY KEY ("year", "tmID"),
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID")
);

/*
Schema: NULL
Table: TeamVsTeam
Rows: 25602
Sample rows:
| year   | lgID   | tmID   | oppID   | W   | L   | T   | OTL    |
|--------|--------|--------|---------|-----|-----|-----|--------|
| 1909   | NHA    | COB    | HAI     | 1   | 1   | 0   | [NULL] |
| 1909   | NHA    | COB    | LES     | 2   | 0   | 0   | [NULL] |
| 1909   | NHA    | COB    | MOS     | 1   | 1   | 0   | [NULL] |
| 1909   | NHA    | COB    | MOW     | 0   | 2   | 0   | [NULL] |
| 1909   | NHA    | COB    | OT1     | 0   | 2   | 0   | [NULL] |
| ...    | ...    | ...    | ...     | ... | ... | ... | ...    |
*/
CREATE TABLE TeamVsTeam (
    "year" INTEGER NOT NULL,
        -- <example>1909</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    "tmID" TEXT NOT NULL,
        -- <example>'COB'</example>
        -- <fk>composite</fk>
    "oppID" TEXT NOT NULL,
        -- <example>'HAI'</example>
        -- <fk>composite</fk>
    "W" INTEGER NOT NULL,
        -- <example>1</example>
    "L" INTEGER NOT NULL,
        -- <example>1</example>
    "T" INTEGER NULL,
        -- <example>0</example>
    "OTL" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    PRIMARY KEY ("year", "tmID", "oppID"),
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID"),
    FOREIGN KEY ("oppID", "year") REFERENCES Teams("tmID", "year")
);

/*
Schema: NULL
Table: Teams
Rows: 1519
Sample rows:
| year   | lgID   | tmID   | franchID   | confID   | divID   | rank   | playoff   | G   | W   | L   | T   | OTL    | Pts   | SoW    | SoL    | GF   | GA   | name                   | PIM    | BenchMinor   | PPG    | PPC    | SHA    | PKG    | PKC    | SHF    |
|--------|--------|--------|------------|----------|---------|--------|-----------|-----|-----|-----|-----|--------|-------|--------|--------|------|------|------------------------|--------|--------------|--------|--------|--------|--------|--------|--------|
| 1909   | NHA    | COB    | BKN        | [NULL]   | [NULL]  | 4      | [NULL]    | 12  | 4   | 8   | 0   | [NULL] | 8     | [NULL] | [NULL] | 79   | 104  | Cobalt Silver Kings    | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| 1909   | NHA    | HAI    | MTL        | [NULL]   | [NULL]  | 5      | [NULL]    | 12  | 4   | 8   | 0   | [NULL] | 8     | [NULL] | [NULL] | 77   | 83   | Haileybury Hockey Club | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| 1909   | NHA    | LES    | TBS        | [NULL]   | [NULL]  | 7      | [NULL]    | 12  | 2   | 10  | 0   | [NULL] | 4     | [NULL] | [NULL] | 59   | 100  | Les Canadiens          | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| 1909   | NHA    | MOS    | MOS        | [NULL]   | [NULL]  | 6      | [NULL]    | 12  | 3   | 8   | 1   | [NULL] | 7     | [NULL] | [NULL] | 52   | 95   | Montreal Shamrocks     | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| 1909   | NHA    | MOW    | MTW        | [NULL]   | [NULL]  | 1      | [NULL]    | 12  | 11  | 1   | 0   | [NULL] | 22    | [NULL] | [NULL] | 91   | 41   | Montreal Wanderers     | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| ...    | ...    | ...    | ...        | ...      | ...     | ...    | ...       | ... | ... | ... | ... | ...    | ...   | ...    | ...    | ...  | ...  | ...                    | ...    | ...          | ...    | ...    | ...    | ...    | ...    | ...    |
*/
CREATE TABLE Teams (
    "year" INTEGER NOT NULL,
        -- <example>1909</example>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    "tmID" TEXT NOT NULL,
        -- <example>'COB'</example>
    "franchID" TEXT NOT NULL,
        -- <example>'BKN'</example>
    "confID" TEXT NULL,
        -- <values>{'CC', 'EC', 'WA', 'WC'}</values>
    "divID" TEXT NULL,
        -- <example>'AM'</example>
    "rank" INTEGER NOT NULL,
        -- <example>4</example>
    "playoff" TEXT NULL,
        -- <example>'LCS'</example>
    "G" INTEGER NOT NULL,
        -- <example>12</example>
    "W" INTEGER NOT NULL,
        -- <example>4</example>
    "L" INTEGER NOT NULL,
        -- <example>8</example>
    "T" INTEGER NULL,
        -- <example>0</example>
    "OTL" TEXT NULL,
        -- <example>'3'</example>
    "Pts" INTEGER NOT NULL,
        -- <example>8</example>
    "SoW" TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '14', '15', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "SoL" TEXT NULL,
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    "GF" INTEGER NOT NULL,
        -- <example>79</example>
    "GA" INTEGER NOT NULL,
        -- <example>104</example>
    "name" TEXT NOT NULL,
        -- <example>'Cobalt Silver Kings'</example>
    "PIM" TEXT NULL,
        -- <example>'336'</example>
    "BenchMinor" TEXT NULL,
        -- <example>'12'</example>
    "PPG" TEXT NULL,
        -- <example>'28'</example>
    "PPC" TEXT NULL,
        -- <example>'220'</example>
    "SHA" TEXT NULL,
        -- <example>'4'</example>
    "PKG" TEXT NULL,
        -- <example>'45'</example>
    "PKC" TEXT NULL,
        -- <example>'242'</example>
    "SHF" TEXT NULL,
        -- <example>'3'</example>
    PRIMARY KEY ("year", "tmID")
);

/*
Schema: NULL
Table: TeamsHalf
Rows: 41
Sample rows:
| year   | lgID   | tmID   | half   | rank   | G   | W   | L   | T   | GF   | GA   |
|--------|--------|--------|--------|--------|-----|-----|-----|-----|------|------|
| 1916   | NHA    | MOC    | 1      | 1      | 10  | 7   | 3   | 0   | 58   | 38   |
| 1916   | NHA    | MOC    | 2      | 3      | 10  | 3   | 7   | 0   | 31   | 42   |
| 1916   | NHA    | MOW    | 1      | 5      | 10  | 3   | 7   | 0   | 56   | 72   |
| 1916   | NHA    | MOW    | 2      | 4      | 10  | 2   | 8   | 0   | 38   | 65   |
| 1916   | NHA    | OT1    | 1      | 2      | 10  | 7   | 3   | 0   | 56   | 41   |
| ...    | ...    | ...    | ...    | ...    | ... | ... | ... | ... | ...  | ...  |
*/
CREATE TABLE TeamsHalf (
    "year" INTEGER NOT NULL,
        -- <example>1916</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL'}</values>
    "tmID" TEXT NOT NULL,
        -- <example>'MOC'</example>
        -- <fk>composite</fk>
    "half" INTEGER NOT NULL,
        -- <example>1</example>
    "rank" INTEGER NOT NULL,
        -- <example>1</example>
    "G" INTEGER NOT NULL,
        -- <example>10</example>
    "W" INTEGER NOT NULL,
        -- <example>7</example>
    "L" INTEGER NOT NULL,
        -- <example>3</example>
    "T" INTEGER NOT NULL,
        -- <example>0</example>
    "GF" INTEGER NOT NULL,
        -- <example>58</example>
    "GA" INTEGER NOT NULL,
        -- <example>38</example>
    PRIMARY KEY ("year", "tmID", "half"),
    FOREIGN KEY ("tmID", "year") REFERENCES Teams("tmID", "year")
);

/*
Schema: NULL
Table: TeamsPost
Rows: 927
Sample rows:
| year   | lgID   | tmID   | G   | W   | L   | T   | GF   | GA   | PIM    | BenchMinor   | PPG    | PPC    | SHA    | PKG    | PKC    | SHF    |
|--------|--------|--------|-----|-----|-----|-----|------|------|--------|--------------|--------|--------|--------|--------|--------|--------|
| 1913   | NHA    | MOC    | 2   | 1   | 1   | 0   | 2    | 6    | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| 1913   | NHA    | TBS    | 2   | 1   | 1   | 0   | 6    | 2    | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| 1914   | NHA    | MOW    | 2   | 1   | 1   | 0   | 1    | 4    | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| 1914   | NHA    | OT1    | 2   | 1   | 1   | 0   | 4    | 1    | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| 1916   | NHA    | MOC    | 2   | 1   | 1   | 0   | 7    | 6    | [NULL] | [NULL]       | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] | [NULL] |
| ...    | ...    | ...    | ... | ... | ... | ... | ...  | ...  | ...    | ...          | ...    | ...    | ...    | ...    | ...    | ...    |
*/
CREATE TABLE TeamsPost (
    "year" INTEGER NOT NULL,
        -- <example>1913</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    "tmID" TEXT NOT NULL,
        -- <example>'MOC'</example>
        -- <fk>composite</fk>
    "G" INTEGER NOT NULL,
        -- <example>2</example>
    "W" INTEGER NOT NULL,
        -- <example>1</example>
    "L" INTEGER NOT NULL,
        -- <example>1</example>
    "T" INTEGER NOT NULL,
        -- <example>0</example>
    "GF" INTEGER NOT NULL,
        -- <example>2</example>
    "GA" INTEGER NOT NULL,
        -- <example>6</example>
    "PIM" TEXT NULL,
        -- <example>'59'</example>
    "BenchMinor" TEXT NULL,
        -- <values>{'0', '10', '12', '14', '2', '4', '6', '8'}</values>
    "PPG" TEXT NULL,
        -- <example>'1'</example>
    "PPC" TEXT NULL,
        -- <example>'39'</example>
    "SHA" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8'}</values>
    "PKG" TEXT NULL,
        -- <example>'3'</example>
    "PKC" TEXT NULL,
        -- <example>'55'</example>
    "SHF" TEXT NULL,
        -- <example>'0'</example>
    PRIMARY KEY ("year", "tmID"),
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID")
);

/*
Schema: NULL
Table: TeamsSC
Rows: 30
Sample rows:
| year   | lgID   | tmID   | G   | W   | L   | T   | GF   | GA   | PIM    |
|--------|--------|--------|-----|-----|-----|-----|------|------|--------|
| 1912   | NHA    | QU1    | 3   | 1   | 2   | 0   | 12   | 16   | [NULL] |
| 1912   | PCHA   | VA1    | 3   | 2   | 1   | 0   | 16   | 12   | [NULL] |
| 1913   | NHA    | TBS    | 3   | 3   | 0   | 0   | 13   | 8    | [NULL] |
| 1913   | PCHA   | VA1    | 3   | 0   | 3   | 0   | 8    | 13   | [NULL] |
| 1914   | NHA    | OT1    | 3   | 0   | 3   | 0   | 8    | 26   | [NULL] |
| ...    | ...    | ...    | ... | ... | ... | ... | ...  | ...  | ...    |
*/
CREATE TABLE TeamsSC (
    "year" INTEGER NOT NULL,
        -- <example>1912</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL'}</values>
    "tmID" TEXT NOT NULL,
        -- <example>'QU1'</example>
        -- <fk>composite</fk>
    "G" INTEGER NOT NULL,
        -- <example>3</example>
    "W" INTEGER NOT NULL,
        -- <example>1</example>
    "L" INTEGER NOT NULL,
        -- <example>2</example>
    "T" INTEGER NOT NULL,
        -- <example>0</example>
    "GF" INTEGER NOT NULL,
        -- <example>12</example>
    "GA" INTEGER NOT NULL,
        -- <example>16</example>
    "PIM" TEXT NULL,
        -- <values>{'18', '20', '24', '49', '50', '53', '75'}</values>
    PRIMARY KEY ("year", "tmID"),
    FOREIGN KEY ("year", "tmID") REFERENCES Teams("year", "tmID")
);

/*
Schema: NULL
Table: abbrev
Rows: 58
Sample rows:
| Type       | Code   | Fullname            |
|------------|--------|---------------------|
| Conference | CC     | Campbell Conference |
| Conference | EC     | Eastern Conference  |
| Conference | WA     | Wales Conference    |
| Conference | WC     | Western Conference  |
| Division   | AD     | Adams Division      |
| ...        | ...    | ...                 |
*/
CREATE TABLE abbrev (
    "Type" TEXT NOT NULL,
        -- <values>{'Conference', 'Division', 'Playoffs', 'Round'}</values>
    "Code" TEXT NOT NULL,
        -- <example>'CC'</example>
    "Fullname" TEXT NOT NULL,
        -- <example>'Campbell Conference'</example>
    PRIMARY KEY ("Type", "Code")
);
```