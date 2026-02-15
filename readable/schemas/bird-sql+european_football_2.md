```sql
-- Database: european_football_2

/*
Schema: NULL
Table: Country
Rows: 11
Sample rows:
| id    | name    |
|-------|---------|
| 1     | Belgium |
| 1729  | England |
| 4769  | France  |
| 7809  | Germany |
| 10257 | Italy   |
| ...   | ...     |
*/
CREATE TABLE Country (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "name" TEXT NOT NULL
        -- <example>'Belgium'</example>
);

/*
Schema: NULL
Table: League
Rows: 11
Sample rows:
| id    | country_id   | name                   |
|-------|--------------|------------------------|
| 1     | 1            | Belgium Jupiler League |
| 1729  | 1729         | England Premier League |
| 4769  | 4769         | France Ligue 1         |
| 7809  | 7809         | Germany 1. Bundesliga  |
| 10257 | 10257        | Italy Serie A          |
| ...   | ...          | ...                    |
*/
CREATE TABLE League (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "country_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> country."id"</fk>
    "name" TEXT NOT NULL,
        -- <example>'Belgium Jupiler League'</example>
    FOREIGN KEY ("country_id") REFERENCES country("id")
);

/*
Schema: NULL
Table: Match
Rows: 25979
Sample rows:
| id   | country_id   | league_id   | season    | stage   | date                | match_api_id   | home_team_api_id   | away_team_api_id   | home_team_goal   | away_team_goal   | home_player_X1   | home_player_X2   | home_player_X3   | home_player_X4   | home_player_X5   | home_player_X6   | home_player_X7   | home_player_X8   | home_player_X9   | home_player_X10   | home_player_X11   | away_player_X1   | away_player_X2   | away_player_X3   | away_player_X4   | away_player_X5   | away_player_X6   | away_player_X7   | away_player_X8   | away_player_X9   | away_player_X10   | away_player_X11   | home_player_Y1   | home_player_Y2   | home_player_Y3   | home_player_Y4   | home_player_Y5   | home_player_Y6   | home_player_Y7   | home_player_Y8   | home_player_Y9   | home_player_Y10   | home_player_Y11   | away_player_Y1   | away_player_Y2   | away_player_Y3   | away_player_Y4   | away_player_Y5   | away_player_Y6   | away_player_Y7   | away_player_Y8   | away_player_Y9   | away_player_Y10   | away_player_Y11   | home_player_1   | home_player_2   | home_player_3   | home_player_4   | home_player_5   | home_player_6   | home_player_7   | home_player_8   | home_player_9   | home_player_10   | home_player_11   | away_player_1   | away_player_2   | away_player_3   | away_player_4   | away_player_5   | away_player_6   | away_player_7   | away_player_8   | away_player_9   | away_player_10   | away_player_11   | goal   | shoton   | shotoff   | foulcommit   | card   | cross   | corner   | possession   | B365H   | B365D   | B365A   | BWH   | BWD   | BWA   | IWH   | IWD   | IWA   | LBH   | LBD   | LBA   | PSH    | PSD    | PSA    | WHH   | WHD   | WHA   | SJH   | SJD   | SJA   | VCH   | VCD   | VCA   | GBH   | GBD   | GBA   | BSH   | BSD   | BSA   |
|------|--------------|-------------|-----------|---------|---------------------|----------------|--------------------|--------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|-------------------|-------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|-------------------|-------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|-------------------|-------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|------------------|-------------------|-------------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|------------------|------------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|-----------------|------------------|------------------|--------|----------|-----------|--------------|--------|---------|----------|--------------|---------|---------|---------|-------|-------|-------|-------|-------|-------|-------|-------|-------|--------|--------|--------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|-------|
| 1    | 1            | 1           | 2008/2009 | 1       | 2008-08-17 00:00:00 | 492473         | 9987               | 9993               | 1                | 1                | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL] | [NULL]   | [NULL]    | [NULL]       | [NULL] | [NULL]  | [NULL]   | [NULL]       | 1.73    | 3.4     | 5.0     | 1.75  | 3.35  | 4.2   | 1.85  | 3.2   | 3.5   | 1.8   | 3.3   | 3.75  | [NULL] | [NULL] | [NULL] | 1.7   | 3.3   | 4.33  | 1.9   | 3.3   | 4.0   | 1.65  | 3.4   | 4.5   | 1.78  | 3.25  | 4.0   | 1.73  | 3.4   | 4.2   |
| 2    | 1            | 1           | 2008/2009 | 1       | 2008-08-16 00:00:00 | 492474         | 10000              | 9994               | 0                | 0                | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL] | [NULL]   | [NULL]    | [NULL]       | [NULL] | [NULL]  | [NULL]   | [NULL]       | 1.95    | 3.2     | 3.6     | 1.8   | 3.3   | 3.95  | 1.9   | 3.2   | 3.5   | 1.9   | 3.2   | 3.5   | [NULL] | [NULL] | [NULL] | 1.83  | 3.3   | 3.6   | 1.95  | 3.3   | 3.8   | 2.0   | 3.25  | 3.25  | 1.85  | 3.25  | 3.75  | 1.91  | 3.25  | 3.6   |
| 3    | 1            | 1           | 2008/2009 | 1       | 2008-08-16 00:00:00 | 492475         | 9984               | 8635               | 0                | 3                | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL] | [NULL]   | [NULL]    | [NULL]       | [NULL] | [NULL]  | [NULL]   | [NULL]       | 2.38    | 3.3     | 2.75    | 2.4   | 3.3   | 2.55  | 2.6   | 3.1   | 2.3   | 2.5   | 3.2   | 2.5   | [NULL] | [NULL] | [NULL] | 2.5   | 3.25  | 2.4   | 2.63  | 3.3   | 2.5   | 2.35  | 3.25  | 2.65  | 2.5   | 3.2   | 2.5   | 2.3   | 3.2   | 2.75  |
| 4    | 1            | 1           | 2008/2009 | 1       | 2008-08-17 00:00:00 | 492476         | 9991               | 9998               | 5                | 0                | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL] | [NULL]   | [NULL]    | [NULL]       | [NULL] | [NULL]  | [NULL]   | [NULL]       | 1.44    | 3.75    | 7.5     | 1.4   | 4.0   | 6.8   | 1.4   | 3.9   | 6.0   | 1.44  | 3.6   | 6.5   | [NULL] | [NULL] | [NULL] | 1.44  | 3.75  | 6.0   | 1.44  | 4.0   | 7.5   | 1.45  | 3.75  | 6.5   | 1.5   | 3.75  | 5.5   | 1.44  | 3.75  | 6.5   |
| 5    | 1            | 1           | 2008/2009 | 1       | 2008-08-16 00:00:00 | 492477         | 7947               | 9985               | 1                | 3                | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]           | [NULL]            | [NULL]            | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]          | [NULL]           | [NULL]           | [NULL] | [NULL]   | [NULL]    | [NULL]       | [NULL] | [NULL]  | [NULL]   | [NULL]       | 5.0     | 3.5     | 1.65    | 5.0   | 3.5   | 1.6   | 4.0   | 3.3   | 1.7   | 4.0   | 3.4   | 1.72  | [NULL] | [NULL] | [NULL] | 4.2   | 3.4   | 1.7   | 4.5   | 3.5   | 1.73  | 4.5   | 3.4   | 1.65  | 4.5   | 3.5   | 1.65  | 4.75  | 3.3   | 1.67  |
| ...  | ...          | ...         | ...       | ...     | ...                 | ...            | ...                | ...                | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...               | ...               | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...               | ...               | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...               | ...               | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...              | ...               | ...               | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...              | ...              | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...             | ...              | ...              | ...    | ...      | ...       | ...          | ...    | ...     | ...      | ...          | ...     | ...     | ...     | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...    | ...    | ...    | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   | ...   |
*/
CREATE TABLE Match (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>4769</example>
    "country_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> Country."id"</fk>
    "league_id" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> League."id"</fk>
    "season" TEXT NOT NULL,
        -- <values>{'2008/2009', '2009/2010', '2010/2011', '2011/2012', '2012/2013', '2013/2014', '2014/2015', '2015/2016'}</values>
    "stage" INTEGER NOT NULL,
        -- <example>1</example>
    "date" TEXT NOT NULL,
        -- <example>'2008-08-17 00:00:00'</example>
    "match_api_id" INTEGER NOT NULL,
        -- <example>483129</example>
    "home_team_api_id" INTEGER NOT NULL,
        -- <example>9987</example>
        -- <fk> -> Team."team_api_id"</fk>
    "away_team_api_id" INTEGER NOT NULL,
        -- <example>9993</example>
        -- <fk> -> Team."team_api_id"</fk>
    "home_team_goal" INTEGER NOT NULL,
        -- <example>1</example>
    "away_team_goal" INTEGER NOT NULL,
        -- <example>1</example>
    "home_player_X1" INTEGER NULL,
        -- <example>1</example>
    "home_player_X2" INTEGER NULL,
        -- <example>2</example>
    "home_player_X3" INTEGER NULL,
        -- <example>4</example>
    "home_player_X4" INTEGER NULL,
        -- <example>6</example>
    "home_player_X5" INTEGER NULL,
        -- <example>8</example>
    "home_player_X6" INTEGER NULL,
        -- <example>2</example>
    "home_player_X7" INTEGER NULL,
        -- <example>4</example>
    "home_player_X8" INTEGER NULL,
        -- <example>6</example>
    "home_player_X9" INTEGER NULL,
        -- <example>8</example>
    "home_player_X10" INTEGER NULL,
        -- <example>4</example>
    "home_player_X11" INTEGER NULL,
        -- <example>6</example>
    "away_player_X1" INTEGER NULL,
        -- <example>1</example>
    "away_player_X2" INTEGER NULL,
        -- <example>2</example>
    "away_player_X3" INTEGER NULL,
        -- <example>4</example>
    "away_player_X4" INTEGER NULL,
        -- <example>6</example>
    "away_player_X5" INTEGER NULL,
        -- <example>8</example>
    "away_player_X6" INTEGER NULL,
        -- <example>2</example>
    "away_player_X7" INTEGER NULL,
        -- <example>4</example>
    "away_player_X8" INTEGER NULL,
        -- <example>6</example>
    "away_player_X9" INTEGER NULL,
        -- <example>8</example>
    "away_player_X10" INTEGER NULL,
        -- <example>4</example>
    "away_player_X11" INTEGER NULL,
        -- <example>6</example>
    "home_player_Y1" INTEGER NULL,
        -- <example>1</example>
    "home_player_Y2" INTEGER NULL,
        -- <example>3</example>
    "home_player_Y3" INTEGER NULL,
        -- <example>3</example>
    "home_player_Y4" INTEGER NULL,
        -- <example>3</example>
    "home_player_Y5" INTEGER NULL,
        -- <example>3</example>
    "home_player_Y6" INTEGER NULL,
        -- <example>7</example>
    "home_player_Y7" INTEGER NULL,
        -- <example>7</example>
    "home_player_Y8" INTEGER NULL,
        -- <example>7</example>
    "home_player_Y9" INTEGER NULL,
        -- <example>7</example>
    "home_player_Y10" INTEGER NULL,
        -- <example>10</example>
    "home_player_Y11" INTEGER NULL,
        -- <example>10</example>
    "away_player_Y1" INTEGER NULL,
        -- <example>1</example>
    "away_player_Y2" INTEGER NULL,
        -- <example>3</example>
    "away_player_Y3" INTEGER NULL,
        -- <example>3</example>
    "away_player_Y4" INTEGER NULL,
        -- <example>3</example>
    "away_player_Y5" INTEGER NULL,
        -- <example>3</example>
    "away_player_Y6" INTEGER NULL,
        -- <example>7</example>
    "away_player_Y7" INTEGER NULL,
        -- <example>7</example>
    "away_player_Y8" INTEGER NULL,
        -- <example>7</example>
    "away_player_Y9" INTEGER NULL,
        -- <example>7</example>
    "away_player_Y10" INTEGER NULL,
        -- <example>10</example>
    "away_player_Y11" INTEGER NULL,
        -- <example>10</example>
    "home_player_1" INTEGER NULL,
        -- <example>39890</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_2" INTEGER NULL,
        -- <example>67950</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_3" INTEGER NULL,
        -- <example>38788</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_4" INTEGER NULL,
        -- <example>38312</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_5" INTEGER NULL,
        -- <example>26235</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_6" INTEGER NULL,
        -- <example>36393</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_7" INTEGER NULL,
        -- <example>148286</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_8" INTEGER NULL,
        -- <example>67898</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_9" INTEGER NULL,
        -- <example>26916</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_10" INTEGER NULL,
        -- <example>38801</example>
        -- <fk> -> Player."player_api_id"</fk>
    "home_player_11" INTEGER NULL,
        -- <example>94289</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_1" INTEGER NULL,
        -- <example>34480</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_2" INTEGER NULL,
        -- <example>38388</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_3" INTEGER NULL,
        -- <example>26458</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_4" INTEGER NULL,
        -- <example>13423</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_5" INTEGER NULL,
        -- <example>38389</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_6" INTEGER NULL,
        -- <example>38798</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_7" INTEGER NULL,
        -- <example>30949</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_8" INTEGER NULL,
        -- <example>38253</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_9" INTEGER NULL,
        -- <example>106013</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_10" INTEGER NULL,
        -- <example>38383</example>
        -- <fk> -> Player."player_api_id"</fk>
    "away_player_11" INTEGER NULL,
        -- <example>46552</example>
        -- <fk> -> Player."player_api_id"</fk>
    "goal" TEXT NULL,
        -- <example>'<goal><value><comment>n</comment><stats><goals>1</...goal</type><goal_type>n</goal_type></value></goal>'</example>
    "shoton" TEXT NULL,
        -- <example>'<shoton><value><stats><blocked>1</blocked></stats>...type>shoton</type><id>379466</id></value></shoton>'</example>
    "shotoff" TEXT NULL,
        -- <example>'<shotoff><value><stats><shotoff>1</shotoff></stats...pe>shotoff</type><id>379573</id></value></shotoff>'</example>
    "foulcommit" TEXT NULL,
        -- <example>'<foulcommit><value><stats><foulscommitted>1</fouls...lcommit</type><id>379571</id></value></foulcommit>'</example>
    "card" TEXT NULL,
        -- <example>'<card><value><comment>y</comment><stats><ycards>1<.../n><type>card</type><id>379547</id></value></card>'</example>
    "cross" TEXT NULL,
        -- <example>'<cross><value><stats><crosses>1</crosses></stats><...><type>cross</type><id>379540</id></value></cross>'</example>
    "corner" TEXT NULL,
        -- <example>'<corner><value><stats><corners>1</corners></stats>...type>corner</type><id>379460</id></value></corner>'</example>
    "possession" TEXT NULL,
        -- <example>'<possession><value><comment>56</comment><event_inc...special</type><id>379575</id></value></possession>'</example>
    "B365H" REAL NULL,
        -- <example>1.730</example>
    "B365D" REAL NULL,
        -- <example>3.400</example>
    "B365A" REAL NULL,
        -- <example>5.000</example>
    "BWH" REAL NULL,
        -- <example>1.750</example>
    "BWD" REAL NULL,
        -- <example>3.350</example>
    "BWA" REAL NULL,
        -- <example>4.200</example>
    "IWH" REAL NULL,
        -- <example>1.850</example>
    "IWD" REAL NULL,
        -- <example>3.200</example>
    "IWA" REAL NULL,
        -- <example>3.500</example>
    "LBH" REAL NULL,
        -- <example>1.800</example>
    "LBD" REAL NULL,
        -- <example>3.300</example>
    "LBA" REAL NULL,
        -- <example>3.750</example>
    "PSH" REAL NULL,
        -- <example>5.100</example>
    "PSD" REAL NULL,
        -- <example>3.820</example>
    "PSA" REAL NULL,
        -- <example>1.760</example>
    "WHH" REAL NULL,
        -- <example>1.700</example>
    "WHD" REAL NULL,
        -- <example>3.300</example>
    "WHA" REAL NULL,
        -- <example>4.330</example>
    "SJH" REAL NULL,
        -- <example>1.900</example>
    "SJD" REAL NULL,
        -- <example>3.300</example>
    "SJA" REAL NULL,
        -- <example>4.000</example>
    "VCH" REAL NULL,
        -- <example>1.650</example>
    "VCD" REAL NULL,
        -- <example>3.400</example>
    "VCA" REAL NULL,
        -- <example>4.500</example>
    "GBH" REAL NULL,
        -- <example>1.780</example>
    "GBD" REAL NULL,
        -- <example>3.250</example>
    "GBA" REAL NULL,
        -- <example>4.000</example>
    "BSH" REAL NULL,
        -- <example>1.730</example>
    "BSD" REAL NULL,
        -- <example>3.400</example>
    "BSA" REAL NULL,
        -- <example>4.200</example>
    FOREIGN KEY ("away_player_11") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_10") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_9") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_8") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_7") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_6") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_5") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_4") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_3") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_2") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_player_1") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_11") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_10") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_9") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_8") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_7") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_6") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_5") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_4") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_3") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_2") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("home_player_1") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("away_team_api_id") REFERENCES Team("team_api_id"),
    FOREIGN KEY ("home_team_api_id") REFERENCES Team("team_api_id"),
    FOREIGN KEY ("league_id") REFERENCES League("id"),
    FOREIGN KEY ("country_id") REFERENCES Country("id")
);

/*
Schema: NULL
Table: Player
Rows: 11060
Sample rows:
| id   | player_api_id   | player_name        | player_fifa_api_id   | birthday            | height   | weight   |
|------|-----------------|--------------------|----------------------|---------------------|----------|----------|
| 1    | 505942          | Aaron Appindangoye | 218353               | 1992-02-29 00:00:00 | 182.88   | 187      |
| 2    | 155782          | Aaron Cresswell    | 189615               | 1989-12-15 00:00:00 | 170.18   | 146      |
| 3    | 162549          | Aaron Doran        | 186170               | 1991-05-13 00:00:00 | 170.18   | 163      |
| 4    | 30572           | Aaron Galindo      | 140161               | 1982-05-08 00:00:00 | 182.88   | 198      |
| 5    | 23780           | Aaron Hughes       | 17725                | 1979-11-08 00:00:00 | 182.88   | 154      |
| ...  | ...             | ...                | ...                  | ...                 | ...      | ...      |
*/
CREATE TABLE Player (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>3879</example>
    "player_api_id" INTEGER NOT NULL,
        -- <example>2625</example>
    "player_name" TEXT NOT NULL,
        -- <example>'Aaron Appindangoye'</example>
    "player_fifa_api_id" INTEGER NOT NULL,
        -- <example>2</example>
    "birthday" TEXT NOT NULL,
        -- <example>'1992-02-29 00:00:00'</example>
    "height" INTEGER NOT NULL,
        -- <example>182.880</example>
    "weight" INTEGER NOT NULL
        -- <example>187</example>
);

/*
Schema: NULL
Table: Player_Attributes
Rows: 183978
Sample rows:
| id   | player_fifa_api_id   | player_api_id   | date                | overall_rating   | potential   | preferred_foot   | attacking_work_rate   | defensive_work_rate   | crossing   | finishing   | heading_accuracy   | short_passing   | volleys   | dribbling   | curve   | free_kick_accuracy   | long_passing   | ball_control   | acceleration   | sprint_speed   | agility   | reactions   | balance   | shot_power   | jumping   | stamina   | strength   | long_shots   | aggression   | interceptions   | positioning   | vision   | penalties   | marking   | standing_tackle   | sliding_tackle   | gk_diving   | gk_handling   | gk_kicking   | gk_positioning   | gk_reflexes   |
|------|----------------------|-----------------|---------------------|------------------|-------------|------------------|-----------------------|-----------------------|------------|-------------|--------------------|-----------------|-----------|-------------|---------|----------------------|----------------|----------------|----------------|----------------|-----------|-------------|-----------|--------------|-----------|-----------|------------|--------------|--------------|-----------------|---------------|----------|-------------|-----------|-------------------|------------------|-------------|---------------|--------------|------------------|---------------|
| 1    | 218353               | 505942          | 2016-02-18 00:00:00 | 67               | 71          | right            | medium                | medium                | 49         | 44          | 71                 | 61              | 44        | 51          | 45      | 39                   | 64             | 49             | 60             | 64             | 59        | 47          | 65        | 55           | 58        | 54        | 76         | 35           | 71           | 70              | 45            | 54       | 48          | 65        | 69                | 69               | 6           | 11            | 10           | 8                | 8             |
| 2    | 218353               | 505942          | 2015-11-19 00:00:00 | 67               | 71          | right            | medium                | medium                | 49         | 44          | 71                 | 61              | 44        | 51          | 45      | 39                   | 64             | 49             | 60             | 64             | 59        | 47          | 65        | 55           | 58        | 54        | 76         | 35           | 71           | 70              | 45            | 54       | 48          | 65        | 69                | 69               | 6           | 11            | 10           | 8                | 8             |
| 3    | 218353               | 505942          | 2015-09-21 00:00:00 | 62               | 66          | right            | medium                | medium                | 49         | 44          | 71                 | 61              | 44        | 51          | 45      | 39                   | 64             | 49             | 60             | 64             | 59        | 47          | 65        | 55           | 58        | 54        | 76         | 35           | 63           | 41              | 45            | 54       | 48          | 65        | 66                | 69               | 6           | 11            | 10           | 8                | 8             |
| 4    | 218353               | 505942          | 2015-03-20 00:00:00 | 61               | 65          | right            | medium                | medium                | 48         | 43          | 70                 | 60              | 43        | 50          | 44      | 38                   | 63             | 48             | 60             | 64             | 59        | 46          | 65        | 54           | 58        | 54        | 76         | 34           | 62           | 40              | 44            | 53       | 47          | 62        | 63                | 66               | 5           | 10            | 9            | 7                | 7             |
| 5    | 218353               | 505942          | 2007-02-22 00:00:00 | 61               | 65          | right            | medium                | medium                | 48         | 43          | 70                 | 60              | 43        | 50          | 44      | 38                   | 63             | 48             | 60             | 64             | 59        | 46          | 65        | 54           | 58        | 54        | 76         | 34           | 62           | 40              | 44            | 53       | 47          | 62        | 63                | 66               | 5           | 10            | 9            | 7                | 7             |
| ...  | ...                  | ...             | ...                 | ...              | ...         | ...              | ...                   | ...                   | ...        | ...         | ...                | ...             | ...       | ...         | ...     | ...                  | ...            | ...            | ...            | ...            | ...       | ...         | ...       | ...          | ...       | ...       | ...        | ...          | ...          | ...             | ...           | ...      | ...         | ...       | ...               | ...              | ...         | ...           | ...          | ...              | ...           |
*/
CREATE TABLE Player_Attributes (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "player_fifa_api_id" INTEGER NOT NULL,
        -- <example>218353</example>
        -- <fk> -> Player."player_fifa_api_id"</fk>
    "player_api_id" INTEGER NOT NULL,
        -- <example>505942</example>
        -- <fk> -> Player."player_api_id"</fk>
    "date" TEXT NOT NULL,
        -- <example>'2016-02-18 00:00:00'</example>
    "overall_rating" INTEGER NULL,
        -- <example>67</example>
    "potential" INTEGER NULL,
        -- <example>71</example>
    "preferred_foot" TEXT NULL,
        -- <values>{'left', 'right'}</values>
    "attacking_work_rate" TEXT NULL,
        -- <values>{'None', 'high', 'le', 'low', 'medium', 'norm', 'stoc', 'y'}</values>
    "defensive_work_rate" TEXT NULL,
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '_0', 'ean', 'es', 'high', 'low', 'medium', 'o', 'ormal', 'tocky'}</values>
    "crossing" INTEGER NULL,
        -- <example>49</example>
    "finishing" INTEGER NULL,
        -- <example>44</example>
    "heading_accuracy" INTEGER NULL,
        -- <example>71</example>
    "short_passing" INTEGER NULL,
        -- <example>61</example>
    "volleys" INTEGER NULL,
        -- <example>44</example>
    "dribbling" INTEGER NULL,
        -- <example>51</example>
    "curve" INTEGER NULL,
        -- <example>45</example>
    "free_kick_accuracy" INTEGER NULL,
        -- <example>39</example>
    "long_passing" INTEGER NULL,
        -- <example>64</example>
    "ball_control" INTEGER NULL,
        -- <example>49</example>
    "acceleration" INTEGER NULL,
        -- <example>60</example>
    "sprint_speed" INTEGER NULL,
        -- <example>64</example>
    "agility" INTEGER NULL,
        -- <example>59</example>
    "reactions" INTEGER NULL,
        -- <example>47</example>
    "balance" INTEGER NULL,
        -- <example>65</example>
    "shot_power" INTEGER NULL,
        -- <example>55</example>
    "jumping" INTEGER NULL,
        -- <example>58</example>
    "stamina" INTEGER NULL,
        -- <example>54</example>
    "strength" INTEGER NULL,
        -- <example>76</example>
    "long_shots" INTEGER NULL,
        -- <example>35</example>
    "aggression" INTEGER NULL,
        -- <example>71</example>
    "interceptions" INTEGER NULL,
        -- <example>70</example>
    "positioning" INTEGER NULL,
        -- <example>45</example>
    "vision" INTEGER NULL,
        -- <example>54</example>
    "penalties" INTEGER NULL,
        -- <example>48</example>
    "marking" INTEGER NULL,
        -- <example>65</example>
    "standing_tackle" INTEGER NULL,
        -- <example>69</example>
    "sliding_tackle" INTEGER NULL,
        -- <example>69</example>
    "gk_diving" INTEGER NULL,
        -- <example>6</example>
    "gk_handling" INTEGER NULL,
        -- <example>11</example>
    "gk_kicking" INTEGER NULL,
        -- <example>10</example>
    "gk_positioning" INTEGER NULL,
        -- <example>8</example>
    "gk_reflexes" INTEGER NULL,
        -- <example>8</example>
    FOREIGN KEY ("player_api_id") REFERENCES Player("player_api_id"),
    FOREIGN KEY ("player_fifa_api_id") REFERENCES Player("player_fifa_api_id")
);

/*
Schema: NULL
Table: Team
Rows: 299
Sample rows:
| id   | team_api_id   | team_fifa_api_id   | team_long_name    | team_short_name   |
|------|---------------|--------------------|-------------------|-------------------|
| 1    | 9987          | 673.0              | KRC Genk          | GEN               |
| 2    | 9993          | 675.0              | Beerschot AC      | BAC               |
| 3    | 10000         | 15005.0            | SV Zulte-Waregem  | ZUL               |
| 4    | 9994          | 2007.0             | Sporting Lokeren  | LOK               |
| 5    | 9984          | 1750.0             | KSV Cercle Brugge | CEB               |
| ...  | ...           | ...                | ...               | ...               |
*/
CREATE TABLE Team (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>31446</example>
    "team_api_id" INTEGER NOT NULL,
        -- <example>1601</example>
    "team_fifa_api_id" INTEGER NULL,
        -- <example>673</example>
    "team_long_name" TEXT NOT NULL,
        -- <example>'KRC Genk'</example>
    "team_short_name" TEXT NOT NULL
        -- <example>'GEN'</example>
);

/*
Schema: NULL
Table: Team_Attributes
Rows: 1458
Sample rows:
| id   | team_fifa_api_id   | team_api_id   | date                | buildUpPlaySpeed   | buildUpPlaySpeedClass   | buildUpPlayDribbling   | buildUpPlayDribblingClass   | buildUpPlayPassing   | buildUpPlayPassingClass   | buildUpPlayPositioningClass   | chanceCreationPassing   | chanceCreationPassingClass   | chanceCreationCrossing   | chanceCreationCrossingClass   | chanceCreationShooting   | chanceCreationShootingClass   | chanceCreationPositioningClass   | defencePressure   | defencePressureClass   | defenceAggression   | defenceAggressionClass   | defenceTeamWidth   | defenceTeamWidthClass   | defenceDefenderLineClass   |
|------|--------------------|---------------|---------------------|--------------------|-------------------------|------------------------|-----------------------------|----------------------|---------------------------|-------------------------------|-------------------------|------------------------------|--------------------------|-------------------------------|--------------------------|-------------------------------|----------------------------------|-------------------|------------------------|---------------------|--------------------------|--------------------|-------------------------|----------------------------|
| 1    | 434                | 9930          | 2010-02-22 00:00:00 | 60                 | Balanced                | [NULL]                 | Little                      | 50                   | Mixed                     | Organised                     | 60                      | Normal                       | 65                       | Normal                        | 55                       | Normal                        | Organised                        | 50                | Medium                 | 55                  | Press                    | 45                 | Normal                  | Cover                      |
| 2    | 434                | 9930          | 2014-09-19 00:00:00 | 52                 | Balanced                | 48.0                   | Normal                      | 56                   | Mixed                     | Organised                     | 54                      | Normal                       | 63                       | Normal                        | 64                       | Normal                        | Organised                        | 47                | Medium                 | 44                  | Press                    | 54                 | Normal                  | Cover                      |
| 3    | 434                | 9930          | 2015-09-10 00:00:00 | 47                 | Balanced                | 41.0                   | Normal                      | 54                   | Mixed                     | Organised                     | 54                      | Normal                       | 63                       | Normal                        | 64                       | Normal                        | Organised                        | 47                | Medium                 | 44                  | Press                    | 54                 | Normal                  | Cover                      |
| 4    | 77                 | 8485          | 2010-02-22 00:00:00 | 70                 | Fast                    | [NULL]                 | Little                      | 70                   | Long                      | Organised                     | 70                      | Risky                        | 70                       | Lots                          | 70                       | Lots                          | Organised                        | 60                | Medium                 | 70                  | Double                   | 70                 | Wide                    | Cover                      |
| 5    | 77                 | 8485          | 2011-02-22 00:00:00 | 47                 | Balanced                | [NULL]                 | Little                      | 52                   | Mixed                     | Organised                     | 53                      | Normal                       | 48                       | Normal                        | 52                       | Normal                        | Organised                        | 47                | Medium                 | 47                  | Press                    | 52                 | Normal                  | Cover                      |
| ...  | ...                | ...           | ...                 | ...                | ...                     | ...                    | ...                         | ...                  | ...                       | ...                           | ...                     | ...                          | ...                      | ...                           | ...                      | ...                           | ...                              | ...               | ...                    | ...                 | ...                      | ...                | ...                     | ...                        |
*/
CREATE TABLE Team_Attributes (
    "id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "team_fifa_api_id" INTEGER NOT NULL,
        -- <example>434</example>
        -- <fk> -> Team."team_fifa_api_id"</fk>
    "team_api_id" INTEGER NOT NULL,
        -- <example>9930</example>
        -- <fk> -> Team."team_api_id"</fk>
    "date" TEXT NOT NULL,
        -- <values>{'2010-02-22 00:00:00', '2011-02-22 00:00:00', '2012-02-22 00:00:00', '2013-09-20 00:00:00', '2014-09-19 00:00:00', '2015-09-10 00:00:00'}</values>
    "buildUpPlaySpeed" INTEGER NOT NULL,
        -- <example>60</example>
    "buildUpPlaySpeedClass" TEXT NOT NULL,
        -- <values>{'Balanced', 'Fast', 'Slow'}</values>
    "buildUpPlayDribbling" INTEGER NULL,
        -- <example>48</example>
    "buildUpPlayDribblingClass" TEXT NOT NULL,
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    "buildUpPlayPassing" INTEGER NOT NULL,
        -- <example>50</example>
    "buildUpPlayPassingClass" TEXT NOT NULL,
        -- <values>{'Long', 'Mixed', 'Short'}</values>
    "buildUpPlayPositioningClass" TEXT NOT NULL,
        -- <values>{'Free Form', 'Organised'}</values>
    "chanceCreationPassing" INTEGER NOT NULL,
        -- <example>60</example>
    "chanceCreationPassingClass" TEXT NOT NULL,
        -- <values>{'Normal', 'Risky', 'Safe'}</values>
    "chanceCreationCrossing" INTEGER NOT NULL,
        -- <example>65</example>
    "chanceCreationCrossingClass" TEXT NOT NULL,
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    "chanceCreationShooting" INTEGER NOT NULL,
        -- <example>55</example>
    "chanceCreationShootingClass" TEXT NOT NULL,
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    "chanceCreationPositioningClass" TEXT NOT NULL,
        -- <values>{'Free Form', 'Organised'}</values>
    "defencePressure" INTEGER NOT NULL,
        -- <example>50</example>
    "defencePressureClass" TEXT NOT NULL,
        -- <values>{'Deep', 'High', 'Medium'}</values>
    "defenceAggression" INTEGER NOT NULL,
        -- <example>55</example>
    "defenceAggressionClass" TEXT NOT NULL,
        -- <values>{'Contain', 'Double', 'Press'}</values>
    "defenceTeamWidth" INTEGER NOT NULL,
        -- <example>45</example>
    "defenceTeamWidthClass" TEXT NOT NULL,
        -- <values>{'Narrow', 'Normal', 'Wide'}</values>
    "defenceDefenderLineClass" TEXT NOT NULL,
        -- <values>{'Cover', 'Offside Trap'}</values>
    FOREIGN KEY ("team_api_id") REFERENCES Team("team_api_id"),
    FOREIGN KEY ("team_fifa_api_id") REFERENCES Team("team_fifa_api_id")
);
```