```sql
-- Database: hockey

-- Table: AwardsCoaches (77 rows)
CREATE TABLE AwardsCoaches (
    coachID TEXT,  -- e.g. 'patrile01c'; FK -> Coaches.coachID
    award TEXT,  -- values: {'Baldwin', 'First Team All-Star', 'Jack Adams', 'Schmertz', 'Second Team All-Star'}
    year INTEGER,  -- e.g. 1930
    lgID TEXT,  -- values: {'NHL', 'WHA'}
    note TEXT,
    FOREIGN KEY (coachID) REFERENCES Coaches(coachID)
);

-- Table: AwardsMisc (124 rows)
CREATE TABLE AwardsMisc (
    name TEXT NOT NULL PRIMARY KEY,  -- e.g. '1960 U.S. Olympic Hockey Team'
    ID TEXT,  -- e.g. 'arboual01'
    award TEXT,  -- values: {'Patrick'}
    year INTEGER,  -- e.g. 2001
    lgID TEXT,  -- values: {'NHL'}
    note TEXT  -- values: {'posthumous'}
);

-- Table: AwardsPlayers (2091 rows)
CREATE TABLE AwardsPlayers (
    playerID TEXT NOT NULL,  -- e.g. 'abelsi01'; FK -> Master.playerID
    award TEXT NOT NULL,  -- e.g. 'First Team All-Star'
    year INTEGER NOT NULL,  -- e.g. 1948
    lgID TEXT,  -- values: {'NHL', 'WHA'}
    note TEXT,  -- values: {'Best Defenceman', 'Best Goaltender', 'MVP', 'Most Gentlemanly', 'Rookie', 'Scoring', 'shared', 'tie'}
    pos TEXT,  -- values: {'C', 'D', 'F', 'G', 'LW', 'RW', 'W'}
    PRIMARY KEY (playerID, award, year),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: Coaches (1812 rows)
CREATE TABLE Coaches (
    coachID TEXT NOT NULL,  -- e.g. 'abelsi01c'
    year INTEGER NOT NULL,  -- e.g. 1952; FK (composite)
    tmID TEXT NOT NULL,  -- e.g. 'CHI'; FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}
    stint INTEGER NOT NULL,  -- e.g. 1
    notes TEXT,  -- values: {'co-coach with Barry Smith', 'co-coach with Dave Lewis', 'interim'}
    g INTEGER,  -- e.g. 70
    w INTEGER,  -- e.g. 27
    l INTEGER,  -- e.g. 28
    t INTEGER,  -- e.g. 15
    postg TEXT,  -- e.g. '7'
    postw TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '14', '15', '16', '2', '3', '4', '5', '6', '7', '8', '9'}
    postl TEXT,  -- values: {'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}
    postt TEXT,  -- values: {'0', '1', '2', '3', '4'}
    PRIMARY KEY (coachID, year, tmID, stint),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID)
);

-- Table: CombinedShutouts (54 rows)
CREATE TABLE CombinedShutouts (
    year INTEGER,  -- e.g. 1929
    month INTEGER,  -- e.g. 3
    date INTEGER,  -- e.g. 14
    tmID TEXT,  -- e.g. 'TOR'
    oppID TEXT,  -- e.g. 'NYA'
    "R/P" TEXT,  -- values: {'P', 'R'}
    IDgoalie1 TEXT,  -- e.g. 'chabolo01'; FK -> Master.playerID
    IDgoalie2 TEXT,  -- e.g. 'grantbe01'; FK -> Master.playerID
    FOREIGN KEY (IDgoalie1) REFERENCES Master(playerID),
    FOREIGN KEY (IDgoalie2) REFERENCES Master(playerID)
);

-- Table: Goalies (4278 rows)
CREATE TABLE Goalies (
    playerID TEXT NOT NULL,  -- e.g. 'abbotge01'; FK -> Master.playerID
    year INTEGER NOT NULL,  -- e.g. 1943; FK (composite)
    stint INTEGER NOT NULL,  -- e.g. 1
    tmID TEXT,  -- e.g. 'BOS'; FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}
    GP TEXT,  -- e.g. '1'
    Min TEXT,  -- e.g. '60'
    W TEXT,  -- e.g. '0'
    L TEXT,  -- e.g. '1'
    "T/OL" TEXT,  -- e.g. '0'
    ENG TEXT,  -- values: {'0', '1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}
    SHO TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '14', '15', '2', '22', '3', '4', '5', '6', '7', '8', '9'}
    GA TEXT,  -- e.g. '7'
    SA TEXT,  -- e.g. '504'
    PostGP TEXT,  -- e.g. '1'
    PostMin TEXT,  -- e.g. '1'
    PostW TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '14', '15', '16', '2', '3', '4', '5', '6', '7', '8', '9'}
    PostL TEXT,  -- values: {'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}
    PostT TEXT,  -- values: {'0', '1', '2', '3', '4'}
    PostENG TEXT,  -- values: {'0', '1', '2', '3', '4', '5'}
    PostSHO TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6', '7'}
    PostGA TEXT,  -- e.g. '0'
    PostSA TEXT,  -- e.g. '51'
    PRIMARY KEY (playerID, year, stint),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: GoaliesSC (31 rows)
CREATE TABLE GoaliesSC (
    playerID TEXT NOT NULL,  -- e.g. 'benedcl01'; FK -> Master.playerID
    year INTEGER NOT NULL,  -- e.g. 1914; FK (composite)
    tmID TEXT,  -- e.g. 'OT1'; FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL'}
    GP INTEGER,  -- e.g. 3
    Min INTEGER,  -- e.g. 180
    W INTEGER,  -- e.g. 0
    L INTEGER,  -- e.g. 3
    T INTEGER,  -- e.g. 0
    SHO INTEGER,  -- e.g. 0
    GA INTEGER,  -- e.g. 26
    PRIMARY KEY (playerID, year),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: GoaliesShootout (480 rows)
CREATE TABLE GoaliesShootout (
    playerID TEXT,  -- e.g. 'aebisda01'; FK -> Master.playerID
    year INTEGER,  -- e.g. 2005; FK (composite)
    stint INTEGER,  -- e.g. 1
    tmID TEXT,  -- e.g. 'COL'; FK (composite)
    W INTEGER,  -- e.g. 2
    L INTEGER,  -- e.g. 1
    SA INTEGER,  -- e.g. 10
    GA INTEGER,  -- e.g. 2
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: HOF (365 rows)
CREATE TABLE HOF (
    year INTEGER,  -- e.g. 1969
    hofID TEXT NOT NULL PRIMARY KEY,  -- e.g. 'abelsi01h'
    name TEXT,  -- e.g. 'Sid Abel'
    category TEXT  -- values: {'Builder', 'Player', 'Referee/Linesman'}
);

-- Table: Master (7761 rows)
CREATE TABLE Master (
    playerID TEXT,  -- e.g. 'aaltoan01'
    coachID TEXT,  -- e.g. 'abelsi01c'; FK -> Coaches.coachID
    hofID TEXT,  -- e.g. 'abelsi01h'
    firstName TEXT,  -- e.g. 'Antti'
    lastName TEXT NOT NULL,  -- e.g. 'Aalto'
    nameNote TEXT,  -- values: {'also known as Bellehumeur', 'also known as Block', 'also known as Bowcher', 'also known as Bremberg', 'also known as Burmeister', 'also known as Coleman', 'also known as Couture', 'also known as Desrivieres', 'also known as Kahibaitche', 'also known as Kessler', 'also known as Landiak', 'also known as Linton Muldoon Tracey', 'also known as Mike Jefferson', 'also known as Wochy', 'also listed as Bourdginon', 'born Bodnarchuk', 'born Guoth', 'born Tselios'}
    nameGiven TEXT,  -- e.g. 'Antti'
    nameNick TEXT,  -- e.g. 'Preacher'
    height TEXT,  -- values: {'63', '64', '65', '66', '67', '68', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79', '80', '81'}
    weight TEXT,  -- e.g. '210'
    shootCatch TEXT,  -- values: {'B', 'L', 'R'}
    legendsID TEXT,  -- e.g. '14862'
    ihdbID TEXT,  -- e.g. '5928'
    hrefID TEXT,  -- e.g. 'aaltoan01'
    firstNHL TEXT,  -- e.g. '1997'
    lastNHL TEXT,  -- e.g. '2000'
    firstWHA TEXT,  -- values: {'1972', '1973', '1974', '1975', '1976', '1977', '1978'}
    lastWHA TEXT,  -- values: {'1972', '1973', '1974', '1975', '1976', '1977', '1978'}
    pos TEXT,  -- values: {'C', 'C/D', 'C/L', 'C/R', 'D', 'D/C', 'D/L', 'D/R', 'F', 'G', 'L', 'L/C', 'L/D', 'R', 'R/C', 'R/D', 'R/L', 'W'}
    birthYear TEXT,  -- e.g. '1975'
    birthMon TEXT,  -- values: {'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}
    birthDay TEXT,  -- e.g. '4'
    birthCountry TEXT,  -- e.g. 'Finland'
    birthState TEXT,  -- e.g. 'ON'
    birthCity TEXT,  -- e.g. 'Lappeenranta'
    deathYear TEXT,  -- e.g. '1964'
    deathMon TEXT,  -- values: {'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}
    deathDay TEXT,  -- e.g. '1'
    deathCountry TEXT,  -- values: {'Belarus', 'Belgium', 'Canada', 'Czech Republic', 'France', 'Germany', 'Holland', 'Italy', 'Norway', 'Russia', 'Sweden', 'Switzerland', 'Turkey', 'USA'}
    deathState TEXT,  -- e.g. 'MI'
    deathCity TEXT,  -- e.g. 'Sault Ste. Marie'
    FOREIGN KEY (coachID) REFERENCES Coaches(coachID)
);

-- Table: Scoring (45967 rows)
CREATE TABLE Scoring (
    playerID TEXT,  -- e.g. 'aaltoan01'; FK -> Master.playerID
    year INTEGER,  -- e.g. 1997; FK (composite)
    stint INTEGER,  -- e.g. 1
    tmID TEXT,  -- e.g. 'ANA'; FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}
    pos TEXT,  -- e.g. 'C'
    GP INTEGER,  -- e.g. 3
    G INTEGER,  -- e.g. 0
    A INTEGER,  -- e.g. 0
    Pts INTEGER,  -- e.g. 0
    PIM INTEGER,  -- e.g. 0
    "+/-" TEXT,  -- e.g. '-1'
    PPG TEXT,  -- e.g. '0'
    PPA TEXT,  -- e.g. '0'
    SHG TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}
    SHA TEXT,  -- values: {'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}
    GWG TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '14', '16', '2', '3', '4', '5', '6', '7', '8', '9'}
    GTG TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6', '7'}
    SOG TEXT,  -- e.g. '1'
    PostGP TEXT,  -- e.g. '4'
    PostG TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '2', '3', '4', '5', '6', '7', '8', '9'}
    PostA TEXT,  -- e.g. '0'
    PostPts TEXT,  -- e.g. '0'
    PostPIM TEXT,  -- e.g. '2'
    "Post+/-" TEXT,  -- e.g. '0'
    PostPPG TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9'}
    PostPPA TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '14', '18', '19', '2', '3', '4', '5', '6', '7', '8', '9'}
    PostSHG TEXT,  -- values: {'0', '1', '2', '3'}
    PostSHA TEXT,  -- values: {'0', '1', '2', '3', '4'}
    PostGWG TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6', '7'}
    PostSOG TEXT,  -- e.g. '0'
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: ScoringSC (284 rows)
CREATE TABLE ScoringSC (
    playerID TEXT,  -- e.g. 'adamsbi01'; FK -> Master.playerID
    year INTEGER,  -- e.g. 1920; FK (composite)
    tmID TEXT,  -- e.g. 'VML'; FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL'}
    pos TEXT,  -- e.g. 'R'
    GP INTEGER,  -- e.g. 4
    G INTEGER,  -- e.g. 0
    A INTEGER,  -- e.g. 0
    Pts INTEGER,  -- e.g. 0
    PIM INTEGER,  -- e.g. 0
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: ScoringShootout (2072 rows)
CREATE TABLE ScoringShootout (
    playerID TEXT,  -- e.g. 'adamske01'; FK -> Master.playerID
    year INTEGER,  -- e.g. 2006; FK (composite)
    stint INTEGER,  -- e.g. 1
    tmID TEXT,  -- e.g. 'PHO'; FK (composite)
    S INTEGER,  -- e.g. 1
    G INTEGER,  -- e.g. 0
    GDG INTEGER,  -- e.g. 0
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: ScoringSup (137 rows)
CREATE TABLE ScoringSup (
    playerID TEXT,  -- e.g. 'actonke01'; FK -> Master.playerID
    year INTEGER,  -- e.g. 1988
    PPA TEXT,  -- e.g. '1'
    SHA TEXT,  -- values: {'1', '2', '3', '4'}
    FOREIGN KEY (playerID) REFERENCES Master(playerID)
);

-- Table: SeriesPost (832 rows)
CREATE TABLE SeriesPost (
    year INTEGER,  -- e.g. 1912; FK (composite); FK (composite)
    round TEXT,  -- e.g. 'SCF'
    series TEXT,  -- e.g. 'A'
    tmIDWinner TEXT,  -- e.g. 'VA1'; FK (composite)
    lgIDWinner TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}
    tmIDLoser TEXT,  -- e.g. 'QU1'; FK (composite)
    lgIDLoser TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}
    W INTEGER,  -- e.g. 2
    L INTEGER,  -- e.g. 1
    T INTEGER,  -- e.g. 0
    GoalsWinner INTEGER,  -- e.g. 16
    GoalsLoser INTEGER,  -- e.g. 12
    note TEXT,  -- values: {'DEF', 'EX', 'ND', 'TG'}
    FOREIGN KEY (year, tmIDWinner) REFERENCES Teams(year, tmID),
    FOREIGN KEY (year, tmIDLoser) REFERENCES Teams(year, tmID)
);

-- Table: TeamSplits (1519 rows)
CREATE TABLE TeamSplits (
    year INTEGER NOT NULL,  -- e.g. 1909; FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}
    tmID TEXT NOT NULL,  -- e.g. 'COB'; FK (composite)
    hW INTEGER,  -- e.g. 2
    hL INTEGER,  -- e.g. 4
    hT INTEGER,  -- e.g. 0
    hOTL TEXT,  -- values: {'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}
    rW INTEGER,  -- e.g. 2
    rL INTEGER,  -- e.g. 4
    rT INTEGER,  -- e.g. 0
    rOTL TEXT,  -- values: {'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}
    SepW TEXT,  -- values: {'1'}
    SepL TEXT,  -- values: {'1'}
    SepT TEXT,
    SepOL TEXT,  -- values: {'0'}
    OctW TEXT,  -- values: {'0', '1', '10', '11', '2', '3', '4', '5', '6', '7', '8', '9'}
    OctL TEXT,  -- values: {'0', '1', '10', '11', '13', '2', '3', '4', '5', '6', '7', '8', '9'}
    OctT TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6'}
    OctOL TEXT,  -- values: {'0', '1', '2', '3', '4', '5'}
    NovW TEXT,  -- values: {'0', '1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}
    NovL TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}
    NovT TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6', '7', '8'}
    NovOL TEXT,  -- values: {'0', '1', '2', '3', '4'}
    DecW TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}
    DecL TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}
    DecT TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6', '7'}
    DecOL TEXT,  -- values: {'0', '1', '2', '3', '4', '5'}
    JanW INTEGER,  -- e.g. 1
    JanL INTEGER,  -- e.g. 1
    JanT INTEGER,  -- e.g. 0
    JanOL TEXT,  -- values: {'0', '1', '2', '3', '4', '5'}
    FebW INTEGER,  -- e.g. 2
    FebL INTEGER,  -- e.g. 3
    FebT INTEGER,  -- e.g. 0
    FebOL TEXT,  -- values: {'0', '1', '2', '3', '4', '5'}
    MarW TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '2', '3', '4', '5', '6', '7', '8', '9'}
    MarL TEXT,  -- values: {'0', '1', '10', '11', '12', '13', '15', '2', '3', '4', '5', '6', '7', '8', '9'}
    MarT TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6', '7'}
    MarOL TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6'}
    AprW TEXT,  -- values: {'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}
    AprL TEXT,  -- values: {'0', '1', '10', '2', '3', '4', '5', '6', '7', '8', '9'}
    AprT TEXT,  -- values: {'0', '1', '2', '3', '4', '5'}
    AprOL TEXT,  -- values: {'0', '1', '2', '3'}
    PRIMARY KEY (year, tmID),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID)
);

-- Table: TeamVsTeam (25602 rows)
CREATE TABLE TeamVsTeam (
    year INTEGER NOT NULL,  -- e.g. 1909; FK (composite); FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}
    tmID TEXT NOT NULL,  -- e.g. 'COB'; FK (composite)
    oppID TEXT NOT NULL,  -- e.g. 'HAI'; FK (composite)
    W INTEGER,  -- e.g. 1
    L INTEGER,  -- e.g. 1
    T INTEGER,  -- e.g. 0
    OTL TEXT,  -- values: {'0', '1', '2', '3', '4'}
    PRIMARY KEY (year, tmID, oppID),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID),
    FOREIGN KEY (oppID, year) REFERENCES Teams(tmID, year)
);

-- Table: Teams (1519 rows)
CREATE TABLE Teams (
    year INTEGER NOT NULL,  -- e.g. 1909
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}
    tmID TEXT NOT NULL,  -- e.g. 'COB'
    franchID TEXT,  -- e.g. 'BKN'
    confID TEXT,  -- values: {'CC', 'EC', 'WA', 'WC'}
    divID TEXT,  -- e.g. 'AM'
    rank INTEGER,  -- e.g. 4
    playoff TEXT,  -- e.g. 'LCS'
    G INTEGER,  -- e.g. 12
    W INTEGER,  -- e.g. 4
    L INTEGER,  -- e.g. 8
    T INTEGER,  -- e.g. 0
    OTL TEXT,  -- e.g. '3'
    Pts INTEGER,  -- e.g. 8
    SoW TEXT,  -- values: {'0', '1', '10', '11', '12', '14', '15', '2', '3', '4', '5', '6', '7', '8', '9'}
    SoL TEXT,  -- values: {'1', '10', '11', '12', '2', '3', '4', '5', '6', '7', '8', '9'}
    GF INTEGER,  -- e.g. 79
    GA INTEGER,  -- e.g. 104
    name TEXT,  -- e.g. 'Cobalt Silver Kings'
    PIM TEXT,  -- e.g. '336'
    BenchMinor TEXT,  -- e.g. '12'
    PPG TEXT,  -- e.g. '28'
    PPC TEXT,  -- e.g. '220'
    SHA TEXT,  -- e.g. '4'
    PKG TEXT,  -- e.g. '45'
    PKC TEXT,  -- e.g. '242'
    SHF TEXT,  -- e.g. '3'
    PRIMARY KEY (year, tmID)
);

-- Table: TeamsHalf (41 rows)
CREATE TABLE TeamsHalf (
    year INTEGER NOT NULL,  -- e.g. 1916; FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL'}
    tmID TEXT NOT NULL,  -- e.g. 'MOC'; FK (composite)
    half INTEGER NOT NULL,  -- e.g. 1
    rank INTEGER,  -- e.g. 1
    G INTEGER,  -- e.g. 10
    W INTEGER,  -- e.g. 7
    L INTEGER,  -- e.g. 3
    T INTEGER,  -- e.g. 0
    GF INTEGER,  -- e.g. 58
    GA INTEGER,  -- e.g. 38
    PRIMARY KEY (year, tmID, half),
    FOREIGN KEY (tmID, year) REFERENCES Teams(tmID, year)
);

-- Table: TeamsPost (927 rows)
CREATE TABLE TeamsPost (
    year INTEGER NOT NULL,  -- e.g. 1913; FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL', 'WHA'}
    tmID TEXT NOT NULL,  -- e.g. 'MOC'; FK (composite)
    G INTEGER,  -- e.g. 2
    W INTEGER,  -- e.g. 1
    L INTEGER,  -- e.g. 1
    T INTEGER,  -- e.g. 0
    GF INTEGER,  -- e.g. 2
    GA INTEGER,  -- e.g. 6
    PIM TEXT,  -- e.g. '59'
    BenchMinor TEXT,  -- values: {'0', '10', '12', '14', '2', '4', '6', '8'}
    PPG TEXT,  -- e.g. '1'
    PPC TEXT,  -- e.g. '39'
    SHA TEXT,  -- values: {'0', '1', '2', '3', '4', '5', '6', '7', '8'}
    PKG TEXT,  -- e.g. '3'
    PKC TEXT,  -- e.g. '55'
    SHF TEXT,  -- e.g. '0'
    PRIMARY KEY (year, tmID),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID)
);

-- Table: TeamsSC (30 rows)
CREATE TABLE TeamsSC (
    year INTEGER NOT NULL,  -- e.g. 1912; FK (composite)
    lgID TEXT,  -- values: {'NHA', 'NHL', 'PCHA', 'WCHL'}
    tmID TEXT NOT NULL,  -- e.g. 'QU1'; FK (composite)
    G INTEGER,  -- e.g. 3
    W INTEGER,  -- e.g. 1
    L INTEGER,  -- e.g. 2
    T INTEGER,  -- e.g. 0
    GF INTEGER,  -- e.g. 12
    GA INTEGER,  -- e.g. 16
    PIM TEXT,  -- values: {'18', '20', '24', '49', '50', '53', '75'}
    PRIMARY KEY (year, tmID),
    FOREIGN KEY (year, tmID) REFERENCES Teams(year, tmID)
);

-- Table: abbrev (58 rows)
CREATE TABLE abbrev (
    Type TEXT NOT NULL,  -- values: {'Conference', 'Division', 'Playoffs', 'Round'}
    Code TEXT NOT NULL,  -- e.g. 'CC'
    Fullname TEXT,  -- e.g. 'Campbell Conference'
    PRIMARY KEY (Type, Code)
);
```