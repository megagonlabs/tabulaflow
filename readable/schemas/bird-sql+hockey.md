```sql
-- Database: hockey

-- Table: AwardsCoaches (77 rows)
CREATE TABLE AwardsCoaches (
    coachID TEXT NULL,
        -- <example>'patrile01c'</example>
        -- <fk> -> Coaches.coachID</fk>
    award TEXT NULL,
        -- <values>{'Baldwin', 'First Team All-Star', 'Jack Adams', 'Schmertz', 'Second Team All-Star'}</values>
    year INTEGER NULL,
        -- <example>1930</example>
    lgID TEXT NULL,
        -- <values>{'NHL', 'WHA'}</values>
    note TEXT NULL,
    FOREIGN KEY (coachID) REFERENCES Coaches(coachID)
);

-- Table: AwardsMisc (124 rows)
CREATE TABLE AwardsMisc (
    name TEXT NOT NULL PRIMARY KEY,
        -- <example>'1960 U.S. Olympic Hockey Team'</example>
    ID TEXT NULL,
        -- <example>'arboual01'</example>
    award TEXT NULL,
        -- <values>{'Patrick'}</values>
    year INTEGER NULL,
        -- <example>2001</example>
    lgID TEXT NULL,
        -- <values>{'NHL'}</values>
    note TEXT NULL
        -- <values>{'posthumous'}</values>
);

-- Table: AwardsPlayers (2091 rows)
CREATE TABLE AwardsPlayers (
    playerID TEXT NOT NULL,
        -- <example>'abelsi01'</example>
        -- <fk> -> Master.playerID</fk>
    award TEXT NOT NULL,
        -- <example>'First Team All-Star'</example>
    year INTEGER NOT NULL,
        -- <example>1948</example>
    lgID TEXT NULL,
        -- <values>{'NHL', 'WHA'}</values>
    note TEXT NULL,
        -- <values>{'Best Defenceman', 'Best Goaltender', 'MVP', 'Most Gentlemanly', 'Rookie', 'Scoring', 'shared', 'tie'}</values>
    pos TEXT NULL,
        -- <values>{'C', 'D', 'F', 'G', 'LW', 'RW', 'W'}</values>
    PRIMARY KEY (playerID, award, year),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: Coaches (1812 rows)
CREATE TABLE Coaches (
    coachID TEXT NOT NULL,
        -- <example>'abelsi01c'</example>
    year INTEGER NOT NULL,
        -- <example>1952</example>
        -- <fk>composite</fk>
    tmID TEXT NOT NULL,
        -- <example>'CHI'</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    stint INTEGER NOT NULL,
        -- <example>1</example>
    notes TEXT NULL,
        -- <values>{'co-coach with Barry Smith', 'co-coach with Dave Lewis', 'interim'}</values>
    g INTEGER NULL,
        -- <example>70</example>
    w INTEGER NULL,
        -- <example>27</example>
    l INTEGER NULL,
        -- <example>28</example>
    t INTEGER NULL,
        -- <example>15</example>
    postg TEXT NULL,
        -- <example>'7'</example>
    postw TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '15', '16', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    postl TEXT NULL,
        -- <values>{'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    postt TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    PRIMARY KEY (coachID, year, tmID, stint),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID)
);

-- Table: CombinedShutouts (54 rows)
CREATE TABLE CombinedShutouts (
    year INTEGER NULL,
        -- <example>1929</example>
    month INTEGER NULL,
        -- <example>3</example>
    date INTEGER NULL,
        -- <example>14</example>
    tmID TEXT NULL,
        -- <example>'TOR'</example>
    oppID TEXT NULL,
        -- <example>'NYA'</example>
    "R/P" TEXT NULL,
        -- <values>{'P', 'R'}</values>
    IDgoalie1 TEXT NULL,
        -- <example>'chabolo01'</example>
        -- <fk> -> Master.playerID</fk>
    IDgoalie2 TEXT NULL,
        -- <example>'grantbe01'</example>
        -- <fk> -> Master.playerID</fk>
    FOREIGN KEY (IDgoalie1) REFERENCES Master(playerID),
    FOREIGN KEY (IDgoalie2) REFERENCES Master(playerID)
);

-- Table: Goalies (4278 rows)
CREATE TABLE Goalies (
    playerID TEXT NOT NULL,
        -- <example>'abbotge01'</example>
        -- <fk> -> Master.playerID</fk>
    year INTEGER NOT NULL,
        -- <example>1943</example>
        -- <fk>composite</fk>
    stint INTEGER NOT NULL,
        -- <example>1</example>
    tmID TEXT NULL,
        -- <example>'BOS'</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    GP TEXT NULL,
        -- <example>'1'</example>
    Min TEXT NULL,
        -- <example>'60'</example>
    W TEXT NULL,
        -- <example>'0'</example>
    L TEXT NULL,
        -- <example>'1'</example>
    "T/OL" TEXT NULL,
        -- <example>'0'</example>
    ENG TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    SHO TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '15', '2', '22', '3', '4', '5', '6', '7', '8', '9'}</values>
    GA TEXT NULL,
        -- <example>'7'</example>
    SA TEXT NULL,
        -- <example>'504'</example>
    PostGP TEXT NULL,
        -- <example>'1'</example>
    PostMin TEXT NULL,
        -- <example>'1'</example>
    PostW TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '15', '16', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    PostL TEXT NULL,
        -- <values>{'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    PostT TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    PostENG TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    PostSHO TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    PostGA TEXT NULL,
        -- <example>'0'</example>
    PostSA TEXT NULL,
        -- <example>'51'</example>
    PRIMARY KEY (playerID, year, stint),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: GoaliesSC (31 rows)
CREATE TABLE GoaliesSC (
    playerID TEXT NOT NULL,
        -- <example>'benedcl01'</example>
        -- <fk> -> Master.playerID</fk>
    year INTEGER NOT NULL,
        -- <example>1914</example>
        -- <fk>composite</fk>
    tmID TEXT NULL,
        -- <example>'OT1'</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL'}</values>
    GP INTEGER NULL,
        -- <example>3</example>
    Min INTEGER NULL,
        -- <example>180</example>
    W INTEGER NULL,
        -- <example>0</example>
    L INTEGER NULL,
        -- <example>3</example>
    T INTEGER NULL,
        -- <example>0</example>
    SHO INTEGER NULL,
        -- <example>0</example>
    GA INTEGER NULL,
        -- <example>26</example>
    PRIMARY KEY (playerID, year),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: GoaliesShootout (480 rows)
CREATE TABLE GoaliesShootout (
    playerID TEXT NULL,
        -- <example>'aebisda01'</example>
        -- <fk> -> Master.playerID</fk>
    year INTEGER NULL,
        -- <example>2005</example>
        -- <fk>composite</fk>
    stint INTEGER NULL,
        -- <example>1</example>
    tmID TEXT NULL,
        -- <example>'COL'</example>
        -- <fk>composite</fk>
    W INTEGER NULL,
        -- <example>2</example>
    L INTEGER NULL,
        -- <example>1</example>
    SA INTEGER NULL,
        -- <example>10</example>
    GA INTEGER NULL,
        -- <example>2</example>
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: HOF (365 rows)
CREATE TABLE HOF (
    year INTEGER NULL,
        -- <example>1969</example>
    hofID TEXT NOT NULL PRIMARY KEY,
        -- <example>'abelsi01h'</example>
    name TEXT NULL,
        -- <example>'Sid Abel'</example>
    category TEXT NULL
        -- <values>{'Builder', 'Player', 'Referee/Linesman'}</values>
);

-- Table: Master (7761 rows)
CREATE TABLE Master (
    playerID TEXT NULL,
        -- <example>'aaltoan01'</example>
    coachID TEXT NULL,
        -- <example>'abelsi01c'</example>
        -- <fk> -> Coaches.coachID</fk>
    hofID TEXT NULL,
        -- <example>'abelsi01h'</example>
    firstName TEXT NULL,
        -- <example>'Antti'</example>
    lastName TEXT NOT NULL,
        -- <example>'Aalto'</example>
    nameNote TEXT NULL,
        -- <values>{'also known as Bellehumeur', 'also known as Block', 'also known as Bowcher', 'also known as Bremberg', 'also known as Burmeister', 'also known as Coleman', 'also known as Couture', 'also known as Desrivieres', 'also known as Kahibaitche', 'also known as Kessler', 'also known as Landiak', 'also known as Linton Muldoon Tracey', 'also known as Mike Jefferson', 'also known as Wochy', 'also listed as Bourdginon', 'born Bodnarchuk', 'born Guoth', 'born Tselios'}</values>
    nameGiven TEXT NULL,
        -- <example>'Antti'</example>
    nameNick TEXT NULL,
        -- <example>'Preacher'</example>
    height TEXT NULL,
        -- <values>{'63', '64', '65', '66', '67', '68', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '80', '81'}</values>
    weight TEXT NULL,
        -- <example>'210'</example>
    shootCatch TEXT NULL,
        -- <values>{'B', 'L', 'R'}</values>
    legendsID TEXT NULL,
        -- <example>'14862'</example>
    ihdbID TEXT NULL,
        -- <example>'5928'</example>
    hrefID TEXT NULL,
        -- <example>'aaltoan01'</example>
    firstNHL TEXT NULL,
        -- <example>'1997'</example>
    lastNHL TEXT NULL,
        -- <example>'2000'</example>
    firstWHA TEXT NULL,
        -- <values>{'1972', '1973', '1974', '1975', '1976', '1977', '1978'}</values>
    lastWHA TEXT NULL,
        -- <values>{'1972', '1973', '1974', '1975', '1976', '1977', '1978'}</values>
    pos TEXT NULL,
        -- <values>{'C', 'C/D', 'C/L', 'C/R', 'D', 'D/C', 'D/L', 'D/R', 'F', 'G', 'L', 'L/C', 'L/D', 'R', 'R/C', 'R/D', 'R/L', 'W'}</values>
    birthYear TEXT NULL,
        -- <example>'1975'</example>
    birthMon TEXT NULL,
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    birthDay TEXT NULL,
        -- <example>'4'</example>
    birthCountry TEXT NULL,
        -- <example>'Finland'</example>
    birthState TEXT NULL,
        -- <example>'ON'</example>
    birthCity TEXT NULL,
        -- <example>'Lappeenranta'</example>
    deathYear TEXT NULL,
        -- <example>'1964'</example>
    deathMon TEXT NULL,
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    deathDay TEXT NULL,
        -- <example>'1'</example>
    deathCountry TEXT NULL,
        -- <values>{'Belarus', 'Belgium', 'Canada', 'Czech Republic', 'France', 'Germany', 'Holland', 'Italy', 'Norway', 'Russia', 'Sweden', 'Switzerland', 'Turkey', 'USA'}</values>
    deathState TEXT NULL,
        -- <example>'MI'</example>
    deathCity TEXT NULL,
        -- <example>'Sault Ste. Marie'</example>
    FOREIGN KEY (coachID) REFERENCES Coaches(coachID)
);

-- Table: Scoring (45967 rows)
CREATE TABLE Scoring (
    playerID TEXT NULL,
        -- <example>'aaltoan01'</example>
        -- <fk> -> Master.playerID</fk>
    year INTEGER NULL,
        -- <example>1997</example>
        -- <fk>composite</fk>
    stint INTEGER NULL,
        -- <example>1</example>
    tmID TEXT NULL,
        -- <example>'ANA'</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    pos TEXT NULL,
        -- <example>'C'</example>
    GP INTEGER NULL,
        -- <example>3</example>
    G INTEGER NULL,
        -- <example>0</example>
    A INTEGER NULL,
        -- <example>0</example>
    Pts INTEGER NULL,
        -- <example>0</example>
    PIM INTEGER NULL,
        -- <example>0</example>
    "+/-" TEXT NULL,
        -- <example>'-1'</example>
    PPG TEXT NULL,
        -- <example>'0'</example>
    PPA TEXT NULL,
        -- <example>'0'</example>
    SHG TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    SHA TEXT NULL,
        -- <values>{'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    GWG TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '16', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    GTG TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    SOG TEXT NULL,
        -- <example>'1'</example>
    PostGP TEXT NULL,
        -- <example>'4'</example>
    PostG TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    PostA TEXT NULL,
        -- <example>'0'</example>
    PostPts TEXT NULL,
        -- <example>'0'</example>
    PostPIM TEXT NULL,
        -- <example>'2'</example>
    "Post+/-" TEXT NULL,
        -- <example>'0'</example>
    PostPPG TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    PostPPA TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '14', '18', '19', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    PostSHG TEXT NULL,
        -- <values>{'0', '1', '2', '3'}</values>
    PostSHA TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    PostGWG TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    PostSOG TEXT NULL,
        -- <example>'0'</example>
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: ScoringSC (284 rows)
CREATE TABLE ScoringSC (
    playerID TEXT NULL,
        -- <example>'adamsbi01'</example>
        -- <fk> -> Master.playerID</fk>
    year INTEGER NULL,
        -- <example>1920</example>
        -- <fk>composite</fk>
    tmID TEXT NULL,
        -- <example>'VML'</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL'}</values>
    pos TEXT NULL,
        -- <example>'R'</example>
    GP INTEGER NULL,
        -- <example>4</example>
    G INTEGER NULL,
        -- <example>0</example>
    A INTEGER NULL,
        -- <example>0</example>
    Pts INTEGER NULL,
        -- <example>0</example>
    PIM INTEGER NULL,
        -- <example>0</example>
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: ScoringShootout (2072 rows)
CREATE TABLE ScoringShootout (
    playerID TEXT NULL,
        -- <example>'adamske01'</example>
        -- <fk> -> Master.playerID</fk>
    year INTEGER NULL,
        -- <example>2006</example>
        -- <fk>composite</fk>
    stint INTEGER NULL,
        -- <example>1</example>
    tmID TEXT NULL,
        -- <example>'PHO'</example>
        -- <fk>composite</fk>
    S INTEGER NULL,
        -- <example>1</example>
    G INTEGER NULL,
        -- <example>0</example>
    GDG INTEGER NULL,
        -- <example>0</example>
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: ScoringSup (137 rows)
CREATE TABLE ScoringSup (
    playerID TEXT NULL,
        -- <example>'actonke01'</example>
        -- <fk> -> Master.playerID</fk>
    year INTEGER NULL,
        -- <example>1988</example>
    PPA TEXT NULL,
        -- <example>'1'</example>
    SHA TEXT NULL,
        -- <values>{'1', '2', '3', '4'}</values>
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: SeriesPost (832 rows)
CREATE TABLE SeriesPost (
    year INTEGER NULL,
        -- <example>1912</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    round TEXT NULL,
        -- <example>'SCF'</example>
    series TEXT NULL,
        -- <example>'A'</example>
    tmIDWinner TEXT NULL,
        -- <example>'VA1'</example>
        -- <fk>composite</fk>
    lgIDWinner TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    tmIDLoser TEXT NULL,
        -- <example>'QU1'</example>
        -- <fk>composite</fk>
    lgIDLoser TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    W INTEGER NULL,
        -- <example>2</example>
    L INTEGER NULL,
        -- <example>1</example>
    T INTEGER NULL,
        -- <example>0</example>
    GoalsWinner INTEGER NULL,
        -- <example>16</example>
    GoalsLoser INTEGER NULL,
        -- <example>12</example>
    note TEXT NULL,
        -- <values>{'DEF', 'EX', 'ND', 'TG'}</values>
    FOREIGN KEY (year, tmIDWinner) REFERENCES Teams(year, tmID),
    FOREIGN KEY (year, tmIDLoser) REFERENCES Teams(year, tmID)
);

-- Table: TeamSplits (1519 rows)
CREATE TABLE TeamSplits (
    year INTEGER NOT NULL,
        -- <example>1909</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    tmID TEXT NOT NULL,
        -- <example>'COB'</example>
        -- <fk>composite</fk>
    hW INTEGER NULL,
        -- <example>2</example>
    hL INTEGER NULL,
        -- <example>4</example>
    hT INTEGER NULL,
        -- <example>0</example>
    hOTL TEXT NULL,
        -- <values>{'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    rW INTEGER NULL,
        -- <example>2</example>
    rL INTEGER NULL,
        -- <example>4</example>
    rT INTEGER NULL,
        -- <example>0</example>
    rOTL TEXT NULL,
        -- <values>{'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    SepW TEXT NULL,
        -- <values>{'1'}</values>
    SepL TEXT NULL,
        -- <values>{'1'}</values>
    SepT TEXT NULL,
    SepOL TEXT NULL,
        -- <values>{'0'}</values>
    OctW TEXT NULL,
        -- <values>{'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    OctL TEXT NULL,
        -- <values>{'0', '1', '10', '11', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    OctT TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6'}</values>
    OctOL TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    NovW TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    NovL TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    NovT TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8'}</values>
    NovOL TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    DecW TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    DecL TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    DecT TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    DecOL TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    JanW INTEGER NULL,
        -- <example>1</example>
    JanL INTEGER NULL,
        -- <example>1</example>
    JanT INTEGER NULL,
        -- <example>0</example>
    JanOL TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    FebW INTEGER NULL,
        -- <example>2</example>
    FebL INTEGER NULL,
        -- <example>3</example>
    FebT INTEGER NULL,
        -- <example>0</example>
    FebOL TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    MarW TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    MarL TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '13', '15', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    MarT TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7'}</values>
    MarOL TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6'}</values>
    AprW TEXT NULL,
        -- <values>{'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    AprL TEXT NULL,
        -- <values>{'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    AprT TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5'}</values>
    AprOL TEXT NULL,
        -- <values>{'0', '1', '2', '3'}</values>
    PRIMARY KEY (year, tmID),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID)
);

-- Table: TeamVsTeam (25602 rows)
CREATE TABLE TeamVsTeam (
    year INTEGER NOT NULL,
        -- <example>1909</example>
        -- <fk>composite</fk>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    tmID TEXT NOT NULL,
        -- <example>'COB'</example>
        -- <fk>composite</fk>
    oppID TEXT NOT NULL,
        -- <example>'HAI'</example>
        -- <fk>composite</fk>
    W INTEGER NULL,
        -- <example>1</example>
    L INTEGER NULL,
        -- <example>1</example>
    T INTEGER NULL,
        -- <example>0</example>
    OTL TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4'}</values>
    PRIMARY KEY (year, tmID, oppID),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (oppID, year) REFERENCES Teams(tmID, year)
);

-- Table: Teams (1519 rows)
CREATE TABLE Teams (
    year INTEGER NOT NULL,
        -- <example>1909</example>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    tmID TEXT NOT NULL,
        -- <example>'COB'</example>
    franchID TEXT NULL,
        -- <example>'BKN'</example>
    confID TEXT NULL,
        -- <values>{'CC', 'EC', 'WA', 'WC'}</values>
    divID TEXT NULL,
        -- <example>'AM'</example>
    rank INTEGER NULL,
        -- <example>4</example>
    playoff TEXT NULL,
        -- <example>'LCS'</example>
    G INTEGER NULL,
        -- <example>12</example>
    W INTEGER NULL,
        -- <example>4</example>
    L INTEGER NULL,
        -- <example>8</example>
    T INTEGER NULL,
        -- <example>0</example>
    OTL TEXT NULL,
        -- <example>'3'</example>
    Pts INTEGER NULL,
        -- <example>8</example>
    SoW TEXT NULL,
        -- <values>{'0', '1', '10', '11', '12', '14', '15', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    SoL TEXT NULL,
        -- <values>{'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}</values>
    GF INTEGER NULL,
        -- <example>79</example>
    GA INTEGER NULL,
        -- <example>104</example>
    name TEXT NULL,
        -- <example>'Cobalt Silver Kings'</example>
    PIM TEXT NULL,
        -- <example>'336'</example>
    BenchMinor TEXT NULL,
        -- <example>'12'</example>
    PPG TEXT NULL,
        -- <example>'28'</example>
    PPC TEXT NULL,
        -- <example>'220'</example>
    SHA TEXT NULL,
        -- <example>'4'</example>
    PKG TEXT NULL,
        -- <example>'45'</example>
    PKC TEXT NULL,
        -- <example>'242'</example>
    SHF TEXT NULL,
        -- <example>'3'</example>
    PRIMARY KEY (year, tmID)
);

-- Table: TeamsHalf (41 rows)
CREATE TABLE TeamsHalf (
    year INTEGER NOT NULL,
        -- <example>1916</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL'}</values>
    tmID TEXT NOT NULL,
        -- <example>'MOC'</example>
        -- <fk>composite</fk>
    half INTEGER NOT NULL,
        -- <example>1</example>
    rank INTEGER NULL,
        -- <example>1</example>
    G INTEGER NULL,
        -- <example>10</example>
    W INTEGER NULL,
        -- <example>7</example>
    L INTEGER NULL,
        -- <example>3</example>
    T INTEGER NULL,
        -- <example>0</example>
    GF INTEGER NULL,
        -- <example>58</example>
    GA INTEGER NULL,
        -- <example>38</example>
    PRIMARY KEY (year, tmID, half),
    FOREIGN KEY (tmID, year) REFERENCES Teams(tmID, year)
);

-- Table: TeamsPost (927 rows)
CREATE TABLE TeamsPost (
    year INTEGER NOT NULL,
        -- <example>1913</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}</values>
    tmID TEXT NOT NULL,
        -- <example>'MOC'</example>
        -- <fk>composite</fk>
    G INTEGER NULL,
        -- <example>2</example>
    W INTEGER NULL,
        -- <example>1</example>
    L INTEGER NULL,
        -- <example>1</example>
    T INTEGER NULL,
        -- <example>0</example>
    GF INTEGER NULL,
        -- <example>2</example>
    GA INTEGER NULL,
        -- <example>6</example>
    PIM TEXT NULL,
        -- <example>'59'</example>
    BenchMinor TEXT NULL,
        -- <values>{'0', '10', '12', '14', '2', '4', '6', '8'}</values>
    PPG TEXT NULL,
        -- <example>'1'</example>
    PPC TEXT NULL,
        -- <example>'39'</example>
    SHA TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8'}</values>
    PKG TEXT NULL,
        -- <example>'3'</example>
    PKC TEXT NULL,
        -- <example>'55'</example>
    SHF TEXT NULL,
        -- <example>'0'</example>
    PRIMARY KEY (year, tmID),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID)
);

-- Table: TeamsSC (30 rows)
CREATE TABLE TeamsSC (
    year INTEGER NOT NULL,
        -- <example>1912</example>
        -- <fk>composite</fk>
    lgID TEXT NULL,
        -- <values>{'NHA', 'NHL', 'PCHA', 'WCHL'}</values>
    tmID TEXT NOT NULL,
        -- <example>'QU1'</example>
        -- <fk>composite</fk>
    G INTEGER NULL,
        -- <example>3</example>
    W INTEGER NULL,
        -- <example>1</example>
    L INTEGER NULL,
        -- <example>2</example>
    T INTEGER NULL,
        -- <example>0</example>
    GF INTEGER NULL,
        -- <example>12</example>
    GA INTEGER NULL,
        -- <example>16</example>
    PIM TEXT NULL,
        -- <values>{'18', '20', '24', '49', '50', '53', '75'}</values>
    PRIMARY KEY (year, tmID),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID)
);

-- Table: abbrev (58 rows)
CREATE TABLE abbrev (
    Type TEXT NOT NULL,
        -- <values>{'Conference', 'Division', 'Playoffs', 'Round'}</values>
    Code TEXT NOT NULL,
        -- <example>'CC'</example>
    Fullname TEXT NULL,
        -- <example>'Campbell Conference'</example>
    PRIMARY KEY (Type, Code)
);
```