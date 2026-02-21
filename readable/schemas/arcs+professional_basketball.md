```sql
-- Database: professional_basketball

/*
Schema: NULL
Table: AWARDS_COACHES
Rows: 61
Sample rows:
| id   | year   | coachID   | award                 | lgID   | note   |
|------|--------|-----------|-----------------------|--------|--------|
| 1    | 1962   | gallaha01 | NBA Coach of the Year | NBA    | [NULL] |
| 2    | 1963   | hannual01 | NBA Coach of the Year | NBA    | [NULL] |
| 3    | 1964   | auerbre01 | NBA Coach of the Year | NBA    | [NULL] |
| 4    | 1965   | schaydo01 | NBA Coach of the Year | NBA    | [NULL] |
| 5    | 1966   | kerrjo01  | NBA Coach of the Year | NBA    | [NULL] |
| ...  | ...    | ...       | ...                   | ...    | ...    |
*/
CREATE TABLE AWARDS_COACHES (
    "ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "YEAR" INTEGER NOT NULL,
        -- <example>1962</example>
        -- <fk>composite</fk>
    "coachID" TEXT NOT NULL,
        -- <example>'gallaha01'</example>
        -- <fk>composite</fk>
    "AWARD" TEXT NOT NULL,
        -- <values>{'ABA Coach of the Year', 'NBA Coach of the Year'}</values>
    "lgID" TEXT NOT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    "NOTE" TEXT NULL,
        -- <values>{'tie'}</values>
    FOREIGN KEY ("coachID", "YEAR") REFERENCES COACHES("coachID", "YEAR")
);

/*
Schema: NULL
Table: AWARDS_PLAYERS
Rows: 1719
Sample rows:
| playerID   | award                     | year   | lgID   | note   | pos    |
|------------|---------------------------|--------|--------|--------|--------|
| abdulka01  | All-Defensive Second Team | 1969   | NBA    | [NULL] | [NULL] |
| abdulka01  | All-NBA Second Team       | 1969   | NBA    | [NULL] | C      |
| abdulka01  | Rookie of the Year        | 1969   | NBA    | [NULL] | [NULL] |
| abdulka01  | All-Defensive Second Team | 1970   | NBA    | [NULL] | [NULL] |
| abdulka01  | All-NBA First Team        | 1970   | NBA    | [NULL] | C      |
| ...        | ...                       | ...    | ...    | ...    | ...    |
*/
CREATE TABLE AWARDS_PLAYERS (
    "playerID" TEXT NOT NULL,
        -- <example>'abdulka01'</example>
        -- <fk> -> PLAYERS."playerID"</fk>
    "AWARD" TEXT NOT NULL,
        -- <example>'All-Defensive Second Team'</example>
    "YEAR" INTEGER NOT NULL,
        -- <example>1969</example>
    "lgID" TEXT NOT NULL,
        -- <values>{'ABA', 'ABL1', 'NBA', 'NBL'}</values>
    "NOTE" TEXT NULL,
        -- <values>{'tie'}</values>
    "POS" TEXT NULL,
        -- <values>{'C', 'F', 'F/C', 'F/G', 'G'}</values>
    PRIMARY KEY ("playerID", "AWARD", "YEAR"),
    FOREIGN KEY ("playerID") REFERENCES PLAYERS("playerID")
);

/*
Schema: NULL
Table: COACHES
Rows: 1689
Sample rows:
| coachID   | year   | tmID   | lgID   | stint   | won   | lost   | post_wins   | post_losses   |
|-----------|--------|--------|--------|---------|-------|--------|-------------|---------------|
| adelmri01 | 1988   | POR    | NBA    | 2       | 14    | 21     | 0           | 3             |
| adelmri01 | 1989   | POR    | NBA    | 1       | 59    | 23     | 12          | 9             |
| adelmri01 | 1990   | POR    | NBA    | 1       | 63    | 19     | 9           | 7             |
| adelmri01 | 1991   | POR    | NBA    | 1       | 57    | 25     | 13          | 8             |
| adelmri01 | 1992   | POR    | NBA    | 1       | 51    | 31     | 1           | 3             |
| ...       | ...    | ...    | ...    | ...     | ...   | ...    | ...         | ...           |
*/
CREATE TABLE COACHES (
    "coachID" TEXT NOT NULL,
        -- <example>'adelmri01'</example>
    "YEAR" INTEGER NOT NULL,
        -- <example>1988</example>
        -- <fk>composite</fk>
    "tmID" TEXT NOT NULL,
        -- <example>'POR'</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'ABA', 'ABL1', 'NBA', 'NPBL', 'PBLA'}</values>
    "STINT" INTEGER NOT NULL,
        -- <example>2</example>
    "WON" INTEGER NULL,
        -- <example>14</example>
    "LOST" INTEGER NULL,
        -- <example>21</example>
    "POST_WINS" INTEGER NULL,
        -- <example>0</example>
    "POST_LOSSES" INTEGER NULL,
        -- <example>3</example>
    PRIMARY KEY ("coachID", "YEAR", "tmID", "STINT"),
    FOREIGN KEY ("tmID", "YEAR") REFERENCES TEAMS("tmID", "YEAR")
);

/*
Schema: NULL
Table: DRAFT
Rows: 8621
Sample rows:
| id   | draftYear   | draftRound   | draftSelection   | draftOverall   | tmID   | firstName   | lastName   | suffixName   | playerID   | draftFrom      | lgID   |
|------|-------------|--------------|------------------|----------------|--------|-------------|------------|--------------|------------|----------------|--------|
| 1    | 1967        | 0            | 0                | 0              | ANA    | Darrell     | Hardy      | [NULL]       | hardyda01  | Baylor         | ABA    |
| 2    | 1967        | 0            | 0                | 0              | ANA    | Bob         | Krulish    | [NULL]       | [NULL]     | Pacific        | ABA    |
| 3    | 1967        | 0            | 0                | 0              | ANA    | Bob         | Lewis      | [NULL]       | lewisbo01  | North Carolina | ABA    |
| 4    | 1967        | 0            | 0                | 0              | ANA    | Mike        | Lynn       | [NULL]       | lynnmi01   | UCLA           | ABA    |
| 5    | 1967        | 0            | 0                | 0              | ANA    | Tom         | Workman    | [NULL]       | workmto01  | Seattle        | ABA    |
| ...  | ...         | ...          | ...              | ...            | ...    | ...         | ...        | ...          | ...        | ...            | ...    |
*/
CREATE TABLE DRAFT (
    "ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "draftYear" INTEGER NOT NULL,
        -- <example>1967</example>
        -- <fk>composite</fk>
    "draftRound" INTEGER NOT NULL,
        -- <example>0</example>
    "draftSelection" INTEGER NOT NULL,
        -- <example>0</example>
    "draftOverall" INTEGER NOT NULL,
        -- <example>0</example>
    "tmID" TEXT NOT NULL,
        -- <example>'ANA'</example>
        -- <fk>composite</fk>
    "firstName" TEXT NOT NULL,
        -- <example>'Darrell'</example>
    "lastName" TEXT NOT NULL,
        -- <example>'Hardy'</example>
    "suffixName" TEXT NULL,
        -- <values>{'Jr.'}</values>
    "playerID" TEXT NULL,
        -- <example>'hardyda01'</example>
    "draftFrom" TEXT NULL,
        -- <example>'Baylor'</example>
    "lgID" TEXT NOT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    FOREIGN KEY ("tmID", "draftYear") REFERENCES TEAMS("tmID", "YEAR")
);

/*
Schema: NULL
Table: PLAYER_ALLSTAR
Rows: 1608
Sample rows:
| playerID   | last_name    | first_name   | season_id   | conference   | league_id   | games_played   | minutes   | points   | o_rebounds   | d_rebounds   | rebounds   | assists   | steals   | blocks   | turnovers   | personal_fouls   | fg_attempted   | fg_made   | ft_attempted   | ft_made   | three_attempted   | three_made   |
|------------|--------------|--------------|-------------|--------------|-------------|----------------|-----------|----------|--------------|--------------|------------|-----------|----------|----------|-------------|------------------|----------------|-----------|----------------|-----------|-------------------|--------------|
| abdulka01  | Abdul-Jabbar | Kareem       | 1969        | East         | NBA         | 1              | 18        | 10.0     | [NULL]       | [NULL]       | 11.0       | 4.0       | [NULL]   | [NULL]   | [NULL]      | [NULL]           | 8.0            | 4.0       | 2.0            | 2.0       | [NULL]            | [NULL]       |
| abdulka01  | Abdul-Jabbar | Kareem       | 1970        | West         | NBA         | 1              | 30        | 19.0     | [NULL]       | [NULL]       | 14.0       | 1.0       | [NULL]   | [NULL]   | [NULL]      | [NULL]           | 16.0           | 8.0       | 4.0            | 3.0       | [NULL]            | [NULL]       |
| abdulka01  | Abdul-Jabbar | Kareem       | 1971        | West         | NBA         | 1              | 19        | 12.0     | [NULL]       | [NULL]       | 7.0        | 2.0       | [NULL]   | [NULL]   | [NULL]      | [NULL]           | 10.0           | 5.0       | 2.0            | 2.0       | [NULL]            | [NULL]       |
| abdulka01  | Abdul-Jabbar | Kareem       | 1972        | West         | NBA         | 1              | 98        | [NULL]   | [NULL]       | [NULL]       | [NULL]     | [NULL]    | [NULL]   | [NULL]   | [NULL]      | [NULL]           | [NULL]         | [NULL]    | [NULL]         | [NULL]    | [NULL]            | [NULL]       |
| abdulka01  | Abdul-Jabbar | Kareem       | 1973        | West         | NBA         | 1              | 23        | 14.0     | [NULL]       | [NULL]       | 8.0        | 6.0       | [NULL]   | [NULL]   | [NULL]      | [NULL]           | 11.0           | 7.0       | 0.0            | 0.0       | [NULL]            | [NULL]       |
| ...        | ...          | ...          | ...         | ...          | ...         | ...            | ...       | ...      | ...          | ...          | ...        | ...       | ...      | ...      | ...         | ...              | ...            | ...       | ...            | ...       | ...               | ...          |
*/
CREATE TABLE PLAYER_ALLSTAR (
    "playerID" TEXT NOT NULL,
        -- <example>'abdulka01'</example>
        -- <fk> -> PLAYERS."playerID"</fk>
    "LAST_NAME" TEXT NOT NULL,
        -- <example>'Abdul-Jabbar'</example>
    "FIRST_NAME" TEXT NOT NULL,
        -- <example>'Kareem'</example>
    "SEASON_ID" INTEGER NOT NULL,
        -- <example>1969</example>
    "CONFERENCE" TEXT NOT NULL,
        -- <values>{'Allstars', 'Denver', 'East', 'Weset', 'West'}</values>
    "LEAGUE_ID" TEXT NOT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    "GAMES_PLAYED" INTEGER NOT NULL,
        -- <example>1</example>
    "MINUTES" INTEGER NOT NULL,
        -- <example>18</example>
    "POINTS" INTEGER NULL,
        -- <example>10</example>
    "O_REBOUNDS" INTEGER NULL,
        -- <example>1</example>
    "D_REBOUNDS" INTEGER NULL,
        -- <example>2</example>
    "REBOUNDS" INTEGER NULL,
        -- <example>11</example>
    "ASSISTS" INTEGER NULL,
        -- <example>4</example>
    "STEALS" INTEGER NULL,
        -- <example>3</example>
    "BLOCKS" INTEGER NULL,
        -- <example>2</example>
    "TURNOVERS" INTEGER NULL,
        -- <example>1</example>
    "PERSONAL_FOULS" INTEGER NULL,
        -- <example>3</example>
    "FG_ATTEMPTED" INTEGER NULL,
        -- <example>8</example>
    "FG_MADE" INTEGER NULL,
        -- <example>4</example>
    "FT_ATTEMPTED" INTEGER NULL,
        -- <example>2</example>
    "FT_MADE" INTEGER NULL,
        -- <example>2</example>
    "THREE_ATTEMPTED" INTEGER NULL,
        -- <example>0</example>
    "THREE_MADE" INTEGER NULL,
        -- <example>0</example>
    PRIMARY KEY ("playerID", "SEASON_ID"),
    FOREIGN KEY ("playerID") REFERENCES PLAYERS("playerID")
);

/*
Schema: NULL
Table: PLAYERS
Rows: 5062
Sample rows:
| playerID   | useFirst   | firstName   | middleName   | lastName     | nameGiven   | fullGivenName                 | nameSuffix   | nameNick   | pos   | firstseason   | lastseason   | height   | weight   | college         | collegeOther      | birthDate   | birthCity      | birthState   | birthCountry   | highSchool            | hsCity                | hsState   | hsCountry   | deathDate   | race   |
|------------|------------|-------------|--------------|--------------|-------------|-------------------------------|--------------|------------|-------|---------------|--------------|----------|----------|-----------------|-------------------|-------------|----------------|--------------|----------------|-----------------------|-----------------------|-----------|-------------|-------------|--------|
| abdelal01  | Alaa       | Alaa        | [NULL]       | Abdelnaby    | [NULL]      | [NULL]                        | [NULL]       | [NULL]     | F-C   | 0             | 0            | 82.0     | 240      | Duke            | [NULL]            | 1968-06-24  | Cairo          | [NULL]       | EGY            | Bloomfield Senior     | Bloomfield            | NJ        | USA         | 0000-00-00  | B      |
| abdulka01  | Kareem     | Kareem      | [NULL]       | Abdul-Jabbar | [NULL]      | Ferdinand Lewis Alcindor, Jr. | [NULL]       | Lew, Cap   | C     | 0             | 0            | 85.0     | 225      | UCLA            | [NULL]            | 1947-04-16  | New York       | NY           | USA            | Power Memorial        | New York              | NY        | USA         | 0000-00-00  | B      |
| abdulma01  | Mahdi      | Mahdi       | [NULL]       | Abdul-Rahman | [NULL]      | Walter Raphael Hazzard, Jr.   | [NULL]       | Walt       | G     | 0             | 0            | 74.0     | 185      | UCLA            | Santa Monica City | 1942-04-15  | Wilmington     | DE           | USA            | Overbrook / Moton     | Philadelphia / Easton | PA / MD   | USA         | 2011-11-18  | B      |
| abdulma02  | Mahmoud    | Mahmoud     | [NULL]       | Abdul-Rauf   | [NULL]      | Chris Wayne Jackson           | [NULL]       | [NULL]     | G     | 0             | 0            | 73.0     | 162      | Louisiana State | [NULL]            | 1969-03-09  | Gulfport       | MS           | USA            | Gulfport              | Gulfport              | MS        | USA         | 0000-00-00  | B      |
| abdulta01  | Tariq      | Tariq       | [NULL]       | Abdul-Wahad  | [NULL]      | Olivier Michael Saint-Jean    | [NULL]       | [NULL]     | G-F   | 0             | 0            | 78.0     | 223      | San Jose State  | Michigan          | 1974-11-03  | Maisons Alfort | [NULL]       | FRA            | Lycee Aristide Briand | Evreux                | [NULL]    | FRA         | 0000-00-00  | B      |
| ...        | ...        | ...         | ...          | ...          | ...         | ...                           | ...          | ...        | ...   | ...           | ...          | ...      | ...      | ...             | ...               | ...         | ...            | ...          | ...            | ...                   | ...                   | ...       | ...         | ...         | ...    |
*/
CREATE TABLE PLAYERS (
    "playerID" TEXT NOT NULL PRIMARY KEY,
        -- <example>'abdelal01'</example>
    "useFirst" TEXT NULL,
        -- <example>'Alaa'</example>
    "firstName" TEXT NULL,
        -- <example>'Alaa'</example>
    "middleName" TEXT NULL,
        -- <example>'Shareef'</example>
    "lastName" TEXT NOT NULL,
        -- <example>'Abdelnaby'</example>
    "nameGiven" TEXT NULL,
        -- <values>{'Dave', 'Ed', 'Jim', 'Mike', 'Mort', 'Robert', 'Thomas', 'Willie', 'nameGiven'}</values>
    "fullGivenName" TEXT NULL,
        -- <example>'Ferdinand Lewis Alcindor, Jr.'</example>
    "nameSuffix" TEXT NULL,
        -- <values>{'II', 'III', 'IV', 'Jr.', 'Sr.', 'nameSuffix'}</values>
    "nameNick" TEXT NULL,
        -- <example>'Lew, Cap'</example>
    "POS" TEXT NULL,
        -- <values>{' G', 'C', 'C-F', 'C-F-G', 'C-G', 'F', 'F-C', 'F-C-G', 'F-G', 'F-G-C', 'G', 'G-F', 'G-F-C', 'pos'}</values>
    "FIRSTSEASON" INTEGER NULL,
        -- <example>0</example>
    "LASTSEASON" INTEGER NULL,
        -- <example>0</example>
    "HEIGHT" REAL NULL,
        -- <example>82.000</example>
    "WEIGHT" INTEGER NULL,
        -- <example>240</example>
    "COLLEGE" TEXT NULL,
        -- <example>'Duke'</example>
    "collegeOther" TEXT NULL,
        -- <example>'Santa Monica City'</example>
    "birthDate" DATE NULL,
        -- <example>'1968-06-24'</example>
    "birthCity" TEXT NULL,
        -- <example>'Cairo'</example>
    "birthState" TEXT NULL,
        -- <example>'NY'</example>
    "birthCountry" TEXT NULL,
        -- <example>'EGY'</example>
    "highSchool" TEXT NULL,
        -- <example>'Bloomfield Senior'</example>
    "hsCity" TEXT NULL,
        -- <example>'Bloomfield'</example>
    "hsState" TEXT NULL,
        -- <example>'NJ'</example>
    "hsCountry" TEXT NULL,
        -- <example>'USA'</example>
    "deathDate" DATE NOT NULL,
        -- <example>'0000-00-00'</example>
    "RACE" TEXT NULL
        -- <values>{'1', 'B', 'O', 'W', 'r'}</values>
);

/*
Schema: NULL
Table: PLAYERS_TEAMS
Rows: 23751
Sample rows:
| id   | playerID   | year   | stint   | tmID   | lgID   | GP   | GS   | minutes   | points   | oRebounds   | dRebounds   | rebounds   | assists   | steals   | blocks   | turnovers   | PF   | fgAttempted   | fgMade   | ftAttempted   | ftMade   | threeAttempted   | threeMade   | PostGP   | PostGS   | PostMinutes   | PostPoints   | PostoRebounds   | PostdRebounds   | PostRebounds   | PostAssists   | PostSteals   | PostBlocks   | PostTurnovers   | PostPF   | PostfgAttempted   | PostfgMade   | PostftAttempted   | PostftMade   | PostthreeAttempted   | PostthreeMade   | note   |
|------|------------|--------|---------|--------|--------|------|------|-----------|----------|-------------|-------------|------------|-----------|----------|----------|-------------|------|---------------|----------|---------------|----------|------------------|-------------|----------|----------|---------------|--------------|-----------------|-----------------|----------------|---------------|--------------|--------------|-----------------|----------|-------------------|--------------|-------------------|--------------|----------------------|-----------------|--------|
| 1    | abdelal01  | 1990   | 1       | POR    | NBA    | 43   | 0    | 290       | 135      | 27          | 62          | 89         | 12        | 4        | 12       | 22          | 39   | 116           | 55       | 44            | 25       | 0                | 0           | 5        | 0        | 13            | 4            | 1               | 2               | 3              | 0             | 0            | 0            | 0               | 0        | 6                 | 2            | 0                 | 0            | 0                    | 0               | [NULL] |
| 2    | abdelal01  | 1991   | 1       | POR    | NBA    | 71   | 0    | 934       | 432      | 81          | 179         | 260        | 30        | 25       | 17       | 66          | 132  | 361           | 178      | 101           | 76       | 0                | 0           | 8        | 0        | 25            | 12           | 0               | 4               | 4              | 2             | 0            | 0            | 2               | 4        | 10                | 5            | 4                 | 2            | 0                    | 0               | [NULL] |
| 3    | abdelal01  | 1992   | 1       | MIL    | NBA    | 12   | 0    | 159       | 64       | 12          | 25          | 37         | 10        | 6        | 4        | 0           | 24   | 56            | 26       | 16            | 12       | 1                | 0           | 0        | 0        | 0             | 0            | 0               | 0               | 0              | 0             | 0            | 0            | 0               | 0        | 0                 | 0            | 0                 | 0            | 0                    | 0               | [NULL] |
| 4    | abdelal01  | 1992   | 2       | BOS    | NBA    | 63   | 0    | 1152      | 514      | 114         | 186         | 300        | 17        | 19       | 22       | 97          | 165  | 417           | 219      | 100           | 76       | 0                | 0           | 4        | 0        | 68            | 22           | 2               | 11              | 13             | 1             | 0            | 1            | 9               | 7        | 24                | 11           | 0                 | 0            | 0                    | 0               | [NULL] |
| 5    | abdelal01  | 1993   | 1       | BOS    | NBA    | 13   | 0    | 159       | 64       | 12          | 34          | 46         | 3         | 2        | 3        | 17          | 20   | 55            | 24       | 25            | 16       | 0                | 0           | 0        | 0        | 0             | 0            | 0               | 0               | 0              | 0             | 0            | 0            | 0               | 0        | 0                 | 0            | 0                 | 0            | 0                    | 0               | [NULL] |
| ...  | ...        | ...    | ...     | ...    | ...    | ...  | ...  | ...       | ...      | ...         | ...         | ...        | ...       | ...      | ...      | ...         | ...  | ...           | ...      | ...           | ...      | ...              | ...         | ...      | ...      | ...           | ...          | ...             | ...             | ...            | ...           | ...          | ...          | ...             | ...      | ...               | ...          | ...               | ...          | ...                  | ...             | ...    |
*/
CREATE TABLE PLAYERS_TEAMS (
    "ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "playerID" TEXT NOT NULL,
        -- <example>'abdelal01'</example>
        -- <fk> -> PLAYERS."playerID"</fk>
    "YEAR" INTEGER NOT NULL,
        -- <example>1990</example>
        -- <fk>composite</fk>
    "STINT" INTEGER NOT NULL,
        -- <example>1</example>
    "tmID" TEXT NOT NULL,
        -- <example>'POR'</example>
        -- <fk>composite</fk>
    "lgID" TEXT NOT NULL,
        -- <values>{'ABA', 'ABL1', 'NBA', 'NBL', 'NPBL', 'PBLA'}</values>
    "GP" INTEGER NOT NULL,
        -- <example>43</example>
    "GS" INTEGER NOT NULL,
        -- <example>0</example>
    "MINUTES" INTEGER NOT NULL,
        -- <example>290</example>
    "POINTS" INTEGER NOT NULL,
        -- <example>135</example>
    "oRebounds" INTEGER NOT NULL,
        -- <example>27</example>
    "dRebounds" INTEGER NOT NULL,
        -- <example>62</example>
    "REBOUNDS" INTEGER NOT NULL,
        -- <example>89</example>
    "ASSISTS" INTEGER NOT NULL,
        -- <example>12</example>
    "STEALS" INTEGER NOT NULL,
        -- <example>4</example>
    "BLOCKS" INTEGER NOT NULL,
        -- <example>12</example>
    "TURNOVERS" INTEGER NOT NULL,
        -- <example>22</example>
    "PF" INTEGER NOT NULL,
        -- <example>39</example>
    "fgAttempted" INTEGER NOT NULL,
        -- <example>116</example>
    "fgMade" INTEGER NOT NULL,
        -- <example>55</example>
    "ftAttempted" INTEGER NOT NULL,
        -- <example>44</example>
    "ftMade" INTEGER NOT NULL,
        -- <example>25</example>
    "threeAttempted" INTEGER NOT NULL,
        -- <example>0</example>
    "threeMade" INTEGER NOT NULL,
        -- <example>0</example>
    "PostGP" INTEGER NOT NULL,
        -- <example>5</example>
    "PostGS" INTEGER NOT NULL,
        -- <example>0</example>
    "PostMinutes" INTEGER NOT NULL,
        -- <example>13</example>
    "PostPoints" INTEGER NOT NULL,
        -- <example>4</example>
    "PostoRebounds" INTEGER NOT NULL,
        -- <example>1</example>
    "PostdRebounds" INTEGER NOT NULL,
        -- <example>2</example>
    "PostRebounds" INTEGER NOT NULL,
        -- <example>3</example>
    "PostAssists" INTEGER NOT NULL,
        -- <example>0</example>
    "PostSteals" INTEGER NOT NULL,
        -- <example>0</example>
    "PostBlocks" INTEGER NOT NULL,
        -- <example>0</example>
    "PostTurnovers" INTEGER NOT NULL,
        -- <example>0</example>
    "PostPF" INTEGER NOT NULL,
        -- <example>0</example>
    "PostfgAttempted" INTEGER NOT NULL,
        -- <example>6</example>
    "PostfgMade" INTEGER NOT NULL,
        -- <example>2</example>
    "PostftAttempted" INTEGER NOT NULL,
        -- <example>0</example>
    "PostftMade" INTEGER NOT NULL,
        -- <example>0</example>
    "PostthreeAttempted" INTEGER NOT NULL,
        -- <example>0</example>
    "PostthreeMade" INTEGER NOT NULL,
        -- <example>0</example>
    "NOTE" TEXT NULL,
        -- <values>{'C'}</values>
    FOREIGN KEY ("tmID", "YEAR") REFERENCES TEAMS("tmID", "YEAR"),
    FOREIGN KEY ("playerID") REFERENCES PLAYERS("playerID")
);

/*
Schema: NULL
Table: SERIES_POST
Rows: 775
Sample rows:
| id   | year   | round   | series   | tmIDWinner   | lgIDWinner   | tmIDLoser   | lgIDLoser   | W   | L   |
|------|--------|---------|----------|--------------|--------------|-------------|-------------|-----|-----|
| 1    | 1946   | F       | O        | PHW          | NBA          | CHS         | NBA         | 4   | 1   |
| 2    | 1946   | QF      | M        | NYK          | NBA          | CLR         | NBA         | 2   | 1   |
| 3    | 1946   | QF      | M        | PHW          | NBA          | STB         | NBA         | 2   | 1   |
| 4    | 1946   | SF      | N        | PHW          | NBA          | NYK         | NBA         | 2   | 0   |
| 5    | 1946   | SF      | N        | CHS          | NBA          | WSC         | NBA         | 4   | 2   |
| ...  | ...    | ...     | ...      | ...          | ...          | ...         | ...         | ... | ... |
*/
CREATE TABLE SERIES_POST (
    "ID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "YEAR" INTEGER NOT NULL,
        -- <example>1946</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    "ROUND" TEXT NOT NULL,
        -- <example>'F'</example>
    "SERIES" TEXT NOT NULL,
        -- <example>'O'</example>
    "tmIDWinner" TEXT NOT NULL,
        -- <example>'PHW'</example>
        -- <fk>composite</fk>
    "lgIDWinner" TEXT NOT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    "tmIDLoser" TEXT NULL,
        -- <example>'CHS'</example>
        -- <fk>composite</fk>
    "lgIDLoser" TEXT NOT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    "W" INTEGER NOT NULL,
        -- <example>4</example>
    "L" INTEGER NOT NULL,
        -- <example>1</example>
    FOREIGN KEY ("tmIDWinner", "YEAR") REFERENCES TEAMS("tmID", "YEAR"),
    FOREIGN KEY ("tmIDLoser", "YEAR") REFERENCES TEAMS("tmID", "YEAR")
);

/*
Schema: NULL
Table: TEAMS
Rows: 1536
Sample rows:
| year   | lgID   | tmID   | franchID   | confID   | divID   | rank   | confRank   | playoff   | name                                        | o_fgm   | o_ftm   | o_pts   | d_pts   | homeWon   | homeLost   | awayWon   | awayLost   | won   | lost   | games   | arena   |
|--------|--------|--------|------------|----------|---------|--------|------------|-----------|---------------------------------------------|---------|---------|---------|---------|-----------|------------|-----------|------------|-------|--------|---------|---------|
| 1937   | NBL    | AFS    | AFS        | [NULL]   | EA      | 1      | 0          | CF        | Akron Firestone Non-Skids                   | 249     | 183     | 681     | 578     | 8         | 1          | 5         | 3          | 14    | 4      | 18      | [NULL]  |
| 1937   | NBL    | AGW    | AGW        | [NULL]   | EA      | 2      | 0          | WC        | Akron Goodyear Wingfoots                    | 243     | 159     | 645     | 498     | 8         | 1          | 5         | 4          | 13    | 5      | 18      | [NULL]  |
| 1937   | NBL    | BFB    | BFB        | [NULL]   | EA      | 4      | 0          | [NULL]    | Buffalo Bisons                              | 108     | 46      | 262     | 275     | 2         | 2          | 1         | 4          | 3     | 6      | 9       | [NULL]  |
| 1937   | NBL    | CNC    | CNC        | [NULL]   | WE      | 5      | 0          | [NULL]    | Richmond King Clothiers/Cincinnati Comellos | 110     | 42      | 262     | 338     | 3         | 1          | 0         | 5          | 3     | 7      | 10      | [NULL]  |
| 1937   | NBL    | COL    | COL        | [NULL]   | EA      | 6      | 0          | [NULL]    | Columbus Athletic Supply                    | 109     | 64      | 282     | 426     | 1         | 3          | 0         | 7          | 1     | 12     | 13      | [NULL]  |
| ...    | ...    | ...    | ...        | ...      | ...     | ...    | ...        | ...       | ...                                         | ...     | ...     | ...     | ...     | ...       | ...        | ...       | ...        | ...   | ...    | ...     | ...     |
*/
CREATE TABLE TEAMS (
    "YEAR" INTEGER NOT NULL,
        -- <example>1937</example>
    "lgID" TEXT NOT NULL,
        -- <values>{'ABA', 'ABL1', 'NBA', 'NBL', 'NPBL', 'PBLA'}</values>
    "tmID" TEXT NOT NULL,
        -- <example>'AFS'</example>
    "franchID" TEXT NOT NULL,
        -- <example>'AFS'</example>
    "confID" TEXT NULL,
        -- <values>{'EC', 'WC'}</values>
    "divID" TEXT NULL,
        -- <values>{'AT', 'CD', 'EA', 'ED', 'MW', 'NO', 'NW', 'PC', 'SE', 'SO', 'SW', 'WD', 'WE'}</values>
    "RANK" INTEGER NOT NULL,
        -- <example>1</example>
    "confRank" INTEGER NOT NULL,
        -- <example>0</example>
    "PLAYOFF" TEXT NULL,
        -- <values>{'AC', 'C1', 'CF', 'CS', 'D1', 'DF', 'DR', 'DS', 'DT', 'F', 'LC', 'NC', 'R1', 'SF', 'WC'}</values>
    "NAME" TEXT NOT NULL,
        -- <example>'Akron Firestone Non-Skids'</example>
    "O_FGM" INTEGER NOT NULL,
        -- <example>249</example>
    "O_FTM" INTEGER NOT NULL,
        -- <example>183</example>
    "O_PTS" INTEGER NOT NULL,
        -- <example>681</example>
    "D_PTS" INTEGER NOT NULL,
        -- <example>578</example>
    "homeWon" INTEGER NOT NULL,
        -- <example>8</example>
    "homeLost" INTEGER NOT NULL,
        -- <example>1</example>
    "awayWon" INTEGER NOT NULL,
        -- <example>5</example>
    "awayLost" INTEGER NOT NULL,
        -- <example>3</example>
    "WON" INTEGER NOT NULL,
        -- <example>14</example>
    "LOST" INTEGER NOT NULL,
        -- <example>4</example>
    "GAMES" INTEGER NOT NULL,
        -- <example>18</example>
    "ARENA" TEXT NULL,
        -- <example>'Boston Garden'</example>
    PRIMARY KEY ("YEAR", "tmID")
);
```