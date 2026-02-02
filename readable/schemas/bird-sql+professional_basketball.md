```sql
-- Database: professional_basketball

-- Table: awards_coaches (61 rows)
CREATE TABLE awards_coaches (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    year INTEGER NULL,
        -- <example>1962</example>
        -- <fk>composite</fk>
    coachID TEXT NULL,
        -- <example>'gallaha01'</example>
        -- <fk>composite</fk>
    award TEXT NULL,
        -- <values>{'ABA Coach of the Year', 'NBA Coach of the Year'}</values>
    lgID TEXT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    note TEXT NULL,
        -- <values>{'tie'}</values>
    FOREIGN KEY (coachID, year) REFERENCES coaches(coachID, year)
);

-- Table: awards_players (1719 rows)
CREATE TABLE awards_players (
    playerID TEXT NOT NULL,
        -- <example>'abdulka01'</example>
        -- <fk> -> players.playerID</fk>
    award TEXT NOT NULL,
        -- <example>'All-Defensive Second Team'</example>
    year INTEGER NOT NULL,
        -- <example>1969</example>
    lgID TEXT NULL,
        -- <values>{'ABA', 'ABL1', 'NBA', 'NBL'}</values>
    note TEXT NULL,
        -- <values>{'tie'}</values>
    pos TEXT NULL,
        -- <values>{'C', 'F', 'F/C', 'F/G', 'G'}</values>
    PRIMARY KEY (playerID, award, year),
    FOREIGN KEY (playerID) REFERENCES players(playerID)
);

-- Table: coaches (1689 rows)
CREATE TABLE coaches (
    coachID TEXT NOT NULL,
        -- <example>'adelmri01'</example>
    year INTEGER NOT NULL,
        -- <example>1988</example>
        -- <fk>composite</fk>
    tmID TEXT NOT NULL,
        -- <example>'POR'</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'ABA', 'ABL1', 'NBA', 'NPBL', 'PBLA'}</values>
    stint INTEGER NOT NULL,
        -- <example>2</example>
    won INTEGER NULL,
        -- <example>14</example>
    lost INTEGER NULL,
        -- <example>21</example>
    post_wins INTEGER NULL,
        -- <example>0</example>
    post_losses INTEGER NULL,
        -- <example>3</example>
    PRIMARY KEY (coachID, year, tmID, stint),
    FOREIGN KEY (tmID, year) REFERENCES teams(tmID, year)
);

-- Table: draft (8621 rows)
CREATE TABLE draft (
    id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    draftYear INTEGER NULL,
        -- <example>1967</example>
        -- <fk>composite</fk>
    draftRound INTEGER NULL,
        -- <example>0</example>
    draftSelection INTEGER NULL,
        -- <example>0</example>
    draftOverall INTEGER NULL,
        -- <example>0</example>
    tmID TEXT NULL,
        -- <example>'ANA'</example>
        -- <fk>composite</fk>
    firstName TEXT NULL,
        -- <example>'Darrell'</example>
    lastName TEXT NULL,
        -- <example>'Hardy'</example>
    suffixName TEXT NULL,
        -- <values>{'Jr.'}</values>
    playerID TEXT NULL,
        -- <example>'hardyda01'</example>
    draftFrom TEXT NULL,
        -- <example>'Baylor'</example>
    lgID TEXT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    FOREIGN KEY (tmID, draftYear) REFERENCES teams(tmID, year)
);

-- Table: player_allstar (1608 rows)
CREATE TABLE player_allstar (
    playerID TEXT NOT NULL,
        -- <example>'abdulka01'</example>
        -- <fk> -> players.playerID</fk>
    last_name TEXT NULL,
        -- <example>'Abdul-Jabbar'</example>
    first_name TEXT NULL,
        -- <example>'Kareem'</example>
    season_id INTEGER NOT NULL,
        -- <example>1969</example>
    conference TEXT NULL,
        -- <values>{'Allstars', 'Denver', 'East', 'Weset', 'West'}</values>
    league_id TEXT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    games_played INTEGER NULL,
        -- <example>1</example>
    minutes INTEGER NULL,
        -- <example>18</example>
    points INTEGER NULL,
        -- <example>10</example>
    o_rebounds INTEGER NULL,
        -- <example>1</example>
    d_rebounds INTEGER NULL,
        -- <example>2</example>
    rebounds INTEGER NULL,
        -- <example>11</example>
    assists INTEGER NULL,
        -- <example>4</example>
    steals INTEGER NULL,
        -- <example>3</example>
    blocks INTEGER NULL,
        -- <example>2</example>
    turnovers INTEGER NULL,
        -- <example>1</example>
    personal_fouls INTEGER NULL,
        -- <example>3</example>
    fg_attempted INTEGER NULL,
        -- <example>8</example>
    fg_made INTEGER NULL,
        -- <example>4</example>
    ft_attempted INTEGER NULL,
        -- <example>2</example>
    ft_made INTEGER NULL,
        -- <example>2</example>
    three_attempted INTEGER NULL,
        -- <example>0</example>
    three_made INTEGER NULL,
        -- <example>0</example>
    PRIMARY KEY (playerID, season_id),
    FOREIGN KEY (playerID) REFERENCES players(playerID)
);

-- Table: players (5062 rows)
CREATE TABLE players (
    playerID TEXT NOT NULL PRIMARY KEY,
        -- <example>'abdelal01'</example>
    useFirst TEXT NULL,
        -- <example>'Alaa'</example>
    firstName TEXT NULL,
        -- <example>'Alaa'</example>
    middleName TEXT NULL,
        -- <example>'Shareef'</example>
    lastName TEXT NULL,
        -- <example>'Abdelnaby'</example>
    nameGiven TEXT NULL,
        -- <values>{'Dave', 'Ed', 'Jim', 'Mike', 'Mort', 'Robert', 'Thomas', 'Willie', 'nameGiven'}</values>
    fullGivenName TEXT NULL,
        -- <example>'Ferdinand Lewis Alcindor, Jr.'</example>
    nameSuffix TEXT NULL,
        -- <values>{'II', 'III', 'IV', 'Jr.', 'Sr.', 'nameSuffix'}</values>
    nameNick TEXT NULL,
        -- <example>'Lew, Cap'</example>
    pos TEXT NULL,
        -- <values>{' G', 'C', 'C-F', 'C-F-G', 'C-G', 'F', 'F-C', 'F-C-G', 'F-G', 'F-G-C', 'G', 'G-F', 'G-F-C', 'pos'}</values>
    firstseason INTEGER NULL,
        -- <example>0</example>
    lastseason INTEGER NULL,
        -- <example>0</example>
    height REAL NULL,
        -- <example>82.000</example>
    weight INTEGER NULL,
        -- <example>240</example>
    college TEXT NULL,
        -- <example>'Duke'</example>
    collegeOther TEXT NULL,
        -- <example>'Santa Monica City'</example>
    birthDate DATE NULL,
        -- <example>'1968-06-24'</example>
    birthCity TEXT NULL,
        -- <example>'Cairo'</example>
    birthState TEXT NULL,
        -- <example>'NY'</example>
    birthCountry TEXT NULL,
        -- <example>'EGY'</example>
    highSchool TEXT NULL,
        -- <example>'Bloomfield Senior'</example>
    hsCity TEXT NULL,
        -- <example>'Bloomfield'</example>
    hsState TEXT NULL,
        -- <example>'NJ'</example>
    hsCountry TEXT NULL,
        -- <example>'USA'</example>
    deathDate DATE NULL,
        -- <example>'0000-00-00'</example>
    race TEXT NULL
        -- <values>{'1', 'B', 'O', 'W', 'r'}</values>
);

-- Table: players_teams (23751 rows)
CREATE TABLE players_teams (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    playerID TEXT NOT NULL,
        -- <example>'abdelal01'</example>
        -- <fk> -> players.playerID</fk>
    year INTEGER NULL,
        -- <example>1990</example>
        -- <fk>composite</fk>
    stint INTEGER NULL,
        -- <example>1</example>
    tmID TEXT NULL,
        -- <example>'POR'</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'ABA', 'ABL1', 'NBA', 'NBL', 'NPBL', 'PBLA'}</values>
    GP INTEGER NULL,
        -- <example>43</example>
    GS INTEGER NULL,
        -- <example>0</example>
    minutes INTEGER NULL,
        -- <example>290</example>
    points INTEGER NULL,
        -- <example>135</example>
    oRebounds INTEGER NULL,
        -- <example>27</example>
    dRebounds INTEGER NULL,
        -- <example>62</example>
    rebounds INTEGER NULL,
        -- <example>89</example>
    assists INTEGER NULL,
        -- <example>12</example>
    steals INTEGER NULL,
        -- <example>4</example>
    blocks INTEGER NULL,
        -- <example>12</example>
    turnovers INTEGER NULL,
        -- <example>22</example>
    PF INTEGER NULL,
        -- <example>39</example>
    fgAttempted INTEGER NULL,
        -- <example>116</example>
    fgMade INTEGER NULL,
        -- <example>55</example>
    ftAttempted INTEGER NULL,
        -- <example>44</example>
    ftMade INTEGER NULL,
        -- <example>25</example>
    threeAttempted INTEGER NULL,
        -- <example>0</example>
    threeMade INTEGER NULL,
        -- <example>0</example>
    PostGP INTEGER NULL,
        -- <example>5</example>
    PostGS INTEGER NULL,
        -- <example>0</example>
    PostMinutes INTEGER NULL,
        -- <example>13</example>
    PostPoints INTEGER NULL,
        -- <example>4</example>
    PostoRebounds INTEGER NULL,
        -- <example>1</example>
    PostdRebounds INTEGER NULL,
        -- <example>2</example>
    PostRebounds INTEGER NULL,
        -- <example>3</example>
    PostAssists INTEGER NULL,
        -- <example>0</example>
    PostSteals INTEGER NULL,
        -- <example>0</example>
    PostBlocks INTEGER NULL,
        -- <example>0</example>
    PostTurnovers INTEGER NULL,
        -- <example>0</example>
    PostPF INTEGER NULL,
        -- <example>0</example>
    PostfgAttempted INTEGER NULL,
        -- <example>6</example>
    PostfgMade INTEGER NULL,
        -- <example>2</example>
    PostftAttempted INTEGER NULL,
        -- <example>0</example>
    PostftMade INTEGER NULL,
        -- <example>0</example>
    PostthreeAttempted INTEGER NULL,
        -- <example>0</example>
    PostthreeMade INTEGER NULL,
        -- <example>0</example>
    note TEXT NULL,
        -- <values>{'C'}</values>
    FOREIGN KEY (tmID, year) REFERENCES teams(tmID, year),
    FOREIGN KEY (playerID) REFERENCES players(playerID)
);

-- Table: series_post (775 rows)
CREATE TABLE series_post (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    year INTEGER NULL,
        -- <example>1946</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    round TEXT NULL,
        -- <example>'F'</example>
    series TEXT NULL,
        -- <example>'O'</example>
    tmIDWinner TEXT NULL,
        -- <example>'PHW'</example>
        -- <fk>composite</fk>
    lgIDWinner TEXT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    tmIDLoser TEXT NULL,
        -- <example>'CHS'</example>
        -- <fk>composite</fk>
    lgIDLoser TEXT NULL,
        -- <values>{'ABA', 'NBA'}</values>
    W INTEGER NULL,
        -- <example>4</example>
    L INTEGER NULL,
        -- <example>1</example>
    FOREIGN KEY (tmIDWinner, year) REFERENCES teams(tmID, year),
    FOREIGN KEY (tmIDLoser, year) REFERENCES teams(tmID, year)
);

-- Table: teams (1536 rows)
CREATE TABLE teams (
    year INTEGER NOT NULL,
        -- <example>1937</example>
    lgID TEXT NULL,
        -- <values>{'ABA', 'ABL1', 'NBA', 'NBL', 'NPBL', 'PBLA'}</values>
    tmID TEXT NOT NULL,
        -- <example>'AFS'</example>
    franchID TEXT NULL,
        -- <example>'AFS'</example>
    confID TEXT NULL,
        -- <values>{'EC', 'WC'}</values>
    divID TEXT NULL,
        -- <values>{'AT', 'CD', 'EA', 'ED', 'MW', 'NO', 'NW', 'PC', 'SE', 'SO', 'SW', 'WD', 'WE'}</values>
    rank INTEGER NULL,
        -- <example>1</example>
    confRank INTEGER NULL,
        -- <example>0</example>
    playoff TEXT NULL,
        -- <values>{'AC', 'C1', 'CF', 'CS', 'D1', 'DF', 'DR', 'DS', 'DT', 'F', 'LC', 'NC', 'R1', 'SF', 'WC'}</values>
    name TEXT NULL,
        -- <example>'Akron Firestone Non-Skids'</example>
    o_fgm INTEGER NULL,
        -- <example>249</example>
    o_ftm INTEGER NULL,
        -- <example>183</example>
    o_pts INTEGER NULL,
        -- <example>681</example>
    d_pts INTEGER NULL,
        -- <example>578</example>
    homeWon INTEGER NULL,
        -- <example>8</example>
    homeLost INTEGER NULL,
        -- <example>1</example>
    awayWon INTEGER NULL,
        -- <example>5</example>
    awayLost INTEGER NULL,
        -- <example>3</example>
    won INTEGER NULL,
        -- <example>14</example>
    lost INTEGER NULL,
        -- <example>4</example>
    games INTEGER NULL,
        -- <example>18</example>
    arena TEXT NULL,
        -- <example>'Boston Garden'</example>
    PRIMARY KEY (year, tmID)
);
```