```sql
-- Database: ice_hockey_draft

-- Table: PlayerInfo (2171 rows)
CREATE TABLE PlayerInfo (
    ELITEID INTEGER NULL PRIMARY KEY,
        -- <example>9</example>
    PlayerName TEXT NULL,
        -- <example>'David Bornhammar'</example>
    birthdate TEXT NULL,
        -- <example>'1981-06-15'</example>
    birthyear DATE NULL,
        -- <example>1981</example>
    birthmonth INTEGER NULL,
        -- <example>6</example>
    birthday INTEGER NULL,
        -- <example>15</example>
    birthplace TEXT NULL,
        -- <example>'Lidingo, SWE'</example>
    nation TEXT NULL,
        -- <example>'Sweden'</example>
    height INTEGER NULL,
        -- <example>73</example>
        -- <fk> -> height_info.height_id</fk>
    weight INTEGER NULL,
        -- <example>198</example>
        -- <fk> -> weight_info.weight_id</fk>
    position_info TEXT NULL,
        -- <example>'D'</example>
    shoots TEXT NULL,
        -- <values>{'-', 'L', 'R'}</values>
    draftyear INTEGER NULL,
        -- <example>1999</example>
    draftround INTEGER NULL,
        -- <example>7</example>
    overall INTEGER NULL,
        -- <example>192</example>
    overallby TEXT NULL,
        -- <example>'Washington Capitals'</example>
    CSS_rank INTEGER NULL,
        -- <example>192</example>
    sum_7yr_GP INTEGER NULL,
        -- <example>0</example>
    sum_7yr_TOI INTEGER NULL,
        -- <example>0</example>
    GP_greater_than_0 TEXT NULL,
        -- <values>{'no', 'yes'}</values>
    FOREIGN KEY (height) REFERENCES height_info(height_id),
    FOREIGN KEY (weight) REFERENCES weight_info(weight_id)
);

-- Table: SeasonStatus (5485 rows)
CREATE TABLE SeasonStatus (
    ELITEID INTEGER NULL,
        -- <example>3667</example>
        -- <fk> -> PlayerInfo.ELITEID</fk>
    SEASON TEXT NULL,
        -- <values>{'1997-1998', '1998-1999', '1999-2000', '2000-2001', '2001-2002', '2003-2004', '2004-2005', '2005-2006', '2006-2007', '2007-2008'}</values>
    TEAM TEXT NULL,
        -- <example>'Rimouski Oceanic'</example>
    LEAGUE TEXT NULL,
        -- <example>'QMJHL'</example>
    GAMETYPE TEXT NULL,
        -- <values>{'Playoffs', 'Regular Season'}</values>
    GP INTEGER NULL,
        -- <example>58</example>
    G INTEGER NULL,
        -- <example>44</example>
    A INTEGER NULL,
        -- <example>71</example>
    P INTEGER NULL,
        -- <example>115</example>
    PIM INTEGER NULL,
        -- <example>117</example>
    PLUSMINUS INTEGER NULL,
        -- <example>27</example>
    FOREIGN KEY (ELITEID) REFERENCES PlayerInfo(ELITEID)
);

-- Table: height_info (16 rows)
CREATE TABLE height_info (
    height_id INTEGER NULL PRIMARY KEY,
        -- <example>65</example>
    height_in_cm INTEGER NULL,
        -- <example>165</example>
    height_in_inch TEXT NULL
        -- <example>'5'5"'</example>
);

-- Table: weight_info (46 rows)
CREATE TABLE weight_info (
    weight_id INTEGER NULL PRIMARY KEY,
        -- <example>154</example>
    weight_in_kg INTEGER NULL,
        -- <example>70</example>
    weight_in_lbs INTEGER NULL
        -- <example>154</example>
);
```