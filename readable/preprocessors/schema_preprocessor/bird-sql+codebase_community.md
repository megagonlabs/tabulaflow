```sql
-- Database: codebase_community

/*
Schema: NULLTable: badges
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
CREATE TABLE badges (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Badge identifier — identifies a single badge award record (one row per badge granted to a user).</description>
        -- <example>1</example>
    UserId INTEGER NOT NULL,
        -- <description>Badge recipient user identifier — the Id of the user who earned the badge.</description>
        -- <example>5</example>
        -- <fk> -> users.Id</fk>
    Name TEXT NOT NULL,
        -- <description>Badge name awarded to a user (the title of the badge they received).</description>
        -- <example>'Teacher'</example>
        -- <fk> -> tags.TagName</fk>
    Date DATETIME NOT NULL,
        -- <description>Badge award date — the date and time when the user received the badge (timestamp of the award).</description>
        -- <example>'2010-07-19 19:39:07.0'</example>
    FOREIGN KEY (UserId) REFERENCES users(Id),
    FOREIGN KEY (Name) REFERENCES tags(TagName)
);

/*
Schema: NULLTable: comments
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
CREATE TABLE comments (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Comment identifier — unique id assigned to each comment row in the comments table.</description>
        -- <example>1</example>
    PostId INTEGER NOT NULL,
        -- <description>Reference to the parent post (links to posts.Id).</description>
        -- <example>3</example>
        -- <fk> -> posts.Id</fk>
    Score INTEGER NOT NULL,
        -- <description>Comment score — a numeric measure of community reception; higher values indicate more positive reception (original notes suggested >60 ≈ positive and <60 ≈ negative).</description>
        -- <example>5</example>
    Text TEXT NOT NULL,
        -- <description>Comment body: the full text content of a comment (may contain plain text and occasional HTML or Markdown-like fragments).</description>
        -- <example>'Could be a poster child fo argumentative and subjective.  At the least, need to define 'valuable'.'</example>
    CreationDate DATETIME NOT NULL,
        -- <description>Comment creation timestamp — the date and time when a comment was posted (used to order comments and measure comment activity over time).</description>
        -- <example>'2010-07-19 19:15:52.0'</example>
    UserId INTEGER NULL,
        -- <description>Comment author's user id — identifies the user account that posted the comment.</description>
        -- <example>13</example>
        -- <fk> -> users.Id</fk>
    UserDisplayName TEXT NULL,
        -- <description>Commenter display name — the name shown for the author of the comment, used as a fallback when the comment isn’t linked to a users.Id or to preserve the displayed name at posting (often NULL for comments tied to a user account).</description>
        -- <example>'user28'</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

/*
Schema: NULLTable: postHistory
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
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Post history entry identifier — unique identifier for each record in the postHistory table.</description>
        -- <example>1</example>
    PostHistoryTypeId INTEGER NOT NULL,
        -- <description>Post history type identifier — identifies the kind of history event recorded for the post (maps to a post-history-type lookup).</description>
        -- <example>2</example>
    PostId INTEGER NOT NULL,
        -- <description>Post associated with this history entry — identifies the post whose revision or change the postHistory row records.</description>
        -- <example>1</example>
        -- <fk> -> posts.Id</fk>
    RevisionGUID TEXT NOT NULL,
        -- <description>Revision GUID for the post-history entry — a stable, globally unique identifier that identifies and can be used to correlate a specific revision of a post.</description>
        -- <example>'e58bf7fd-e60f-4c58-a6e4-dfc91cf98a69'</example>
    CreationDate DATETIME NOT NULL,
        -- <description>Post-history entry creation timestamp — the date and time when that post history (revision) record was recorded.</description>
        -- <example>'2010-07-19 19:12:12.0'</example>
    UserId INTEGER NULL,
        -- <description>Author of the post-history entry — identifies the user who performed the action recorded in this postHistory row; NULL when the change isn't attributed to a registered user (e.g., community or deleted account).</description>
        -- <example>8</example>
        -- <fk> -> users.Id</fk>
    Text TEXT NOT NULL,
        -- <description>Post-history revision text — the revision's full post content (e.g., title, body or tag markup), often containing HTML/Markdown, code, LaTeX or XML-like tag fragments.</description>
        -- <example>'How should I elicit prior distributions from experts when fitting a Bayesian model?'</example>
    Comment TEXT NOT NULL,
        -- <description>Edit/comment note for a post-history record that briefly describes the change or rationale (short human-written summaries such as 'deleted 26 characters in body', 'additional information about time series', or 'fixed formatting').</description>
        -- <example>''</example>
    UserDisplayName TEXT NOT NULL,
        -- <description>Display name of the user who made the post-history entry.</description>
        -- <example>''</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

/*
Schema: NULLTable: postLinks
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
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Post link identifier — unique primary key for a postLinks row that records a link between two posts.</description>
        -- <example>108</example>
    CreationDate DATETIME NOT NULL,
        -- <description>Post link creation timestamp indicating when the relationship (link) between two posts was created.</description>
        -- <example>'2010-07-21 14:47:33.0'</example>
    PostId INTEGER NOT NULL,
        -- <description>Source post identifier for the link (references posts.Id).</description>
        -- <example>395</example>
        -- <fk> -> posts.Id</fk>
    RelatedPostId INTEGER NOT NULL,
        -- <description>Related post identifier — the Id of the post referenced by this link (the target post connected to the row's PostId).</description>
        -- <example>173</example>
        -- <fk> -> posts.Id</fk>
    LinkTypeId INTEGER NOT NULL,
        -- <description>link type identifier classifying the relationship between the PostId and RelatedPostId</description>
        -- <example>1</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (RelatedPostId) REFERENCES posts(Id)
);

/*
Schema: NULLTable: posts
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
CREATE TABLE posts (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Post identifier — unique identifier for a post, used to reference posts from other tables (e.g., comments.PostId, votes.PostId, postHistory.PostId, postLinks.PostId/RelatedPostId, tags.ExcerptPostId)</description>
        -- <example>1</example>
    PostTypeId INTEGER NOT NULL,
        -- <description>Post type identifier indicating the category of the post (for example, question, answer, or other post types).</description>
        -- <example>1</example>
    AcceptedAnswerId INTEGER NULL,
        -- <description>Accepted answer post id — Id of the post chosen as this question's accepted answer; null when the post has no accepted answer or isn't a question.</description>
        -- <example>15</example>
    CreaionDate DATETIME NOT NULL,
        -- <description>Post creation date — the timestamp when the post was originally published (column name contains a typo: 'CreaionDate').</description>
        -- <example>'2010-07-19 19:12:12.0'</example>
    Score INTEGER NOT NULL,
        -- <description>Post score (net votes) — the net number of votes (upvotes minus downvotes) received by the post; higher values indicate greater community approval or popularity.</description>
        -- <example>23</example>
    ViewCount INTEGER NULL,
        -- <description>Post view count — total number of times the post page has been viewed; commonly used as a proxy for the post's popularity.</description>
        -- <example>1278</example>
    Body TEXT NULL,
        -- <description>Post body content — the main HTML-formatted content of a post (question or answer), containing markup such as paragraphs, lists, links, code blocks, and images. Often long and may be NULL for system placeholders or deleted posts.</description>
        -- <example>'<p>How should I elicit prior distributions from experts when fitting a Bayesian model?</p>
'</example>
    OwnerUserId INTEGER NULL,
        -- <description>Owner user reference — Id of the registered user who created or owns the post (NULL for anonymous or deleted owners).</description>
        -- <example>8</example>
        -- <fk> -> users.Id</fk>
    LasActivityDate DATETIME NOT NULL,
        -- <description>Last activity timestamp for the post — the most recent date/time when the post saw activity (for example edits, new answers, comments, or other actions affecting the post).</description>
        -- <example>'2010-09-15 21:08:26.0'</example>
    Title TEXT NULL,
        -- <description>Post title — the short, human-readable heading of a post, used as the question's title in listings and search; typically populated for question posts and NULL for answer-type posts.</description>
        -- <example>'Eliciting priors from experts'</example>
    Tags TEXT NULL,
        -- <description>Post tags stored as a single text field with each tag wrapped in angle brackets (e.g. <bayesian><prior><elicitation>).</description>
        -- <example>'<bayesian><prior><elicitation>'</example>
    AnswerCount INTEGER NULL,
        -- <description>Number of answers associated with the post (for question posts — count of answer posts that reference this post as their parent).</description>
        -- <example>5</example>
    CommentCount INTEGER NOT NULL,
        -- <description>Number of comments on this post (total count of comment records attached to the post).</description>
        -- <example>1</example>
    FavoriteCount INTEGER NULL,
        -- <description>Post favorite count — total number of times users marked the post as a favorite; higher values indicate greater popularity.</description>
        -- <example>14</example>
    LastEditorUserId INTEGER NULL,
        -- <description>Id of the user who last edited the post (references users.Id); NULL when the last edit has no linked user (e.g. anonymous or deleted account).</description>
        -- <example>88</example>
        -- <fk> -> users.Id</fk>
    LastEditDate DATETIME NULL,
        -- <description>Post last-edit timestamp — the date and time when the post was most recently edited; null if the post has never been edited. Updated when the post's content or metadata changes and typically paired with LastEditorUserId.</description>
        -- <example>'2010-08-07 17:56:44.0'</example>
    CommunityOwnedDate DATETIME NULL,
        -- <description>Community-owned date — the date when a post was converted to community-owned (community wiki), indicating ownership was transferred from its original author.</description>
        -- <example>'2010-07-19 19:13:28.0'</example>
    ParentId INTEGER NULL,
        -- <description>Parent post reference — Id of the parent post; NULL for root (top-level) posts.</description>
        -- <example>3</example>
        -- <fk> -> posts.Id</fk>
    ClosedDate DATETIME NULL,
        -- <description>Post closed date — the date and time when the post was closed; null if the post remains open. Indicates when a post was closed by moderators or the community (for reasons such as duplicate, off‑topic, or other moderation actions).</description>
        -- <example>'2010-07-19 20:19:46.0'</example>
    OwnerDisplayName TEXT NULL,
        -- <description>Post owner's display name — the public name shown with the post (commonly populated for unregistered or anonymous authors or when a custom name is provided).</description>
        -- <example>'user28'</example>
    LastEditorDisplayName TEXT NULL,
        -- <description>Display name of the post's most recent editor (text shown for the editor, often used when the editor isn't linked to a user account).</description>
        -- <example>'user28'</example>
    FOREIGN KEY (LastEditorUserId) REFERENCES users(Id),
    FOREIGN KEY (OwnerUserId) REFERENCES users(Id),
    FOREIGN KEY (ParentId) REFERENCES posts(Id)
);

/*
Schema: NULLTable: tags
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
CREATE TABLE tags (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique tag identifier.</description>
        -- <example>1</example>
    TagName TEXT NOT NULL,
        -- <description>Tag name — the canonical label identifying a topic or category applied to posts (used for tag lookup and post categorization).</description>
        -- <example>'bayesian'</example>
    Count INTEGER NOT NULL,
        -- <description>Tag usage count — number of posts that include this tag (higher values indicate greater tag popularity).</description>
        -- <example>1342</example>
    ExcerptPostId INTEGER NULL,
        -- <description>Excerpt post id — the post that provides the tag’s excerpt (nullable; references posts.Id).</description>
        -- <example>20258</example>
        -- <fk> -> posts.Id</fk>
    WikiPostId INTEGER NULL,
        -- <description>Tag wiki post identifier linking the tag to its full wiki post (posts.Id).</description>
        -- <example>20257</example>
    FOREIGN KEY (ExcerptPostId) REFERENCES posts(Id)
);

/*
Schema: NULLTable: users
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
CREATE TABLE users (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>User identifier (unique numeric identifier for the user account).</description>
        -- <example>-1</example>
    Reputation INTEGER NOT NULL,
        -- <description>User reputation score indicating the community-earned standing of the account; higher values indicate greater trust or influence.</description>
        -- <example>1</example>
    CreationDate DATETIME NOT NULL,
        -- <description>User account creation timestamp — the moment the user registered their account.</description>
        -- <example>'2010-07-19 06:55:26.0'</example>
    DisplayName TEXT NOT NULL,
        -- <description>User display name — the public name shown on the user's profile and next to their posts; used for attribution and display (may differ from account or real name).</description>
        -- <example>'Community'</example>
    LastAccessDate DATETIME NOT NULL,
        -- <description>Last access time for the user — indicates when the account was last active on the site.</description>
        -- <example>'2010-07-19 06:55:26.0'</example>
    WebsiteUrl TEXT NULL,
        -- <description>User's website URL (personal or professional site linked from the user's profile).</description>
        -- <example>'http://meta.stackexchange.com/'</example>
    Location TEXT NULL,
        -- <description>User location — a user-provided geographic location (free-form); typically a city, region, or country (e.g., 'Europe', 'Degerfors, Sweden', 'East Greenwich, RI'). Values are optional and can be inconsistent.</description>
        -- <example>'on the server farm'</example>
    AboutMe TEXT NULL,
        -- <description>User profile self-introduction — the free-text bio from a user's profile, often including HTML, links and basic formatting.</description>
        -- <example>'<p>Hi, I'm not really a person.</p>

<p>I'm a back.../92006">Remove abandoned questions</a></li>
</ul>
'</example>
    Views INTEGER NOT NULL,
        -- <description>User profile view count — total number of times this user's profile page has been viewed.</description>
        -- <example>0</example>
    UpVotes INTEGER NOT NULL,
        -- <description>User upvote count — total number of upvotes the user has received on their posts and other contributions.</description>
        -- <example>5007</example>
    DownVotes INTEGER NOT NULL,
        -- <description>Count of downvotes received by the user (negative feedback on their posts).</description>
        -- <example>1920</example>
    AccountId INTEGER NOT NULL,
        -- <description>Account identifier for the user's account (the id of the account associated with this user record).</description>
        -- <example>-1</example>
    Age INTEGER NULL,
        -- <description>User age — the user's age in years, often used to segment accounts by life stage (e.g., teen, adult, elder).</description>
        -- <example>37</example>
    ProfileImageUrl TEXT NULL
        -- <description>User profile image URL — the web address used to display the user's avatar (typically an HTTP(S) link to an image file, e.g. http://i.stack.imgur.com/d1oHX.jpg).</description>
        -- <example>'http://i.stack.imgur.com/d1oHX.jpg'</example>
);

/*
Schema: NULLTable: votes
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
CREATE TABLE votes (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Vote identifier — unique identifier for each vote in the votes table.</description>
        -- <example>1</example>
    PostId INTEGER NOT NULL,
        -- <description>Identifier of the post that received the vote (references posts.Id).</description>
        -- <example>3</example>
        -- <fk> -> posts.Id</fk>
    VoteTypeId INTEGER NOT NULL,
        -- <description>Vote type identifier indicating the kind of vote (maps to the system’s vote-type codes such as upvote, downvote, accepted answer, bounty).</description>
        -- <example>2</example>
    CreationDate DATE NOT NULL,
        -- <description>Vote creation date — the calendar date when the vote was recorded (i.e., the day the vote was cast).</description>
        -- <example>'2010-07-19'</example>
    UserId INTEGER NULL,
        -- <description>Id of the user who cast the vote; null indicates the vote is not associated with a specific user (for example, anonymous or system-generated votes).</description>
        -- <example>58</example>
        -- <fk> -> users.Id</fk>
    BountyAmount INTEGER NULL,
        -- <description>bounty amount — the amount awarded for a bounty vote (set when VoteTypeId represents a bounty); NULL for votes that are not bounty awards.</description>
        -- <example>50</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);
```