```sql
-- Database: college_completion

/*
Schema: NULLTable: institution_details
Rows: 3798
Sample rows:
| unitid   | chronname                           | city       | state   | level   | control                | basic                                              | hbcu   | flagship   | long_x     | lat_y     | site                           | student_count   | awards_per_value   | awards_per_state_value   | awards_per_natl_value   | exp_award_value   | exp_award_state_value   | exp_award_natl_value   | exp_award_percentile   | ft_pct   | fte_value   | fte_percentile   | med_sat_value   | med_sat_percentile   | aid_value   | aid_percentile   | endow_value   | endow_percentile   | grad_100_value   | grad_100_percentile   | grad_150_value   | grad_150_percentile   | pell_value   | pell_percentile   | retain_value   | retain_percentile   | ft_fac_value   | ft_fac_percentile   | vsa_year   | vsa_grad_after4_first   | vsa_grad_elsewhere_after4_first   | vsa_enroll_after4_first   | vsa_enroll_elsewhere_after4_first   | vsa_grad_after6_first   | vsa_grad_elsewhere_after6_first   | vsa_enroll_after6_first   | vsa_enroll_elsewhere_after6_first   | vsa_grad_after4_transfer   | vsa_grad_elsewhere_after4_transfer   | vsa_enroll_after4_transfer   | vsa_enroll_elsewhere_after4_transfer   | vsa_grad_after6_transfer   | vsa_grad_elsewhere_after6_transfer   | vsa_enroll_after6_transfer   | vsa_enroll_elsewhere_after6_transfer   | similar                                                                                                                                     | state_sector_ct   | carnegie_ct   | counted_pct   | nicknames   | cohort_size   |
|----------|-------------------------------------|------------|---------|---------|------------------------|----------------------------------------------------|--------|------------|------------|-----------|--------------------------------|-----------------|--------------------|--------------------------|-------------------------|-------------------|-------------------------|------------------------|------------------------|----------|-------------|------------------|-----------------|----------------------|-------------|------------------|---------------|--------------------|------------------|-----------------------|------------------|-----------------------|--------------|-------------------|----------------|---------------------|----------------|---------------------|------------|-------------------------|-----------------------------------|---------------------------|-------------------------------------|-------------------------|-----------------------------------|---------------------------|-------------------------------------|----------------------------|--------------------------------------|------------------------------|----------------------------------------|----------------------------|--------------------------------------|------------------------------|----------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------|-------------------|---------------|---------------|-------------|---------------|
| 100654   | Alabama A&M University              | Normal     | Alabama | 4-year  | Public                 | Masters Colleges and Universities--larger programs | X      | NULL       | -86.568502 | 34.783368 | www.aamu.edu/                  | 4051            | 14.2               | 18.8                     | 21.5                    | 105331            | 75743                   | 66436                  | 90                     | 93.8     | 3906        | 33               | 823             | 0                    | 7142        | 72               | NULL          | NULL               | 10.0             | 15                    | 29.1             | 14                    | 71.2         | 98                | 63.1           | 17                  | 82.8           | 89                  | 2010       | 14.7                    | 2                                 | 36.5                      | 16.1                                | 33                      | 5.3                               | 12.5                      | 14.6                                | 15.7                       | 1.5                                  | 40.9                         | 17.2                                   | 36.4                       | 5.6                                  | 17.2                         | 11.1                                   | 232937|100724|405997|113607|139533|144005|228501|101480|131876|144759|419509|176479|243197|228529|372222|228431|206695|139366|159993|224147 | 13                | 386           | 99.7|07       | NULL        | 882           |
| 100663   | University of Alabama at Birmingham | Birmingham | Alabama | 4-year  | Public                 | Research Universities--very high research activity | NULL   | NULL       | -86.80917  | 33.50223  | www.uab.edu                    | 11502           | 20.9               | 18.8                     | 21.5                    | 136546            | 75743                   | 66436                  | 97                     | 72.7     | 10032       | 67               | 1146            | 84                   | 6088        | 50               | 24136         | 93                 | 29.4             | 67                    | 53.5             | 66                    | 35.1         | 39                | 80.2           | 70                  | 92.4           | 98                  | 2011       | 22.3                    | 2.9                               | 34.2                      | 19.2                                | 42.6                    | 10.5                              | 7.9                       | 13.1                                | NULL                       | NULL                                 | NULL                         | NULL                                   | NULL                       | NULL                                 | NULL                         | NULL                                   | 196060|180461|201885|145600|209542|236939|126818|230764|104151|104179|157085|171100|153603|141574|155317|110714|137351|126562|243780|196088 | 13                | 106           | 56.0|07       | UAB         | 1376          |
| 100690   | Amridge University                  | Montgomery | Alabama | 4-year  | Private not-for-profit | Baccalaureate Colleges--Arts & Sciences            | NULL   | NULL       | -86.17401  | 32.362609 | www.amridgeuniversity.edu      | 322             | 29.9               | 17.8                     | 22.5                    | 58414             | 92268                   | 101725                 | 30                     | 62.7     | 294         | 12               | NULL            | NULL                 | 2540        | 1                | 302           | 1                  | 0.0              | 0                     | 66.7             | 72                    | 68.4         | 91                | 37.5           | 2                   | 67.2           | 71                  | NULL       | NULL                    | NULL                              | NULL                      | NULL                                | NULL                    | NULL                              | NULL                      | NULL                                | NULL                       | NULL                                 | NULL                         | NULL                                   | NULL                       | NULL                                 | NULL                         | NULL                                   | 217925|441511|205124|247825|197647|221856|135364|117575|164207|193070|199315|166054|367893|183804|439701|193052|197744|193247|137777|176789 | 16                | 252           | 100.0|07      | NULL        | 3             |
| 100706   | University of Alabama at Huntsville | Huntsville | Alabama | 4-year  | Public                 | Research Universities--very high research activity | NULL   | NULL       | -86.63842  | 34.722818 | www.uah.edu                    | 5696            | 20.9               | 18.8                     | 21.5                    | 64418             | 75743                   | 66436                  | 61                     | 74.4     | 5000        | 40               | 1180            | 89                   | 6647        | 63               | 11502         | 81                 | 16.5             | 34                    | 48.4             | 54                    | 32.8         | 32                | 81.0           | 72                  | 65.5           | 56                  | 2010       | 12.8                    | 4.7                               | 42.8                      | 18.3                                | 43                      | 14.5                              | 10.2                      | 11.7                                | 0                          | 0                                    | 0                            | 0                                      | 0                          | 0                                    | 0                            | 0                                      | 232186|133881|196103|196413|207388|171128|190044|178402|185828|202480|183044|132903|163268|223232|157289|100858|216339|230728|165334|204024 | 13                | 106           | 43.1|07       | UAH         | 759           |
| 100724   | Alabama State University            | Montgomery | Alabama | 4-year  | Public                 | Masters Colleges and Universities--larger programs | X      | NULL       | -86.295677 | 32.364317 | www.alasu.edu/email/index.aspx | 5356            | 11.6               | 18.8                     | 21.5                    | 132407            | 75743                   | 66436                  | 96                     | 91.0     | 5035        | 41               | 830             | 1                    | 7256        | 74               | 13202         | 84                 | 8.8              | 11                    | 25.2             | 9                     | 82.7         | 100               | 62.2           | 15                  | 67.0           | 58                  | NULL       | NULL                    | NULL                              | NULL                      | NULL                                | NULL                    | NULL                              | NULL                      | NULL                                | NULL                       | NULL                                 | NULL                         | NULL                                   | NULL                       | NULL                                 | NULL                         | NULL                                   | 100654|232937|242617|243197|144005|241739|235422|243601|113607|405997|139533|190114|228501|131876|101480|144759|419509|176479|228529|372222 | 13                | 386           | 88.0|07       | ASU         | 1351          |
| ...      | ...                                 | ...        | ...     | ...     | ...                    | ...                                                | ...    | ...        | ...        | ...       | ...                            | ...             | ...                | ...                      | ...                     | ...               | ...                     | ...                    | ...                    | ...      | ...         | ...              | ...             | ...                  | ...         | ...              | ...           | ...                | ...              | ...                   | ...              | ...                   | ...          | ...               | ...            | ...                 | ...            | ...                 | ...        | ...                     | ...                               | ...                       | ...                                 | ...                     | ...                               | ...                       | ...                                 | ...                        | ...                                  | ...                          | ...                                    | ...                        | ...                                  | ...                          | ...                                    | ...                                                                                                                                         | ...               | ...           | ...           | ...         | ...           |
*/
CREATE TABLE institution_details (
    unitid INTEGER NOT NULL PRIMARY KEY,
        -- <example>100654</example>
    chronname TEXT NOT NULL,
        -- <example>'Alabama A&M University'</example>
    city TEXT NOT NULL,
        -- <example>'Normal'</example>
    state TEXT NOT NULL,
        -- <example>'Alabama'</example>
    level TEXT NOT NULL,
        -- <values>{'2-year', '4-year'}</values>
    control TEXT NOT NULL,
        -- <values>{'Private for-profit', 'Private not-for-profit', 'Public'}</values>
    basic TEXT NOT NULL,
        -- <example>'Masters Colleges and Universities--larger programs'</example>
    hbcu TEXT NOT NULL,
        -- <values>{'NULL', 'X'}</values>
    flagship TEXT NOT NULL,
        -- <values>{'NULL', 'X'}</values>
    long_x REAL NOT NULL,
        -- <example>-86.569</example>
    lat_y REAL NOT NULL,
        -- <example>34.783</example>
    site TEXT NULL,
        -- <example>'www.aamu.edu/'</example>
    student_count INTEGER NOT NULL,
        -- <example>4051</example>
    awards_per_value REAL NOT NULL,
        -- <example>14.200</example>
    awards_per_state_value REAL NOT NULL,
        -- <example>18.800</example>
    awards_per_natl_value REAL NOT NULL,
        -- <example>21.500</example>
    exp_award_value INTEGER NOT NULL,
        -- <example>105331</example>
    exp_award_state_value INTEGER NOT NULL,
        -- <example>75743</example>
    exp_award_natl_value INTEGER NOT NULL,
        -- <example>66436</example>
    exp_award_percentile INTEGER NOT NULL,
        -- <example>90</example>
    ft_pct REAL NULL,
        -- <example>93.800</example>
    fte_value INTEGER NOT NULL,
        -- <example>3906</example>
    fte_percentile INTEGER NOT NULL,
        -- <example>33</example>
    med_sat_value TEXT NOT NULL,
        -- <example>'823'</example>
    med_sat_percentile TEXT NOT NULL,
        -- <example>'0'</example>
    aid_value INTEGER NULL,
        -- <example>7142</example>
    aid_percentile INTEGER NULL,
        -- <example>72</example>
    endow_value TEXT NOT NULL,
        -- <example>'NULL'</example>
    endow_percentile TEXT NOT NULL,
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
    vsa_grad_after4_first TEXT NOT NULL,
        -- <example>'14.7'</example>
    vsa_grad_elsewhere_after4_first TEXT NOT NULL,
        -- <example>'2'</example>
    vsa_enroll_after4_first TEXT NOT NULL,
        -- <example>'36.5'</example>
    vsa_enroll_elsewhere_after4_first TEXT NOT NULL,
        -- <example>'16.1'</example>
    vsa_grad_after6_first TEXT NOT NULL,
        -- <example>'33'</example>
    vsa_grad_elsewhere_after6_first TEXT NOT NULL,
        -- <example>'5.3'</example>
    vsa_enroll_after6_first TEXT NOT NULL,
        -- <example>'12.5'</example>
    vsa_enroll_elsewhere_after6_first TEXT NOT NULL,
        -- <example>'14.6'</example>
    vsa_grad_after4_transfer TEXT NOT NULL,
        -- <example>'15.7'</example>
    vsa_grad_elsewhere_after4_transfer TEXT NOT NULL,
        -- <example>'1.5'</example>
    vsa_enroll_after4_transfer TEXT NOT NULL,
        -- <example>'40.9'</example>
    vsa_enroll_elsewhere_after4_transfer TEXT NOT NULL,
        -- <example>'17.2'</example>
    vsa_grad_after6_transfer TEXT NOT NULL,
        -- <example>'36.4'</example>
    vsa_grad_elsewhere_after6_transfer TEXT NOT NULL,
        -- <example>'5.6'</example>
    vsa_enroll_after6_transfer TEXT NOT NULL,
        -- <example>'17.2'</example>
    vsa_enroll_elsewhere_after6_transfer TEXT NOT NULL,
        -- <example>'11.1'</example>
    similar TEXT NOT NULL,
        -- <example>'232937|100724|405997|113607|139533|144005|228501|1...7|228529|372222|228431|206695|139366|159993|224147'</example>
    state_sector_ct INTEGER NOT NULL,
        -- <example>13</example>
    carnegie_ct INTEGER NOT NULL,
        -- <example>386</example>
    counted_pct TEXT NOT NULL,
        -- <example>'99.7|07'</example>
    nicknames TEXT NOT NULL,
        -- <example>'NULL'</example>
    cohort_size INTEGER NULL
        -- <example>882</example>
);

/*
Schema: NULLTable: institution_grads
Rows: 1302102
Sample rows:
| unitid   | year   | gender   | race   | cohort   | grad_cohort   | grad_100   | grad_150   | grad_100_rate   | grad_150_rate   |
|----------|--------|----------|--------|----------|---------------|------------|------------|-----------------|-----------------|
| 100760   | 2011   | B        | X      | 2y all   | 446           | 73         | 105        | 16.4            | 23.5            |
| 100760   | 2011   | M        | X      | 2y all   | 185           | NULL       | 40         | NULL            | 21.6            |
| 100760   | 2011   | F        | X      | 2y all   | 261           | NULL       | 65         | NULL            | 24.9            |
| 100760   | 2011   | B        | W      | 2y all   | 348           | NULL       | 86         | NULL            | 24.7            |
| 100760   | 2011   | M        | W      | 2y all   | 162           | NULL       | 35         | NULL            | 21.6            |
| ...      | ...    | ...      | ...    | ...      | ...           | ...        | ...        | ...             | ...             |
*/
CREATE TABLE institution_grads (
    unitid INTEGER NOT NULL,
        -- <example>100760</example>
        -- <fk> -> institution_details.unitid</fk>
    year INTEGER NOT NULL,
        -- <example>2011</example>
    gender TEXT NOT NULL,
        -- <values>{'B', 'F', 'M'}</values>
    race TEXT NOT NULL,
        -- <values>{'A', 'Ai', 'B', 'H', 'W', 'X'}</values>
    cohort TEXT NOT NULL,
        -- <values>{'2y all', '4y bach', '4y other'}</values>
    grad_cohort TEXT NOT NULL,
        -- <example>'446'</example>
    grad_100 TEXT NOT NULL,
        -- <example>'73'</example>
    grad_150 TEXT NOT NULL,
        -- <example>'105'</example>
    grad_100_rate TEXT NOT NULL,
        -- <example>'16.4'</example>
    grad_150_rate TEXT NOT NULL,
        -- <example>'23.5'</example>
    FOREIGN KEY (unitid) REFERENCES institution_details(unitid)
);

/*
Schema: NULLTable: state_sector_details
Rows: 312
Sample rows:
| stateid   | state         | state_post   | level   | control                | schools_count   | counted_pct   | awards_per_state_value   | awards_per_natl_value   | exp_award_state_value   | exp_award_natl_value   | state_appr_value   | state_appr_rank   | grad_rate_rank   | awards_per_rank   |
|-----------|---------------|--------------|---------|------------------------|-----------------|---------------|--------------------------|-------------------------|-------------------------|------------------------|--------------------|-------------------|------------------|-------------------|
| 0         | United States | U.S.         | 4-year  | Public                 | 632             | NULL          | NULL                     | 21.5                    | NULL                    | 66436                  | NULL               | NULL              | 23               | NULL              |
| 0         | United States | U.S.         | 4-year  | Private not-for-profit | 1180            | NULL          | NULL                     | 22.5                    | NULL                    | 101725                 | NULL               | NULL              | 18               | NULL              |
| 0         | United States | U.S.         | 4-year  | Private for-profit     | 527             | NULL          | NULL                     | 24.6                    | NULL                    | 38763                  | NULL               | NULL              | 8                | NULL              |
| 0         | United States | U.S.         | 2-year  | Public                 | 926             | NULL          | NULL                     | 16.5                    | NULL                    | 37780                  | NULL               | NULL              | 25               | NULL              |
| 0         | United States | U.S.         | 2-year  | Private not-for-profit | 68              | NULL          | NULL                     | 25.9                    | NULL                    | 34510                  | NULL               | NULL              | 12               | NULL              |
| ...       | ...           | ...          | ...     | ...                    | ...             | ...           | ...                      | ...                     | ...                     | ...                    | ...                | ...               | ...              | ...               |
*/
CREATE TABLE state_sector_details (
    stateid INTEGER NOT NULL,
        -- <example>0</example>
    state TEXT NOT NULL,
        -- <example>'United States'</example>
        -- <fk> -> institution_details.state</fk>
    state_post TEXT NOT NULL,
        -- <example>'U.S.'</example>
    level TEXT NOT NULL,
        -- <values>{'2-year', '4-year'}</values>
    control TEXT NOT NULL,
        -- <values>{'Private for-profit', 'Private not-for-profit', 'Public'}</values>
    schools_count INTEGER NOT NULL,
        -- <example>632</example>
    counted_pct TEXT NOT NULL,
        -- <example>'NULL'</example>
    awards_per_state_value TEXT NOT NULL,
        -- <example>'NULL'</example>
    awards_per_natl_value REAL NOT NULL,
        -- <example>21.500</example>
    exp_award_state_value TEXT NOT NULL,
        -- <example>'NULL'</example>
    exp_award_natl_value INTEGER NOT NULL,
        -- <example>66436</example>
    state_appr_value TEXT NOT NULL,
        -- <example>'NULL'</example>
    state_appr_rank TEXT NOT NULL,
        -- <example>'NULL'</example>
    grad_rate_rank TEXT NOT NULL,
        -- <example>'23'</example>
    awards_per_rank TEXT NOT NULL,
        -- <example>'NULL'</example>
    PRIMARY KEY (stateid, level, control),
    FOREIGN KEY (state) REFERENCES institution_details(state)
);

/*
Schema: NULLTable: state_sector_grads
Rows: 84942
Sample rows:
| stateid   | state   | state_abbr   | control            | level   | year   | gender   | race   | cohort   | grad_cohort   | grad_100   | grad_150   | grad_100_rate   | grad_150_rate   | grad_cohort_ct   |
|-----------|---------|--------------|--------------------|---------|--------|----------|--------|----------|---------------|------------|------------|-----------------|-----------------|------------------|
| 1         | Alabama | AL           | Private for-profit | 4-year  | 2011   | B        | A      | 4y bach  | 0             | 0          | 0          | NULL            | NULL            | 9                |
| 1         | Alabama | AL           | Private for-profit | 4-year  | 2011   | B        | Ai     | 4y bach  | 1             | 0          | 0          | 0               | 0               | 9                |
| 1         | Alabama | AL           | Private for-profit | 4-year  | 2011   | B        | B      | 4y bach  | 51            | 2          | 3          | 3.9             | 5.9             | 9                |
| 1         | Alabama | AL           | Private for-profit | 4-year  | 2011   | B        | H      | 4y bach  | 1             | 0          | 0          | 0               | 0               | 9                |
| 1         | Alabama | AL           | Private for-profit | 4-year  | 2011   | B        | W      | 4y bach  | 66            | 15         | 18         | 22.7            | 27.3            | 9                |
| ...       | ...     | ...          | ...                | ...     | ...    | ...      | ...    | ...      | ...           | ...        | ...        | ...             | ...             | ...              |
*/
CREATE TABLE state_sector_grads (
    stateid INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> state_sector_details.stateid</fk>
    state TEXT NOT NULL,
        -- <example>'Alabama'</example>
        -- <fk> -> institution_details.state</fk>
    state_abbr TEXT NOT NULL,
        -- <example>'AL'</example>
    control TEXT NOT NULL,
        -- <values>{'Private for-profit', 'Private not-for-profit', 'Public'}</values>
    level TEXT NOT NULL,
        -- <values>{'2-year', '4-year'}</values>
    year INTEGER NOT NULL,
        -- <example>2011</example>
    gender TEXT NOT NULL,
        -- <values>{'B', 'F', 'M'}</values>
    race TEXT NOT NULL,
        -- <values>{'A', 'Ai', 'B', 'H', 'W', 'X'}</values>
    cohort TEXT NOT NULL,
        -- <values>{'2y all', '4y bach', '4y other'}</values>
    grad_cohort TEXT NOT NULL,
        -- <example>'0'</example>
    grad_100 TEXT NOT NULL,
        -- <example>'0'</example>
    grad_150 TEXT NOT NULL,
        -- <example>'0'</example>
    grad_100_rate TEXT NOT NULL,
        -- <example>'NULL'</example>
    grad_150_rate TEXT NOT NULL,
        -- <example>'NULL'</example>
    grad_cohort_ct INTEGER NOT NULL,
        -- <example>9</example>
    FOREIGN KEY (state) REFERENCES institution_details(state),
    FOREIGN KEY (stateid) REFERENCES state_sector_details(stateid)
);
```