```sql
-- Database: european_football_2

/*
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
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Country identifier used to reference a country from other tables (e.g., League.country_id, Match.country_id).</description>
        -- <example>1</example>
    name TEXT NOT NULL
        -- <description>Country name — the common name of the country (for example: Germany, Italy, Scotland).</description>
        -- <example>'Belgium'</example>
);

/*
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
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>League identifier — unique identifier for each league in the League table.</description>
        -- <example>1</example>
    country_id INTEGER NOT NULL,
        -- <description>Country reference for the league — foreign key to Country.id indicating the country the league belongs to.</description>
        -- <example>1</example>
        -- <fk> -> country.id</fk>
    name TEXT NOT NULL,
        -- <description>League name — the official full name of the football competition or league (for example, England Premier League or Italy Serie A).</description>
        -- <example>'Belgium Jupiler League'</example>
    FOREIGN KEY (country_id) REFERENCES country(id)
);

/*
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
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for each match in the dataset.</description>
        -- <example>4769</example>
    country_id INTEGER NOT NULL,
        -- <description>Match country identifier — identifies the country where the match was played.</description>
        -- <example>1</example>
        -- <fk> -> Country.id</fk>
    league_id INTEGER NOT NULL,
        -- <description>League identifier for the match — a foreign key reference to League.id that indicates which league the fixture belongs to.</description>
        -- <example>1</example>
        -- <fk> -> League.id</fk>
    season TEXT NOT NULL,
        -- <description>Match season — the league year span for the fixture (format 'YYYY/YYYY'); values in this dataset range from '2008/2009' to '2015/2016' (e.g., '2014/2015').</description>
        -- <values>{'2008/2009', '2009/2010', '2010/2011', '2011/2012', '2012/2013', '2013/2014', '2014/2015', '2015/2016'}</values>
    stage INTEGER NOT NULL,
        -- <description>Match stage — the competition stage, round, or matchday within the season (a numeric code indicating the match’s round or phase such as group/regular season vs. knockout).</description>
        -- <example>1</example>
    date TEXT NOT NULL,
        -- <description>Match kickoff timestamp in 'YYYY-MM-DD HH:MM:SS' format.</description>
        -- <example>'2008-08-17 00:00:00'</example>
    match_api_id INTEGER NOT NULL,
        -- <description>External match API identifier — unique ID assigned by the data source to link this row to the original match record.</description>
        -- <example>483129</example>
    home_team_api_id INTEGER NOT NULL,
        -- <description>Home team API identifier linking the match to the Team table — identifies which team was the home side in the match.</description>
        -- <example>9987</example>
        -- <fk> -> Team.team_api_id</fk>
    away_team_api_id INTEGER NOT NULL,
        -- <description>Away team API identifier — the team_api_id of the away team that played in the match.</description>
        -- <example>9993</example>
        -- <fk> -> Team.team_api_id</fk>
    home_team_goal INTEGER NOT NULL,
        -- <description>Home team goals scored — the total number of goals scored by the home side in the match (used to determine outcome and goal difference).</description>
        -- <example>1</example>
    away_team_goal INTEGER NOT NULL,
        -- <description>Away team goals — total number of goals scored by the away team in the match (the away side’s final score).</description>
        -- <example>1</example>
    home_player_X1 INTEGER NULL,
        -- <description>Home player 1 horizontal (X) pitch coordinate — the X (horizontal) location on the pitch for the player referenced by home_player_1, expressed in the dataset’s formation/position coordinate system; use together with home_player_Y1 to reconstruct the player’s starting position.</description>
        -- <example>1</example>
    home_player_X2 INTEGER NULL,
        -- <description>Home-team second player's horizontal (X) pitch coordinate — the X position for the second-listed home player in the starting lineup; pair with home_player_Y2 to form the player's on-pitch coordinates. Often NULL in this dataset.</description>
        -- <example>2</example>
    home_player_X3 INTEGER NULL,
        -- <description>Horizontal pitch X-coordinate for the third home player in the starting lineup, representing that player's left–right position on the field at match time; pairs with home_player_3 (player id) and home_player_Y3 (vertical coordinate).</description>
        -- <example>4</example>
    home_player_X4 INTEGER NULL,
        -- <description>Home team player 4 X coordinate — the pitch X (horizontal) position of the home team's fourth listed player in this match, typically paired with home_player_Y4 to form a (X,Y) location; often NULL when position data is unavailable.</description>
        -- <example>6</example>
    home_player_X5 INTEGER NULL,
        -- <description>Home player X-position for the fifth starting home player — the player's horizontal pitch coordinate (slot 5) used to record that player's starting location (e.g. 8).</description>
        -- <example>8</example>
    home_player_X6 INTEGER NULL,
        -- <description>Home player 6 X-coordinate — horizontal pitch location for the sixth listed home player (paired with home_player_Y6 to give the player's on-field position).</description>
        -- <example>2</example>
    home_player_X7 INTEGER NULL,
        -- <description>Starting X-coordinate on the pitch for the home team’s 7th listed player in the match (discrete pitch grid position).</description>
        -- <example>4</example>
    home_player_X8 INTEGER NULL,
        -- <description>Home team player‑slot 8 X‑coordinate (starting pitch position).</description>
        -- <example>6</example>
    home_player_X9 INTEGER NULL,
        -- <description>Home player 9 X-coordinate (horizontal pitch position) — the numeric horizontal position of the 9th listed home player; use together with home_player_Y9 to obtain the player's 2‑D on‑pitch location (many rows may be NULL).</description>
        -- <example>8</example>
    home_player_X10 INTEGER NULL,
        -- <description>Horizontal pitch grid coordinate for the home team's player in slot 10 — used together with home_player_Y10 to locate that player on the field (discrete/ordinal grid position representing a formation/starting location).</description>
        -- <example>4</example>
    home_player_X11 INTEGER NULL,
        -- <description>Home team 11th player's X (horizontal) pitch coordinate for the starting lineup — used together with home_player_Y11 to determine that player’s on-field starting position.</description>
        -- <example>6</example>
    away_player_X1 INTEGER NULL,
        -- <description>X-coordinate of the away-team player in slot 1 on the pitch (horizontal position), paired with away_player_Y1 and linked to the player id in away_player_1.</description>
        -- <example>1</example>
    away_player_X2 INTEGER NULL,
        -- <description>Horizontal pitch coordinate for the second away-listed player — the player's X (column) location on the field, used together with away_player_Y2 to determine that player's on-field/formation position.</description>
        -- <example>2</example>
    away_player_X3 INTEGER NULL,
        -- <description>Away player X-coordinate for the third away-listed player — the horizontal pitch position of the away team's third-listed player (use with away_player_Y3 to get that player’s starting location).</description>
        -- <example>4</example>
    away_player_X4 INTEGER NULL,
        -- <description>Away team fourth player's starting pitch X-coordinate (horizontal position); corresponds to the player listed in away_player_4.</description>
        -- <example>6</example>
    away_player_X5 INTEGER NULL,
        -- <description>Horizontal (X) pitch coordinate for the fifth away player — part of the away_player_X1–X11/Y1–Y11 set recording each away player's pitch position (e.g., starting/formation coordinates).</description>
        -- <example>8</example>
    away_player_X6 INTEGER NULL,
        -- <description>Away team player 6 X-coordinate on the pitch for the match — the horizontal position for the away team's sixth listed player (paired with away_player_Y6 to form the player's on-pitch location, typically for the starting lineup).</description>
        -- <example>2</example>
    away_player_X7 INTEGER NULL,
        -- <description>Away player 7 X-axis pitch coordinate — the horizontal position of the away team’s seventh listed player on the field (typically recorded at match kickoff).</description>
        -- <example>4</example>
    away_player_X8 INTEGER NULL,
        -- <description>Away player #8 horizontal pitch coordinate — the numeric X position for the away team’s eighth listed player (used together with away_player_Y8 and the away_player_8 id to locate that player on the pitch). May be NULL when position data is not available.</description>
        -- <example>6</example>
    away_player_X9 INTEGER NULL,
        -- <description>Away player 9 X-coordinate: the horizontal (X) pitch position of the away team’s ninth-listed player in the match lineup, used together with away_player_Y9 to represent the player’s starting 2‑D location.</description>
        -- <example>8</example>
    away_player_X10 INTEGER NULL,
        -- <description>Away team player 10 starting X-coordinate on the pitch (horizontal position) for the match — the recorded horizontal location for the away-side player occupying slot 10 in the lineup; often NULL when position data is not available.</description>
        -- <example>4</example>
    away_player_X11 INTEGER NULL,
        -- <description>Away player X-coordinate for the 11th listed away player — the horizontal pitch position (x) for the away team's #11, typically used together with away_player_Y11 to form the player's (x,y) location.</description>
        -- <example>6</example>
    home_player_Y1 INTEGER NULL,
        -- <description>Vertical (Y) pitch coordinate for the home team's first-listed player in a match, used together with home_player_X1 to form that player's on-field position.</description>
        -- <example>1</example>
    home_player_Y2 INTEGER NULL,
        -- <description>Y-coordinate of the second home player on the pitch (vertical field position); pairs with home_player_X2 to give that player’s on-field location.</description>
        -- <example>3</example>
    home_player_Y3 INTEGER NULL,
        -- <description>Home third player's Y-coordinate on the pitch (vertical position) at the recorded match snapshot; pairs with home_player_X3 to give that player's on-field location.</description>
        -- <example>3</example>
    home_player_Y4 INTEGER NULL,
        -- <description>Y-coordinate (vertical pitch position) of the home team’s fourth listed starting player at match kickoff or snapshot.</description>
        -- <example>3</example>
    home_player_Y5 INTEGER NULL,
        -- <description>Home player #5 vertical pitch position — the Y-axis coordinate (pitch zone) for the fifth-listed home player in the match lineup.</description>
        -- <example>3</example>
    home_player_Y6 INTEGER NULL,
        -- <description>Home player Y-coordinate (slot 6) — the match-level pitch Y position recorded for the sixth listed home player (location at kickoff/lineup).</description>
        -- <example>7</example>
    home_player_Y7 INTEGER NULL,
        -- <description>Y-coordinate of the home team’s seventh starting player on the pitch (vertical position in the starting formation); pair with home_player_X7 to obtain the player’s 2-D kickoff location. Unit/origin not specified.</description>
        -- <example>7</example>
    home_player_Y8 INTEGER NULL,
        -- <description>Y-coordinate of the home team's eighth listed player's pitch position, i.e. the player's vertical location on the field (paired with home_player_X8 to provide 2‑D pitch coordinates).</description>
        -- <example>7</example>
    home_player_Y9 INTEGER NULL,
        -- <description>Home player's Y-coordinate (vertical pitch position) for the ninth home-player slot in the match lineup.</description>
        -- <example>7</example>
    home_player_Y10 INTEGER NULL,
        -- <description>Y-coordinate of the home team’s 10th listed player’s pitch position.</description>
        -- <example>10</example>
    home_player_Y11 INTEGER NULL,
        -- <description>Starting home player #11 vertical pitch coordinate (Y) — the recorded Y position for the 11th listed home player.</description>
        -- <example>10</example>
    away_player_Y1 INTEGER NULL,
        -- <description>Y-coordinate (vertical pitch position) for away-team player in slot 1 — used together with away_player_X1 to record that player’s on-field location for the match.</description>
        -- <example>1</example>
    away_player_Y2 INTEGER NULL,
        -- <description>Away player Y coordinate — the vertical (Y) pitch position for the second-listed away player in the match lineup, typically used together with away_player_X2 and away_player_2 (the player id).</description>
        -- <example>3</example>
    away_player_Y3 INTEGER NULL,
        -- <description>Away player's Y (vertical) pitch coordinate for the third listed away starter — used with away_player_X3 (and away_player_3) to indicate that player's position/location on the pitch.</description>
        -- <example>3</example>
    away_player_Y4 INTEGER NULL,
        -- <description>Away player Y4 — Y-coordinate (vertical pitch position) for the away team’s fourth listed player in the match lineup.</description>
        -- <example>3</example>
    away_player_Y5 INTEGER NULL,
        -- <description>Away team player #5 Y-position on the pitch (vertical coordinate or zone) — numeric value indicating the away side’s fifth listed player’s pitch Y coordinate/zone at match time; used together with away_player_X5 (X coordinate) and away_player_5 (player id) to locate the player.</description>
        -- <example>3</example>
    away_player_Y6 INTEGER NULL,
        -- <description>Away player Y position (6th away starter) — the recorded Y‑axis / vertical position or formation/grid location of the away team's sixth listed player on the pitch.</description>
        -- <example>7</example>
    away_player_Y7 INTEGER NULL,
        -- <description>Y-coordinate of the away team's 7th starting player's pitch location at kickoff — used together with away_player_X7 and away_player_7 to form the player's 2‑D starting position on the field.</description>
        -- <example>7</example>
    away_player_Y8 INTEGER NULL,
        -- <description>Y-coordinate for the 8th away player's on-pitch position; used together with away_player_X8 to locate that away player's formation/position.</description>
        -- <example>7</example>
    away_player_Y9 INTEGER NULL,
        -- <description>Y-coordinate of the 9th away team's starting player on the pitch, describing that player’s vertical position on the field (used together with away_player_X9 to locate the player’s starting location).</description>
        -- <example>7</example>
    away_player_Y10 INTEGER NULL,
        -- <description>Away player #10 Y-coordinate on the pitch (starting vertical position), paired with away_player_X10 to give that player's on-field starting location.</description>
        -- <example>10</example>
    away_player_Y11 INTEGER NULL,
        -- <description>Y-coordinate of the 11th away player's on-field position, recorded for the match (pairs with away_player_X11 and away_player_11).</description>
        -- <example>10</example>
    home_player_1 INTEGER NULL,
        -- <description>Home team's first starting player identifier — the player_api_id occupying the home-side starting slot 1 (maps to Player.player_api_id). NULL when the lineup for this slot wasn't recorded.</description>
        -- <example>39890</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_2 INTEGER NULL,
        -- <description>Home team's second listed player identifier in the match lineup.</description>
        -- <example>67950</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_3 INTEGER NULL,
        -- <description>Home team's third starting player — the player_api_id for the player occupying home lineup slot 3 (references Player.player_api_id).</description>
        -- <example>38788</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_4 INTEGER NULL,
        -- <description>Fourth home-team lineup player — identifies the player listed in the home team’s fourth lineup slot (one of home_player_1 … home_player_11).</description>
        -- <example>38312</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_5 INTEGER NULL,
        -- <description>Home team's fifth starting-player identifier (player occupying home lineup slot 5).</description>
        -- <example>26235</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_6 INTEGER NULL,
        -- <description>Home team's sixth listed player in the match (identifier for the sixth home player in the recorded lineup).</description>
        -- <example>36393</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_7 INTEGER NULL,
        -- <description>Seventh home-team starter (player slot) — identifies the home team's seventh-listed starting player by their player_api_id.</description>
        -- <example>148286</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_8 INTEGER NULL,
        -- <description>Home team’s eighth starting player (lineup slot 8) — stores the player_api_id for the player listed in the home lineup (references Player.player_api_id).</description>
        -- <example>67898</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_9 INTEGER NULL,
        -- <description>Home team's ninth starting player — the player_api_id for the ninth-listed home starter in this match (foreign key to Player.player_api_id).</description>
        -- <example>26916</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_10 INTEGER NULL,
        -- <description>Home team starting player #10 identifier — the player_api_id for the tenth listed home starter (FK → Player.player_api_id).</description>
        -- <example>38801</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_11 INTEGER NULL,
        -- <description>Home team's eleventh starting player identifier — stores the Player.player_api_id for the home-side player assigned to the 11th position; NULL when not recorded.</description>
        -- <example>94289</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_1 INTEGER NULL,
        -- <description>Away team starting player 1 — the first-listed starter for the away team, stored as the player_api_id that identifies which Player started the match for the away side.</description>
        -- <example>34480</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_2 INTEGER NULL,
        -- <description>Away team's second starting player id (player listed in the away lineup slot #2).</description>
        -- <example>38388</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_3 INTEGER NULL,
        -- <description>Away team's third starting-lineup player identifier (the third slot in the away team's starting eleven).</description>
        -- <example>26458</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_4 INTEGER NULL,
        -- <description>Fourth away-team player in the match lineup (away-player slot #4 — stores the player's player_api_id; e.g. 13423).</description>
        -- <example>13423</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_5 INTEGER NULL,
        -- <description>Away team's fifth player slot in a match — the player_api_id identifying the away team's fifth listed player (references Player.player_api_id).</description>
        -- <example>38389</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_6 INTEGER NULL,
        -- <description>Away team's sixth-listed player identifier — the player_api_id for the sixth player recorded in the away team's lineup for this match (may be NULL when not recorded).</description>
        -- <example>38798</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_7 INTEGER NULL,
        -- <description>Away team's seventh listed player in the match lineup.</description>
        -- <example>30949</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_8 INTEGER NULL,
        -- <description>Away team player in lineup slot 8 — identifier referencing Player.player_api_id that indicates the player assigned to the away team’s #8 position in the match lineup.</description>
        -- <example>38253</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_9 INTEGER NULL,
        -- <description>Away team's ninth player identifier — the player_api_id for the ninth-listed away player in the match lineup (references Player.player_api_id).</description>
        -- <example>106013</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_10 INTEGER NULL,
        -- <description>Away-team tenth player identifier — the tenth-listed away-team player on the match roster.</description>
        -- <example>38383</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_11 INTEGER NULL,
        -- <description>Away team's 11th starting player in the match lineup (player_api_id referencing the Player table).</description>
        -- <example>46552</example>
        -- <fk> -> Player.player_api_id</fk>
    goal TEXT NULL,
        -- <description>XML-encoded goal event log for the match containing one or more recorded goal events (stored as text); may be NULL.</description>
        -- <example>'<goal><value><comment>n</comment><stats><goals>1</...goal</type><goal_type>n</goal_type></value></goal>'</example>
    shoton TEXT NULL,
        -- <description>XML-encoded list of shots-on-target events for the match, where each <value> entry holds nested per-event stats (e.g. blocked flag, player/time, event type and event id).</description>
        -- <example>'<shoton><value><stats><blocked>1</blocked></stats>...type>shoton</type><id>379466</id></value></shoton>'</example>
    shotoff TEXT NULL,
        -- <description>Match off-target shot events recorded as XML-like markup describing off-target shots and related attributes (counts, timestamps, event/player ids).</description>
        -- <example>'<shotoff><value><stats><shotoff>1</shotoff></stats...pe>shotoff</type><id>379573</id></value></shotoff>'</example>
    foulcommit TEXT NULL,
        -- <description>Match foul events log (XML) that records fouls, counts and related event metadata (e.g. event id, type, optional comments and stats).</description>
        -- <example>'<foulcommit><value><stats><foulscommitted>1</fouls...lcommit</type><id>379571</id></value></foulcommit>'</example>
    card TEXT NULL,
        -- <description>match disciplinary (card) events recorded as an XML string, with one or more <value> entries describing each card (yellow/red) and related metadata (player, time/minute, comment, counts, event id).</description>
        -- <example>'<card><value><comment>y</comment><stats><ycards>1<.../n><type>card</type><id>379547</id></value></card>'</example>
    cross TEXT NULL,
        -- <description>Match crossing events — an XML-like event log of crosses into the opposition area, recording per-event counts, event ids and other nested stats.</description>
        -- <example>'<cross><value><stats><crosses>1</crosses></stats><...><type>cross</type><id>379540</id></value></cross>'</example>
    corner TEXT NULL,
        -- <description>Corner-kick event log — XML-style event records listing corner kicks and per-event stats</description>
        -- <example>'<corner><value><stats><corners>1</corners></stats>...type>corner</type><id>379460</id></value></corner>'</example>
    possession TEXT NULL,
        -- <description>match possession information as XML-like text containing overall possession percentage and optional per-event/team details (often stored in a <comment> or <stats> tag).</description>
        -- <example>'<possession><value><comment>56</comment><event_inc...special</type><id>379575</id></value></possession>'</example>
    B365H REAL NULL,
        -- <description>Bet365 home-win decimal odds — the bookmaker Bet365’s decimal odds for a home-team victory in the match (lower values indicate a stronger favorite).</description>
        -- <example>1.730</example>
    B365D REAL NULL,
        -- <description>Bet365 draw odds — the bookmaker Bet365's decimal odds for the match finishing as a draw (typically recorded pre-match).</description>
        -- <example>3.400</example>
    B365A REAL NULL,
        -- <description>Bet365 away-win decimal odds — pre-match odds from the Bet365 bookmaker representing the payout multiplier for an away-team victory.</description>
        -- <example>5.000</example>
    BWH REAL NULL,
        -- <description>Home-win betting odds from the BWH bookmaker (decimal/European odds, typically recorded pre-match).</description>
        -- <example>1.750</example>
    BWD REAL NULL,
        -- <description>Bet&Win (BWH) draw odds — the bookmaker's pre-match decimal odds for the game ending in a draw.</description>
        -- <example>3.350</example>
    BWA REAL NULL,
        -- <description>Away-team decimal betting odds from the BWA bookmaker (Bet&Win/Bwin). Represents the bookmaker’s quoted decimal odd for the away team to win — useful for computing market-implied win probabilities or comparing bookmaker lines. Example: 4.2 (implied probability ≈ 1/4.2 ≈ 23.8%).</description>
        -- <example>4.200</example>
    IWH REAL NULL,
        -- <description>Interwetten home win odds — the odds quoted by the Interwetten bookmaker for a home-team victory in the match.</description>
        -- <example>1.850</example>
    IWD REAL NULL,
        -- <description>Interwetten draw odds (decimal) — the decimal betting odds offered by the Interwetten bookmaker for the match ending in a draw (null when not available).</description>
        -- <example>3.200</example>
    IWA REAL NULL,
        -- <description>Away-team win decimal odds from the Interwetten bookmaker for the match (odds for an away victory).</description>
        -- <example>3.500</example>
    LBH REAL NULL,
        -- <description>Ladbrokes home-win betting odds — pre-match decimal odds for a home-team victory offered by the Ladbrokes bookmaker.</description>
        -- <example>1.800</example>
    LBD REAL NULL,
        -- <description>Ladbrokes draw odds (pre-match decimal odds for the match outcome being a draw).</description>
        -- <example>3.300</example>
    LBA REAL NULL,
        -- <description>Ladbrokes decimal odds for an away-team win (bookmaker pre-match/closing odds).</description>
        -- <example>3.750</example>
    PSH REAL NULL,
        -- <description>Home-team decimal odds from bookmaker 'PS' (PSH), representing the quoted odds for a home win.</description>
        -- <example>5.100</example>
    PSD REAL NULL,
        -- <description>Pinnacle (PS) bookmaker draw odds for the match — decimal odds offered for a draw outcome.</description>
        -- <example>3.820</example>
    PSA REAL NULL,
        -- <description>PS (Pinnacle Sports) away-team decimal odds for the match — the bookmaker's offered odds for an away win.</description>
        -- <example>1.760</example>
    WHH REAL NULL,
        -- <description>William Hill decimal odds for a home-team win (bookmaker pre-match odds for the match outcome).</description>
        -- <example>1.700</example>
    WHD REAL NULL,
        -- <description>William Hill draw odds for the match — the bookmaker’s decimal odds for the draw outcome (paired with WHH and WHA for home/draw/away).</description>
        -- <example>3.300</example>
    WHA REAL NULL,
        -- <description>William Hill decimal odds for an away-team win (the bookmaker’s pre-match odds for the away side to win; e.g., 4.33).</description>
        -- <example>4.330</example>
    SJH REAL NULL,
        -- <description>Stan James bookmaker's quoted decimal odds for the home team to win the match (home-win market).</description>
        -- <example>1.900</example>
    SJD REAL NULL,
        -- <description>Stan James draw betting odds for the match (bookmaker Stan James; decimal odds for a draw outcome).</description>
        -- <example>3.300</example>
    SJA REAL NULL,
        -- <description>Stan James bookmaker's quoted decimal odds for an away-team win in the match (i.e., the market price implying the probability of an away victory).</description>
        -- <example>4.000</example>
    VCH REAL NULL,
        -- <description>Victor Chandler pre-match decimal odds for a home-team win.</description>
        -- <example>1.650</example>
    VCD REAL NULL,
        -- <description>VC draw odds — decimal betting odds from bookmaker “VC” representing the offered payout for a match draw.</description>
        -- <example>3.400</example>
    VCA REAL NULL,
        -- <description>Victor Chandler (VC) bookmaker decimal odds for an away-team win in the match — a payout multiplier where lower values imply a higher implied probability.</description>
        -- <example>4.500</example>
    GBH REAL NULL,
        -- <description>Gamebookers home-win decimal odds — pre-match bookmaker odds quoted by Gamebookers for a home-team victory (higher values indicate a larger payout/longer shot).</description>
        -- <example>1.780</example>
    GBD REAL NULL,
        -- <description>Gamebookers (GB) bookmaker odds for a draw outcome in the match.</description>
        -- <example>3.250</example>
    GBA REAL NULL,
        -- <description>Gamebookers away-win decimal odds (bookmaker odds for the away team to win). May be NULL if odds are unavailable.</description>
        -- <example>4.000</example>
    BSH REAL NULL,
        -- <description>Home-win betting odds from bookmaker 'BS' (decimal format).</description>
        -- <example>1.730</example>
    BSD REAL NULL,
        -- <description>Draw odds quoted by the 'BS' bookmaker for the match (the bookmaker's decimal odds for a draw outcome).</description>
        -- <example>3.400</example>
    BSA REAL NULL,
        -- <description>Away-team decimal pre-match odds provided by the “BS” bookmaker (the away-side counterpart to BSH and BSD); larger values imply a lower implied probability of an away win.</description>
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

/*
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
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Player table primary key — unique identifier for each player row.</description>
        -- <example>3879</example>
    player_api_id INTEGER NOT NULL,
        -- <description>Player API identifier used as the stable external player ID and join key across tables (referenced by Match and Player_Attributes); distinct from the table's internal primary key.</description>
        -- <example>2625</example>
    player_name TEXT NOT NULL,
        -- <description>Player name — the player's full name used to identify the individual within the dataset and when joining to other tables.</description>
        -- <example>'Aaron Appindangoye'</example>
    player_fifa_api_id INTEGER NOT NULL,
        -- <description>FIFA API player identifier — an external FIFA player ID used to link this player to FIFA-specific records (e.g., Player_Attributes and other FIFA datasets).</description>
        -- <example>2</example>
    birthday TEXT NOT NULL,
        -- <description>Player date of birth — the player's birth date, used to compute age and to compare or sort players by age (an earlier date indicates an older player).</description>
        -- <example>'1992-02-29 00:00:00'</example>
    height INTEGER NOT NULL,
        -- <description>Player height in centimeters (recorded player height; sample values show decimal precision even though the column is declared integer).</description>
        -- <example>182.880</example>
    weight INTEGER NOT NULL
        -- <description>Player weight — the recorded weight of the player (unit not specified in the schema).</description>
        -- <example>187</example>
);

/*
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
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Player-attributes record identifier — unique identifier for each row in the Player_Attributes table.</description>
        -- <example>1</example>
    player_fifa_api_id INTEGER NOT NULL,
        -- <description>FIFA player identifier — the official FIFA API id that identifies the player referenced by this attribute record.</description>
        -- <example>218353</example>
        -- <fk> -> Player.player_fifa_api_id</fk>
    player_api_id INTEGER NOT NULL,
        -- <description>Player API identifier linking a Player_Attributes record to a specific player (refers to Player.player_api_id).</description>
        -- <example>505942</example>
        -- <fk> -> Player.player_api_id</fk>
    date TEXT NOT NULL,
        -- <description>Attribute snapshot timestamp — the date and time when this player-attributes record was recorded (format: YYYY-MM-DD HH:MM:SS). Useful for ordering and tracking changes to a player's attributes over time.</description>
        -- <example>'2016-02-18 00:00:00'</example>
    overall_rating INTEGER NULL,
        -- <description>Player overall rating — FIFA’s composite score representing the player’s assessed current ability at the time the attribute record was taken.</description>
        -- <example>67</example>
    potential INTEGER NULL,
        -- <description>Player potential score — a FIFA-assigned rating (0–100) estimating how much a player's ability is expected to improve; higher values indicate greater future potential.</description>
        -- <example>71</example>
    preferred_foot TEXT NULL,
        -- <description>Player's preferred foot — indicates which foot the player favors when performing actions (e.g., shooting, passing, crossing).</description>
        -- <values>{'left', 'right'}</values>
    attacking_work_rate TEXT NULL,
        -- <description>Player attacking work rate — categorical indicator of a player's propensity to join attacking actions; higher settings (e.g. “high”) mean frequent involvement in attacks, “medium” indicates occasional participation, and “low” means the player tends to hold position.</description>
        -- <values>{'None', 'high', 'le', 'low', 'medium', 'norm', 'stoc', 'y'}</values>
    defensive_work_rate TEXT NULL,
        -- <description>Defensive work rate — the player's typical defensive effort and positioning tendency; a higher defensive work rate means the player stays deeper and prioritizes defending, a medium rate indicates selective defensive involvement, and a lower rate means the player pushes forward and participates more in attacks.</description>
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '_0', 'ean', 'es', 'high', 'low', 'medium', 'o', 'ormal', 'tocky'}</values>
    crossing INTEGER NULL,
        -- <description>Player crossing ability score — a FIFA-derived measure of a player's tendency and accuracy when delivering crosses into the penalty area; higher values indicate better/more frequent crossing.</description>
        -- <example>49</example>
    finishing INTEGER NULL,
        -- <description>Player finishing ability — a FIFA-derived score indicating a player's proficiency at converting goal-scoring chances (higher = better).</description>
        -- <example>44</example>
    heading_accuracy INTEGER NULL,
        -- <description>Player heading accuracy — a FIFA-derived rating that measures a player's effectiveness at directing headers (higher values indicate stronger aerial ability).</description>
        -- <example>71</example>
    short_passing INTEGER NULL,
        -- <description>Player short-passing ability score (FIFA-derived)</description>
        -- <example>61</example>
    volleys INTEGER NULL,
        -- <description>Player volley ability score (0–100) indicating how well a player strikes the ball on the volley; higher values denote better volley technique, power and accuracy.</description>
        -- <example>44</example>
    dribbling INTEGER NULL,
        -- <description>Player dribbling score — a FIFA-calculated measure of a player's ability to control the ball and beat opponents while advancing play.</description>
        -- <example>51</example>
    curve INTEGER NULL,
        -- <description>Player's shot-curving ability as assessed by FIFA (higher values indicate greater ability to bend the ball).</description>
        -- <example>45</example>
    free_kick_accuracy INTEGER NULL,
        -- <description>Free-kick accuracy score for the player (FIFA-derived, 0–100; higher = better).</description>
        -- <example>39</example>
    long_passing INTEGER NULL,
        -- <description>Player long-passing ability score (FIFA-calculated; higher is better, typically 0–100).</description>
        -- <example>64</example>
    ball_control INTEGER NULL,
        -- <description>Player ball control rating — a FIFA-derived measure of a player’s ability to control and retain the ball (first touch and general ball-handling); higher values indicate better technical control.</description>
        -- <example>49</example>
    acceleration INTEGER NULL,
        -- <description>Player acceleration rating (FIFA 0–100) — an index estimating how quickly a player reaches top speed; higher values indicate a quicker initial burst.</description>
        -- <example>60</example>
    sprint_speed INTEGER NULL,
        -- <description>Player sprint speed rating (FIFA-derived) — a FIFA-calculated score representing a player's sprinting pace and short-distance acceleration.</description>
        -- <example>64</example>
    agility INTEGER NULL,
        -- <description>Player agility rating — a FIFA-derived measure of a player's quickness and ability to change direction; higher values indicate greater nimbleness and lateral speed.</description>
        -- <example>59</example>
    reactions INTEGER NULL,
        -- <description>FIFA-derived player reaction rating indicating how quickly a player responds to in-game events; higher values mean faster/better reactions.</description>
        -- <example>47</example>
    balance INTEGER NULL,
        -- <description>Player balance rating — a FIFA-derived score indicating a player's physical stability and ability to maintain footing/control under pressure.</description>
        -- <example>65</example>
    shot_power INTEGER NULL,
        -- <description>Player shot power rating — FIFA-provided measure of the force a player typically puts behind shots.</description>
        -- <example>55</example>
    jumping INTEGER NULL,
        -- <description>Player jumping score — a FIFA-derived measure (higher values indicate better vertical leap and aerial reach).</description>
        -- <example>58</example>
    stamina INTEGER NULL,
        -- <description>Player stamina score — a FIFA-derived measure of a player’s endurance and ability to sustain running intensity and physical performance throughout a match (higher values indicate greater endurance and resistance to fatigue).</description>
        -- <example>54</example>
    strength INTEGER NULL,
        -- <description>Player strength rating — a FIFA-derived measure of a player's physical power and effectiveness in physical duels; higher values indicate a more physically dominant player.</description>
        -- <example>76</example>
    long_shots INTEGER NULL,
        -- <description>Long-shots rating — a FIFA-provided attribute that reflects a player’s ability and accuracy when shooting from long range; higher values indicate stronger long-range shooting.</description>
        -- <example>35</example>
    aggression INTEGER NULL,
        -- <description>Player aggression rating — a FIFA-derived score indicating a player's tendency to engage opponents and make aggressive challenges.</description>
        -- <example>71</example>
    interceptions INTEGER NULL,
        -- <description>Player interceptions score — a FIFA-derived measure of a player's ability to read the game and intercept opposition passes; higher values indicate stronger interception skill.</description>
        -- <example>70</example>
    positioning INTEGER NULL,
        -- <description>Player positioning score — FIFA's assessment of a player's positional sense on the pitch; higher values indicate better positioning.</description>
        -- <example>45</example>
    vision INTEGER NULL,
        -- <description>Player vision score — a FIFA‑calculated measure of a player’s ability to spot teammates, identify passing opportunities and create chances through vision and decision‑making.</description>
        -- <example>54</example>
    penalties INTEGER NULL,
        -- <description>Penalty-taking ability rating (FIFA-calculated)</description>
        -- <example>48</example>
    marking INTEGER NULL,
        -- <description>Player marking score — a FIFA-derived measure of a player’s defensive marking ability (0–100, higher is better).</description>
        -- <example>65</example>
    standing_tackle INTEGER NULL,
        -- <description>Standing-tackle ability score — a FIFA-derived measure of a player’s effectiveness at winning or contesting tackles while remaining on their feet; higher values indicate better performance.</description>
        -- <example>69</example>
    sliding_tackle INTEGER NULL,
        -- <description>Sliding tackle rating — a FIFA-calculated defensive attribute that measures a player's effectiveness at performing sliding tackles.</description>
        -- <example>69</example>
    gk_diving INTEGER NULL,
        -- <description>Goalkeeper diving rating — a FIFA-derived score indicating a goalkeeper's ability to dive and reach shots.</description>
        -- <example>6</example>
    gk_handling INTEGER NULL,
        -- <description>Goalkeeper handling score — a FIFA-derived rating of a goalkeeper's ability to catch, hold and control shots, crosses and loose balls.</description>
        -- <example>11</example>
    gk_kicking INTEGER NULL,
        -- <description>Goalkeeper kicking ability — FIFA-derived score indicating a goalkeeper's kicking power and distribution accuracy.</description>
        -- <example>10</example>
    gk_positioning INTEGER NULL,
        -- <description>Goalkeeper positioning score — a FIFA-assigned rating that reflects a goalkeeper's ability to position themselves during play.</description>
        -- <example>8</example>
    gk_reflexes INTEGER NULL,
        -- <description>Goalkeeper reflexes rating (FIFA-derived, 0–100) — a numeric score where higher values indicate quicker reaction/reflex ability when playing as a goalkeeper.</description>
        -- <example>8</example>
    FOREIGN KEY (player_api_id) REFERENCES Player(player_api_id),
    FOREIGN KEY (player_fifa_api_id) REFERENCES Player(player_fifa_api_id)
);

/*
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
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for each team.</description>
        -- <example>31446</example>
    team_api_id INTEGER NOT NULL,
        -- <description>Team API identifier — the dataset’s stable team ID used to link this team record to other tables (e.g., referenced by Match.home_team_api_id/away_team_api_id and Team_Attributes.team_api_id).</description>
        -- <example>1601</example>
    team_fifa_api_id INTEGER NULL,
        -- <description>FIFA API team identifier linking the team record to FIFA's external dataset.</description>
        -- <example>673</example>
    team_long_name TEXT NOT NULL,
        -- <description>Team long name — the club's full or official name used for display (for example, 'KRC Genk', 'Queens Park Rangers', 'Sporting CP').</description>
        -- <example>'KRC Genk'</example>
    team_short_name TEXT NOT NULL
        -- <description>Team short name — abbreviated team name or short code used for display and labeling (e.g., 'GEN', 'BAC', 'ZUL').</description>
        -- <example>'GEN'</example>
);

/*
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
    id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique record identifier for a Team_Attributes row (identifies a single team attribute snapshot).</description>
        -- <example>1</example>
    team_fifa_api_id INTEGER NOT NULL,
        -- <description>Team FIFA API identifier — the FIFA-based identifier for the team that these attributes describe (e.g. 434).</description>
        -- <example>434</example>
        -- <fk> -> Team.team_fifa_api_id</fk>
    team_api_id INTEGER NOT NULL,
        -- <description>Team API identifier linking a team-attributes record to the Team table (references Team.team_api_id).</description>
        -- <example>9930</example>
        -- <fk> -> Team.team_api_id</fk>
    date TEXT NOT NULL,
        -- <description>Recording date of the team attributes entry — the timestamp when those attributes were measured, used for versioning and temporal analysis.</description>
        -- <values>{'2010-02-22 00:00:00', '2011-02-22 00:00:00', '2012-02-22 00:00:00', '2013-09-20 00:00:00', '2014-09-19 00:00:00', '2015-09-10 00:00:00'}</values>
    buildUpPlaySpeed INTEGER NOT NULL,
        -- <description>Build-up play speed rating indicating how quickly a team constructs attacking moves.</description>
        -- <example>60</example>
    buildUpPlaySpeedClass TEXT NOT NULL,
        -- <description>Build-up play speed class — categorical label for a team’s attack build-up speed, derived from the numeric buildUpPlaySpeed by grouping scores into ranges: 1–33 (Slow), 34–66 (Balanced), 67–100 (Fast).</description>
        -- <values>{'Balanced', 'Fast', 'Slow'}</values>
    buildUpPlayDribbling INTEGER NULL,
        -- <description>Build-up play dribbling tendency — a team-level score indicating how often a team uses dribbling during build-up play (higher values mean more frequent dribbling).</description>
        -- <example>48</example>
    buildUpPlayDribblingClass TEXT NOT NULL,
        -- <description>Build-up play dribbling class — a qualitative label for a team’s dribbling tendency during build-up play; corresponds to low/medium/high bands of the underlying dribbling score (approximately 1–33, 34–66, 67–100).</description>
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    buildUpPlayPassing INTEGER NOT NULL,
        -- <description>Team build-up passing score — indicates a team's passing behavior during build-up play, reflecting typical passing distance and level of teammate support (higher = longer/riskier passes and more support).</description>
        -- <example>50</example>
    buildUpPlayPassingClass TEXT NOT NULL,
        -- <description>Build-up passing style class indicating the team’s typical passing length and level of teammate support used when progressing the ball in build-up play.</description>
        -- <values>{'Long', 'Mixed', 'Short'}</values>
    buildUpPlayPositioningClass TEXT NOT NULL,
        -- <description>Build-up positioning class — indicates how structured or free a team’s positioning is during build-up play in the first two-thirds of the pitch (e.g. 'Organised' = structured positioning, 'Free Form' = fluid positioning).</description>
        -- <values>{'Free Form', 'Organised'}</values>
    chanceCreationPassing INTEGER NOT NULL,
        -- <description>Chance-creation passing score — a team's tendency to use risky or creative passes when creating scoring opportunities; captures pass-decision risk and supporting runs (higher values indicate more risk/creativity).</description>
        -- <example>60</example>
    chanceCreationPassingClass TEXT NOT NULL,
        -- <description>Chance-creation passing risk class — categorizes how conservative or risky a team’s passing is when creating scoring opportunities (higher class means more risk/forward/long passes; lower means safer/shorter passes).</description>
        -- <values>{'Normal', 'Risky', 'Safe'}</values>
    chanceCreationCrossing INTEGER NOT NULL,
        -- <description>Crossing tendency — a numeric score indicating how frequently a team delivers crosses into the penalty area to create goal-scoring chances.</description>
        -- <example>65</example>
    chanceCreationCrossingClass TEXT NOT NULL,
        -- <description>Crossing tendency class for a team’s chance creation — a categorical label summarizing how frequently the team delivers crosses into the opponent’s penalty area (interpreted as low / medium / high crossing frequency).</description>
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    chanceCreationShooting INTEGER NOT NULL,
        -- <description>Team shooting chance-creation tendency — measures how frequently the team generates shooting opportunities (higher = more frequent).</description>
        -- <example>55</example>
    chanceCreationShootingClass TEXT NOT NULL,
        -- <description>Chance-creation shooting class — a coarse label for how frequently a team generates shots when creating chances, mapped to numeric bands (Little ≈ 1–33, Normal ≈ 34–66, Lots ≈ 67–100).</description>
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    chanceCreationPositioningClass TEXT NOT NULL,
        -- <description>Final-third positioning class — indicates how structured versus free the team's movement is when creating scoring chances in the attacking third.</description>
        -- <values>{'Free Form', 'Organised'}</values>
    defencePressure INTEGER NOT NULL,
        -- <description>team defensive pressure score — measures how high up the pitch the team applies pressure (higher values indicate a more aggressive, higher pressing line).</description>
        -- <example>50</example>
    defencePressureClass TEXT NOT NULL,
        -- <description>Defensive pressure class — categorical label describing a team’s typical pressing height, derived from the numeric defencePressure score; the score is mapped into three ordered levels (approx. 1–33, 34–66, 67–100).</description>
        -- <values>{'Deep', 'High', 'Medium'}</values>
    defenceAggression INTEGER NOT NULL,
        -- <description>Team defensive aggression — a numeric score indicating how aggressively the team challenges and presses the ball carrier (higher values = more aggressive).</description>
        -- <example>55</example>
    defenceAggressionClass TEXT NOT NULL,
        -- <description>Defensive aggression class — categorical label indicating a team’s typical level of defensive aggression (maps to low/medium/high). Used to interpret the numeric defenceAggression score when analysing a team’s defensive tactics.</description>
        -- <values>{'Contain', 'Double', 'Press'}</values>
    defenceTeamWidth INTEGER NOT NULL,
        -- <description>Team defensive width — numeric score that measures how wide the team’s defensive shape is and how far the defense shifts toward the ball (higher = wider). Often used alongside defenceTeamWidthClass to categorize the width.</description>
        -- <example>45</example>
    defenceTeamWidthClass TEXT NOT NULL,
        -- <description>Defence team-width class — a qualitative label for how wide a team defends on the pitch, derived from the team's numeric defence-team-width score (lower scores map to narrower defensive setups; higher scores map to wider setups).</description>
        -- <values>{'Narrow', 'Normal', 'Wide'}</values>
    defenceDefenderLineClass TEXT NOT NULL,
        -- <description>Defender-line strategy — the team's defensive shape and tactics that determine how the defensive line is positioned and organized.</description>
        -- <values>{'Cover', 'Offside Trap'}</values>
    FOREIGN KEY (team_api_id) REFERENCES Team(team_api_id),
    FOREIGN KEY (team_fifa_api_id) REFERENCES Team(team_fifa_api_id)
);
```