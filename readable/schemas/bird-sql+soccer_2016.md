```sql
-- Database: soccer_2016

-- Table: Ball_by_Ball (136590 rows)
CREATE TABLE Ball_by_Ball (
    Match_Id INTEGER NULL,
        -- <example>335987</example>
        -- <fk> -> Match.Match_Id</fk>
    Over_Id INTEGER NULL,
        -- <example>1</example>
    Ball_Id INTEGER NULL,
        -- <example>1</example>
    Innings_No INTEGER NULL,
        -- <example>1</example>
    Team_Batting INTEGER NULL,
        -- <example>1</example>
    Team_Bowling INTEGER NULL,
        -- <example>2</example>
    Striker_Batting_Position INTEGER NULL,
        -- <example>1</example>
    Striker INTEGER NULL,
        -- <example>1</example>
    Non_Striker INTEGER NULL,
        -- <example>2</example>
    Bowler INTEGER NULL,
        -- <example>14</example>
    PRIMARY KEY (Match_Id, Over_Id, Ball_Id, Innings_No),
    FOREIGN KEY (Match_Id) REFERENCES Match(Match_Id)
);

-- Table: Batsman_Scored (133097 rows)
CREATE TABLE Batsman_Scored (
    Match_Id INTEGER NULL,
        -- <example>335987</example>
        -- <fk> -> Match.Match_Id</fk>
    Over_Id INTEGER NULL,
        -- <example>1</example>
    Ball_Id INTEGER NULL,
        -- <example>1</example>
    Runs_Scored INTEGER NULL,
        -- <example>0</example>
    Innings_No INTEGER NULL,
        -- <example>1</example>
    PRIMARY KEY (Match_Id, Over_Id, Ball_Id, Innings_No),
    FOREIGN KEY (Match_Id) REFERENCES Match(Match_Id)
);

-- Table: Batting_Style (2 rows)
CREATE TABLE Batting_Style (
    Batting_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Batting_hand TEXT NULL
        -- <values>{'Left-hand bat', 'Right-hand bat'}</values>
);

-- Table: Bowling_Style (14 rows)
CREATE TABLE Bowling_Style (
    Bowling_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Bowling_skill TEXT NULL
        -- <example>'Right-arm medium'</example>
);

-- Table: City (29 rows)
CREATE TABLE City (
    City_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    City_Name TEXT NULL,
        -- <example>'Bangalore'</example>
    Country_id INTEGER NULL
        -- <example>1</example>
);

-- Table: Country (12 rows)
CREATE TABLE Country (
    Country_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
        -- <fk> -> Country.Country_Id</fk>
    Country_Name TEXT NULL,
        -- <example>'India'</example>
    FOREIGN KEY (Country_Id) REFERENCES Country(Country_Id)
);

-- Table: Extra_Runs (7469 rows)
CREATE TABLE Extra_Runs (
    Match_Id INTEGER NULL,
        -- <example>335987</example>
    Over_Id INTEGER NULL,
        -- <example>1</example>
    Ball_Id INTEGER NULL,
        -- <example>1</example>
    Extra_Type_Id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Extra_Type.Extra_Id</fk>
    Extra_Runs INTEGER NULL,
        -- <example>1</example>
    Innings_No INTEGER NULL,
        -- <example>1</example>
    PRIMARY KEY (Match_Id, Over_Id, Ball_Id, Innings_No),
    FOREIGN KEY (Extra_Type_Id) REFERENCES Extra_Type(Extra_Id)
);

-- Table: Extra_Type (5 rows)
CREATE TABLE Extra_Type (
    Extra_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Extra_Name TEXT NULL
        -- <values>{'byes', 'legbyes', 'noballs', 'penalty', 'wides'}</values>
);

-- Table: Match (577 rows)
CREATE TABLE Match (
    Match_Id INTEGER NULL PRIMARY KEY,
        -- <example>335987</example>
    Team_1 INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> Team.Team_Id</fk>
    Team_2 INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Team.Team_Id</fk>
    Match_Date DATE NULL,
        -- <example>'2008-04-18'</example>
    Season_Id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Season.Season_Id</fk>
    Venue_Id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Venue.Venue_Id</fk>
    Toss_Winner INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> Team.Team_Id</fk>
    Toss_Decide INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Toss_Decision.Toss_Id</fk>
    Win_Type INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Win_By.Win_Id</fk>
    Win_Margin INTEGER NULL,
        -- <example>140</example>
    Outcome_type INTEGER NULL,
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

-- Table: Out_Type (9 rows)
CREATE TABLE Out_Type (
    Out_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Out_Name TEXT NULL
        -- <values>{'bowled', 'caught and bowled', 'caught', 'hit wicket', 'lbw', 'obstructing the field', 'retired hurt', 'run out', 'stumped'}</values>
);

-- Table: Outcome (3 rows)
CREATE TABLE Outcome (
    Outcome_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Outcome_Type TEXT NULL
        -- <values>{'No Result', 'Result', 'Superover'}</values>
);

-- Table: Player (469 rows)
CREATE TABLE Player (
    Player_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Player_Name TEXT NULL,
        -- <example>'SC Ganguly'</example>
    DOB DATE NULL,
        -- <example>'1972-07-08'</example>
    Batting_hand INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Batting_Style.Batting_Id</fk>
    Bowling_skill INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Bowling_Style.Bowling_Id</fk>
    Country_Name INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Country.Country_Id</fk>
    FOREIGN KEY (Batting_hand) REFERENCES Batting_Style(Batting_Id),
    FOREIGN KEY (Bowling_skill) REFERENCES Bowling_Style(Bowling_Id),
    FOREIGN KEY (Country_Name) REFERENCES Country(Country_Id)
);

-- Table: Player_Match (12694 rows)
CREATE TABLE Player_Match (
    Match_Id INTEGER NULL,
        -- <example>335987</example>
        -- <fk> -> Match.Match_Id</fk>
    Player_Id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Player.Player_Id</fk>
    Role_Id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Rolee.Role_Id</fk>
    Team_Id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Team.Team_Id</fk>
    PRIMARY KEY (Match_Id, Player_Id, Role_Id),
    FOREIGN KEY (Match_Id) REFERENCES Match(Match_Id),
    FOREIGN KEY (Player_Id) REFERENCES Player(Player_Id),
    FOREIGN KEY (Team_Id) REFERENCES Team(Team_Id),
    FOREIGN KEY (Role_Id) REFERENCES Rolee(Role_Id)
);

-- Table: Rolee (4 rows)
CREATE TABLE Rolee (
    Role_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Role_Desc TEXT NULL
        -- <values>{'Captain', 'CaptainKeeper', 'Keeper', 'Player'}</values>
);

-- Table: Season (9 rows)
CREATE TABLE Season (
    Season_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Man_of_the_Series INTEGER NULL,
        -- <example>32</example>
    Orange_Cap INTEGER NULL,
        -- <example>100</example>
    Purple_Cap INTEGER NULL,
        -- <example>102</example>
    Season_Year INTEGER NULL
        -- <example>2008</example>
);

-- Table: Team (13 rows)
CREATE TABLE Team (
    Team_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Team_Name TEXT NULL
        -- <example>'Kolkata Knight Riders'</example>
);

-- Table: Toss_Decision (2 rows)
CREATE TABLE Toss_Decision (
    Toss_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Toss_Name TEXT NULL
        -- <values>{'bat', 'field'}</values>
);

-- Table: Umpire (52 rows)
CREATE TABLE Umpire (
    Umpire_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Umpire_Name TEXT NULL,
        -- <example>'Asad Rauf'</example>
    Umpire_Country INTEGER NULL,
        -- <example>6</example>
        -- <fk> -> Country.Country_Id</fk>
    FOREIGN KEY (Umpire_Country) REFERENCES Country(Country_Id)
);

-- Table: Venue (35 rows)
CREATE TABLE Venue (
    Venue_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Venue_Name TEXT NULL,
        -- <example>'M Chinnaswamy Stadium'</example>
    City_Id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> City.City_Id</fk>
    FOREIGN KEY (City_Id) REFERENCES City(City_Id)
);

-- Table: Wicket_Taken (6727 rows)
CREATE TABLE Wicket_Taken (
    Match_Id INTEGER NULL,
        -- <example>335987</example>
        -- <fk> -> Match.Match_Id</fk>
    Over_Id INTEGER NULL,
        -- <example>2</example>
    Ball_Id INTEGER NULL,
        -- <example>1</example>
    Player_Out INTEGER NULL,
        -- <example>6</example>
        -- <fk> -> Player.Player_Id</fk>
    Kind_Out INTEGER NULL,
        -- <example>2</example>
        -- <fk> -> Out_Type.Out_Id</fk>
    Fielders INTEGER NULL,
        -- <example>83</example>
        -- <fk> -> Player.Player_Id</fk>
    Innings_No INTEGER NULL,
        -- <example>2</example>
    PRIMARY KEY (Match_Id, Over_Id, Ball_Id, Innings_No),
    FOREIGN KEY (Match_Id) REFERENCES Match(Match_Id),
    FOREIGN KEY (Player_Out) REFERENCES Player(Player_Id),
    FOREIGN KEY (Kind_Out) REFERENCES Out_Type(Out_Id),
    FOREIGN KEY (Fielders) REFERENCES Player(Player_Id)
);

-- Table: Win_By (4 rows)
CREATE TABLE Win_By (
    Win_Id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    Win_Type TEXT NULL
        -- <values>{'NO Result', 'Tie', 'runs', 'wickets'}</values>
);
```