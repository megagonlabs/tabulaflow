```sql
-- Database: european_football_2

-- Table: Country (11 rows)
CREATE TABLE Country (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    name TEXT NULL
        -- <example>'Belgium'</example>
);

-- Table: League (11 rows)
CREATE TABLE League (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    country_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> country.id</fk>
    name TEXT NULL,
        -- <example>'Belgium Jupiler League'</example>
    FOREIGN KEY (country_id) REFERENCES country(id)
);

-- Table: Match (25979 rows)
CREATE TABLE Match (
    id INTEGER NULL PRIMARY KEY,
        -- <example>4769</example>
    country_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> Country.id</fk>
    league_id INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> League.id</fk>
    season TEXT NULL,
        -- <values>{'2008/2009', '2009/2010', '2010/2011', '2011/2012', '2012/2013', '2013/2014', '2014/2015', '2015/2016'}</values>
    stage INTEGER NULL,
        -- <example>1</example>
    date TEXT NULL,
        -- <example>'2008-08-17 00:00:00'</example>
    match_api_id INTEGER NULL,
        -- <example>483129</example>
    home_team_api_id INTEGER NULL,
        -- <example>9987</example>
        -- <fk> -> Team.team_api_id</fk>
    away_team_api_id INTEGER NULL,
        -- <example>9993</example>
        -- <fk> -> Team.team_api_id</fk>
    home_team_goal INTEGER NULL,
        -- <example>1</example>
    away_team_goal INTEGER NULL,
        -- <example>1</example>
    home_player_X1 INTEGER NULL,
        -- <example>1</example>
    home_player_X2 INTEGER NULL,
        -- <example>2</example>
    home_player_X3 INTEGER NULL,
        -- <example>4</example>
    home_player_X4 INTEGER NULL,
        -- <example>6</example>
    home_player_X5 INTEGER NULL,
        -- <example>8</example>
    home_player_X6 INTEGER NULL,
        -- <example>2</example>
    home_player_X7 INTEGER NULL,
        -- <example>4</example>
    home_player_X8 INTEGER NULL,
        -- <example>6</example>
    home_player_X9 INTEGER NULL,
        -- <example>8</example>
    home_player_X10 INTEGER NULL,
        -- <example>4</example>
    home_player_X11 INTEGER NULL,
        -- <example>6</example>
    away_player_X1 INTEGER NULL,
        -- <example>1</example>
    away_player_X2 INTEGER NULL,
        -- <example>2</example>
    away_player_X3 INTEGER NULL,
        -- <example>4</example>
    away_player_X4 INTEGER NULL,
        -- <example>6</example>
    away_player_X5 INTEGER NULL,
        -- <example>8</example>
    away_player_X6 INTEGER NULL,
        -- <example>2</example>
    away_player_X7 INTEGER NULL,
        -- <example>4</example>
    away_player_X8 INTEGER NULL,
        -- <example>6</example>
    away_player_X9 INTEGER NULL,
        -- <example>8</example>
    away_player_X10 INTEGER NULL,
        -- <example>4</example>
    away_player_X11 INTEGER NULL,
        -- <example>6</example>
    home_player_Y1 INTEGER NULL,
        -- <example>1</example>
    home_player_Y2 INTEGER NULL,
        -- <example>3</example>
    home_player_Y3 INTEGER NULL,
        -- <example>3</example>
    home_player_Y4 INTEGER NULL,
        -- <example>3</example>
    home_player_Y5 INTEGER NULL,
        -- <example>3</example>
    home_player_Y6 INTEGER NULL,
        -- <example>7</example>
    home_player_Y7 INTEGER NULL,
        -- <example>7</example>
    home_player_Y8 INTEGER NULL,
        -- <example>7</example>
    home_player_Y9 INTEGER NULL,
        -- <example>7</example>
    home_player_Y10 INTEGER NULL,
        -- <example>10</example>
    home_player_Y11 INTEGER NULL,
        -- <example>10</example>
    away_player_Y1 INTEGER NULL,
        -- <example>1</example>
    away_player_Y2 INTEGER NULL,
        -- <example>3</example>
    away_player_Y3 INTEGER NULL,
        -- <example>3</example>
    away_player_Y4 INTEGER NULL,
        -- <example>3</example>
    away_player_Y5 INTEGER NULL,
        -- <example>3</example>
    away_player_Y6 INTEGER NULL,
        -- <example>7</example>
    away_player_Y7 INTEGER NULL,
        -- <example>7</example>
    away_player_Y8 INTEGER NULL,
        -- <example>7</example>
    away_player_Y9 INTEGER NULL,
        -- <example>7</example>
    away_player_Y10 INTEGER NULL,
        -- <example>10</example>
    away_player_Y11 INTEGER NULL,
        -- <example>10</example>
    home_player_1 INTEGER NULL,
        -- <example>39890</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_2 INTEGER NULL,
        -- <example>67950</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_3 INTEGER NULL,
        -- <example>38788</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_4 INTEGER NULL,
        -- <example>38312</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_5 INTEGER NULL,
        -- <example>26235</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_6 INTEGER NULL,
        -- <example>36393</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_7 INTEGER NULL,
        -- <example>148286</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_8 INTEGER NULL,
        -- <example>67898</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_9 INTEGER NULL,
        -- <example>26916</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_10 INTEGER NULL,
        -- <example>38801</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_11 INTEGER NULL,
        -- <example>94289</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_1 INTEGER NULL,
        -- <example>34480</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_2 INTEGER NULL,
        -- <example>38388</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_3 INTEGER NULL,
        -- <example>26458</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_4 INTEGER NULL,
        -- <example>13423</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_5 INTEGER NULL,
        -- <example>38389</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_6 INTEGER NULL,
        -- <example>38798</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_7 INTEGER NULL,
        -- <example>30949</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_8 INTEGER NULL,
        -- <example>38253</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_9 INTEGER NULL,
        -- <example>106013</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_10 INTEGER NULL,
        -- <example>38383</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_11 INTEGER NULL,
        -- <example>46552</example>
        -- <fk> -> Player.player_api_id</fk>
    goal TEXT NULL,
        -- <example>'<goal><value><comment>n</comment><stats><goals>1</...goal</type><goal_type>n</goal_type></value></goal>'</example>
    shoton TEXT NULL,
        -- <example>'<shoton><value><stats><blocked>1</blocked></stats>...type>shoton</type><id>379466</id></value></shoton>'</example>
    shotoff TEXT NULL,
        -- <example>'<shotoff><value><stats><shotoff>1</shotoff></stats...pe>shotoff</type><id>379573</id></value></shotoff>'</example>
    foulcommit TEXT NULL,
        -- <example>'<foulcommit><value><stats><foulscommitted>1</fouls...lcommit</type><id>379571</id></value></foulcommit>'</example>
    card TEXT NULL,
        -- <example>'<card><value><comment>y</comment><stats><ycards>1<.../n><type>card</type><id>379547</id></value></card>'</example>
    cross TEXT NULL,
        -- <example>'<cross><value><stats><crosses>1</crosses></stats><...><type>cross</type><id>379540</id></value></cross>'</example>
    corner TEXT NULL,
        -- <example>'<corner><value><stats><corners>1</corners></stats>...type>corner</type><id>379460</id></value></corner>'</example>
    possession TEXT NULL,
        -- <example>'<possession><value><comment>56</comment><event_inc...special</type><id>379575</id></value></possession>'</example>
    B365H REAL NULL,
        -- <example>1.730</example>
    B365D REAL NULL,
        -- <example>3.400</example>
    B365A REAL NULL,
        -- <example>5.000</example>
    BWH REAL NULL,
        -- <example>1.750</example>
    BWD REAL NULL,
        -- <example>3.350</example>
    BWA REAL NULL,
        -- <example>4.200</example>
    IWH REAL NULL,
        -- <example>1.850</example>
    IWD REAL NULL,
        -- <example>3.200</example>
    IWA REAL NULL,
        -- <example>3.500</example>
    LBH REAL NULL,
        -- <example>1.800</example>
    LBD REAL NULL,
        -- <example>3.300</example>
    LBA REAL NULL,
        -- <example>3.750</example>
    PSH REAL NULL,
        -- <example>5.100</example>
    PSD REAL NULL,
        -- <example>3.820</example>
    PSA REAL NULL,
        -- <example>1.760</example>
    WHH REAL NULL,
        -- <example>1.700</example>
    WHD REAL NULL,
        -- <example>3.300</example>
    WHA REAL NULL,
        -- <example>4.330</example>
    SJH REAL NULL,
        -- <example>1.900</example>
    SJD REAL NULL,
        -- <example>3.300</example>
    SJA REAL NULL,
        -- <example>4.000</example>
    VCH REAL NULL,
        -- <example>1.650</example>
    VCD REAL NULL,
        -- <example>3.400</example>
    VCA REAL NULL,
        -- <example>4.500</example>
    GBH REAL NULL,
        -- <example>1.780</example>
    GBD REAL NULL,
        -- <example>3.250</example>
    GBA REAL NULL,
        -- <example>4.000</example>
    BSH REAL NULL,
        -- <example>1.730</example>
    BSD REAL NULL,
        -- <example>3.400</example>
    BSA REAL NULL,
        -- <example>4.200</example>
    FOREIGN KEY (away_player_11) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_10) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_9) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_8) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_7) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_6) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_5) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_4) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_3) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_2) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_player_1) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_11) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_10) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_9) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_8) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_7) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_6) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_5) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_4) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_3) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_2) REFERENCES Player(player_api_id),
    FOREIGN KEY (home_player_1) REFERENCES Player(player_api_id),
    FOREIGN KEY (away_team_api_id) REFERENCES Team(team_api_id),
    FOREIGN KEY (home_team_api_id) REFERENCES Team(team_api_id),
    FOREIGN KEY (league_id) REFERENCES League(id),
    FOREIGN KEY (country_id) REFERENCES Country(id)
);

-- Table: Player (11060 rows)
CREATE TABLE Player (
    id INTEGER NULL PRIMARY KEY,
        -- <example>3879</example>
    player_api_id INTEGER NULL,
        -- <example>2625</example>
    player_name TEXT NULL,
        -- <example>'Aaron Appindangoye'</example>
    player_fifa_api_id INTEGER NULL,
        -- <example>2</example>
    birthday TEXT NULL,
        -- <example>'1992-02-29 00:00:00'</example>
    height INTEGER NULL,
        -- <example>182.880</example>
    weight INTEGER NULL
        -- <example>187</example>
);

-- Table: Player_Attributes (183978 rows)
CREATE TABLE Player_Attributes (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    player_fifa_api_id INTEGER NULL,
        -- <example>218353</example>
        -- <fk> -> Player.player_fifa_api_id</fk>
    player_api_id INTEGER NULL,
        -- <example>505942</example>
        -- <fk> -> Player.player_api_id</fk>
    date TEXT NULL,
        -- <example>'2016-02-18 00:00:00'</example>
    overall_rating INTEGER NULL,
        -- <example>67</example>
    potential INTEGER NULL,
        -- <example>71</example>
    preferred_foot TEXT NULL,
        -- <values>{'left', 'right'}</values>
    attacking_work_rate TEXT NULL,
        -- <values>{'None', 'high', 'le', 'low', 'medium', 'norm', 'stoc', 'y'}</values>
    defensive_work_rate TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '_0', 'ean', 'es', 'high', 'low', 'medium', 'o', 'ormal', 'tocky'}</values>
    crossing INTEGER NULL,
        -- <example>49</example>
    finishing INTEGER NULL,
        -- <example>44</example>
    heading_accuracy INTEGER NULL,
        -- <example>71</example>
    short_passing INTEGER NULL,
        -- <example>61</example>
    volleys INTEGER NULL,
        -- <example>44</example>
    dribbling INTEGER NULL,
        -- <example>51</example>
    curve INTEGER NULL,
        -- <example>45</example>
    free_kick_accuracy INTEGER NULL,
        -- <example>39</example>
    long_passing INTEGER NULL,
        -- <example>64</example>
    ball_control INTEGER NULL,
        -- <example>49</example>
    acceleration INTEGER NULL,
        -- <example>60</example>
    sprint_speed INTEGER NULL,
        -- <example>64</example>
    agility INTEGER NULL,
        -- <example>59</example>
    reactions INTEGER NULL,
        -- <example>47</example>
    balance INTEGER NULL,
        -- <example>65</example>
    shot_power INTEGER NULL,
        -- <example>55</example>
    jumping INTEGER NULL,
        -- <example>58</example>
    stamina INTEGER NULL,
        -- <example>54</example>
    strength INTEGER NULL,
        -- <example>76</example>
    long_shots INTEGER NULL,
        -- <example>35</example>
    aggression INTEGER NULL,
        -- <example>71</example>
    interceptions INTEGER NULL,
        -- <example>70</example>
    positioning INTEGER NULL,
        -- <example>45</example>
    vision INTEGER NULL,
        -- <example>54</example>
    penalties INTEGER NULL,
        -- <example>48</example>
    marking INTEGER NULL,
        -- <example>65</example>
    standing_tackle INTEGER NULL,
        -- <example>69</example>
    sliding_tackle INTEGER NULL,
        -- <example>69</example>
    gk_diving INTEGER NULL,
        -- <example>6</example>
    gk_handling INTEGER NULL,
        -- <example>11</example>
    gk_kicking INTEGER NULL,
        -- <example>10</example>
    gk_positioning INTEGER NULL,
        -- <example>8</example>
    gk_reflexes INTEGER NULL,
        -- <example>8</example>
    FOREIGN KEY (player_api_id) REFERENCES Player(player_api_id),
    FOREIGN KEY (player_fifa_api_id) REFERENCES Player(player_fifa_api_id)
);

-- Table: Team (299 rows)
CREATE TABLE Team (
    id INTEGER NULL PRIMARY KEY,
        -- <example>31446</example>
    team_api_id INTEGER NULL,
        -- <example>1601</example>
    team_fifa_api_id INTEGER NULL,
        -- <example>673</example>
    team_long_name TEXT NULL,
        -- <example>'KRC Genk'</example>
    team_short_name TEXT NULL
        -- <example>'GEN'</example>
);

-- Table: Team_Attributes (1458 rows)
CREATE TABLE Team_Attributes (
    id INTEGER NULL PRIMARY KEY,
        -- <example>1</example>
    team_fifa_api_id INTEGER NULL,
        -- <example>434</example>
        -- <fk> -> Team.team_fifa_api_id</fk>
    team_api_id INTEGER NULL,
        -- <example>9930</example>
        -- <fk> -> Team.team_api_id</fk>
    date TEXT NULL,
        -- <values>{'2010-02-22 00:00:00', '2011-02-22 00:00:00', '2012-02-22 00:00:00', '2013-09-20 00:00:00', '2014-09-19 00:00:00', '2015-09-10 00:00:00'}</values>
    buildUpPlaySpeed INTEGER NULL,
        -- <example>60</example>
    buildUpPlaySpeedClass TEXT NULL,
        -- <values>{'Balanced', 'Fast', 'Slow'}</values>
    buildUpPlayDribbling INTEGER NULL,
        -- <example>48</example>
    buildUpPlayDribblingClass TEXT NULL,
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    buildUpPlayPassing INTEGER NULL,
        -- <example>50</example>
    buildUpPlayPassingClass TEXT NULL,
        -- <values>{'Long', 'Mixed', 'Short'}</values>
    buildUpPlayPositioningClass TEXT NULL,
        -- <values>{'Free Form', 'Organised'}</values>
    chanceCreationPassing INTEGER NULL,
        -- <example>60</example>
    chanceCreationPassingClass TEXT NULL,
        -- <values>{'Normal', 'Risky', 'Safe'}</values>
    chanceCreationCrossing INTEGER NULL,
        -- <example>65</example>
    chanceCreationCrossingClass TEXT NULL,
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    chanceCreationShooting INTEGER NULL,
        -- <example>55</example>
    chanceCreationShootingClass TEXT NULL,
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    chanceCreationPositioningClass TEXT NULL,
        -- <values>{'Free Form', 'Organised'}</values>
    defencePressure INTEGER NULL,
        -- <example>50</example>
    defencePressureClass TEXT NULL,
        -- <values>{'Deep', 'High', 'Medium'}</values>
    defenceAggression INTEGER NULL,
        -- <example>55</example>
    defenceAggressionClass TEXT NULL,
        -- <values>{'Contain', 'Double', 'Press'}</values>
    defenceTeamWidth INTEGER NULL,
        -- <example>45</example>
    defenceTeamWidthClass TEXT NULL,
        -- <values>{'Narrow', 'Normal', 'Wide'}</values>
    defenceDefenderLineClass TEXT NULL,
        -- <values>{'Cover', 'Offside Trap'}</values>
    FOREIGN KEY (team_api_id) REFERENCES Team(team_api_id),
    FOREIGN KEY (team_fifa_api_id) REFERENCES Team(team_fifa_api_id)
);
```