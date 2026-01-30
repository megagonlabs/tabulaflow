```sql
-- Database: codebase_community

-- Table: badges (79851 rows)
CREATE TABLE badges (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    UserId INTEGER,  -- e.g. 5; FK -> users.Id
    Name TEXT,  -- e.g. 'Teacher'
    Date DATETIME,  -- e.g. '2010-07-19 19:39:07.0'
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

-- Table: comments (174285 rows)
CREATE TABLE comments (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    PostId INTEGER,  -- e.g. 3; FK -> posts.Id
    Score INTEGER,  -- e.g. 5
    Text TEXT,  -- e.g. 'Could be a poster child fo argumentative and subjective.  At the least, need to define 'valuable'.'
    CreationDate DATETIME,  -- e.g. '2010-07-19 19:15:52.0'
    UserId INTEGER,  -- e.g. 13; FK -> users.Id
    UserDisplayName TEXT,  -- e.g. 'user28'
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

-- Table: postHistory (303155 rows)
CREATE TABLE postHistory (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    PostHistoryTypeId INTEGER,  -- e.g. 2
    PostId INTEGER,  -- e.g. 1; FK -> posts.Id
    RevisionGUID TEXT,  -- e.g. 'e58bf7fd-e60f-4c58-a6e4-dfc91cf98a69'
    CreationDate DATETIME,  -- e.g. '2010-07-19 19:12:12.0'
    UserId INTEGER,  -- e.g. 8; FK -> users.Id
    Text TEXT,  -- e.g. 'How should I elicit prior distributions from experts when fitting a Bayesian model?'
    Comment TEXT,  -- e.g. ''
    UserDisplayName TEXT,  -- e.g. ''
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

-- Table: postLinks (11102 rows)
CREATE TABLE postLinks (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 108
    CreationDate DATETIME,  -- e.g. '2010-07-21 14:47:33.0'
    PostId INTEGER,  -- e.g. 395; FK -> posts.Id
    RelatedPostId INTEGER,  -- e.g. 173; FK -> posts.Id
    LinkTypeId INTEGER,  -- e.g. 1
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (RelatedPostId) REFERENCES posts(Id)
);

-- Table: posts (91966 rows)
CREATE TABLE posts (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    PostTypeId INTEGER,  -- e.g. 1
    AcceptedAnswerId INTEGER,  -- e.g. 15
    CreaionDate DATETIME,  -- e.g. '2010-07-19 19:12:12.0'
    Score INTEGER,  -- e.g. 23
    ViewCount INTEGER,  -- e.g. 1278
    Body TEXT,  -- e.g. '<p>How should I elicit prior distributions from experts when fitting a Bayesian model?</p>
'
    OwnerUserId INTEGER,  -- e.g. 8; FK -> users.Id
    LasActivityDate DATETIME,  -- e.g. '2010-09-15 21:08:26.0'
    Title TEXT,  -- e.g. 'Eliciting priors from experts'
    Tags TEXT,  -- e.g. '<bayesian><prior><elicitation>'
    AnswerCount INTEGER,  -- e.g. 5
    CommentCount INTEGER,  -- e.g. 1
    FavoriteCount INTEGER,  -- e.g. 14
    LastEditorUserId INTEGER,  -- e.g. 88; FK -> users.Id
    LastEditDate DATETIME,  -- e.g. '2010-08-07 17:56:44.0'
    CommunityOwnedDate DATETIME,  -- e.g. '2010-07-19 19:13:28.0'
    ParentId INTEGER,  -- e.g. 3; FK -> posts.Id
    ClosedDate DATETIME,  -- e.g. '2010-07-19 20:19:46.0'
    OwnerDisplayName TEXT,  -- e.g. 'user28'
    LastEditorDisplayName TEXT,  -- e.g. 'user28'
    FOREIGN KEY (LastEditorUserId) REFERENCES users(Id),
    FOREIGN KEY (OwnerUserId) REFERENCES users(Id),
    FOREIGN KEY (ParentId) REFERENCES posts(Id)
);

-- Table: tags (1032 rows)
CREATE TABLE tags (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    TagName TEXT,  -- e.g. 'bayesian'
    Count INTEGER,  -- e.g. 1342
    ExcerptPostId INTEGER,  -- e.g. 20258; FK -> posts.Id
    WikiPostId INTEGER,  -- e.g. 20257
    FOREIGN KEY (ExcerptPostId) REFERENCES posts(Id)
);

-- Table: users (40325 rows)
CREATE TABLE users (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. -1
    Reputation INTEGER,  -- e.g. 1
    CreationDate DATETIME,  -- e.g. '2010-07-19 06:55:26.0'
    DisplayName TEXT,  -- e.g. 'Community'
    LastAccessDate DATETIME,  -- e.g. '2010-07-19 06:55:26.0'
    WebsiteUrl TEXT,  -- e.g. 'http://meta.stackexchange.com/'
    Location TEXT,  -- e.g. 'on the server farm'
    AboutMe TEXT,  -- e.g. '<p>Hi, I'm not really a person.</p>

<p>I'm a back.../92006">Remove abandoned questions</a></li>
</ul>
'
    Views INTEGER,  -- e.g. 0
    UpVotes INTEGER,  -- e.g. 5007
    DownVotes INTEGER,  -- e.g. 1920
    AccountId INTEGER,  -- e.g. -1
    Age INTEGER,  -- e.g. 37
    ProfileImageUrl TEXT  -- e.g. 'http://i.stack.imgur.com/d1oHX.jpg'
);

-- Table: votes (38930 rows)
CREATE TABLE votes (
    Id INTEGER NOT NULL PRIMARY KEY,  -- e.g. 1
    PostId INTEGER,  -- e.g. 3; FK -> posts.Id
    VoteTypeId INTEGER,  -- e.g. 2
    CreationDate DATE,  -- e.g. '2010-07-19'
    UserId INTEGER,  -- e.g. 58; FK -> users.Id
    BountyAmount INTEGER,  -- e.g. 50
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);
```