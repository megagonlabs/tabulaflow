```sql
-- Database: codebase_community

-- Table: badges (79851 rows)
CREATE TABLE badges (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Badge identifier — unique identifier for each badge row in the table.</description>
        -- <example>1</example>
    UserId INTEGER NULL,
        -- <description>User id for badge owner — identifies the user who earned the badge; links to users.Id (foreign key), is always present (no NULLs) and is not unique (many badges can belong to the same user).</description>
        -- <example>5</example>
        -- <fk> -> users.Id</fk>
    Name TEXT NULL,
        -- <description>Badge name awarded to a user — identifies which badge the user earned (e.g., Student, Supporter, Editor).</description>
        -- <example>'Teacher'</example>
    Date DATETIME NULL,
        -- <description>Badge award timestamp — the date and time when the user received this badge (records present for all rows; range observed 2010-07-19 to 2014-09-14).</description>
        -- <example>'2010-07-19 19:39:07.0'</example>
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

-- Table: comments (174285 rows)
CREATE TABLE comments (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique comment identifier</description>
        -- <example>1</example>
    PostId INTEGER NULL,
        -- <description>Post id referenced by the comment (the post this comment is attached to). Contains no nulls; a small number of rows reference posts that do not exist.</description>
        -- <example>3</example>
        -- <fk> -> posts.Id</fk>
    Score INTEGER NULL,
        -- <description>Comment upvote count — the number of upvotes a comment has received. Most comments have a score of 0; in this dataset scores range from 0 up to 90 with a low average (~0.39).</description>
        -- <example>5</example>
    Text TEXT NULL,
        -- <description>Comment content — the full text of a comment (the comment body, may include inline code or HTML). Typical length ~230 characters (range 7–667); no empty values in this table.</description>
        -- <example>'Could be a poster child fo argumentative and subjective.  At the least, need to define 'valuable'.'</example>
    CreationDate DATETIME NULL,
        -- <description>Comment creation timestamp — the date and time the comment was posted (no missing values; range in this dataset: 2009-02-02 to 2014-09-14).</description>
        -- <example>'2010-07-19 19:15:52.0'</example>
    UserId INTEGER NULL,
        -- <description>Comment author's user id (NULL when the comment was posted anonymously or the user account is unavailable).</description>
        -- <example>13</example>
        -- <fk> -> users.Id</fk>
    UserDisplayName TEXT NULL,
        -- <description>Comment author's display name — the display name provided for the user who posted the comment. Mostly empty (present in ~1.6% of rows); used to record a textual name (often for unlinked/anonymous commenters) when UserId is not available.</description>
        -- <example>'user28'</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);

-- Table: postHistory (303155 rows)
CREATE TABLE postHistory (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Post history entry identifier</description>
        -- <example>1</example>
    PostHistoryTypeId INTEGER NULL,
        -- <description>Post-history event type identifier — integer code indicating the kind of change recorded for a post (e.g., creation, edit, title/tag change).</description>
        -- <example>2</example>
        -- <fk> -> PostHistoryTypes.Id</fk>
    PostId INTEGER NULL,
        -- <description>Referenced post for this postHistory entry — the post whose revision or change the history row records.</description>
        -- <example>1</example>
        -- <fk> -> posts.Id</fk>
    RevisionGUID TEXT NULL,
        -- <description>Revision GUID that identifies a specific post-history revision (UUID used to group rows belonging to the same revision).</description>
        -- <example>'e58bf7fd-e60f-4c58-a6e4-dfc91cf98a69'</example>
    CreationDate DATETIME NULL,
        -- <description>Post-history creation timestamp — the timestamp when a post-history (revision/event) record was recorded.</description>
        -- <example>'2010-07-19 19:12:12.0'</example>
    UserId INTEGER NULL,
        -- <description>User who made the post-history entry; many rows are NULL (≈7%) and a sentinel value (-1) appears for some system/community edits.</description>
        -- <example>8</example>
        -- <fk> -> users.Id</fk>
    Text TEXT NULL,
        -- <description>Post revision text — the full textual content recorded for a post-history entry (the detailed content of a revision). May contain HTML/markup, code snippets, tags, titles or other free-form text captured when the post was edited.</description>
        -- <example>'How should I elicit prior distributions from experts when fitting a Bayesian model?'</example>
    Comment TEXT NULL,
        -- <description>Post-history edit comment — short free-text note describing the revision (e.g., summaries of changes like “deleted 26 characters in body”, “added 115 characters in body”, tag edits, or brief explanatory notes and links).</description>
        -- <example>''</example>
    UserDisplayName TEXT NULL,
        -- <description>Display name of the user who made the post (often empty for deleted/anonymous entries).</description>
        -- <example>''</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id),
    FOREIGN KEY (PostHistoryTypeId) REFERENCES PostHistoryTypes(Id)
);

-- Table: postLinks (11102 rows)
CREATE TABLE postLinks (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Post link identifier — unique identifier for a record in the postLinks table.</description>
        -- <example>108</example>
    CreationDate DATETIME NULL,
        -- <description>Creation timestamp of the post link, recording when the link record was added (used to order or filter post-link activity).</description>
        -- <example>'2010-07-21 14:47:33.0'</example>
    PostId INTEGER NULL,
        -- <description>Source post identifier for the link — the post that contains the link to RelatedPostId (references posts.Id).</description>
        -- <example>395</example>
        -- <fk> -> posts.Id</fk>
    RelatedPostId INTEGER NULL,
        -- <description>Related post identifier — the posts.Id referenced by this postLinks record; together with PostId and LinkTypeId it specifies which other post is linked (e.g., duplicate, related).</description>
        -- <example>173</example>
        -- <fk> -> posts.Id</fk>
    LinkTypeId INTEGER NULL,
        -- <description>Post link type identifier — enumerated code indicating the kind of relationship between PostId and RelatedPostId (observed values: 1 and 3; 1 is by far the most common).</description>
        -- <example>1</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (RelatedPostId) REFERENCES posts(Id)
);

-- Table: posts (91966 rows)
CREATE TABLE posts (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Post identifier uniquely identifying each post record.</description>
        -- <example>1</example>
    PostTypeId INTEGER NULL,
        -- <description>Post type code indicating the kind of post (primary values: 1 = question, 2 = answer); other small integer codes represent rarer, non-question/answer post types.</description>
        -- <example>1</example>
    AcceptedAnswerId INTEGER NULL,
        -- <description>Accepted answer post id — identifies which answer post (posts.Id) was accepted for a question; NULL when no answer has been accepted. Almost all non-null values reference existing posts.</description>
        -- <example>15</example>
    CreaionDate DATETIME NULL,
        -- <description>Post creation timestamp (records when a post was created; column name is misspelled as 'CreaionDate').</description>
        -- <example>'2010-07-19 19:12:12.0'</example>
    Score INTEGER NULL,
        -- <description>Post score — the net votes on a post (upvotes minus downvotes); can be negative.</description>
        -- <example>23</example>
    ViewCount INTEGER NULL,
        -- <description>Total number of views for the post — an indicator of the post's popularity. Present for ~46.7% of rows (many posts have NULL); observed values range from 1 to 175,495 (mean ≈ 566).</description>
        -- <example>1278</example>
    Body TEXT NULL,
        -- <description>Post body — the main content of a post, stored as HTML-formatted text containing the question or answer content; may include paragraphs, lists, links, images, code blocks and other inline HTML markup.</description>
        -- <example>'<p>How should I elicit prior distributions from experts when fitting a Bayesian model?</p>
'</example>
    OwnerUserId INTEGER NULL,
        -- <description>Post owner user id — identifier of the user who created/owns the post. About 1.5% of posts have a NULL owner (1,392 of 91,966); there are 21,979 distinct non-null owners and all non-null values reference existing users.</description>
        -- <example>8</example>
        -- <fk> -> users.Id</fk>
    LasActivityDate DATETIME NULL,
        -- <description>Last activity timestamp for the post (column name is misspelled as 'LasActivityDate'); records the most recent activity time for the post (edits, answers, comments, etc.).</description>
        -- <example>'2010-09-15 21:08:26.0'</example>
    Title TEXT NULL,
        -- <description>Post title — the human-readable title for a post (used for question posts; null for many answer rows). Present in 42,912 of 91,966 rows (~46.7%); title lengths range from 15 to 154 characters (avg ≈57).</description>
        -- <example>'Eliciting priors from experts'</example>
    Tags TEXT NULL,
        -- <description>Post tag list — a single string of one or more tag names wrapped in angle brackets (e.g. <r><regression>); many posts have no tags (≈49,054 of 91,966) and there are many distinct tag combinations.</description>
        -- <example>'<bayesian><prior><elicitation>'</example>
    AnswerCount INTEGER NULL,
        -- <description>Number of answers for the post — total number of answers; many rows are NULL (49,054 of 91,966). Among non-null values (42,912) the range is 0–136 (mean ≈1.11); most frequent values are 1 (17,869) and 0 (13,911).</description>
        -- <example>5</example>
    CommentCount INTEGER NULL,
        -- <description>Comment count for the post — total number of comments attached to the post. Values are typically small (many posts have 0–2 comments); about 42% of posts have 0 comments, the observed range is 0–45 and the mean is ≈1.9.</description>
        -- <example>1</example>
    FavoriteCount INTEGER NULL,
        -- <description>Number of times the post was marked as a favorite — total favorites received. Most posts have no value here (only ~14% of rows populated); among populated values the range is 0–233 with a mean ≈2.5, so counts are sparse and heavily skewed toward small integers (1 is the most common).</description>
        -- <example>14</example>
    LastEditorUserId INTEGER NULL,
        -- <description>Last editor user id — identifier of the user account who last edited the post; NULL when the post has no registered last-editor (e.g., never edited or edited anonymously).</description>
        -- <example>88</example>
        -- <fk> -> users.Id</fk>
    LastEditDate DATETIME NULL,
        -- <description>Timestamp of the post's most recent edit — NULL if the post was never edited. In this dataset 46,934 of 91,966 rows are NULL (≈51%); non-NULL values range from 2010-07-19 to 2014-09-14.</description>
        -- <example>'2010-08-07 17:56:44.0'</example>
    CommunityOwnedDate DATETIME NULL,
        -- <description>Date the post became community-owned (community wiki); null if the post was never converted to community ownership.</description>
        -- <example>'2010-07-19 19:13:28.0'</example>
    ParentId INTEGER NULL,
        -- <description>Parent post id referencing posts.Id — the parent question's post id for answers/child posts; null for top-level posts (questions).</description>
        -- <example>3</example>
        -- <fk> -> posts.Id</fk>
    ClosedDate DATETIME NULL,
        -- <description>Post closed timestamp — date and time when a post was closed (NULL for posts that are still open). Applies to question posts; 1,610 posts in this dataset have a non‑null ClosedDate.</description>
        -- <example>'2010-07-19 20:19:46.0'</example>
    OwnerDisplayName TEXT NULL,
        -- <description>Owner display name — free-text snapshot of the post owner's display name; typically populated for anonymous/unregistered posts and occasionally retained alongside an OwnerUserId (2,509 non-null values, ~1,388 of which lack an OwnerUserId).</description>
        -- <example>'user28'</example>
    LastEditorDisplayName TEXT NULL,
        -- <description>Display name of the post’s last editor (free-text). Usually null — present in ~465 of 91,966 rows (~0.5%) — and duplicates the linked LastEditorUserId when that ID exists, so it is not a reliable identifier for the editor.</description>
        -- <example>'user28'</example>
    FOREIGN KEY (LastEditorUserId) REFERENCES users(Id),
    FOREIGN KEY (OwnerUserId) REFERENCES users(Id),
    FOREIGN KEY (ParentId) REFERENCES posts(Id)
);

-- Table: tags (1032 rows)
CREATE TABLE tags (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Tag identifier used to reference a tag row.</description>
        -- <example>1</example>
    TagName TEXT NULL,
        -- <description>Tag name — the canonical textual label that identifies a tag used to categorize posts.</description>
        -- <example>'bayesian'</example>
    Count INTEGER NULL,
        -- <description>Tag usage count — the number of posts that include this tag (higher values indicate a more widely used/popular tag).</description>
        -- <example>1342</example>
    ExcerptPostId INTEGER NULL,
        -- <description>Excerpt post ID — the post used as this tag's excerpt/wiki (null when the tag has no excerpt). Some tags reference the same post: in this dataset 596 tags reference posts and 436 are null; one referenced post appears to be missing from posts (orphan).</description>
        -- <example>20258</example>
        -- <fk> -> posts.Id</fk>
    WikiPostId INTEGER NULL,
        -- <description>Tag wiki post id — the posts.Id of this tag’s wiki/excerpt page (nullable); links a tag to its wiki entry. Present for about 58% of tags.</description>
        -- <example>20257</example>
    FOREIGN KEY (ExcerptPostId) REFERENCES posts(Id)
);

-- Table: users (40325 rows)
CREATE TABLE users (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>User identifier — unique numeric id assigned to each user; includes special/system accounts (example: -1 for the Community/system user).</description>
        -- <example>-1</example>
    Reputation INTEGER NULL,
        -- <description>User reputation score representing the cumulative community assessment of a user's contributions; higher values indicate greater trust, privileges, and influence.</description>
        -- <example>1</example>
    CreationDate DATETIME NULL,
        -- <description>User account creation timestamp (when the user registered).</description>
        -- <example>'2010-07-19 06:55:26.0'</example>
    DisplayName TEXT NULL,
        -- <description>User display name shown publicly on the user's profile and alongside their posts and comments — a human-readable name that is not guaranteed to be unique.</description>
        -- <example>'Community'</example>
    LastAccessDate DATETIME NULL,
        -- <description>Timestamp of the user's most recent site access (last time the account was used); populated for all users — values in this dataset range from 2010-07-19 to 2014-09-14.</description>
        -- <example>'2010-07-19 06:55:26.0'</example>
    WebsiteUrl TEXT NULL,
        -- <description>User website URL — user-provided personal or profile link (often a full HTTP(S) address).</description>
        -- <example>'http://meta.stackexchange.com/'</example>
    Location TEXT NULL,
        -- <description>User-provided free-text location (place name such as city, region, or country); optional and often inconsistent.</description>
        -- <example>'on the server farm'</example>
    AboutMe TEXT NULL,
        -- <description>User biography (HTML-formatted): a free-text self-introduction/profile that often contains HTML markup (paragraphs, lists, links) and plain text. Many rows are empty — about 9,379 of 40,325 users (≈23%) have non-empty bios; average populated length ≈220 characters and maximum ≈3,900 characters.</description>
        -- <example>'<p>Hi, I'm not really a person.</p>

<p>I'm a back.../92006">Remove abandoned questions</a></li>
</ul>
'</example>
    Views INTEGER NULL,
        -- <description>User profile view count — total number of times the user's profile page has been viewed.</description>
        -- <example>0</example>
    UpVotes INTEGER NULL,
        -- <description>User upvote count — the number of upvote actions the user has cast on posts across the site.</description>
        -- <example>5007</example>
    DownVotes INTEGER NULL,
        -- <description>User downvote count — total number of downvotes the user has received (higher values indicate more negative feedback).</description>
        -- <example>1920</example>
    AccountId INTEGER NULL,
        -- <description>Network account identifier for the user — the account id that identifies the user's global/account-level profile (used to associate this site profile with a central account).</description>
        -- <example>-1</example>
    Age INTEGER NULL,
        -- <description>User age in years (self‑reported); commonly missing — often used for simple demographic grouping (e.g., teenager 13–18, adult 19–65, elder >65).</description>
        -- <example>37</example>
    ProfileImageUrl TEXT NULL
        -- <description>Profile image URL (user avatar) — the web address of the user's profile picture (commonly hosted on i.stack.imgur.com). Many accounts have no image; roughly 41% of rows contain a non-empty URL.</description>
        -- <example>'http://i.stack.imgur.com/d1oHX.jpg'</example>
);

-- Table: votes (38930 rows)
CREATE TABLE votes (
    Id INTEGER NOT NULL PRIMARY KEY,
        -- <description>Unique identifier for a vote record.</description>
        -- <example>1</example>
    PostId INTEGER NULL,
        -- <description>Post referenced by the vote — identifies which post the vote applies to.</description>
        -- <example>3</example>
        -- <fk> -> posts.Id</fk>
    VoteTypeId INTEGER NULL,
        -- <description>Vote-type code identifying the category of a vote (maps to the site’s canonical vote-type lookup such as upvote, downvote, accept, bounty).</description>
        -- <example>2</example>
    CreationDate DATE NULL,
        -- <description>Vote creation date — the calendar day on which each vote was recorded (dataset range: 2010-07-19 to 2011-05-01).</description>
        -- <example>'2010-07-19'</example>
    UserId INTEGER NULL,
        -- <description>Voter user id — the users.Id of the account that cast the vote; many votes are anonymous/system-generated so the column is NULL for most rows (35,505 of 38,930, ~91%), with 509 distinct non-null users.</description>
        -- <example>58</example>
        -- <fk> -> users.Id</fk>
    BountyAmount INTEGER NULL,
        -- <description>Bounty amount awarded with a vote (points); the numeric bounty attached to a vote when present — sparsely populated and typically one of a few fixed amounts.</description>
        -- <example>50</example>
    FOREIGN KEY (PostId) REFERENCES posts(Id),
    FOREIGN KEY (UserId) REFERENCES users(Id)
);
```