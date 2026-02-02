```sql
-- Database: college_completion

-- Table: institution_details (3798 rows)
CREATE TABLE institution_details (
    unitid INTEGER NULL PRIMARY KEY,
        -- <example>100654</example>
    chronname TEXT NULL,
        -- <example>'Alabama A&M University'</example>
    city TEXT NULL,
        -- <example>'Normal'</example>
    state TEXT NULL,
        -- <example>'Alabama'</example>
    level TEXT NULL,
        -- <values>{'2-year', '4-year'}</values>
    control TEXT NULL,
        -- <values>{'Private for-profit', 'Private not-for-profit', 'Public'}</values>
    basic TEXT NULL,
        -- <example>'Masters Colleges and Universities--larger programs'</example>
    hbcu TEXT NULL,
        -- <values>{'NULL', 'X'}</values>
    flagship TEXT NULL,
        -- <values>{'NULL', 'X'}</values>
    long_x REAL NULL,
        -- <example>-86.569</example>
    lat_y REAL NULL,
        -- <example>34.783</example>
    site TEXT NULL,
        -- <example>'www.aamu.edu/'</example>
    student_count INTEGER NULL,
        -- <example>4051</example>
    awards_per_value REAL NULL,
        -- <example>14.200</example>
    awards_per_state_value REAL NULL,
        -- <example>18.800</example>
    awards_per_natl_value REAL NULL,
        -- <example>21.500</example>
    exp_award_value INTEGER NULL,
        -- <example>105331</example>
    exp_award_state_value INTEGER NULL,
        -- <example>75743</example>
    exp_award_natl_value INTEGER NULL,
        -- <example>66436</example>
    exp_award_percentile INTEGER NULL,
        -- <example>90</example>
    ft_pct REAL NULL,
        -- <example>93.800</example>
    fte_value INTEGER NULL,
        -- <example>3906</example>
    fte_percentile INTEGER NULL,
        -- <example>33</example>
    med_sat_value TEXT NULL,
        -- <example>'823'</example>
    med_sat_percentile TEXT NULL,
        -- <example>'0'</example>
    aid_value INTEGER NULL,
        -- <example>7142</example>
    aid_percentile INTEGER NULL,
        -- <example>72</example>
    endow_value TEXT NULL,
        -- <example>'NULL'</example>
    endow_percentile TEXT NULL,
        -- <example>'NULL'</example>
    grad_100_value REAL NULL,
        -- <example>10.000</example>
    grad_100_percentile INTEGER NULL,
        -- <example>15</example>
    grad_150_value REAL NULL,
        -- <example>29.100</example>
    grad_150_percentile INTEGER NULL,
        -- <example>14</example>
    pell_value REAL NULL,
        -- <example>71.200</example>
    pell_percentile INTEGER NULL,
        -- <example>98</example>
    retain_value REAL NULL,
        -- <example>63.100</example>
    retain_percentile INTEGER NULL,
        -- <example>17</example>
    ft_fac_value REAL NULL,
        -- <example>82.800</example>
    ft_fac_percentile INTEGER NULL,
        -- <example>89</example>
    vsa_year TEXT NULL,
        -- <values>{'2008', '2009', '2010', '2011', 'NULL'}</values>
    vsa_grad_after4_first TEXT NULL,
        -- <example>'14.7'</example>
    vsa_grad_elsewhere_after4_first TEXT NULL,
        -- <example>'2'</example>
    vsa_enroll_after4_first TEXT NULL,
        -- <example>'36.5'</example>
    vsa_enroll_elsewhere_after4_first TEXT NULL,
        -- <example>'16.1'</example>
    vsa_grad_after6_first TEXT NULL,
        -- <example>'33'</example>
    vsa_grad_elsewhere_after6_first TEXT NULL,
        -- <example>'5.3'</example>
    vsa_enroll_after6_first TEXT NULL,
        -- <example>'12.5'</example>
    vsa_enroll_elsewhere_after6_first TEXT NULL,
        -- <example>'14.6'</example>
    vsa_grad_after4_transfer TEXT NULL,
        -- <example>'15.7'</example>
    vsa_grad_elsewhere_after4_transfer TEXT NULL,
        -- <example>'1.5'</example>
    vsa_enroll_after4_transfer TEXT NULL,
        -- <example>'40.9'</example>
    vsa_enroll_elsewhere_after4_transfer TEXT NULL,
        -- <example>'17.2'</example>
    vsa_grad_after6_transfer TEXT NULL,
        -- <example>'36.4'</example>
    vsa_grad_elsewhere_after6_transfer TEXT NULL,
        -- <example>'5.6'</example>
    vsa_enroll_after6_transfer TEXT NULL,
        -- <example>'17.2'</example>
    vsa_enroll_elsewhere_after6_transfer TEXT NULL,
        -- <example>'11.1'</example>
    similar TEXT NULL,
        -- <example>'232937|100724|405997|113607|139533|144005|228501|1...7|228529|372222|228431|206695|139366|159993|224147'</example>
    state_sector_ct INTEGER NULL,
        -- <example>13</example>
    carnegie_ct INTEGER NULL,
        -- <example>386</example>
    counted_pct TEXT NULL,
        -- <example>'99.7|07'</example>
    nicknames TEXT NULL,
        -- <example>'NULL'</example>
    cohort_size INTEGER NULL
        -- <example>882</example>
);

-- Table: institution_grads (1302102 rows)
CREATE TABLE institution_grads (
    unitid INTEGER NULL,
        -- <example>100760</example>
        -- <fk> -> institution_details.unitid</fk>
    year INTEGER NULL,
        -- <example>2011</example>
    gender TEXT NULL,
        -- <values>{'B', 'F', 'M'}</values>
    race TEXT NULL,
        -- <values>{'A', 'Ai', 'B', 'H', 'W', 'X'}</values>
    cohort TEXT NULL,
        -- <values>{'2y all', '4y bach', '4y other'}</values>
    grad_cohort TEXT NULL,
        -- <example>'446'</example>
    grad_100 TEXT NULL,
        -- <example>'73'</example>
    grad_150 TEXT NULL,
        -- <example>'105'</example>
    grad_100_rate TEXT NULL,
        -- <example>'16.4'</example>
    grad_150_rate TEXT NULL,
        -- <example>'23.5'</example>
    FOREIGN KEY (unitid) REFERENCES institution_details(unitid)
);

-- Table: state_sector_details (312 rows)
CREATE TABLE state_sector_details (
    stateid INTEGER NULL,
        -- <example>0</example>
    state TEXT NULL,
        -- <example>'United States'</example>
        -- <fk> -> institution_details.state</fk>
    state_post TEXT NULL,
        -- <example>'U.S.'</example>
    level TEXT NULL,
        -- <values>{'2-year', '4-year'}</values>
    control TEXT NULL,
        -- <values>{'Private for-profit', 'Private not-for-profit', 'Public'}</values>
    schools_count INTEGER NULL,
        -- <example>632</example>
    counted_pct TEXT NULL,
        -- <example>'NULL'</example>
    awards_per_state_value TEXT NULL,
        -- <example>'NULL'</example>
    awards_per_natl_value REAL NULL,
        -- <example>21.500</example>
    exp_award_state_value TEXT NULL,
        -- <example>'NULL'</example>
    exp_award_natl_value INTEGER NULL,
        -- <example>66436</example>
    state_appr_value TEXT NULL,
        -- <example>'NULL'</example>
    state_appr_rank TEXT NULL,
        -- <example>'NULL'</example>
    grad_rate_rank TEXT NULL,
        -- <example>'23'</example>
    awards_per_rank TEXT NULL,
        -- <example>'NULL'</example>
    PRIMARY KEY (stateid, level, control),
    FOREIGN KEY (state) REFERENCES institution_details(state)
);

-- Table: state_sector_grads (84942 rows)
CREATE TABLE state_sector_grads (
    stateid INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> state_sector_details.stateid</fk>
    state TEXT NULL,
        -- <example>'Alabama'</example>
        -- <fk> -> institution_details.state</fk>
    state_abbr TEXT NULL,
        -- <example>'AL'</example>
    control TEXT NULL,
        -- <values>{'Private for-profit', 'Private not-for-profit', 'Public'}</values>
    level TEXT NULL,
        -- <values>{'2-year', '4-year'}</values>
    year INTEGER NULL,
        -- <example>2011</example>
    gender TEXT NULL,
        -- <values>{'B', 'F', 'M'}</values>
    race TEXT NULL,
        -- <values>{'A', 'Ai', 'B', 'H', 'W', 'X'}</values>
    cohort TEXT NULL,
        -- <values>{'2y all', '4y bach', '4y other'}</values>
    grad_cohort TEXT NULL,
        -- <example>'0'</example>
    grad_100 TEXT NULL,
        -- <example>'0'</example>
    grad_150 TEXT NULL,
        -- <example>'0'</example>
    grad_100_rate TEXT NULL,
        -- <example>'NULL'</example>
    grad_150_rate TEXT NULL,
        -- <example>'NULL'</example>
    grad_cohort_ct INTEGER NULL,
        -- <example>9</example>
    FOREIGN KEY (state) REFERENCES institution_details(state),
    FOREIGN KEY (stateid) REFERENCES state_sector_details(stateid)
);
```