```sql
-- Database: ice_hockey_draft

/*
Schema: NULL
Table: PlayerInfo
Rows: 2171
Sample rows:
| ELITEID   | PlayerName       | birthdate   | birthyear   | birthmonth   | birthday   | birthplace     | nation   | height   | weight   | position_info   | shoots   | draftyear   | draftround   | overall   | overallby             | CSS_rank   | sum_7yr_GP   | sum_7yr_TOI   | GP_greater_than_0   |
|-----------|------------------|-------------|-------------|--------------|------------|----------------|----------|----------|----------|-----------------|----------|-------------|--------------|-----------|-----------------------|------------|--------------|---------------|---------------------|
| 9         | David Bornhammar | 1981-06-15  | 1981        | 6            | 15         | Lidingo, SWE   | Sweden   | 73       | 198      | D               | L        | 1999        | 7            | 192       | Washington Capitals   | 192        | 0            | 0             | no                  |
| 18        | David Printz     | 1980-07-24  | 1980        | 7            | 24         | Stockholm, SWE | Sweden   | 76       | 220      | D               | L        | 2001        | 7            | 225       | Philadelphia Flyers   | 176        | 13           | 84            | yes                 |
| 27        | Yared Hagos      | 1983-03-27  | 1983        | 3            | 27         | Stockholm, SWE | Sweden   | 73       | 218      | C               | L        | 2001        | 3            | 70        | Dallas Stars          | 24         | 0            | 0             | no                  |
| 30        | Andreas Jamtin   | 1983-05-04  | 1983        | 5            | 4          | Stockholm, SWE | Sweden   | 72       | 194      | LW/C            | L        | 2001        | 5            | 157       | Detroit Red Wings     | 36         | 0            | 0             | no                  |
| 58        | Per Mars         | 1982-10-23  | 1982        | 10           | 23         | Ostersund, SWE | Sweden   | 75       | 216      | C               | L        | 2001        | 3            | 87        | Columbus Blue Jackets | 176        | 0            | 0             | no                  |
| ...       | ...              | ...         | ...         | ...          | ...        | ...            | ...      | ...      | ...      | ...             | ...      | ...         | ...          | ...       | ...                   | ...        | ...          | ...           | ...                 |
*/
CREATE TABLE PlayerInfo (
    "ELITEID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>9</example>
    "PlayerName" TEXT NOT NULL,
        -- <example>'David Bornhammar'</example>
    "birthdate" TEXT NOT NULL,
        -- <example>'1981-06-15'</example>
    "birthyear" DATE NOT NULL,
        -- <example>1981</example>
    "birthmonth" INTEGER NOT NULL,
        -- <example>6</example>
    "birthday" INTEGER NOT NULL,
        -- <example>15</example>
    "birthplace" TEXT NOT NULL,
        -- <example>'Lidingo, SWE'</example>
    "nation" TEXT NOT NULL,
        -- <example>'Sweden'</example>
    "height" INTEGER NOT NULL,
        -- <example>73</example>
        -- <fk> -> height_info."height_id"</fk>
    "weight" INTEGER NOT NULL,
        -- <example>198</example>
        -- <fk> -> weight_info."weight_id"</fk>
    "position_info" TEXT NOT NULL,
        -- <example>'D'</example>
    "shoots" TEXT NOT NULL,
        -- <values>{'-', 'L', 'R'}</values>
    "draftyear" INTEGER NOT NULL,
        -- <example>1999</example>
    "draftround" INTEGER NOT NULL,
        -- <example>7</example>
    "overall" INTEGER NOT NULL,
        -- <example>192</example>
    "overallby" TEXT NOT NULL,
        -- <example>'Washington Capitals'</example>
    "CSS_rank" INTEGER NOT NULL,
        -- <example>192</example>
    "sum_7yr_GP" INTEGER NOT NULL,
        -- <example>0</example>
    "sum_7yr_TOI" INTEGER NOT NULL,
        -- <example>0</example>
    "GP_greater_than_0" TEXT NOT NULL,
        -- <values>{'no', 'yes'}</values>
    FOREIGN KEY ("height") REFERENCES height_info("height_id"),
    FOREIGN KEY ("weight") REFERENCES weight_info("weight_id")
);

/*
Schema: NULL
Table: SeasonStatus
Rows: 5485
Sample rows:
| ELITEID   | SEASON    | TEAM             | LEAGUE   | GAMETYPE       | GP   | G   | A   | P   | PIM   | PLUSMINUS   |
|-----------|-----------|------------------|----------|----------------|------|-----|-----|-----|-------|-------------|
| 3667      | 1997-1998 | Rimouski Oceanic | QMJHL    | Regular Season | 58   | 44  | 71  | 115 | 117   | 27          |
| 3667      | 1997-1998 | Rimouski Oceanic | QMJHL    | Playoffs       | 18   | 15  | 26  | 41  | 46    | 4           |
| 3667      | 1997-1998 | Canada U20       | WJC-20   | Regular Season | 7    | 1   | 1   | 2   | 4     | 0           |
| 3668      | 1997-1998 | Plymouth Whalers | OHL      | Regular Season | 59   | 54  | 51  | 105 | 56    | 50          |
| 3668      | 1997-1998 | Plymouth Whalers | OHL      | Playoffs       | 15   | 8   | 12  | 20  | 24    | 3           |
| ...       | ...       | ...              | ...      | ...            | ...  | ... | ... | ... | ...   | ...         |
*/
CREATE TABLE SeasonStatus (
    "ELITEID" INTEGER NOT NULL,
        -- <example>3667</example>
        -- <fk> -> PlayerInfo."ELITEID"</fk>
    "SEASON" TEXT NOT NULL,
        -- <values>{'1997-1998', '1998-1999', '1999-2000', '2000-2001', '2001-2002', '2003-2004', '2004-2005', '2005-2006', '2006-2007', '2007-2008'}</values>
    "TEAM" TEXT NOT NULL,
        -- <example>'Rimouski Oceanic'</example>
    "LEAGUE" TEXT NOT NULL,
        -- <example>'QMJHL'</example>
    "GAMETYPE" TEXT NOT NULL,
        -- <values>{'Playoffs', 'Regular Season'}</values>
    "GP" INTEGER NOT NULL,
        -- <example>58</example>
    "G" INTEGER NOT NULL,
        -- <example>44</example>
    "A" INTEGER NOT NULL,
        -- <example>71</example>
    "P" INTEGER NOT NULL,
        -- <example>115</example>
    "PIM" INTEGER NOT NULL,
        -- <example>117</example>
    "PLUSMINUS" INTEGER NOT NULL,
        -- <example>27</example>
    FOREIGN KEY ("ELITEID") REFERENCES PlayerInfo("ELITEID")
);

/*
Schema: NULL
Table: height_info
Rows: 16
Sample rows:
| height_id   | height_in_cm   | height_in_inch   |
|-------------|----------------|------------------|
| 65          | 165            | 5'5"             |
| 67          | 170            | 5'7"             |
| 68          | 172            | 5'8"             |
| 69          | 174            | 5'9"             |
| 70          | 177            | 5'10"            |
| ...         | ...            | ...              |
*/
CREATE TABLE height_info (
    "height_id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>65</example>
    "height_in_cm" INTEGER NOT NULL,
        -- <example>165</example>
    "height_in_inch" TEXT NOT NULL
        -- <example>'5'5"'</example>
);

/*
Schema: NULL
Table: weight_info
Rows: 46
Sample rows:
| weight_id   | weight_in_kg   | weight_in_lbs   |
|-------------|----------------|-----------------|
| 154         | 70             | 154             |
| 159         | 72             | 159             |
| 161         | 73             | 161             |
| 163         | 74             | 163             |
| 165         | 75             | 165             |
| ...         | ...            | ...             |
*/
CREATE TABLE weight_info (
    "weight_id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>154</example>
    "weight_in_kg" INTEGER NOT NULL,
        -- <example>70</example>
    "weight_in_lbs" INTEGER NOT NULL
        -- <example>154</example>
);
```