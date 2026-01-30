```sql
-- Database: professional_basketball

-- Table: awards_coaches (61 rows)
CREATE TABLE awards_coaches (
    id INTEGER PRIMARY KEY,  -- e.g. 1
    year INTEGER,  -- e.g. 1962; FK (composite)
    coachID TEXT,  -- e.g. 'gallaha01'; FK (composite)
    award TEXT,  -- values: {'ABA Coach of the Year', 'NBA Coach of the Year'}
    lgID TEXT,  -- values: {'ABA', 'NBA'}
    note TEXT,  -- values: {'tie'}
    FOREIGN KEY (coachID, year) REFERENCES coaches(coachID, year)
);

-- Table: awards_players (1719 rows)
CREATE TABLE awards_players (
    playerID TEXT NOT NULL,  -- e.g. 'abdulka01'; FK -> players.playerID
    award TEXT NOT NULL,  -- e.g. 'All-Defensive Second Team'
    year INTEGER NOT NULL,  -- e.g. 1969
    lgID TEXT,  -- values: {'ABA', 'ABL1', 'NBA', 'NBL'}
    note TEXT,  -- values: {'tie'}
    pos TEXT,  -- values: {'C', 'F', 'F/C', 'F/G', 'G'}
    PRIMARY KEY (playerID, award, year),
    FOREIGN KEY (playerID) REFERENCES players(playerID)
);

-- Table: coaches (1689 rows)
CREATE TABLE coaches (
    coachID TEXT NOT NULL,  -- e.g. 'adelmri01'
    year INTEGER NOT NULL,  -- e.g. 1988; FK (composite)
    tmID TEXT NOT NULL,  -- e.g. 'POR'; FK (composite)
    lgID TEXT,  -- values: {'ABA', 'ABL1', 'NBA', 'NPBL', 'PBLA'}
    stint INTEGER NOT NULL,  -- e.g. 2
    won INTEGER,  -- e.g. 14
    lost INTEGER,  -- e.g. 21
    post_wins INTEGER,  -- e.g. 0
    post_losses INTEGER,  -- e.g. 3
    PRIMARY KEY (coachID, year, tmID, stint),
    FOREIGN KEY (tmID, year) REFERENCES teams(tmID, year)
);

-- Table: draft (8621 rows)
CREATE TABLE draft (
    id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    draftYear INTEGER,  -- e.g. 1967; FK (composite)
    draftRound INTEGER,  -- e.g. 0
    draftSelection INTEGER,  -- e.g. 0
    draftOverall INTEGER,  -- e.g. 0
    tmID TEXT,  -- e.g. 'ANA'; FK (composite)
    firstName TEXT,  -- e.g. 'Darrell'
    lastName TEXT,  -- e.g. 'Hardy'
    suffixName TEXT,  -- values: {'Jr.'}
    playerID TEXT,  -- e.g. 'hardyda01'
    draftFrom TEXT,  -- e.g. 'Baylor'
    lgID TEXT,  -- values: {'ABA', 'NBA'}
    FOREIGN KEY (tmID, draftYear) REFERENCES teams(tmID, year)
);

-- Table: player_allstar (1608 rows)
CREATE TABLE player_allstar (
    playerID TEXT NOT NULL,  -- e.g. 'abdulka01'; FK -> players.playerID
    last_name TEXT,  -- e.g. 'Abdul-Jabbar'
    first_name TEXT,  -- e.g. 'Kareem'
    season_id INTEGER NOT NULL,  -- e.g. 1969
    conference TEXT,  -- values: {'Allstars', 'Denver', 'East', 'Weset', 'West'}
    league_id TEXT,  -- values: {'ABA', 'NBA'}
    games_played INTEGER,  -- e.g. 1
    minutes INTEGER,  -- e.g. 18
    points INTEGER,  -- e.g. 10
    o_rebounds INTEGER,  -- e.g. 1
    d_rebounds INTEGER,  -- e.g. 2
    rebounds INTEGER,  -- e.g. 11
    assists INTEGER,  -- e.g. 4
    steals INTEGER,  -- e.g. 3
    blocks INTEGER,  -- e.g. 2
    turnovers INTEGER,  -- e.g. 1
    personal_fouls INTEGER,  -- e.g. 3
    fg_attempted INTEGER,  -- e.g. 8
    fg_made INTEGER,  -- e.g. 4
    ft_attempted INTEGER,  -- e.g. 2
    ft_made INTEGER,  -- e.g. 2
    three_attempted INTEGER,  -- e.g. 0
    three_made INTEGER,  -- e.g. 0
    PRIMARY KEY (playerID, season_id),
    FOREIGN KEY (playerID) REFERENCES players(playerID)
);

-- Table: players (5062 rows)
CREATE TABLE players (
    playerID TEXT NOT NULL PRIMARY KEY,  -- e.g. 'abdelal01'
    useFirst TEXT,  -- e.g. 'Alaa'
    firstName TEXT,  -- e.g. 'Alaa'
    middleName TEXT,  -- e.g. 'Shareef'
    lastName TEXT,  -- e.g. 'Abdelnaby'
    nameGiven TEXT,  -- values: {'Dave', 'Ed', 'Jim', 'Mike', 'Mort', 'Robert', 'Thomas', 'Willie', 'nameGiven'}
    fullGivenName TEXT,  -- e.g. 'Ferdinand Lewis Alcindor, Jr.'
    nameSuffix TEXT,  -- values: {'II', 'III', 'IV', 'Jr.', 'Sr.', 'nameSuffix'}
    nameNick TEXT,  -- e.g. 'Lew, Cap'
    pos TEXT,  -- values: {' G', 'C', 'C-F', 'C-F-G', 'C-G', 'F', 'F-C', 'F-C-G', 'F-G', 'F-G-C', 'G', 'G-F', 'G-F-C', 'pos'}
    firstseason INTEGER,  -- e.g. 0
    lastseason INTEGER,  -- e.g. 0
    height REAL,  -- e.g. 82.000
    weight INTEGER,  -- e.g. 240
    college TEXT,  -- e.g. 'Duke'
    collegeOther TEXT,  -- e.g. 'Santa Monica City'
    birthDate DATE,  -- e.g. '1968-06-24'
    birthCity TEXT,  -- e.g. 'Cairo'
    birthState TEXT,  -- e.g. 'NY'
    birthCountry TEXT,  -- e.g. 'EGY'
    highSchool TEXT,  -- e.g. 'Bloomfield Senior'
    hsCity TEXT,  -- e.g. 'Bloomfield'
    hsState TEXT,  -- e.g. 'NJ'
    hsCountry TEXT,  -- e.g. 'USA'
    deathDate DATE,  -- e.g. '0000-00-00'
    race TEXT  -- values: {'1', 'B', 'O', 'W', 'r'}
);

-- Table: players_teams (23751 rows)
CREATE TABLE players_teams (
    id INTEGER PRIMARY KEY,  -- e.g. 1
    playerID TEXT NOT NULL,  -- e.g. 'abdelal01'; FK -> players.playerID
    year INTEGER,  -- e.g. 1990; FK (composite)
    stint INTEGER,  -- e.g. 1
    tmID TEXT,  -- e.g. 'POR'; FK (composite)
    lgID TEXT,  -- values: {'ABA', 'ABL1', 'NBA', 'NBL', 'NPBL', 'PBLA'}
    GP INTEGER,  -- e.g. 43
    GS INTEGER,  -- e.g. 0
    minutes INTEGER,  -- e.g. 290
    points INTEGER,  -- e.g. 135
    oRebounds INTEGER,  -- e.g. 27
    dRebounds INTEGER,  -- e.g. 62
    rebounds INTEGER,  -- e.g. 89
    assists INTEGER,  -- e.g. 12
    steals INTEGER,  -- e.g. 4
    blocks INTEGER,  -- e.g. 12
    turnovers INTEGER,  -- e.g. 22
    PF INTEGER,  -- e.g. 39
    fgAttempted INTEGER,  -- e.g. 116
    fgMade INTEGER,  -- e.g. 55
    ftAttempted INTEGER,  -- e.g. 44
    ftMade INTEGER,  -- e.g. 25
    threeAttempted INTEGER,  -- e.g. 0
    threeMade INTEGER,  -- e.g. 0
    PostGP INTEGER,  -- e.g. 5
    PostGS INTEGER,  -- e.g. 0
    PostMinutes INTEGER,  -- e.g. 13
    PostPoints INTEGER,  -- e.g. 4
    PostoRebounds INTEGER,  -- e.g. 1
    PostdRebounds INTEGER,  -- e.g. 2
    PostRebounds INTEGER,  -- e.g. 3
    PostAssists INTEGER,  -- e.g. 0
    PostSteals INTEGER,  -- e.g. 0
    PostBlocks INTEGER,  -- e.g. 0
    PostTurnovers INTEGER,  -- e.g. 0
    PostPF INTEGER,  -- e.g. 0
    PostfgAttempted INTEGER,  -- e.g. 6
    PostfgMade INTEGER,  -- e.g. 2
    PostftAttempted INTEGER,  -- e.g. 0
    PostftMade INTEGER,  -- e.g. 0
    PostthreeAttempted INTEGER,  -- e.g. 0
    PostthreeMade INTEGER,  -- e.g. 0
    note TEXT,  -- values: {'C'}
    FOREIGN KEY (tmID, year) REFERENCES teams(tmID, year),
    FOREIGN KEY (playerID) REFERENCES players(playerID)
);

-- Table: series_post (775 rows)
CREATE TABLE series_post (
    id INTEGER PRIMARY KEY,  -- e.g. 1
    year INTEGER,  -- e.g. 1946; FK (composite); FK (composite)
    round TEXT,  -- e.g. 'F'
    series TEXT,  -- e.g. 'O'
    tmIDWinner TEXT,  -- e.g. 'PHW'; FK (composite)
    lgIDWinner TEXT,  -- values: {'ABA', 'NBA'}
    tmIDLoser TEXT,  -- e.g. 'CHS'; FK (composite)
    lgIDLoser TEXT,  -- values: {'ABA', 'NBA'}
    W INTEGER,  -- e.g. 4
    L INTEGER,  -- e.g. 1
    FOREIGN KEY (tmIDWinner, year) REFERENCES teams(tmID, year),
    FOREIGN KEY (tmIDLoser, year) REFERENCES teams(tmID, year)
);

-- Table: teams (1536 rows)
CREATE TABLE teams (
    year INTEGER NOT NULL,  -- e.g. 1937
    lgID TEXT,  -- values: {'ABA', 'ABL1', 'NBA', 'NBL', 'NPBL', 'PBLA'}
    tmID TEXT NOT NULL,  -- e.g. 'AFS'
    franchID TEXT,  -- e.g. 'AFS'
    confID TEXT,  -- values: {'EC', 'WC'}
    divID TEXT,  -- values: {'AT', 'CD', 'EA', 'ED', 'MW', 'NO', 'NW', 'PC', 'SE', 'SO', 'SW', 'WD', 'WE'}
    rank INTEGER,  -- e.g. 1
    confRank INTEGER,  -- e.g. 0
    playoff TEXT,  -- values: {'AC', 'C1', 'CF', 'CS', 'D1', 'DF', 'DR', 'DS', 'DT', 'F', 'LC', 'NC', 'R1', 'SF', 'WC'}
    name TEXT,  -- e.g. 'Akron Firestone Non-Skids'
    o_fgm INTEGER,  -- e.g. 249
    o_ftm INTEGER,  -- e.g. 183
    o_pts INTEGER,  -- e.g. 681
    d_pts INTEGER,  -- e.g. 578
    homeWon INTEGER,  -- e.g. 8
    homeLost INTEGER,  -- e.g. 1
    awayWon INTEGER,  -- e.g. 5
    awayLost INTEGER,  -- e.g. 3
    won INTEGER,  -- e.g. 14
    lost INTEGER,  -- e.g. 4
    games INTEGER,  -- e.g. 18
    arena TEXT,  -- e.g. 'Boston Garden'
    PRIMARY KEY (year, tmID)
);
```