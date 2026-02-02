```sql
-- Database: codebase_community

-- Table: badges (79851 rows)
CREATE TABLE badges (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    UserId INTEGER NULL,
        -- <example>5</example>
        -- <fk> -> users.Id</fk>
    Name TEXT NULL,
        -- <example>'Teacher'</example>
    Date DATETIME NULL,
        -- <example>'2010-07-19 19:39:07.0'</example>
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

-- Table: comments (174285 rows)
CREATE TABLE comments (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    PostId INTEGER NULL,
        -- <example>3</example>
        -- <fk> -> posts.Id</fk>
    Score INTEGER NULL,
        -- <example>5</example>
    Text TEXT NULL,
        -- <example>'Could be a poster child fo argumentative and subjective.  At the least, need to define 'valuable'.'</example>
    CreationDate DATETIME NULL,
        -- <example>'2010-07-19 19:15:52.0'</example>
    UserId INTEGER NULL,
        -- <example>13</example>
        -- <fk> -> users.Id</fk>
    UserDisplayName TEXT NULL,
        -- <example>'user28'</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

-- Table: postHistory (303155 rows)
CREATE TABLE postHistory (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    PostHistoryTypeId INTEGER NULL,
        -- <example>2</example>
    PostId INTEGER NULL,
        -- <example>1</example>
        -- <fk> -> posts.Id</fk>
    RevisionGUID TEXT NULL,
        -- <example>'e58bf7fd-e60f-4c58-a6e4-dfc91cf98a69'</example>
    CreationDate DATETIME NULL,
        -- <example>'2010-07-19 19:12:12.0'</example>
    UserId INTEGER NULL,
        -- <example>8</example>
        -- <fk> -> users.Id</fk>
    Text TEXT NULL,
        -- <example>'How should I elicit prior distributions from experts when fitting a Bayesian model?'</example>
    Comment TEXT NULL,
        -- <example>''</example>
    UserDisplayName TEXT NULL,
        -- <example>''</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

-- Table: postLinks (11102 rows)
CREATE TABLE postLinks (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>108</example>
    CreationDate DATETIME NULL,
        -- <example>'2010-07-21 14:47:33.0'</example>
    PostId INTEGER NULL,
        -- <example>395</example>
        -- <fk> -> posts.Id</fk>
    RelatedPostId INTEGER NULL,
        -- <example>173</example>
        -- <fk> -> posts.Id</fk>
    LinkTypeId INTEGER NULL,
        -- <example>1</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (RelatedPostId) REFERENCES posts(Id)
);

-- Table: posts (91966 rows)
CREATE TABLE posts (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    PostTypeId INTEGER NULL,
        -- <example>1</example>
    AcceptedAnswerId INTEGER NULL,
        -- <example>15</example>
    CreaionDate DATETIME NULL,
        -- <example>'2010-07-19 19:12:12.0'</example>
    Score INTEGER NULL,
        -- <example>23</example>
    ViewCount INTEGER NULL,
        -- <example>1278</example>
    Body TEXT NULL,
        -- <example>'<p>How should I elicit prior distributions from experts when fitting a Bayesian model?</p>
'</example>
    OwnerUserId INTEGER NULL,
        -- <example>8</example>
        -- <fk> -> users.Id</fk>
    LasActivityDate DATETIME NULL,
        -- <example>'2010-09-15 21:08:26.0'</example>
    Title TEXT NULL,
        -- <example>'Eliciting priors from experts'</example>
    Tags TEXT NULL,
        -- <example>'<bayesian><prior><elicitation>'</example>
    AnswerCount INTEGER NULL,
        -- <example>5</example>
    CommentCount INTEGER NULL,
        -- <example>1</example>
    FavoriteCount INTEGER NULL,
        -- <example>14</example>
    LastEditorUserId INTEGER NULL,
        -- <example>88</example>
        -- <fk> -> users.Id</fk>
    LastEditDate DATETIME NULL,
        -- <example>'2010-08-07 17:56:44.0'</example>
    CommunityOwnedDate DATETIME NULL,
        -- <example>'2010-07-19 19:13:28.0'</example>
    ParentId INTEGER NULL,
        -- <example>3</example>
        -- <fk> -> posts.Id</fk>
    ClosedDate DATETIME NULL,
        -- <example>'2010-07-19 20:19:46.0'</example>
    OwnerDisplayName TEXT NULL,
        -- <example>'user28'</example>
    LastEditorDisplayName TEXT NULL,
        -- <example>'user28'</example>
    FOREIGN KEY (LastEditorUserId) REFERENCES users(Id),
    FOREIGN KEY (OwnerUserId) REFERENCES users(Id),
    FOREIGN KEY (ParentId) REFERENCES posts(Id)
);

-- Table: tags (1032 rows)
CREATE TABLE tags (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    TagName TEXT NULL,
        -- <example>'bayesian'</example>
    Count INTEGER NULL,
        -- <example>1342</example>
    ExcerptPostId INTEGER NULL,
        -- <example>20258</example>
        -- <fk> -> posts.Id</fk>
    WikiPostId INTEGER NULL,
        -- <example>20257</example>
    FOREIGN KEY (ExcerptPostId) REFERENCES posts(Id)
);

-- Table: users (40325 rows)
CREATE TABLE users (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>-1</example>
    Reputation INTEGER NULL,
        -- <example>1</example>
    CreationDate DATETIME NULL,
        -- <example>'2010-07-19 06:55:26.0'</example>
    DisplayName TEXT NULL,
        -- <example>'Community'</example>
    LastAccessDate DATETIME NULL,
        -- <example>'2010-07-19 06:55:26.0'</example>
    WebsiteUrl TEXT NULL,
        -- <example>'http://meta.stackexchange.com/'</example>
    Location TEXT NULL,
        -- <example>'on the server farm'</example>
    AboutMe TEXT NULL,
        -- <example>'<p>Hi, I'm not really a person.</p>

<p>I'm a back.../92006">Remove abandoned questions</a></li>
</ul>
'</example>
    Views INTEGER NULL,
        -- <example>0</example>
    UpVotes INTEGER NULL,
        -- <example>5007</example>
    DownVotes INTEGER NULL,
        -- <example>1920</example>
    AccountId INTEGER NULL,
        -- <example>-1</example>
    Age INTEGER NULL,
        -- <example>37</example>
    ProfileImageUrl TEXT NULL
        -- <example>'http://i.stack.imgur.com/d1oHX.jpg'</example>
);

-- Table: votes (38930 rows)
CREATE TABLE votes (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <example>1</example>
    PostId INTEGER NULL,
        -- <example>3</example>
        -- <fk> -> posts.Id</fk>
    VoteTypeId INTEGER NULL,
        -- <example>2</example>
    CreationDate DATE NULL,
        -- <example>'2010-07-19'</example>
    UserId INTEGER NULL,
        -- <example>58</example>
        -- <fk> -> users.Id</fk>
    BountyAmount INTEGER NULL,
        -- <example>50</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);
```