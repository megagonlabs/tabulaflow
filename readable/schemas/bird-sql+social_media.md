```sql
-- Database: social_media

/*
Schema: NULL
Table: location
Rows: 6211
Sample rows:
| LocationID   | Country   | State       | StateCode   | City        |
|--------------|-----------|-------------|-------------|-------------|
| 1            | Albania   | Elbasan     | AL          | Elbasan     |
| 2            | Albania   | Tirane      | AL          | Tirana      |
| 3            | Algeria   | Souk Ahras  | DZ          | Souk Ahras  |
| 4            | Algeria   | Alger       | DZ          | Algiers     |
| 5            | Algeria   | Constantine | DZ          | Constantine |
| ...          | ...       | ...         | ...         | ...         |
*/
CREATE TABLE location (
    "LocationID" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "Country" TEXT NULL,
        -- <example>'Albania'</example>
    "State" TEXT NULL,
        -- <example>'Elbasan'</example>
    "StateCode" TEXT NULL,
        -- <example>'AL'</example>
    "City" TEXT NULL
        -- <example>'Elbasan'</example>
);

/*
Schema: NULL
Table: twitter
Rows: 99901
Sample rows:
| TweetID               | Weekday   | Hour   | Day   | Lang   | IsReshare   | Reach   | RetweetCount   | Likes   | Klout   | Sentiment   | text                                                                                                                                                                                                        | LocationID   | UserID        |
|-----------------------|-----------|--------|-------|--------|-------------|---------|----------------|---------|---------|-------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------|---------------|
| tw-682712873332805633 | Thursday  | 17     | 31    | en     | FALSE       | 44      | 0              | 0       | 35      | 0.0         | We are hiring: Senior Software Engineer - Proto http://www.reqcloud.com/jobs/719865/?k=0LaPxXuFwczs1...twitter&utm_campaign=reqCloud_JobPost #job @awscloud #job #protocol #networking #aws #mediastreaming | 3751         | tw-40932430   |
| tw-682713045357998080 | Thursday  | 17     | 31    | en     | TRUE        | 1810    | 5              | 0       | 53      | 2.0         | RT @CodeMineStatus: This is true Amazon Web Services https://aws.amazon.com/ #php #html #html5 #css #webdesign #seo #java #javascript htt                                                                   | 3989         | tw-3179389829 |
| tw-682713219375476736 | Thursday  | 17     | 31    | en     | FALSE       | 282     | 0              | 0       | 47      | 0.0         | Devops Engineer Aws Ansible Cassandra Mysql Ubuntu Ruby On Rails Jobs in Austin TX #Austin #TX #jobs...w.jobfindly.com/devops-engineer-aws-ansible-cassandra-mysql-ubuntu-ruby-on-rails-jobs-austin-tx.html | 3741         | tw-4624808414 |
| tw-682713436967579648 | Thursday  | 17     | 31    | en     | FALSE       | 2087    | 4              | 0       | 53      | 0.0         | Happy New Year to all those AWS instances of ours!                                                                                                                                                          | 3753         | tw-356447127  |
| tw-682714048199311366 | Thursday  | 17     | 31    | en     | FALSE       | 953     | 0              | 0       | 47      | 0.0         | Amazon is hiring! #Sr. #International Tax Manager - AWS in #Seattle apply now! #jobs http://neuvoo.c...national%20Tax%20Manager%20-%20AWS http://twitter.com/NeuvooAccSea/status/682714048199311366/photo/1 | 3751         | tw-3172686669 |
| ...                   | ...       | ...    | ...   | ...    | ...         | ...     | ...            | ...     | ...     | ...         | ...                                                                                                                                                                                                         | ...          | ...           |
*/
CREATE TABLE twitter (
    "TweetID" TEXT NULL PRIMARY KEY,
        -- <example>'tw-682712873332805633'</example>
    "Weekday" TEXT NULL,
        -- <values>{'Friday', 'Monday', 'Saturday', 'Sunday', 'Thursday', 'Tuesday', 'Wednesday'}</values>
    "Hour" INTEGER NULL,
        -- <example>17</example>
    "Day" INTEGER NULL,
        -- <example>31</example>
    "Lang" TEXT NULL,
        -- <example>'en'</example>
    "IsReshare" TEXT NULL,
        -- <values>{'FALSE', 'TRUE'}</values>
    "Reach" INTEGER NULL,
        -- <example>44</example>
    "RetweetCount" INTEGER NULL,
        -- <example>0</example>
    "Likes" INTEGER NULL,
        -- <example>0</example>
    "Klout" INTEGER NULL,
        -- <example>35</example>
    "Sentiment" REAL NULL,
        -- <example>0.000</example>
    "text" TEXT NULL,
        -- <example>'We are hiring: Senior Software Engineer - Proto ht...ud #job #protocol #networking #aws #mediastreaming'</example>
    "LocationID" INTEGER NULL,
        -- <example>3751</example>
        -- <fk> -> location."LocationID"</fk>
    "UserID" TEXT NULL,
        -- <example>'tw-40932430'</example>
        -- <fk> -> user."UserID"</fk>
    FOREIGN KEY ("LocationID") REFERENCES location("LocationID"),
    FOREIGN KEY ("UserID") REFERENCES user("UserID")
);

/*
Schema: NULL
Table: user
Rows: 99260
Sample rows:
| UserID        | Gender   |
|---------------|----------|
| tw-1267804344 | Unknown  |
| tw-27229880   | Male     |
| tw-199664730  | Male     |
| tw-99958381   | Unknown  |
| tw-126745533  | Male     |
| ...           | ...      |
*/
CREATE TABLE user (
    "UserID" TEXT NOT NULL PRIMARY KEY,
        -- <example>'nknow531394'</example>
    "Gender" TEXT NOT NULL
        -- <values>{'Female', 'Male', 'Unisex', 'Unknown'}</values>
);
```