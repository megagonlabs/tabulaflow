```sql
-- Database: soccer_2016

/*
Schema: NULLTable: Ball_by_Ball
Rows: 136590
Sample rows:
| Match_Id   | Over_Id   | Ball_Id   | Innings_No   | Team_Batting   | Team_Bowling   | Striker_Batting_Position   | Striker   | Non_Striker   | Bowler   |
|------------|-----------|-----------|--------------|----------------|----------------|----------------------------|-----------|---------------|----------|
| 335987     | 1         | 1         | 1            | 1              | 2              | 1                          | 1         | 2             | 14       |
| 335987     | 1         | 1         | 2            | 2              | 1              | 1                          | 6         | 7             | 106      |
| 335987     | 1         | 2         | 1            | 1              | 2              | 2                          | 2         | 1             | 14       |
| 335987     | 1         | 2         | 2            | 2              | 1              | 2                          | 7         | 6             | 106      |
| 335987     | 1         | 3         | 1            | 1              | 2              | 2                          | 2         | 1             | 14       |
| ...        | ...       | ...       | ...          | ...            | ...            | ...                        | ...       | ...           | ...      |
*/
CREATE TABLE Ball_by_Ball (
    Match_Id INTEGER NOT NULL,
        -- <example>335987</example>
        -- <fk> -> Match.Match_Id</fk>
    Over_Id INTEGER NOT NULL,
        -- <example>1</example>
    Ball_Id INTEGER NOT NULL,
        -- <example>1</example>
    Innings_No INTEGER NOT NULL,
        -- <example>1</example>
    Team_Batting INTEGER NOT NULL,
        -- <example>1</example>
    Team_Bowling INTEGER NOT NULL,
        -- <example>2</example>
    Striker_Batting_Position INTEGER NOT NULL,
        -- <example>1</example>
    Striker INTEGER NOT NULL,
        -- <example>1</example>
    Non_Striker INTEGER NOT NULL,
        -- <example>2</example>
    Bowler INTEGER NOT NULL,
        -- <example>14</example>
    PRIMARY KEY (Match_Id, Over_Id, Ball_Id, Innings_No),
    FOREIGN KEY (Match_Id) REFERENCES Match(Match_Id)
);

/*
Schema: NULLTable: Batsman_Scored
Rows: 133097
Sample rows:
| Match_Id   | Over_Id   | Ball_Id   | Runs_Scored   | Innings_No   |
|------------|-----------|-----------|---------------|--------------|
| 335987     | 1         | 1         | 0             | 1            |
| 335987     | 1         | 1         | 1             | 2            |
| 335987     | 1         | 2         | 0             | 1            |
| 335987     | 1         | 3         | 0             | 2            |
| 335987     | 1         | 4         | 0             | 1            |
| ...        | ...       | ...       | ...           | ...          |
*/
CREATE TABLE Batsman_Scored (
    Match_Id INTEGER NOT NULL,
        -- <example>335987</example>
        -- <fk> -> Match.Match_Id</fk>
    Over_Id INTEGER NOT NULL,
        -- <example>1</example>
    Ball_Id INTEGER NOT NULL,
        -- <example>1</example>
    Runs_Scored INTEGER NOT NULL,
        -- <example>0</example>
    Innings_No INTEGER NOT NULL,
        -- <example>1</example>
    PRIMARY KEY (Match_Id, Over_Id, Ball_Id, Innings_No),
    FOREIGN KEY (Match_Id) REFERENCES Match(Match_Id)
);

/*
Schema: NULLTable: Batting_Style
Rows: 2
All rows:
|   Batting_Id | Batting_hand   |
|--------------|----------------|
|            1 | Left-hand bat  |
|            2 | Right-hand bat |
*/
CREATE TABLE Batting_Style (
    Batting_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Batting_hand TEXT NOT NULL
        -- <values>{'Left-hand bat', 'Right-hand bat'}</values>
);

/*
Schema: NULLTable: Bowling_Style
Rows: 14
Sample rows:
| Bowling_Id   | Bowling_skill         |
|--------------|-----------------------|
| 1            | Right-arm medium      |
| 2            | Right-arm offbreak    |
| 3            | Right-arm fast-medium |
| 4            | Legbreak googly       |
| 5            | Right-arm medium-fast |
| ...          | ...                   |
*/
CREATE TABLE Bowling_Style (
    Bowling_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Bowling_skill TEXT NOT NULL
        -- <example>'Right-arm medium'</example>
);

/*
Schema: NULLTable: City
Rows: 29
Sample rows:
| City_Id   | City_Name   | Country_id   |
|-----------|-------------|--------------|
| 1         | Bangalore   | 1            |
| 2         | Chandigarh  | 1            |
| 3         | Delhi       | 1            |
| 4         | Mumbai      | 1            |
| 5         | Kolkata     | 1            |
| ...       | ...         | ...          |
*/
CREATE TABLE City (
    City_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    City_Name TEXT NOT NULL,
        -- <example>'Bangalore'</example>
    Country_id INTEGER NOT NULL
        -- <example>1</example>
);

/*
Schema: NULLTable: Country
Rows: 12
Sample rows:
| Country_Id   | Country_Name   |
|--------------|----------------|
| 1            | India          |
| 2            | South Africa   |
| 3            | U.A.E          |
| 4            | New Zealand    |
| 5            | Australia      |
| ...          | ...            |
*/
CREATE TABLE Country (
    Country_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> Country.Country_Id</fk>
    Country_Name TEXT NOT NULL,
        -- <example>'India'</example>
    FOREIGN KEY (Country_Id) REFERENCES Country(Country_Id)
);

/*
Schema: NULLTable: Extra_Runs
Rows: 7469
Sample rows:
| Match_Id   | Over_Id   | Ball_Id   | Extra_Type_Id   | Extra_Runs   | Innings_No   |
|------------|-----------|-----------|-----------------|--------------|--------------|
| 335987     | 1         | 1         | 1               | 1            | 1            |
| 335987     | 1         | 2         | 2               | 1            | 2            |
| 335987     | 1         | 3         | 2               | 1            | 1            |
| 335987     | 1         | 7         | 1               | 1            | 1            |
| 335987     | 2         | 3         | 1               | 4            | 2            |
| ...        | ...       | ...       | ...             | ...          | ...          |
*/
CREATE TABLE Extra_Runs (
    Match_Id INTEGER NOT NULL,
        -- <example>335987</example>
    Over_Id INTEGER NOT NULL,
        -- <example>1</example>
    Ball_Id INTEGER NOT NULL,
        -- <example>1</example>
    Extra_Type_Id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Extra_Type.Extra_Id</fk>
    Extra_Runs INTEGER NOT NULL,
        -- <example>1</example>
    Innings_No INTEGER NOT NULL,
        -- <example>1</example>
    PRIMARY KEY (Match_Id, Over_Id, Ball_Id, Innings_No),
    FOREIGN KEY (Extra_Type_Id) REFERENCES Extra_Type(Extra_Id)
);

/*
Schema: NULLTable: Extra_Type
Rows: 5
All rows:
|   Extra_Id | Extra_Name   |
|------------|--------------|
|          1 | legbyes      |
|          2 | wides        |
|          3 | byes         |
|          4 | noballs      |
|          5 | penalty      |
*/
CREATE TABLE Extra_Type (
    Extra_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Extra_Name TEXT NOT NULL
        -- <values>{'byes', 'legbyes', 'noballs', 'penalty', 'wides'}</values>
);

/*
Schema: NULLTable: Match
Rows: 577
Sample rows:
| Match_Id   | Team_1   | Team_2   | Match_Date   | Season_Id   | Venue_Id   | Toss_Winner   | Toss_Decide   | Win_Type   | Win_Margin   | Outcome_type   | Match_Winner   | Man_of_the_Match   |
|------------|----------|----------|--------------|-------------|------------|---------------|---------------|------------|--------------|----------------|----------------|--------------------|
| 335987     | 2        | 1        | 2008-04-18   | 1           | 1          | 2             | 1             | 1          | 140          | 1              | 1              | 2                  |
| 335988     | 4        | 3        | 2008-04-19   | 1           | 2          | 3             | 2             | 1          | 33           | 1              | 3              | 19                 |
| 335989     | 6        | 5        | 2008-04-19   | 1           | 3          | 5             | 2             | 2          | 9            | 1              | 6              | 90                 |
| 335990     | 7        | 2        | 2008-04-20   | 1           | 4          | 7             | 2             | 2          | 5            | 1              | 2              | 11                 |
| 335991     | 1        | 8        | 2008-04-20   | 1           | 5          | 8             | 2             | 2          | 5            | 1              | 1              | 4                  |
| ...        | ...      | ...      | ...          | ...         | ...        | ...           | ...           | ...        | ...          | ...            | ...            | ...                |
*/
CREATE TABLE Match (
    Match_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>335987</example>
    Team_1 INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> Team.Team_Id</fk>
    Team_2 INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Team.Team_Id</fk>
    Match_Date DATE NOT NULL,
        -- <example>'2008-04-18'</example>
    Season_Id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Season.Season_Id</fk>
    Venue_Id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Venue.Venue_Id</fk>
    Toss_Winner INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> Team.Team_Id</fk>
    Toss_Decide INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Toss_Decision.Toss_Id</fk>
    Win_Type INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Win_By.Win_Id</fk>
    Win_Margin INTEGER NULL,
        -- <example>140</example>
    Outcome_type INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Out_Type.Out_Id</fk>
    Match_Winner INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Team.Team_Id</fk>
    Man_of_the_Match INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> Player.Player_Id</fk>
    FOREIGN KEY (Team_1) REFERENCES Team(Team_Id),
    FOREIGN KEY (Team_2) REFERENCES Team(Team_Id),
    FOREIGN KEY (Season_Id) REFERENCES Season(Season_Id),
    FOREIGN KEY (Venue_Id) REFERENCES Venue(Venue_Id),
    FOREIGN KEY (Toss_Winner) REFERENCES Team(Team_Id),
    FOREIGN KEY (Toss_Decide) REFERENCES Toss_Decision(Toss_Id),
    FOREIGN KEY (Win_Type) REFERENCES Win_By(Win_Id),
    FOREIGN KEY (Outcome_type) REFERENCES Out_Type(Out_Id),
    FOREIGN KEY (Match_Winner) REFERENCES Team(Team_Id),
    FOREIGN KEY (Man_of_the_Match) REFERENCES Player(Player_Id)
);

/*
Schema: NULLTable: Out_Type
Rows: 9
All rows:
|   Out_Id | Out_Name              |
|----------|-----------------------|
|        1 | caught                |
|        2 | bowled                |
|        3 | run out               |
|        4 | lbw                   |
|        5 | retired hurt          |
|        6 | stumped               |
|        7 | caught and bowled     |
|        8 | hit wicket            |
|        9 | obstructing the field |
*/
CREATE TABLE Out_Type (
    Out_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Out_Name TEXT NOT NULL
        -- <values>{'bowled', 'caught and bowled', 'caught', 'hit wicket', 'lbw', 'obstructing the field', 'retired hurt', 'run out', 'stumped'}</values>
);

/*
Schema: NULLTable: Outcome
Rows: 3
All rows:
|   Outcome_Id | Outcome_Type   |
|--------------|----------------|
|            1 | Result         |
|            2 | No Result      |
|            3 | Superover      |
*/
CREATE TABLE Outcome (
    Outcome_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Outcome_Type TEXT NOT NULL
        -- <values>{'No Result', 'Result', 'Superover'}</values>
);

/*
Schema: NULLTable: Player
Rows: 469
Sample rows:
| Player_Id   | Player_Name     | DOB        | Batting_hand   | Bowling_skill   | Country_Name   |
|-------------|-----------------|------------|----------------|-----------------|----------------|
| 1           | SC Ganguly      | 1972-07-08 | 1              | 1               | 1              |
| 2           | BB McCullum     | 1981-09-27 | 2              | 1               | 4              |
| 3           | RT Ponting      | 1974-12-19 | 2              | 1               | 5              |
| 4           | DJ Hussey       | 1977-07-15 | 2              | 2               | 5              |
| 5           | Mohammad Hafeez | 1980-10-17 | 2              | 2               | 6              |
| ...         | ...             | ...        | ...            | ...             | ...            |
*/
CREATE TABLE Player (
    Player_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Player_Name TEXT NOT NULL,
        -- <example>'SC Ganguly'</example>
    DOB DATE NOT NULL,
        -- <example>'1972-07-08'</example>
    Batting_hand INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Batting_Style.Batting_Id</fk>
    Bowling_skill INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Bowling_Style.Bowling_Id</fk>
    Country_Name INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Country.Country_Id</fk>
    FOREIGN KEY (Batting_hand) REFERENCES Batting_Style(Batting_Id),
    FOREIGN KEY (Bowling_skill) REFERENCES Bowling_Style(Bowling_Id),
    FOREIGN KEY (Country_Name) REFERENCES Country(Country_Id)
);

/*
Schema: NULLTable: Player_Match
Rows: 12694
Sample rows:
| Match_Id   | Player_Id   | Role_Id   | Team_Id   |
|------------|-------------|-----------|-----------|
| 335987     | 1           | 1         | 1         |
| 335987     | 2           | 3         | 1         |
| 335987     | 3           | 3         | 1         |
| 335987     | 4           | 3         | 1         |
| 335987     | 5           | 3         | 1         |
| ...        | ...         | ...       | ...       |
*/
CREATE TABLE Player_Match (
    Match_Id INTEGER NOT NULL,
        -- <example>335987</example>
        -- <fk> -> Match.Match_Id</fk>
    Player_Id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Player.Player_Id</fk>
    Role_Id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Rolee.Role_Id</fk>
    Team_Id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Team.Team_Id</fk>
    PRIMARY KEY (Match_Id, Player_Id, Role_Id),
    FOREIGN KEY (Match_Id) REFERENCES Match(Match_Id),
    FOREIGN KEY (Player_Id) REFERENCES Player(Player_Id),
    FOREIGN KEY (Team_Id) REFERENCES Team(Team_Id),
    FOREIGN KEY (Role_Id) REFERENCES Rolee(Role_Id)
);

/*
Schema: NULLTable: Rolee
Rows: 4
All rows:
|   Role_Id | Role_Desc     |
|-----------|---------------|
|         1 | Captain       |
|         2 | Keeper        |
|         3 | Player        |
|         4 | CaptainKeeper |
*/
CREATE TABLE Rolee (
    Role_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Role_Desc TEXT NOT NULL
        -- <values>{'Captain', 'CaptainKeeper', 'Keeper', 'Player'}</values>
);

/*
Schema: NULLTable: Season
Rows: 9
All rows:
|   Season_Id |   Man_of_the_Series |   Orange_Cap |   Purple_Cap |   Season_Year |
|-------------|---------------------|--------------|--------------|---------------|
|           1 |                  32 |          100 |          102 |          2008 |
|           2 |                  53 |           18 |           61 |          2009 |
|           3 |                 133 |          133 |          131 |          2010 |
|           4 |                 162 |          162 |          194 |          2011 |
|           5 |                 315 |          162 |          190 |          2012 |
|           6 |                  32 |           19 |           71 |          2013 |
|           7 |                 305 |           46 |          364 |          2014 |
|           8 |                 334 |          187 |           71 |          2015 |
|           9 |                   8 |            8 |          299 |          2016 |
*/
CREATE TABLE Season (
    Season_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Man_of_the_Series INTEGER NOT NULL,
        -- <example>32</example>
    Orange_Cap INTEGER NOT NULL,
        -- <example>100</example>
    Purple_Cap INTEGER NOT NULL,
        -- <example>102</example>
    Season_Year INTEGER NOT NULL
        -- <example>2008</example>
);

/*
Schema: NULLTable: Team
Rows: 13
Sample rows:
| Team_Id   | Team_Name                   |
|-----------|-----------------------------|
| 1         | Kolkata Knight Riders       |
| 2         | Royal Challengers Bangalore |
| 3         | Chennai Super Kings         |
| 4         | Kings XI Punjab             |
| 5         | Rajasthan Royals            |
| ...       | ...                         |
*/
CREATE TABLE Team (
    Team_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Team_Name TEXT NOT NULL
        -- <example>'Kolkata Knight Riders'</example>
);

/*
Schema: NULLTable: Toss_Decision
Rows: 2
All rows:
|   Toss_Id | Toss_Name   |
|-----------|-------------|
|         1 | field       |
|         2 | bat         |
*/
CREATE TABLE Toss_Decision (
    Toss_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Toss_Name TEXT NOT NULL
        -- <values>{'bat', 'field'}</values>
);

/*
Schema: NULLTable: Umpire
Rows: 52
Sample rows:
| Umpire_Id   | Umpire_Name   | Umpire_Country   |
|-------------|---------------|------------------|
| 1           | Asad Rauf     | 6                |
| 2           | MR Benson     | 10               |
| 3           | Aleem Dar     | 6                |
| 4           | SJ Davis      | 10               |
| 5           | BF Bowden     | 4                |
| ...         | ...           | ...              |
*/
CREATE TABLE Umpire (
    Umpire_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Umpire_Name TEXT NOT NULL,
        -- <example>'Asad Rauf'</example>
    Umpire_Country INTEGER NOT NULL,
        -- <example>6</example>
        -- <fk> -> Country.Country_Id</fk>
    FOREIGN KEY (Umpire_Country) REFERENCES Country(Country_Id)
);

/*
Schema: NULLTable: Venue
Rows: 35
Sample rows:
| Venue_Id   | Venue_Name                         | City_Id   |
|------------|------------------------------------|-----------|
| 1          | M Chinnaswamy Stadium              | 1         |
| 2          | Punjab Cricket Association Stadium | 2         |
| 3          | Feroz Shah Kotla                   | 3         |
| 4          | Wankhede Stadium                   | 4         |
| 5          | Eden Gardens                       | 5         |
| ...        | ...                                | ...       |
*/
CREATE TABLE Venue (
    Venue_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Venue_Name TEXT NOT NULL,
        -- <example>'M Chinnaswamy Stadium'</example>
    City_Id INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> City.City_Id</fk>
    FOREIGN KEY (City_Id) REFERENCES City(City_Id)
);

/*
Schema: NULLTable: Wicket_Taken
Rows: 6727
Sample rows:
| Match_Id   | Over_Id   | Ball_Id   | Player_Out   | Kind_Out   | Fielders   | Innings_No   |
|------------|-----------|-----------|--------------|------------|------------|--------------|
| 335987     | 2         | 1         | 6            | 2          | [NULL]     | 2            |
| 335987     | 3         | 2         | 8            | 2          | [NULL]     | 2            |
| 335987     | 5         | 5         | 9            | 1          | 83.0       | 2            |
| 335987     | 6         | 2         | 1            | 1          | 9.0        | 1            |
| 335987     | 6         | 2         | 7            | 1          | 3.0        | 2            |
| ...        | ...       | ...       | ...          | ...        | ...        | ...          |
*/
CREATE TABLE Wicket_Taken (
    Match_Id INTEGER NOT NULL,
        -- <example>335987</example>
        -- <fk> -> Match.Match_Id</fk>
    Over_Id INTEGER NOT NULL,
        -- <example>2</example>
    Ball_Id INTEGER NOT NULL,
        -- <example>1</example>
    Player_Out INTEGER NOT NULL,
        -- <example>6</example>
        -- <fk> -> Player.Player_Id</fk>
    Kind_Out INTEGER NOT NULL,
        -- <example>2</example>
        -- <fk> -> Out_Type.Out_Id</fk>
    Fielders INTEGER NULL,
        -- <example>83</example>
        -- <fk> -> Player.Player_Id</fk>
    Innings_No INTEGER NOT NULL,
        -- <example>2</example>
    PRIMARY KEY (Match_Id, Over_Id, Ball_Id, Innings_No),
    FOREIGN KEY (Match_Id) REFERENCES Match(Match_Id),
    FOREIGN KEY (Player_Out) REFERENCES Player(Player_Id),
    FOREIGN KEY (Kind_Out) REFERENCES Out_Type(Out_Id),
    FOREIGN KEY (Fielders) REFERENCES Player(Player_Id)
);

/*
Schema: NULLTable: Win_By
Rows: 4
All rows:
|   Win_Id | Win_Type   |
|----------|------------|
|        1 | runs       |
|        2 | wickets    |
|        3 | NO Result  |
|        4 | Tie        |
*/
CREATE TABLE Win_By (
    Win_Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    Win_Type TEXT NOT NULL
        -- <values>{'NO Result', 'Tie', 'runs', 'wickets'}</values>
);
```