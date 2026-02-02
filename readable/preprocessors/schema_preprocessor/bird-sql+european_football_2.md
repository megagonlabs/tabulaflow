```sql
-- Database: european_football_2

-- Table: Country (11 rows)
CREATE TABLE Country (
    id INTEGER NULL PRIMARY KEY,
        -- <description>Unique identifier for a country in this dataset.</description>
        -- <example>1</example>
    name TEXT NULL
        -- <description>Country name — the country's common name (e.g., Belgium, England, France).</description>
        -- <example>'Belgium'</example>
);

-- Table: League (11 rows)
CREATE TABLE League (
    id INTEGER NULL PRIMARY KEY,
        -- <description>League identifier — unique id for each league (primary key).</description>
        -- <example>1</example>
    country_id INTEGER NULL,
        -- <description>Country reference (foreign key to Country.id) — identifies the country associated with the league; used to join League records to the Country table.</description>
        -- <example>1</example>
        -- <fk> -> country.id</fk>
    name TEXT NULL,
        -- <description>League name — the full official title used to identify the competition (e.g., England Premier League, Italy Serie A).</description>
        -- <example>'Belgium Jupiler League'</example>
    FOREIGN KEY (country_id) REFERENCES country(id)
);

-- Table: Match (25979 rows)
CREATE TABLE Match (
    id INTEGER NULL PRIMARY KEY,
        -- <description>Match identifier — unique identifier for each recorded match, used to reference and join match-level records across tables.</description>
        -- <example>4769</example>
    country_id INTEGER NULL,
        -- <description>Match country identifier — the country where the match was played.</description>
        -- <example>1</example>
        -- <fk> -> Country.id</fk>
    league_id INTEGER NULL,
        -- <description>League associated with the match</description>
        -- <example>1</example>
        -- <fk> -> League.id</fk>
    season TEXT NULL,
        -- <description>Match season — the competition season for the match, recorded as a year-range string (e.g., "2014/2015").</description>
        -- <values>{'2008/2009', '2009/2010', '2010/2011', '2011/2012', '2012/2013', '2013/2014', '2014/2015', '2015/2016'}</values>
    stage INTEGER NULL,
        -- <description>Matchday number — identifies the round of the competition a fixture belongs to (used to order matches within a season).</description>
        -- <example>1</example>
    date TEXT NULL,
        -- <description>Match kickoff datetime — the recorded match timestamp (format: YYYY-MM-DD HH:MM:SS). Populated for all rows (25,979) with values ranging from 2008-07-18 to 2016-05-25.</description>
        -- <example>'2008-08-17 00:00:00'</example>
    match_api_id INTEGER NULL,
        -- <description>External match identifier from the source API — a unique, non‑null ID that maps each Match row to the original data provider (distinct from the table primary key).</description>
        -- <example>483129</example>
    home_team_api_id INTEGER NULL,
        -- <description>Home team API identifier — foreign key to Team.team_api_id that identifies the team designated as the home side for each match (present for all matches; 299 distinct teams in this dataset).</description>
        -- <example>9987</example>
        -- <fk> -> Team.team_api_id</fk>
    away_team_api_id INTEGER NULL,
        -- <description>Away team API identifier — identifies which team played as the away side in the match.</description>
        -- <example>9993</example>
        -- <fk> -> Team.team_api_id</fk>
    home_team_goal INTEGER NULL,
        -- <description>Number of goals scored by the home team in the match (final/home-side score).</description>
        -- <example>1</example>
    away_team_goal INTEGER NULL,
        -- <description>Away team goals scored in the match.</description>
        -- <example>1</example>
    home_player_X1 INTEGER NULL,
        -- <description>Home-player X1 slot code — a small undocumented categorical flag associated with the first home-player X-slot (likely a positional/role indicator). Most non-null values are 1; very few rows contain 0 or 2, and 1,821 rows are NULL.</description>
        -- <example>1</example>
    home_player_X2 INTEGER NULL,
        -- <description>Home player 2 horizontal position index — a small integer code representing the second starting home player's X (left–right) location on the match formation/grid; used together with home_player_Y2 and home_player_2 to locate the player on the pitch (observed values 0–8).</description>
        -- <example>2</example>
    home_player_X3 INTEGER NULL,
        -- <description>Home player 3 X-position code — a small integer code indicating the horizontal/pitch-zone location for the third-listed home starter (corresponds to home_player_3). Observed as discrete zone codes (mostly 4, with values up to 8); present in ~24,147 of 25,979 matches.</description>
        -- <example>4</example>
    home_player_X4 INTEGER NULL,
        -- <description>Home player 4 X-position on the pitch (horizontal zone for the player listed in home_player_4) — small integer code used with home_player_Y4 to record the player’s on-field X coordinate/zone; values mainly 6 (modal), range ~2–8, with ~7% nulls.</description>
        -- <example>6</example>
    home_player_X5 INTEGER NULL,
        -- <description>Home player 5 X-coordinate (horizontal pitch location) — field position index for the fifth listed home player; used with home_player_Y5 to indicate that player's starting/formation location. Observed values range 1–9; ~7.1% null (1,832 of 25,979).</description>
        -- <example>8</example>
    home_player_X6 INTEGER NULL,
        -- <description>Home player's X-coordinate (horizontal pitch position) for the sixth starting/home player — indicates that player's location on a coarse formation grid; paired with home_player_Y6 (vertical coordinate) and home_player_6 (player id).</description>
        -- <example>2</example>
    home_player_X7 INTEGER NULL,
        -- <description>Home player 7 X position on the pitch — a discrete ordinal (values 1–9) indicating the horizontal/location bucket for the seventh listed home player in the starting lineup; intended to be used together with home_player_Y7 and linked to home_player_7 (the player id). Populated in most matches (≈93%) with 9 distinct values.</description>
        -- <example>4</example>
    home_player_X8 INTEGER NULL,
        -- <description>Home player 8 X-coordinate — coarse horizontal pitch position index for the home team's starting player listed in home_player_8; paired with home_player_Y8 to give a 2‑D starting location on a coarse 1–11 grid. Populated for most matches (≈24,147 of 25,979).</description>
        -- <example>6</example>
    home_player_X9 INTEGER NULL,
        -- <description>Home player 9 horizontal pitch coordinate — discrete X position (values 1–9) for the ninth listed starting home player; nullable (~7% NULL).</description>
        -- <example>8</example>
    home_player_X10 INTEGER NULL,
        -- <description>X-coordinate (position slot) for the tenth home player in the starting lineup — a small discrete position code typically paired with home_player_Y10 to give the on-pitch location. Populated in 24,147 of 25,979 matches; 9 distinct values with range 1–9 (mean ≈ 5.39).</description>
        -- <example>4</example>
    home_player_X11 INTEGER NULL,
        -- <description>Home player 11 X-coordinate on the pitch for the starting lineup (horizontal position).</description>
        -- <example>6</example>
    away_player_X1 INTEGER NULL,
        -- <description>Away player 1 X-position index (formation/pitch X‑axis slot for the away team's first listed player).</description>
        -- <example>1</example>
    away_player_X2 INTEGER NULL,
        -- <description>Away player 2 starting pitch X-position (formation/zone index) — enumerated horizontal field zone indicating the player's starting location (values observed 1–8).</description>
        -- <example>2</example>
    away_player_X3 INTEGER NULL,
        -- <description>Away player's X-axis pitch coordinate for the third away-player slot (position 3 in the away lineup). Used together with away_player_3 (player id) and away_player_Y3 to record that player's on-pitch location; integer values observed from 2–9 with about 7% NULLs.</description>
        -- <example>4</example>
    away_player_X4 INTEGER NULL,
        -- <description>Away player #4 X-position in the match formation grid (horizontal coordinate for the fourth listed away starter). Often paired with away_player_Y4 to give the player’s (X,Y) pitch position; values observed from 1–8, mostly populated.</description>
        -- <example>6</example>
    away_player_X5 INTEGER NULL,
        -- <description>Away team player #5 X-coordinate on the pitch — the column/grid-based horizontal position recorded for the fifth away player in a match.</description>
        -- <example>8</example>
    away_player_X6 INTEGER NULL,
        -- <description>Away team's sixth-listed player's horizontal pitch zone (coarse X coordinate indicating the away player in lineup slot 6). Common values cluster in a few zones; some rows are missing.</description>
        -- <example>2</example>
    away_player_X7 INTEGER NULL,
        -- <description>Away player #7 formation X-position index — encodes the away team’s X-axis formation/slot for the seventh listed away player; pairs with away_player_Y7 (Y-coordinate) and away_player_7 (player id).</description>
        -- <example>4</example>
    away_player_X8 INTEGER NULL,
        -- <description>Away player 8 X-axis pitch zone — the horizontal/longitudinal position code for the away team’s 8th-listed player on the pitch (observed values ~1–9; many rows are NULL).</description>
        -- <example>6</example>
    away_player_X9 INTEGER NULL,
        -- <description>Away team's 9th player's X-axis formation position (ordinal grid column for the away_player_9 lineup slot).</description>
        -- <example>8</example>
    away_player_X10 INTEGER NULL,
        -- <description>Away team’s #10 player pitch X-position index — the small integer X coordinate for the away team’s tenth starting player (paired with away_player_10 and away_player_Y10 to give the 2D position). Often populated (≈92.9% of matches); a small number of rows show the X value without a matching away_player_10 or vice versa, so joins should handle those mismatches.</description>
        -- <example>4</example>
    away_player_X11 INTEGER NULL,
        -- <description>Away team's 11th player's horizontal pitch position (X-coordinate index); a small set of discrete zone codes (observed values 3–8) typically used together with away_player_Y11 to get the on‑pitch coordinates for the away team's #11.</description>
        -- <example>6</example>
    home_player_Y1 INTEGER NULL,
        -- <description>Home player 1 Y-axis pitch zone (small integer code for the vertical/row position of the home team’s starting player in slot 1).</description>
        -- <example>1</example>
    home_player_Y2 INTEGER NULL,
        -- <description>Home player Y-coordinate (second listed starter) — the second home player's vertical/pitch-zone index used to record their starting position on a small integer grid. Mostly populated (24,158 of 25,979 rows); values are predominantly 3, with a few 0s and ~1,821 NULLs.</description>
        -- <example>3</example>
    home_player_Y3 INTEGER NULL,
        -- <description>Y-position of the third home player (formation grid slot) — indicates the Y-axis slot for the third listed home player in the match formation; mostly value 3 (24,146 of 25,979 rows), one occurrence of 5, and 1,832 NULLs.</description>
        -- <example>3</example>
    home_player_Y4 INTEGER NULL,
        -- <description>Home team's fourth player's Y-position index in the team's formation (vertical pitch band).</description>
        -- <example>3</example>
    home_player_Y5 INTEGER NULL,
        -- <description>Home player's Y-axis pitch position for the fifth starting player — indicates the Y-coordinate or zone of the home team's player in slot 5.</description>
        -- <example>3</example>
    home_player_Y6 INTEGER NULL,
        -- <description>Home sixth player's Y-axis location index for formation/positioning (enumerated pitch zone used by match event/formation data).</description>
        -- <example>7</example>
    home_player_Y7 INTEGER NULL,
        -- <description>Home team's 7th player's secondary lineup/positional code — a supplementary position/slot identifier used with home_player_X7 to describe that starter's location in the formation (values concentrate between 3–9; most frequent value is 7).</description>
        -- <example>7</example>
    home_player_Y8 INTEGER NULL,
        -- <description>Home player 8 vertical (Y) pitch position — ordinal pitch-row index for the home team’s starting player in slot 8; values cluster at 7 and 8 and ~7% of rows are missing.</description>
        -- <example>7</example>
    home_player_Y9 INTEGER NULL,
        -- <description>Home player 9 vertical pitch position index — the Y-coordinate (formation grid slot) for the home team’s ninth starting player.</description>
        -- <example>7</example>
    home_player_Y10 INTEGER NULL,
        -- <description>Home-team 10th player's Y-position code (match-specific coordinate/index that records the player's placement within the team's starting formation).</description>
        -- <example>10</example>
    home_player_Y11 INTEGER NULL,
        -- <description>Home team's 11th player's Y-coordinate (vertical position) on the pitch — used with home_player_X11 to record the player’s on-field Y position. Mostly contains values 10 or 11 (the two most common), with 24,147 non-null entries (≈92.9% of 25,979 matches).</description>
        -- <example>10</example>
    away_player_Y1 INTEGER NULL,
        -- <description>Away player 1 vertical/formation zone code (Y-position for away_player_1).</description>
        -- <example>1</example>
    away_player_Y2 INTEGER NULL,
        -- <description>Away player 2 Y-position on the match formation grid (vertical coordinate).</description>
        -- <example>3</example>
    away_player_Y3 INTEGER NULL,
        -- <description>Y-axis position index for the away team’s third listed player (tied to away_player_3); mostly a single small integer value (typically 3) and contains a notable number of NULLs.</description>
        -- <example>3</example>
    away_player_Y4 INTEGER NULL,
        -- <description>Away team player #4 Y-axis pitch-zone code (discrete vertical location index for the away team's fourth listed player).</description>
        -- <example>3</example>
    away_player_Y5 INTEGER NULL,
        -- <description>Away team's fifth player's Y-axis pitch zone/position index — a formation coordinate recorded for the away side's fifth-listed player.</description>
        -- <example>3</example>
    away_player_Y6 INTEGER NULL,
        -- <description>Away team player 6 Y-position — the vertical (Y) coordinate/index on the match’s normalized pitch grid for the away team’s sixth starting player (represents a coarse positional row; observed values ~3–10, ~7% missing).</description>
        -- <example>7</example>
    away_player_Y7 INTEGER NULL,
        -- <description>Away player 7 vertical pitch position (Y‑coordinate) — discrete ordinal indicating the player’s approximate Y location in the formation.</description>
        -- <example>7</example>
    away_player_Y8 INTEGER NULL,
        -- <description>Away player 8 Y-coordinate (formation position index) — ordinal vertical/slot index used to place the away team’s 8th listed player on the pitch for the match; typically populated (24,147 of 25,979 rows), values observed range from 3–10.</description>
        -- <example>7</example>
    away_player_Y9 INTEGER NULL,
        -- <description>Y-coordinate of the away team's ninth starting player's position on the pitch (formation/vertical coordinate). Observed values in this dataset are typically present (≈24k non-null) and range about 5–11.</description>
        -- <example>7</example>
    away_player_Y10 INTEGER NULL,
        -- <description>Away-team starting player #10 Y-position bucket — an integer code indicating the approximate Y (vertical) position/zone for the away side’s 10th starting player (used together with away_player_X10 and away_player_10). Contains a small set of discrete buckets (values 6–11) and ~7% missing.</description>
        -- <example>10</example>
    away_player_Y11 INTEGER NULL,
        -- <description>Away team 11th player's Y-coordinate on the formation/position grid — small integer used with away_player_X11 to locate that player's on-pitch position.</description>
        -- <example>10</example>
    home_player_1 INTEGER NULL,
        -- <description>Home team's first starting player — player_api_id referencing Player.player_api_id (identifies one member of the home starting XI).</description>
        -- <example>39890</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_2 INTEGER NULL,
        -- <description>Home team’s second starting player identifier (references the Player table). Mostly populated — 25,979 total matches with 1,315 NULL (~5.1%); 2,414 distinct non‑null ids and no orphan ids (all non-null values match Player.player_api_id).</description>
        -- <example>67950</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_3 INTEGER NULL,
        -- <description>Home team's third starting player — identifies the player occupying the third position in the home side’s starting XI for the match.</description>
        -- <example>38788</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_4 INTEGER NULL,
        -- <description>Home team's fourth starting player (the fourth member of the home-side starting XI). Populated in most matches — ~24,656 of 25,979 (~95%) — with many distinct player values.</description>
        -- <example>38312</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_5 INTEGER NULL,
        -- <description>Fifth home-team starter — the player API identifier for the home team’s fifth listed starting player (one of 11 starting player slots).</description>
        -- <example>26235</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_6 INTEGER NULL,
        -- <description>Home team's sixth starting player — the sixth listed player in the recorded home starting XI for the match.</description>
        -- <example>36393</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_7 INTEGER NULL,
        -- <description>Home team's seventh starting-lineup player (home lineup slot 7).</description>
        -- <example>148286</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_8 INTEGER NULL,
        -- <description>Home team's eighth starting-lineup player (player identifier for home lineup slot 8).</description>
        -- <example>67898</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_9 INTEGER NULL,
        -- <description>Ninth home-team starter — the match's ninth-listed home-team player, recorded as the player's api id (references Player.player_api_id).</description>
        -- <example>26916</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_10 INTEGER NULL,
        -- <description>Home team starting-lineup player in slot 10.</description>
        -- <example>38801</example>
        -- <fk> -> Player.player_api_id</fk>
    home_player_11 INTEGER NULL,
        -- <description>Home team's 11th starting-player slot (identifies which player occupied the #11 position in the home starting XI).</description>
        -- <example>94289</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_1 INTEGER NULL,
        -- <description>Away team starting player #1 (first listed away-side starter in the match lineup).</description>
        -- <example>34480</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_2 INTEGER NULL,
        -- <description>Away-team squad member listed in slot 2 (the second away player in the match roster).</description>
        -- <example>38388</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_3 INTEGER NULL,
        -- <description>Away team's third starting player's player_api_id — identifies the third-listed away-side starter using Player.player_api_id.</description>
        -- <example>26458</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_4 INTEGER NULL,
        -- <description>Away team's fourth starting player (the player listed in the fourth away starting position). Mostly populated across matches — 24,658 non-null values out of 25,979 and 2,657 distinct player ids; used to reconstruct the away starting lineup order.</description>
        -- <example>13423</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_5 INTEGER NULL,
        -- <description>Away team's fifth starting player (the fifth-listed away starter for the match).</description>
        -- <example>38389</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_6 INTEGER NULL,
        -- <description>Sixth listed away-team player in the match lineup — records which player occupied the away_player_6 slot for each match. In this dataset 24,666 of 25,979 matches have a value; there are 3,930 distinct player IDs (range 2625–722766).</description>
        -- <example>38798</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_7 INTEGER NULL,
        -- <description>Seventh away-team player listed for the match (slot containing the away player's player_api_id).</description>
        -- <example>30949</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_8 INTEGER NULL,
        -- <description>Away team eighth player id — the Player.player_api_id for the away team’s eighth listed player in the match (the away_player_8 slot). Commonly populated (24,638 of 25,979 rows) and joinable to Player.player_api_id.</description>
        -- <example>38253</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_9 INTEGER NULL,
        -- <description>Away team player 9 ID — identifier for the player occupying the away team's ninth lineup slot (refers to Player.player_api_id).</description>
        -- <example>106013</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_10 INTEGER NULL,
        -- <description>Away team's tenth starting player (player_api_id) — the player_api_id of the away team's #10 in the match lineup; populated in 24,538 of 25,979 matches with 3,891 distinct player ids.</description>
        -- <example>38383</example>
        -- <fk> -> Player.player_api_id</fk>
    away_player_11 INTEGER NULL,
        -- <description>Away team's eleventh starting-player slot — identifier for the player occupying the #11 position in the away team's match lineup.</description>
        -- <example>46552</example>
        -- <fk> -> Player.player_api_id</fk>
    goal TEXT NULL,
        -- <description>Goal event log — an XML-like text field that records one or more goal events for the match (each <value> element typically includes elapsed minute, player/team ids, event subtype and small stats such as shoton/goals).</description>
        -- <example>'<goal><value><comment>n</comment><stats><goals>1</...goal</type><goal_type>n</goal_type></value></goal>'</example>
    shoton TEXT NULL,
        -- <description>Shot-on-target events for the match — an XML-encoded list of individual shot events (each value records minute, player, team, subtype, whether it was on target or blocked, and an event id).</description>
        -- <example>'<shoton><value><stats><blocked>1</blocked></stats>...type>shoton</type><id>379466</id></value></shoton>'</example>
    shotoff TEXT NULL,
        -- <description>Match shotoff event list (XML) recording shots that missed or were off-target, with one <value> entry per shot giving minute, player, team, subtype and an event id.</description>
        -- <example>'<shotoff><value><stats><shotoff>1</shotoff></stats...pe>shotoff</type><id>379573</id></value></shotoff>'</example>
    foulcommit TEXT NULL,
        -- <description>XML-formatted log of foul incidents for the match, with one or more <value> entries describing each foul event.</description>
        -- <example>'<foulcommit><value><stats><foulscommitted>1</fouls...lcommit</type><id>379571</id></value></foulcommit>'</example>
    card TEXT NULL,
        -- <description>Card event XML for a match — an XML fragment listing one or more card incidents (e.g. yellow/red), including minute(s), card type, player and team; empty <card/> means no cards.</description>
        -- <example>'<card><value><comment>y</comment><stats><ycards>1<.../n><type>card</type><id>379547</id></value></card>'</example>
    cross TEXT NULL,
        -- <description>Cross events — XML‑formatted event list recording crosses (balls sent into the opposition area from wide positions), with per-cross details such as elapsed minute, player/team ids, counts and outcome identifiers.</description>
        -- <example>'<cross><value><stats><crosses>1</crosses></stats><...><type>cross</type><id>379540</id></value></cross>'</example>
    corner TEXT NULL,
        -- <description>Corner event log — an XML-like event list that records corner-kick events for the match (one or more <value> entries with per-event time/team/player/id/stats).</description>
        -- <example>'<corner><value><stats><corners>1</corners></stats>...type>corner</type><id>379460</id></value></corner>'</example>
    possession TEXT NULL,
        -- <description>Match possession log (XML-like): time-stamped snapshots of home/away possession percentages and related metadata captured during the match.</description>
        -- <example>'<possession><value><comment>56</comment><event_inc...special</type><id>379575</id></value></possession>'</example>
    B365H REAL NULL,
        -- <description>Bet365 pre-match home-win decimal odds (bookmaker Bet365); observed range ≈1.04–26 with mean ≈2.63; present in about 87% of matches.</description>
        -- <example>1.730</example>
    B365D REAL NULL,
        -- <description>Bet365 draw odds — decimal bookmaker odds offered by Bet365 for the match finishing in a draw.</description>
        -- <example>3.400</example>
    B365A REAL NULL,
        -- <description>Bet365 away-win decimal odds — bookmaker odds for an away team victory (decimal odds provided by Bet365; present for most matches).</description>
        -- <example>5.000</example>
    BWH REAL NULL,
        -- <description>William Hill home-win decimal odds — the bookmaker’s pre-match quoted decimal odds for a home-team victory (present in ~22,575 of 25,979 matches; observed range ≈1.03–34, mean ≈2.56).</description>
        -- <example>1.750</example>
    BWD REAL NULL,
        -- <description>Bet&Win (bwin) draw betting odds — the bookmaker's decimal odds for a match finishing in a draw (typical values ~1.65–19.5; many NULLs).</description>
        -- <example>3.350</example>
    BWA REAL NULL,
        -- <description>Away‑win decimal odds from the bookmaker labeled "BWA" — the quoted decimal odds for an away-team win (present for 22,575 of 25,979 matches; ~13.1% missing). Values in the table range roughly 1.1–51 (mean ≈4.40).</description>
        -- <example>4.200</example>
    IWH REAL NULL,
        -- <description>Interwetten home-win betting odds — the bookmaker Interwetten’s quoted odds for a home-team victory (pre-match). Values cluster near 2.0–2.2 with dataset range ≈1.03–20; ~22,520 of 25,979 rows (~86.7%) populated, ~13.3% missing.</description>
        -- <example>1.850</example>
    IWD REAL NULL,
        -- <description>Interwetten draw odds — bookmaker odds from Interwetten representing the payout for a match draw. Present in 22,520 of 25,979 matches (~86.7%); values range about 1.5–11 (73 distinct values). Example values: 3.2, 3.1, 3.9.</description>
        -- <example>3.200</example>
    IWA REAL NULL,
        -- <description>Interwetten bookmaker decimal odds for an away-team win (away victory odds).</description>
        -- <example>3.500</example>
    LBH REAL NULL,
        -- <description>Ladbrokes pre-match decimal odds for a home-team win (bookmaker LB home-win odds).</description>
        -- <example>1.800</example>
    LBD REAL NULL,
        -- <description>Ladbrokes draw odds — decimal bookmaker odds for a match finishing as a draw (Ladbrokes, draw market).</description>
        -- <example>3.300</example>
    LBA REAL NULL,
        -- <description>Ladbrokes away-win decimal odds — the bookmaker’s pre-match decimal odds for an away team victory (higher values indicate a lower implied probability). Observed in most matches (22,556 non-null of 25,979); values range ≈1.1–51 with mean ≈4.39.</description>
        -- <example>3.750</example>
    PSH REAL NULL,
        -- <description>Pinnacle (PS) home-win decimal betting odds — the bookmaker’s pre-match price for the home team to win (companion columns PSD and PSA give draw and away odds).</description>
        -- <example>5.100</example>
    PSD REAL NULL,
        -- <description>Pinnacle draw odds — closing decimal odds for a match draw offered by the Pinnacle (PS) bookmaker (PSD). Observed in 11,168 of 25,979 matches; values range ≈2.20–29 with mean ≈4.13.</description>
        -- <example>3.820</example>
    PSA REAL NULL,
        -- <description>Pinnacle Sports away-win closing odds — pre-match bookmaker odds for an away team (available for ~43% of matches; observed range ~1.09–47.5, mean ≈4.97).</description>
        -- <example>1.760</example>
    WHH REAL NULL,
        -- <description>William Hill home-win betting odds — decimal bookmaker odds for the home team provided by William Hill (used to infer implied probability; observed values in this dataset range roughly from 1.02 to 26, mean ≈ 2.58).</description>
        -- <example>1.700</example>
    WHD REAL NULL,
        -- <description>William Hill odds for a draw (decimal bookmaker odds offered by William Hill for a match finishing as a draw).</description>
        -- <example>3.300</example>
    WHA REAL NULL,
        -- <description>William Hill away-win odds — decimal odds offered by the William Hill bookmaker representing the price for an away-team victory (complements WHH for home and WHD for draw).</description>
        -- <example>4.330</example>
    SJH REAL NULL,
        -- <description>Stan James home-win betting odds — pre-match decimal odds for a home-team victory (nullable; present in ~17,097 of 25,979 matches, typical range ~1.04–23, mean ≈2.57).</description>
        -- <example>1.900</example>
    SJD REAL NULL,
        -- <description>Stan James draw odds — the bookmaker's quoted decimal odds for a match ending in a draw.</description>
        -- <example>3.300</example>
    SJA REAL NULL,
        -- <description>Away-team decimal betting odds from bookmaker Stan James (SJA) — the market odds for an away win.</description>
        -- <example>4.000</example>
    VCH REAL NULL,
        -- <description>VC bookmaker decimal odds for a home-team win (home-win market). Typical values range ≈1.03–36; present for 22,568 of 25,979 matches.</description>
        -- <example>1.650</example>
    VCD REAL NULL,
        -- <description>Victor Chandler draw odds — the pre-match decimal odds offered by the Victor Chandler (VC) bookmaker for the match finishing as a draw; useful for estimating the market-implied probability of a draw or comparing across bookmakers.</description>
        -- <example>3.400</example>
    VCA REAL NULL,
        -- <description>Away-team decimal betting odds from bookmaker Victor Chandler (VC); the quoted pre-match price for an away win.</description>
        -- <example>4.500</example>
    GBH REAL NULL,
        -- <description>Home-win decimal odds from bookmaker GB (the quoted odds for a home team victory).</description>
        -- <example>1.780</example>
    GBD REAL NULL,
        -- <description>Gamebookers (GB) pre-match decimal odds for a draw — the bookmaker's offered price for the match finishing in a draw.</description>
        -- <example>3.250</example>
    GBA REAL NULL,
        -- <description>Away-team betting odds from bookmaker 'GB' (column GBA); present in 14,162 of 25,979 matches (~54.5% non-null), many rows are missing.</description>
        -- <example>4.000</example>
    BSH REAL NULL,
        -- <description>BS bookmaker home-win decimal odds — pre-match closing odds for the home team from the 'BS' bookmaker (paired with BSD and BSA for draw/away). Many values are missing (~11,818 of 25,979 rows, ~45%); observed range ≈1.04–17 with mean ≈2.50.</description>
        -- <example>1.730</example>
    BSD REAL NULL,
        -- <description>BS draw odds — decimal betting odds offered by bookmaker "BS" for the match draw outcome.</description>
        -- <example>3.400</example>
    BSA REAL NULL,
        -- <description>Away-team decimal pre-match betting odds from the bookmaker labeled “BSA”. Represents the bookmaker's quoted price for an away win — contains ~14,161 non-null values (out of 25,979); observed range ≈1.12–34 with mean ≈4.41.</description>
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
        -- <description>Unique identifier for a player record.</description>
        -- <example>3879</example>
    player_api_id INTEGER NULL,
        -- <description>Canonical external player API identifier — stable, non-null key used to link Player records to Player_Attributes and Match lineup columns.</description>
        -- <example>2625</example>
    player_name TEXT NULL,
        -- <description>Player name — the player's commonly used full name as recorded in the dataset (examples: "Aaron Appindangoye", "Mario Matos", "Junya Tanaka").</description>
        -- <example>'Aaron Appindangoye'</example>
    player_fifa_api_id INTEGER NULL,
        -- <description>FIFA player API identifier — the external FIFA API id for the player; unique and non-null, used to join player records to Player_Attributes (referenced by Player_Attributes.player_fifa_api_id).</description>
        -- <example>2</example>
    birthday TEXT NULL,
        -- <description>Player date of birth — timestamp string (format 'YYYY-MM-DD HH:MM:SS') used to compute player age.</description>
        -- <example>'1992-02-29 00:00:00'</example>
    height INTEGER NULL,
        -- <description>Player height in centimetres — recorded for all players (no missing values); range ≈157.48–208.28 cm, mean ≈181.87 cm; most common value 182.88 cm (1,954 of 11,060 rows).</description>
        -- <example>182.880</example>
    weight INTEGER NULL
        -- <description>Player weight (body mass) — recorded in the dataset's units (appears to be pounds); values range ~117–243 (mean ≈168.4), no missing values.</description>
        -- <example>187</example>
);

-- Table: Player_Attributes (183978 rows)
CREATE TABLE Player_Attributes (
    id INTEGER NULL PRIMARY KEY,
        -- <description>Row identifier for a Player_Attributes record (unique per record).</description>
        -- <example>1</example>
    player_fifa_api_id INTEGER NULL,
        -- <description>Player FIFA API identifier — foreign key that links this attribute record to Player.player_fifa_api_id.</description>
        -- <example>218353</example>
        -- <fk> -> Player.player_fifa_api_id</fk>
    player_api_id INTEGER NULL,
        -- <description>Player API identifier linking each attribute record to the corresponding player (references Player.player_api_id).</description>
        -- <example>505942</example>
        -- <fk> -> Player.player_api_id</fk>
    date TEXT NULL,
        -- <description>player attribute snapshot date — timestamp for each Player_Attributes record indicating when that attribute snapshot was recorded (used to track attribute changes over time).</description>
        -- <example>'2016-02-18 00:00:00'</example>
    overall_rating INTEGER NULL,
        -- <description>FIFA overall rating — score (0–100) summarizing a player's current ability; higher values indicate stronger performance. In this dataset values range 33–94 (mean 68.6); 836 of 183,978 rows are NULL.</description>
        -- <example>67</example>
    potential INTEGER NULL,
        -- <description>Player potential score — a FIFA-derived measure of a player’s projected future ability; higher values indicate greater potential (commonly 0–100; observed range in this dataset: 39–97).</description>
        -- <example>71</example>
    preferred_foot TEXT NULL,
        -- <description>Preferred foot — the player’s dominant foot (used for attacking/technical actions). Distribution: ~75% right-footed, ~24% left-footed; ~0.5% missing.</description>
        -- <values>{'left', 'right'}</values>
    attacking_work_rate TEXT NULL,
        -- <description>Player attacking work-rate category — categorical label indicating the frequency/intensity with which a player joins attacking play. In this dataset the majority of records are 'medium' or 'high'; there are several low-frequency, likely-misspelled or placeholder variants (for example 'le', 'stoc', 'y', 'None') that should be cleaned or normalized before use.</description>
        -- <values>{'None', 'high', 'le', 'low', 'medium', 'norm', 'stoc', 'y'}</values>
    defensive_work_rate TEXT NULL,
        -- <description>Defensive work rate — qualitative indicator of a player’s tendency to perform defensive actions and to stay back (how often they track back, pressure and defend) — higher values imply greater defensive involvement. Note: the column mostly uses standard labels but contains some misspellings/noisy tokens; about 836 rows are NULL.</description>
        -- <values>{'0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '_0', 'ean', 'es', 'high', 'low', 'medium', 'o', 'ormal', 'tocky'}</values>
    crossing INTEGER NULL,
        -- <description>Crossing ability score — a FIFA-derived 0–100 measure of a player’s tendency and effectiveness when delivering crosses into the penalty area; higher values indicate better crossing performance.</description>
        -- <example>49</example>
    finishing INTEGER NULL,
        -- <description>Finishing rating — a FIFA-derived score assessing a player's effectiveness, accuracy and composure when converting goal-scoring chances into goals.</description>
        -- <example>44</example>
    heading_accuracy INTEGER NULL,
        -- <description>Heading accuracy — FIFA-derived score indicating a player's effectiveness and precision when heading the ball; higher values indicate better heading ability.</description>
        -- <example>71</example>
    short_passing INTEGER NULL,
        -- <description>Short-passing rating — a FIFA-derived measure of a player's accuracy and effectiveness with short passes.</description>
        -- <example>61</example>
    volleys INTEGER NULL,
        -- <description>Player volleying ability — a FIFA-derived technical rating that captures a player's effectiveness and technique when striking the ball on the volley; higher values indicate better volley skill. Mostly populated (181,265 of 183,978 records).</description>
        -- <example>44</example>
    dribbling INTEGER NULL,
        -- <description>Player dribbling score — FIFA attribute (0–100) indicating a player's ability to beat opponents with the ball at their feet.</description>
        -- <example>51</example>
    curve INTEGER NULL,
        -- <description>Player curve ability — a FIFA attribute measuring a player's skill at bending the ball on shots, crosses and set pieces (higher = better). Present in ~98.5% of rows (181,265/183,978); observed values span about 2–94 with mean ≈52.97. Most frequent recorded values include 25, 68, 60, 67 and 56.</description>
        -- <example>45</example>
    free_kick_accuracy INTEGER NULL,
        -- <description>Free-kick accuracy — FIFA-calculated score that measures a player’s proficiency and accuracy when taking direct free kicks (higher = better).</description>
        -- <example>39</example>
    long_passing INTEGER NULL,
        -- <description>Long passing ability — FIFA-calculated score that reflects a player's tendency and effectiveness when playing long passes.</description>
        -- <example>64</example>
    ball_control INTEGER NULL,
        -- <description>Player ball-control rating — a FIFA-derived score measuring a player's close control and first touch.</description>
        -- <example>49</example>
    acceleration INTEGER NULL,
        -- <description>Player acceleration rating — a FIFA-derived score (0–100) estimating how quickly the player can reach top speed.</description>
        -- <example>60</example>
    sprint_speed INTEGER NULL,
        -- <description>Player sprint speed — a FIFA-derived attribute that represents a player's sprinting pace (captures acceleration and top running speed), used to compare players' pace.</description>
        -- <example>64</example>
    agility INTEGER NULL,
        -- <description>Player agility score — a FIFA-derived measure of a player's quickness and change-of-direction ability; higher values indicate a more agile player.</description>
        -- <example>59</example>
    reactions INTEGER NULL,
        -- <description>Player reaction rating — FIFA-calculated numeric score (higher is better) that measures how quickly a player responds to in-game events; recorded on a 0–100 scale (most rows populated; dataset mean ≈ 66).</description>
        -- <example>47</example>
    balance INTEGER NULL,
        -- <description>Player balance rating — FIFA-derived attribute measuring a player's ability to maintain stability and body control under pressure (used as a physical attribute in evaluations).</description>
        -- <example>65</example>
    shot_power INTEGER NULL,
        -- <description>Shot power rating — a FIFA-calculated measure of a player's ability to strike the ball with power (affects long shots and shooting force).</description>
        -- <example>55</example>
    jumping INTEGER NULL,
        -- <description>Player jumping ability rating from the FIFA player attributes (higher values indicate better jumping).</description>
        -- <example>58</example>
    stamina INTEGER NULL,
        -- <description>Player stamina rating — FIFA-calculated endurance score estimating a player's ability to sustain physical effort during matches.</description>
        -- <example>54</example>
    strength INTEGER NULL,
        -- <description>FIFA strength rating — the player's physical strength on a 0–100 scale (most records populated). Observed values in this dataset range ~10–96 with mean ≈67.</description>
        -- <example>76</example>
    long_shots INTEGER NULL,
        -- <description>Long shots — FIFA-derived rating of a player's tendency and effectiveness when shooting from distance (evaluates long-range shooting ability).</description>
        -- <example>35</example>
    aggression INTEGER NULL,
        -- <description>player aggression score (FIFA-calculated) — a measure of a player's tendency to engage in physical challenges, press opponents, and play aggressively.</description>
        -- <example>71</example>
    interceptions INTEGER NULL,
        -- <description>Interceptions score — a FIFA-derived defensive attribute measuring a player’s ability to anticipate and intercept opponents’ passes (used as a proxy for defensive reading/anticipation).</description>
        -- <example>70</example>
    positioning INTEGER NULL,
        -- <description>Player positioning rating (FIFA) — FIFA-calculated score indicating a player's ability to read the game and occupy effective positions on the pitch (i.e., positioning and off-the-ball movement).</description>
        -- <example>45</example>
    vision INTEGER NULL,
        -- <description>Player vision rating — FIFA-assessed measure of a player's ability to spot, anticipate and execute attacking passes and creative decisions.</description>
        -- <example>54</example>
    penalties INTEGER NULL,
        -- <description>Penalty-taking skill rating (FIFA-calculated, 0–100).</description>
        -- <example>48</example>
    marking INTEGER NULL,
        -- <description>Player marking ability score (FIFA) — a FIFA-derived rating that reflects a player's tendency and effectiveness at marking opponents. Mostly populated in this dataset (183,142 of 183,978 rows); observed values range from 1 to 96 (mean ≈ 46.77).</description>
        -- <example>65</example>
    standing_tackle INTEGER NULL,
        -- <description>Player standing-tackle ability score (FIFA) — a 0–100 integer measuring a player’s proficiency at performing standing tackles.</description>
        -- <example>69</example>
    sliding_tackle INTEGER NULL,
        -- <description>Sliding tackle rating — FIFA-assessed measure of a player's ability to perform sliding tackles (higher = better).</description>
        -- <example>69</example>
    gk_diving INTEGER NULL,
        -- <description>Goalkeeper diving ability rating (FIFA) — a numeric score where higher values indicate better diving performance.</description>
        -- <example>6</example>
    gk_handling INTEGER NULL,
        -- <description>goalkeeper handling rating — a FIFA-assessed measure of a goalkeeper's ability to catch, hold and control shots, crosses and set-piece deliveries.</description>
        -- <example>11</example>
    gk_kicking INTEGER NULL,
        -- <description>Goalkeeper kicking ability — FIFA-calculated score that quantifies a goalkeeper’s kicking/punting quality (used to assess distribution and long-kick effectiveness).</description>
        -- <example>10</example>
    gk_positioning INTEGER NULL,
        -- <description>Goalkeeper positioning rating — a FIFA-derived score reflecting a goalkeeper’s ability to position themselves during play.</description>
        -- <example>8</example>
    gk_reflexes INTEGER NULL,
        -- <description>Goalkeeper reflexes rating assigned by FIFA — a measure of a goalkeeper's reaction speed (higher is better).</description>
        -- <example>8</example>
    FOREIGN KEY (player_api_id) REFERENCES Player(player_api_id),
    FOREIGN KEY (player_fifa_api_id) REFERENCES Player(player_fifa_api_id)
);

-- Table: Team (299 rows)
CREATE TABLE Team (
    id INTEGER NULL PRIMARY KEY,
        -- <description>Unique identifier for each team (table primary key).</description>
        -- <example>31446</example>
    team_api_id INTEGER NULL,
        -- <description>Team API identifier — the stable external ID used to reference a team across the dataset (unique per team). Referenced by other tables (e.g. Match.home_team_api_id, Match.away_team_api_id, Team_Attributes.team_api_id).</description>
        -- <example>1601</example>
    team_fifa_api_id INTEGER NULL,
        -- <description>FIFA team identifier — external FIFA API ID for the club, used to link Team rows with FIFA-based attributes and other FIFA-sourced tables (285 distinct non-null values; 11 NULLs out of 299 rows).</description>
        -- <example>673</example>
    team_long_name TEXT NULL,
        -- <description>Team long name — the club’s full/display name used to identify the team (e.g., KRC Genk, Queens Park Rangers, Sporting CP).</description>
        -- <example>'KRC Genk'</example>
    team_short_name TEXT NULL
        -- <description>Abbreviated team short name — short uppercase club code used as a compact identifier (typically 3–4 letters); populated for all rows (0 nulls), 259 distinct values across 299 teams. Examples: AAR, ACA, BRE.</description>
        -- <example>'GEN'</example>
);

-- Table: Team_Attributes (1458 rows)
CREATE TABLE Team_Attributes (
    id INTEGER NULL PRIMARY KEY,
        -- <description>Unique row identifier for Team_Attributes records — a distinct id assigned to each team attribute entry.</description>
        -- <example>1</example>
    team_fifa_api_id INTEGER NULL,
        -- <description>Team FIFA API identifier linking each Team_Attributes record to a team (references Team.team_fifa_api_id). Present for all rows — 1,458 records with 285 distinct team FIFA IDs.</description>
        -- <example>434</example>
        -- <fk> -> Team.team_fifa_api_id</fk>
    team_api_id INTEGER NULL,
        -- <description>Team API identifier linking each Team_Attributes record to the Team table (references Team.team_api_id). Fully populated: no NULLs; 288 distinct teams across 1,458 rows; all values match existing Team.team_api_id.</description>
        -- <example>9930</example>
        -- <fk> -> Team.team_api_id</fk>
    date TEXT NULL,
        -- <description>Team attribute record date — timestamp indicating when a team's attributes snapshot was recorded. Contains six distinct snapshot dates spanning 2010-02-22 to 2015-09-10 and is populated for all 1,458 rows.</description>
        -- <values>{'2010-02-22 00:00:00', '2011-02-22 00:00:00', '2012-02-22 00:00:00', '2013-09-20 00:00:00', '2014-09-19 00:00:00', '2015-09-10 00:00:00'}</values>
    buildUpPlaySpeed INTEGER NULL,
        -- <description>Build-up play speed score — a numeric team attribute that indicates how quickly the team constructs attacks (higher values = faster); typically expressed on a 1–100 scale and mapped to buildUpPlaySpeedClass (Slow/Balanced/Fast).</description>
        -- <example>60</example>
    buildUpPlaySpeedClass TEXT NULL,
        -- <description>Build-up play speed class — categorical label describing a team’s typical tempo when constructing attacks; derived from the numeric buildUpPlaySpeed score (1–33 → Slow, 34–66 → Balanced, 67–100 → Fast).</description>
        -- <values>{'Balanced', 'Fast', 'Slow'}</values>
    buildUpPlayDribbling INTEGER NULL,
        -- <description>Build-up play dribbling tendency — a team attribute that measures how frequently a team uses dribbling when building attacks. Note: this field is sparsely populated in the table (489 of 1,458 rows non‑null).</description>
        -- <example>48</example>
    buildUpPlayDribblingClass TEXT NULL,
        -- <description>Build-up play dribbling class — categorical label describing a team’s tendency to dribble during build-up attacks, derived from the numeric buildUpPlayDribbling score (maps low→high).</description>
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    buildUpPlayPassing INTEGER NULL,
        -- <description>Build-up play passing score — a numeric rating of a team’s typical passing length/support during build-up play (higher = longer/more expansive passing). Observed range in the data: 20–80; mean ≈48.5; no missing values.</description>
        -- <example>50</example>
    buildUpPlayPassingClass TEXT NULL,
        -- <description>Build-up passing length preference — indicates a team’s tendency toward shorter, mixed or longer passes when constructing attacks; derived from an underlying 1–100 score (low ≈ short, mid ≈ mixed, high ≈ long).</description>
        -- <values>{'Long', 'Mixed', 'Short'}</values>
    buildUpPlayPositioningClass TEXT NULL,
        -- <description>Team build-up positioning style — indicates how structured the team’s positioning is during build-up play in the first two-thirds of the pitch.</description>
        -- <values>{'Free Form', 'Organised'}</values>
    chanceCreationPassing INTEGER NULL,
        -- <description>Team chance-creation passing score — indicates how risky or conservative a team's passing decisions and supporting runs are when creating scoring opportunities (higher values = riskier).</description>
        -- <example>60</example>
    chanceCreationPassingClass TEXT NULL,
        -- <description>Chance-creation passing risk class — a coarse categorical label for a team’s passing style when creating chances, produced by bucketizing the numeric chanceCreationPassing score (low → Safe, mid → Normal, high → Risky).</description>
        -- <values>{'Normal', 'Risky', 'Safe'}</values>
    chanceCreationCrossing INTEGER NULL,
        -- <description>Tendency to create scoring chances by crossing the ball into the penalty area (higher values indicate more frequent/use of crosses).</description>
        -- <example>65</example>
    chanceCreationCrossingClass TEXT NULL,
        -- <description>Chance creation crossing class — categorical label describing a team's tendency to deliver crosses into the opponent's penalty area, derived from an underlying 1–100 score (Little ≈ 1–33, Normal ≈ 34–66, Lots ≈ 67–100).</description>
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    chanceCreationShooting INTEGER NULL,
        -- <description>Chance-creation shooting tendency — a team rating that measures how frequently the team attempts shots (higher values indicate more frequent shooting).</description>
        -- <example>55</example>
    chanceCreationShootingClass TEXT NULL,
        -- <description>Chance-creation shooting class — categorical label that describes a team's tendency/frequency to create shooting opportunities (a coarse class derived from the numeric chanceCreationShooting attribute).</description>
        -- <values>{'Little', 'Lots', 'Normal'}</values>
    chanceCreationPositioningClass TEXT NULL,
        -- <description>Final-third positioning class — indicates a team’s freedom of movement and positional structure in the attacking (final) third of the pitch.</description>
        -- <values>{'Free Form', 'Organised'}</values>
    defencePressure INTEGER NULL,
        -- <description>Defensive pressure rating — numeric score indicating how far up the pitch a team applies pressure; higher values mean more aggressive/high pressing. Observed values in this dataset are roughly 23–72 (mean ≈46).</description>
        -- <example>50</example>
    defencePressureClass TEXT NULL,
        -- <description>Defensive pressing intensity — an ordinal label describing how aggressively a team presses opponents (how high up the pitch pressure is applied); roughly maps to low/medium/high intensity corresponding to score bands ≈1–33, 34–66, 67–100. Most rows are medium intensity.</description>
        -- <values>{'Deep', 'High', 'Medium'}</values>
    defenceAggression INTEGER NULL,
        -- <description>Defence aggression score — a team-level measure of how aggressively the side presses and tackles to win the ball (pressure/tackling intensity). Observed values in this dataset range from 24 to 72 (mean ≈49); no missing values.</description>
        -- <example>55</example>
    defenceAggressionClass TEXT NULL,
        -- <description>Defence aggression class — categorical label indicating a team’s defensive tackling/pressing style, mapped to low/medium/high aggression ranges.</description>
        -- <values>{'Contain', 'Double', 'Press'}</values>
    defenceTeamWidth INTEGER NULL,
        -- <description>Defensive team width — a team attribute that measures how far the defensive line shifts toward the ball side; higher values indicate a wider shift. (All 1,458 records populated; observed range 29–73, mean ≈52.19.)</description>
        -- <example>45</example>
    defenceTeamWidthClass TEXT NULL,
        -- <description>Defensive width class — a qualitative label for how wide a team sets its defensive shape, grouping the numeric defenceTeamWidth into three bands (Narrow ≈ low scores, Normal ≈ mid scores, Wide ≈ high scores). Useful for interpreting team defensive spacing and tactical width.</description>
        -- <values>{'Narrow', 'Normal', 'Wide'}</values>
    defenceDefenderLineClass TEXT NULL,
        -- <description>Defensive-line strategy class that describes a team’s defensive shape and approach (how the back line operates defensively).</description>
        -- <values>{'Cover', 'Offside Trap'}</values>
    FOREIGN KEY (team_api_id) REFERENCES Team(team_api_id),
    FOREIGN KEY (team_fifa_api_id) REFERENCES Team(team_fifa_api_id)
);
```