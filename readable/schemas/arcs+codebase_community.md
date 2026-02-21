```sql
-- Database: codebase_community

/*
Schema: NULL
Table: BADGES
Rows: 79851
Sample rows:
| Id   | UserId   | Name    | Date                  |
|------|----------|---------|-----------------------|
| 1    | 5        | Teacher | 2010-07-19 19:39:07.0 |
| 2    | 6        | Teacher | 2010-07-19 19:39:07.0 |
| 3    | 8        | Teacher | 2010-07-19 19:39:07.0 |
| 4    | 23       | Teacher | 2010-07-19 19:39:07.0 |
| 5    | 36       | Teacher | 2010-07-19 19:39:07.0 |
| ...  | ...      | ...     | ...                   |
*/
CREATE TABLE BADGES (
    "Id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "UserId" INTEGER NOT NULL,
        -- <example>5</example>
        -- <fk> -> USERS."Id"</fk>
    "Name" TEXT NOT NULL,
        -- <example>'Teacher'</example>
    "Date" DATETIME NOT NULL,
        -- <example>'2010-07-19 19:39:07.0'</example>
    FOREIGN KEY ("UserId") REFERENCES USERS("Id")
);

/*
Schema: NULL
Table: COMMENTS
Rows: 174285
Sample rows:
| Id   | PostId   | Score   | Text                                                                                                                          | CreationDate          | UserId   | UserDisplayName   |
|------|----------|---------|-------------------------------------------------------------------------------------------------------------------------------|-----------------------|----------|-------------------|
| 1    | 3        | 5       | Could be a poster child fo argumentative and subjective.  At the least, need to define 'valuable'.                            | 2010-07-19 19:15:52.0 | 13.0     | [NULL]            |
| 2    | 5        | 0       | Yes, R is nice- but WHY is it 'valuable'.                                                                                     | 2010-07-19 19:16:14.0 | 13.0     | [NULL]            |
| 3    | 9        | 0       | Again- why?  How would I convince my boss to use this over, say, Excel.                                                       | 2010-07-19 19:18:54.0 | 13.0     | [NULL]            |
| 4    | 5        | 11      | It's mature, well supported, and a standard within certain scientific communities (popular in our AI department, for example) | 2010-07-19 19:19:56.0 | 37.0     | [NULL]            |
| 5    | 3        | 1       | Define "valuable"...                                                                                                          | 2010-07-19 19:20:28.0 | 5.0      | [NULL]            |
| ...  | ...      | ...     | ...                                                                                                                           | ...                   | ...      | ...               |
*/
CREATE TABLE COMMENTS (
    "Id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "PostId" INTEGER NOT NULL,
        -- <example>3</example>
        -- <fk> -> POSTS."Id"</fk>
    "Score" INTEGER NOT NULL,
        -- <example>5</example>
    "Text" TEXT NOT NULL,
        -- <example>'Could be a poster child fo argumentative and subjective.  At the least, need to define 'valuable'.'</example>
    "CreationDate" DATETIME NOT NULL,
        -- <example>'2010-07-19 19:15:52.0'</example>
    "UserId" INTEGER NULL,
        -- <example>13</example>
        -- <fk> -> USERS."Id"</fk>
    "UserDisplayName" TEXT NULL,
        -- <example>'user28'</example>
    FOREIGN KEY ("PostId") REFERENCES POSTS("Id"),
    FOREIGN KEY ("UserId") REFERENCES USERS("Id")
);

/*
Schema: NULL
Table: postHistory
Rows: 303155
Sample rows:
| Id   | PostHistoryTypeId   | PostId   | RevisionGUID                         | CreationDate          | UserId   | Text                                                                                                                                       | Comment   | UserDisplayName   |
|------|---------------------|----------|--------------------------------------|-----------------------|----------|--------------------------------------------------------------------------------------------------------------------------------------------|-----------|-------------------|
| 1    | 2                   | 1        | e58bf7fd-e60f-4c58-a6e4-dfc91cf98a69 | 2010-07-19 19:12:12.0 | 8        | How should I elicit prior distributions from experts when fitting a Bayesian model?                                                        |           |                   |
| 2    | 1                   | 1        | e58bf7fd-e60f-4c58-a6e4-dfc91cf98a69 | 2010-07-19 19:12:12.0 | 8        | Eliciting priors from experts                                                                                                              |           |                   |
| 3    | 3                   | 1        | e58bf7fd-e60f-4c58-a6e4-dfc91cf98a69 | 2010-07-19 19:12:12.0 | 8        | <bayesian><prior><elicitation>                                                                                                             |           |                   |
| 4    | 2                   | 2        | 18bf9150-f1cb-432d-b7b7-26d2f8e33581 | 2010-07-19 19:12:57.0 | 24       | In many different statistical methods there is an "assumption of normality".  What is "normality" and how do I know if there is normality? |           |                   |
| 5    | 1                   | 2        | 18bf9150-f1cb-432d-b7b7-26d2f8e33581 | 2010-07-19 19:12:57.0 | 24       | What is normality?                                                                                                                         |           |                   |
| ...  | ...                 | ...      | ...                                  | ...                   | ...      | ...                                                                                                                                        | ...       | ...               |
*/
CREATE TABLE postHistory (
    "Id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "PostHistoryTypeId" INTEGER NOT NULL,
        -- <example>2</example>
    "PostId" INTEGER NOT NULL,
        -- <example>1</example>
        -- <fk> -> POSTS."Id"</fk>
    "RevisionGUID" TEXT NOT NULL,
        -- <example>'e58bf7fd-e60f-4c58-a6e4-dfc91cf98a69'</example>
    "CreationDate" DATETIME NOT NULL,
        -- <example>'2010-07-19 19:12:12.0'</example>
    "UserId" INTEGER NULL,
        -- <example>8</example>
        -- <fk> -> USERS."Id"</fk>
    "Text" TEXT NOT NULL,
        -- <example>'How should I elicit prior distributions from experts when fitting a Bayesian model?'</example>
    "Comment" TEXT NOT NULL,
        -- <example>''</example>
    "UserDisplayName" TEXT NOT NULL,
        -- <example>''</example>
    FOREIGN KEY ("PostId") REFERENCES POSTS("Id"),
    FOREIGN KEY ("UserId") REFERENCES USERS("Id")
);

/*
Schema: NULL
Table: postLinks
Rows: 11102
Sample rows:
| Id   | CreationDate          | PostId   | RelatedPostId   | LinkTypeId   |
|------|-----------------------|----------|-----------------|--------------|
| 108  | 2010-07-21 14:47:33.0 | 395      | 173             | 1            |
| 145  | 2010-07-23 16:30:41.0 | 548      | 539             | 1            |
| 217  | 2010-07-26 20:12:15.0 | 375      | 30              | 1            |
| 263  | 2010-07-27 16:00:22.0 | 769      | 31              | 1            |
| 264  | 2010-07-27 16:00:22.0 | 769      | 6               | 1            |
| ...  | ...                   | ...      | ...             | ...          |
*/
CREATE TABLE postLinks (
    "Id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>108</example>
    "CreationDate" DATETIME NOT NULL,
        -- <example>'2010-07-21 14:47:33.0'</example>
    "PostId" INTEGER NOT NULL,
        -- <example>395</example>
        -- <fk> -> POSTS."Id"</fk>
    "RelatedPostId" INTEGER NOT NULL,
        -- <example>173</example>
        -- <fk> -> POSTS."Id"</fk>
    "LinkTypeId" INTEGER NOT NULL,
        -- <example>1</example>
    FOREIGN KEY ("PostId") REFERENCES POSTS("Id"),
    FOREIGN KEY ("RelatedPostId") REFERENCES POSTS("Id")
);

/*
Schema: NULL
Table: POSTS
Rows: 91966
Sample rows:
| Id   | PostTypeId   | AcceptedAnswerId   | CreaionDate           | Score   | ViewCount   | Body                                                                                                                                                                                                       | OwnerUserId   | LasActivityDate       | Title                                                             | Tags                                      | AnswerCount   | CommentCount   | FavoriteCount   | LastEditorUserId   | LastEditDate          | CommunityOwnedDate    | ParentId   | ClosedDate   | OwnerDisplayName   | LastEditorDisplayName   |
|------|--------------|--------------------|-----------------------|---------|-------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|---------------|-----------------------|-------------------------------------------------------------------|-------------------------------------------|---------------|----------------|-----------------|--------------------|-----------------------|-----------------------|------------|--------------|--------------------|-------------------------|
| 1    | 1            | 15.0               | 2010-07-19 19:12:12.0 | 23      | 1278.0      | <p>How should I elicit prior distributions from experts when fitting a Bayesian model?</p>                                                                                                                 | 8             | 2010-09-15 21:08:26.0 | Eliciting priors from experts                                     | <bayesian><prior><elicitation>            | 5.0           | 1              | 14.0            | [NULL]             | [NULL]                | [NULL]                | [NULL]     | [NULL]       | [NULL]             | [NULL]                  |
| 2    | 1            | 59.0               | 2010-07-19 19:12:57.0 | 22      | 8198.0      | <p>In many different statistical methods there is an "assumption of normality".  What is "normality" and how do I know if there is normality?</p>                                                          | 24            | 2012-11-12 09:21:54.0 | What is normality?                                                | <distributions><normality>                | 7.0           | 1              | 8.0             | 88.0               | 2010-08-07 17:56:44.0 | [NULL]                | [NULL]     | [NULL]       | [NULL]             | [NULL]                  |
| 3    | 1            | 5.0                | 2010-07-19 19:13:28.0 | 54      | 3613.0      | <p>What are some valuable Statistical Analysis open source projects available right now?</p>

<p>Edi...pointed out by Sharpie, valuable could mean helping you get things done faster or more cheaply.</p>                                                                                                                                                                                                            | 18            | 2013-05-27 14:48:36.0 | What are some valuable Statistical Analysis open source projects? | <software><open-source>                   | 19.0          | 4              | 36.0            | 183.0              | 2011-02-12 05:50:03.0 | 2010-07-19 19:13:28.0 | [NULL]     | [NULL]       | [NULL]             | [NULL]                  |
| 4    | 1            | 135.0              | 2010-07-19 19:13:31.0 | 13      | 5224.0      | <p>I have two groups of data.  Each with a different distribution of multiple variables.  I'm trying... not these two groups are significantly different and how do I do that in SAS or R (or Orange)?</p> | 23            | 2010-09-08 03:00:19.0 | Assessing the significance of differences in distributions        | <distributions><statistical-significance> | 5.0           | 2              | 2.0             | [NULL]             | [NULL]                | [NULL]                | [NULL]     | [NULL]       | [NULL]             | [NULL]                  |
| 5    | 2            | [NULL]             | 2010-07-19 19:14:43.0 | 81      | [NULL]      | <p>The R-project</p>

<p><a href="http://www.r-project.org/">http://www.r-project.org/</a></p>

<p>R...torials <a href="http://gettinggeneticsdone.blogspot.com/search/label/ggplot2">here</a>.</li>
</ul>                                                                                                                                                                                                            | 23            | 2010-07-19 19:21:15.0 | [NULL]                                                            | [NULL]                                    | [NULL]        | 3              | [NULL]          | 23.0               | 2010-07-19 19:21:15.0 | 2010-07-19 19:14:43.0 | 3.0        | [NULL]       | [NULL]             | [NULL]                  |
| ...  | ...          | ...                | ...                   | ...     | ...         | ...                                                                                                                                                                                                        | ...           | ...                   | ...                                                               | ...                                       | ...           | ...            | ...             | ...                | ...                   | ...                   | ...        | ...          | ...                | ...                     |
*/
CREATE TABLE POSTS (
    "Id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "PostTypeId" INTEGER NOT NULL,
        -- <example>1</example>
    "AcceptedAnswerId" INTEGER NULL,
        -- <example>15</example>
    "CreaionDate" DATETIME NOT NULL,
        -- <example>'2010-07-19 19:12:12.0'</example>
    "Score" INTEGER NOT NULL,
        -- <example>23</example>
    "ViewCount" INTEGER NULL,
        -- <example>1278</example>
    "Body" TEXT NULL,
        -- <example>'<p>How should I elicit prior distributions from experts when fitting a Bayesian model?</p>
'</example>
    "OwnerUserId" INTEGER NULL,
        -- <example>8</example>
        -- <fk> -> USERS."Id"</fk>
    "LasActivityDate" DATETIME NOT NULL,
        -- <example>'2010-09-15 21:08:26.0'</example>
    "Title" TEXT NULL,
        -- <example>'Eliciting priors from experts'</example>
    "Tags" TEXT NULL,
        -- <example>'<bayesian><prior><elicitation>'</example>
    "AnswerCount" INTEGER NULL,
        -- <example>5</example>
    "CommentCount" INTEGER NOT NULL,
        -- <example>1</example>
    "FavoriteCount" INTEGER NULL,
        -- <example>14</example>
    "LastEditorUserId" INTEGER NULL,
        -- <example>88</example>
        -- <fk> -> USERS."Id"</fk>
    "LastEditDate" DATETIME NULL,
        -- <example>'2010-08-07 17:56:44.0'</example>
    "CommunityOwnedDate" DATETIME NULL,
        -- <example>'2010-07-19 19:13:28.0'</example>
    "ParentId" INTEGER NULL,
        -- <example>3</example>
        -- <fk> -> POSTS."Id"</fk>
    "ClosedDate" DATETIME NULL,
        -- <example>'2010-07-19 20:19:46.0'</example>
    "OwnerDisplayName" TEXT NULL,
        -- <example>'user28'</example>
    "LastEditorDisplayName" TEXT NULL,
        -- <example>'user28'</example>
    FOREIGN KEY ("LastEditorUserId") REFERENCES USERS("Id"),
    FOREIGN KEY ("OwnerUserId") REFERENCES USERS("Id"),
    FOREIGN KEY ("ParentId") REFERENCES POSTS("Id")
);

/*
Schema: NULL
Table: TAGS
Rows: 1032
Sample rows:
| Id   | TagName     | Count   | ExcerptPostId   | WikiPostId   |
|------|-------------|---------|-----------------|--------------|
| 1    | bayesian    | 1342    | 20258.0         | 20257.0      |
| 2    | prior       | 168     | 62158.0         | 62157.0      |
| 3    | elicitation | 6       | [NULL]          | [NULL]       |
| 4    | normality   | 191     | 67815.0         | 67814.0      |
| 5    | open-source | 13      | [NULL]          | [NULL]       |
| ...  | ...         | ...     | ...             | ...          |
*/
CREATE TABLE TAGS (
    "Id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "TagName" TEXT NOT NULL,
        -- <example>'bayesian'</example>
    "Count" INTEGER NOT NULL,
        -- <example>1342</example>
    "ExcerptPostId" INTEGER NULL,
        -- <example>20258</example>
        -- <fk> -> POSTS."Id"</fk>
    "WikiPostId" INTEGER NULL,
        -- <example>20257</example>
    FOREIGN KEY ("ExcerptPostId") REFERENCES POSTS("Id")
);

/*
Schema: NULL
Table: USERS
Rows: 40325
Sample rows:
| Id   | Reputation   | CreationDate          | DisplayName   | LastAccessDate        | WebsiteUrl                     | Location           | AboutMe   | Views   | UpVotes   | DownVotes   | AccountId   | Age    | ProfileImageUrl                    |
|------|--------------|-----------------------|---------------|-----------------------|--------------------------------|--------------------|-----------|---------|-----------|-------------|-------------|--------|------------------------------------|
| -1   | 1            | 2010-07-19 06:55:26.0 | Community     | 2010-07-19 06:55:26.0 | http://meta.stackexchange.com/ | on the server farm | <p>Hi, I'm not really a person.</p>

<p>I'm a background process that helps keep this site clean!</p...</li>
<li><a href="http://meta.stackexchange.com/a/92006">Remove abandoned questions</a></li>
</ul>           | 0       | 5007      | 1920        | -1          | [NULL] | [NULL]                             |
| 2    | 101          | 2010-07-19 14:01:36.0 | Geoff Dalgas  | 2013-11-12 22:07:23.0 | http://stackoverflow.com       | Corvallis, OR      | <p>Developer on the StackOverflow team.  Find me on</p>

<p><a href="http://www.twitter.com/SuperDal...9/05/welcome-stack-overflow-valued-associate-00003/">Stack Overflow Valued Associate #00003</a></p>           | 25      | 3         | 0           | 2           | 37.0   | [NULL]                             |
| 3    | 101          | 2010-07-19 15:34:50.0 | Jarrod Dixon  | 2014-08-08 06:42:58.0 | http://stackoverflow.com       | New York, NY       | <p><a href="http://blog.stackoverflow.com/2009/01/welcome-stack-overflow-valued-associate-00002/">De...arrod_dixon" rel="nofollow">jarrod_dixon</a></li>
<li>Email me: jarrod.m.dixon@gmail.com</li>
</ul>           | 22      | 19        | 0           | 3           | 35.0   | [NULL]                             |
| 4    | 101          | 2010-07-19 19:03:27.0 | Emmett        | 2014-01-02 09:31:02.0 | http://minesweeperonline.com   | San Francisco, CA  | <p>currently at a startup in SF</p>

<p>formerly a dev at Stack Exchange :)</p>           | 11      | 0         | 0           | 1998        | 28.0   | http://i.stack.imgur.com/d1oHX.jpg |
| 5    | 6792         | 2010-07-19 19:03:57.0 | Shane         | 2014-08-13 00:23:47.0 | http://www.statalgo.com        | New York, NY       | <p>Quantitative researcher focusing on statistics and machine learning methods in finance. Primarily...://area51.stackexchange.com/proposals/117/quantitative-finance?referrer=EZoOPpokWeo1</a></li>
</ul>           | 1145    | 662       | 5           | 54503       | 35.0   | [NULL]                             |
| ...  | ...          | ...                   | ...           | ...                   | ...                            | ...                | ...       | ...     | ...       | ...         | ...         | ...    | ...                                |
*/
CREATE TABLE USERS (
    "Id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>-1</example>
    "Reputation" INTEGER NOT NULL,
        -- <example>1</example>
    "CreationDate" DATETIME NOT NULL,
        -- <example>'2010-07-19 06:55:26.0'</example>
    "DisplayName" TEXT NOT NULL,
        -- <example>'Community'</example>
    "LastAccessDate" DATETIME NOT NULL,
        -- <example>'2010-07-19 06:55:26.0'</example>
    "WebsiteUrl" TEXT NULL,
        -- <example>'http://meta.stackexchange.com/'</example>
    "Location" TEXT NULL,
        -- <example>'on the server farm'</example>
    "AboutMe" TEXT NULL,
        -- <example>'<p>Hi, I'm not really a person.</p>

<p>I'm a back.../92006">Remove abandoned questions</a></li>
</ul>
'</example>
    "Views" INTEGER NOT NULL,
        -- <example>0</example>
    "UpVotes" INTEGER NOT NULL,
        -- <example>5007</example>
    "DownVotes" INTEGER NOT NULL,
        -- <example>1920</example>
    "AccountId" INTEGER NOT NULL,
        -- <example>-1</example>
    "Age" INTEGER NULL,
        -- <example>37</example>
    "ProfileImageUrl" TEXT NULL
        -- <example>'http://i.stack.imgur.com/d1oHX.jpg'</example>
);

/*
Schema: NULL
Table: VOTES
Rows: 38930
Sample rows:
| Id   | PostId   | VoteTypeId   | CreationDate   | UserId   | BountyAmount   |
|------|----------|--------------|----------------|----------|----------------|
| 1    | 3        | 2            | 2010-07-19     | [NULL]   | [NULL]         |
| 2    | 2        | 2            | 2010-07-19     | [NULL]   | [NULL]         |
| 3    | 5        | 2            | 2010-07-19     | [NULL]   | [NULL]         |
| 4    | 5        | 2            | 2010-07-19     | [NULL]   | [NULL]         |
| 5    | 3        | 2            | 2010-07-19     | [NULL]   | [NULL]         |
| ...  | ...      | ...          | ...            | ...      | ...            |
*/
CREATE TABLE VOTES (
    "Id" INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    "PostId" INTEGER NOT NULL,
        -- <example>3</example>
        -- <fk> -> POSTS."Id"</fk>
    "VoteTypeId" INTEGER NOT NULL,
        -- <example>2</example>
    "CreationDate" DATE NOT NULL,
        -- <example>'2010-07-19'</example>
    "UserId" INTEGER NULL,
        -- <example>58</example>
        -- <fk> -> USERS."Id"</fk>
    "BountyAmount" INTEGER NULL,
        -- <example>50</example>
    FOREIGN KEY ("PostId") REFERENCES POSTS("Id"),
    FOREIGN KEY ("UserId") REFERENCES USERS("Id")
);
```